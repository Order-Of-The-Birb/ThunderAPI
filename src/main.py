import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from json import loads
from logging.handlers import TimedRotatingFileHandler
from os import getenv, path

from fastapi import FastAPI, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from uvicorn import run as uvicorn_run

import utils
import utils.cache as Cache
import utils.connection.network as Network
from api import router
from api.shared import limiter
from config import DEFAULT_NETWORK_CFG, HOST, LOGS_DIR, PORT, SWAGGER_CSS, SWAGGER_JS
from utils import newsManager, users_auth
from utils.auth import ServerAuth, scheduler
from utils.connection import _populate_serverlist
from utils.connection.blk_utils import Decompress
from utils.geo import update_db

logger = logging.getLogger()

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
	await users_auth.start()
	await Network.start()
	utils.server_auth = await ServerAuth.start()

	await users_auth._refresh() # Clean up old entries on startup

	#region Gaijin servers config init
	content = {}
	try:
		async with Network.get("https://public-configs-warthunder-gcore.cdn.gaijin.net/production/network.blk", timeout=5) as _resp:
			temp = await Network.handle_response(_resp, False)
			content = Decompress(temp)["production"]
	except Exception:
		logger.warning("Failed to fetch server from first server, trying secondary server")
		try:
			async with Network.get("https://public-configs.warthunder.com/production/network.blk", timeout=5) as _resp:
				temp = await Network.handle_response(_resp, False)
				content = Decompress(temp)["production"]
		except Exception:
			pass
	if not content:
		logger.warning("Failed to fetch server list, using default server list")
		content = loads(DEFAULT_NETWORK_CFG.read_text())
	_populate_serverlist(content)
	del content
	#endregion

	Cache.LONG_RUNNING = (
		asyncio.create_task(newsManager.mainloop()),
		asyncio.create_task(update_db())
	)

	await Cache.start()

	try:
		yield
	finally:
		await Cache.stop()

		scheduler.shutdown()
		await users_auth.close()
		await Network.close()


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

class CloudflareClientIPMiddleware:
	"""Rewrite the client address from Cloudflare's CF-Connecting-IP header."""

	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		if scope["type"] in ("http", "websocket"):
			for name, value in scope.get("headers", []):
				if name == b"cf-connecting-ip":
					client = scope.get("client")
					scope["client"] = (value.decode("latin1").strip(), client[1] if client else 0)
					break
		await self.app(scope, receive, send)

app.include_router(router)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CloudflareClientIPMiddleware)

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

	for ep_path in openapi_schema["paths"].values():
		for method in ep_path.values():
			method["responses"].pop("422", None)

	for route in app.routes:
		route_path = getattr(route, "path", None)
		if route_path is None:
			continue

		ws_data = websockets.get(route_path)
		if ws_data is None:
			continue

		openapi_schema["paths"].setdefault(route_path, {})
		openapi_schema["paths"][route_path]["x-websocket"] = ws_data.to_json()

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

	websocket_script = SWAGGER_JS.read_text()
	html = html.replace("</body>", "<script>"+websocket_script+"</script></body>")

	websocket_css = SWAGGER_CSS.read_text()
	html = html.replace("</head>", "<style>"+websocket_css+"</style></head>")

	swagger_docs = html
	return HTMLResponse(html)
#endregion

def main():
	# region Logging

	LOGS_DIR.mkdir(mode=0o755, exist_ok=True, parents=True)

	#region Handler and Formatter
	def log_namer(default_name:str):
		dirname = path.dirname(default_name)
		filename = path.basename(default_name)
		_, _, date = filename.rpartition(".")
		return path.join(dirname, f"{date}.log")
	handler = TimedRotatingFileHandler(LOGS_DIR / "latest.log", when="midnight", interval=1, utc=True, backupCount=5)
	handler.suffix = "%Y-%m-%d"
	formatter = logging.Formatter("%(asctime)s:%(name)-30s:%(funcName)-15s:%(lineno)-3d:%(levelname)-7s:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
	handler.setFormatter(formatter)
	handler.namer = log_namer
	logger.addHandler(handler)
	logger.propagate = False

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	logger.addHandler(console_handler)
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

		uvicorn_logger.addHandler(handler)
		uvicorn_logger.setLevel(level)
		uvicorn_logger.propagate = False
	#endregion
	# endregion

	try:
		uvicorn_run(app, host=HOST, port=PORT)
	except Exception:
		logger.exception("An uncaught error occurred during runtime")
	finally:
		logger.info("Shutting down")

if __name__ == '__main__':
	main()
