import logging, asyncio
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger()

if not load_dotenv(".env"):
	logger.warning(".env not found, copying .example.env")
	example_env = (Path(__file__).parent / ".example.env")
	dotenv = Path(__file__).parent / ".env"
	example_env.copy(dotenv)
	if not load_dotenv(".env"):
		raise RuntimeError("Could not load .env data")
	dotenv.chmod(0o600)
else:
	(Path(__file__).parent / ".env").chmod(0o600)

from logging.handlers import TimedRotatingFileHandler
from fastapi import FastAPI, status
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, HTMLResponse
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from uvicorn import run as uvicorn_run
from os import getenv, path
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from json import loads

from utils import users_cache, networkManager, newsManager
from utils.geo import update_db
from tools import _populate_serverlist
from tools.blk_utils import Decompress
from api import router
from api.shared import limiter

logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

tags_metadata = [
	{
		"name": "authentication",
		"description": "Operations used to authenticate with the API, and get or refresh a token to use in other endpoints."
	},
	{
		"name": "clans",
		"description": "Operations correlating to clans/squadrons.",
	},
	{
		"name": "general",
		"description": "Operations to get general information.",
	},
	#{
	#    "name": "units",
	#    "description": "Operations correlating to getting information about the units of the game War Thunder.",
	#},
	{
		"name": "users",
		"description": "Operations to get information about the users/players.",
	},
	{
		"name": "replays",
		"description": "Operations to get information about replays.",
	},
	{
		"name": "marketplace",
		"description": "Operations to get information about the marketplace.",
	}
]

@asynccontextmanager
async def lifespan(app: FastAPI):
	await users_cache.start()
	await networkManager.start()

	#region Gaijin servers config init
	content = {}
	try:
		async with networkManager.get("https://public-configs-warthunder-gcore.cdn.gaijin.net/production/network.blk", timeout=5) as _resp:
			temp = await networkManager.handle_response(_resp, False)
			content = Decompress(temp)["production"]
	except Exception:
		logger.warning("Failed to fetch server from first server, trying secondary server")
		try:
			async with networkManager.get("https://public-configs.warthunder.com/production/network.blk", timeout=5) as _resp:
				temp = await networkManager.handle_response(_resp, False)
				content = Decompress(temp)["production"]
		except Exception:
			pass
	if not content:
		logger.warning(f"Failed to fetch server list, using default server list")
		content = loads((Path(__file__).parent / "tools" / "default_network_cfg.json").read_text())
	_populate_serverlist(content)
	del content
	#endregion

	newsManager.task = asyncio.create_task(newsManager.mainloop())
	geolocation_task = asyncio.create_task(update_db())

	try:
		yield
	finally:
		newsManager.task.cancel()
		geolocation_task.cancel()
		try:
			await newsManager.task
		except asyncio.CancelledError:
			pass
		try:
			await geolocation_task
		except (asyncio.CancelledError, RuntimeError):
			pass
		await users_cache.close()
		await networkManager.close()


debug = int(getenv("DEBUG_MODE", "0")) == 1
app = FastAPI(
	title="ThunderAPI",
	description="API to retrieve War Thunder data.",
	version="1.0.0",
	openapi_tags=tags_metadata,
	lifespan=lifespan,
	redoc_url=None,
	docs_url=None,
	responses={
		status.HTTP_401_UNAUTHORIZED: {"description": "User token was not found, user is not authenticated or login expired"}
	},
	contact={
		"discord": "https://discord.gg/wsn9Wcqqym",
	},
	debug=debug
)

#region Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(
	RateLimitExceeded, 
	lambda request, exc: (
		logging.warning(f"Rate limit exceeded for {get_remote_address(request)}"), 
		JSONResponse({"detail": "Rate limit exceeded"}, status_code=status.HTTP_429_TOO_MANY_REQUESTS)
	)[1]
)
#endregion
app.include_router(router)
app.add_middleware(SlowAPIMiddleware)

#region Modify OpenAPI schema
@dataclass(slots=True)
class WebSocketInfo:
	tags: list[str]
	summary: str
	description: str

	def to_json(self):
		return asdict(self)
websockets: dict[str, WebSocketInfo] = {
	"/v1/news_ws": WebSocketInfo(
		tags = ["general"],
		summary = "Live news feed",
		description = "Sends the newest news article every time a new one is posted"
	)
}
def custom_openapi():
	if app.openapi_schema: # If already modified
		return app.openapi_schema

	openapi_schema = get_openapi(
		title=app.title,
		version=app.version,
		description=app.description,
		routes=app.routes,
		tags=app.openapi_tags,
	)

	for path in openapi_schema["paths"].values():
		for method in path.values():
			method["responses"].pop("422", None)

	for route in app.routes:
		ws_data = websockets.get(route.path)
		if ws_data is None:
			continue

		openapi_schema["paths"].setdefault(route.path, {})
		openapi_schema["paths"][route.path]["x-websocket"] = ws_data.to_json()

	app.openapi_schema = openapi_schema
	return app.openapi_schema

app.openapi = custom_openapi
#endregion

#region Modify Documentation page
swagger_docs = None
@app.get("/docs", include_in_schema=False)
@app.get("/", include_in_schema=False)
def custom_swagger_ui():
	global swagger_docs
	if swagger_docs:
		return HTMLResponse(swagger_docs)

	page = get_swagger_ui_html(
		openapi_url=app.openapi_url,
		title=f"{app.title} - Swagger UI",
		swagger_ui_parameters={"defaultModelsExpandDepth": -1},
	)

	html = page.body.decode("utf-8")

	websocket_script = (Path(__file__).parent / "swagger_ui_modify.js").read_text()
	html = html.replace("</body>", "<script>"+websocket_script+"</script></body>")

	websocket_css = (Path(__file__).parent / "swagger_ui_modify.css").read_text()
	html = html.replace("</head>", "<style>"+websocket_css+"</style></head>")

	swagger_docs = html
	return HTMLResponse(html)
#endregion

def main():
	# region Logging

	logFolder = Path(__file__).parent / "logs"
	logFolder.mkdir(mode=0o755, exist_ok=True)

	#region Handler and Formatter
	def log_namer(default_name:str):
		dirname = path.dirname(default_name)
		filename = path.basename(default_name)
		_, _, date = filename.rpartition(".")
		return path.join(dirname, f"{date}.log")
	handler = TimedRotatingFileHandler(logFolder / "latest.log", when="midnight", interval=1, utc=True, backupCount=5)
	handler.suffix = "%Y-%m-%d"
	formatter = logging.Formatter(f"%(asctime)s:%(name)-30s:%(funcName)-15s:%(lineno)-3d:%(levelname)-7s:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
	handler.setFormatter(formatter)
	handler.namer = log_namer
	logger.addHandler(handler)
	logger.propagate = False
	#endregion

	#region Log level
	loglevel = getenv("LOG_LEVEL", "INFO")
	match loglevel.upper().strip():
		case "DEBUG":
			level = logging.DEBUG
		case "INFO":
			level = logging.INFO
		case "WARN", "WARNING":
			level = logging.WARNING
		case "ERROR":
			level = logging.ERROR
		case "FATAL", "CRITICAL":
			level = logging.CRITICAL
		case _:
			logger.warning("Invalid logging level entered, defaulting to 'INFO'")
			level = logging.INFO
	logger.setLevel(level)
	#endregion
	#region Replace uvicorn logger
	for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
		uvicorn_logger = logging.getLogger(name)

		uvicorn_logger.handlers.clear()

		uvicorn_logger.setLevel(logging.INFO)
		uvicorn_logger.propagate = True
	#endregion
	# endregion

	try:
		port = int(getenv("PORT", "8001"))
	except ValueError:
		raise EnvironmentError("Environment variable \"PORT\" is not a valid integer")
	if not 1 <= port <= 65535:
		raise EnvironmentError("Invalid port number provided")
	host = getenv("HOST", "127.0.0.1")
	logger.info(f"Starting up on {host}:{port}")
	try:
		uvicorn_run(app, host=host, port=port)
	except Exception:
		logger.exception("An uncaught error occurred during runtime")
	finally:
		logger.info("Shutting down")

if __name__ == '__main__':
	main()