from asyncio import to_thread
from typing import Any, TYPE_CHECKING
from fastapi import HTTPException, status
from logging import getLogger
from aiohttp import ClientResponse, ClientSession
from requests import get as req_get
from requests.exceptions import SSLError
from datetime import timedelta
from random import choice, randint
from templates import TEMPLATES, load as load_template
from json import dumps, loads, JSONDecodeError
from .const import Action, UserAction, ServerPool, GaijinErrorCodes, getAction
from utils import networkManager
from utils.helper import AuthenticationError
from .blk_utils import Compress, Decompress
if TYPE_CHECKING:
	from utils import UserTokenCache

_logger = getLogger(__name__)

#region Fetch server list once at import
try:
	_resp = req_get("https://public-configs-warthunder-gcore.cdn.gaijin.net/production/network.blk", timeout=30)
except SSLError:
	_resp = req_get("https://public-configs.warthunder.com/production/network.blk", timeout=30)
if not _resp.ok:
	raise RuntimeError(f"Failed to fetch server list: {_resp.status_code}")
_cfg = Decompress(_resp.content)["production"]
char_servers: list[str] = _cfg["charServer"]
inv_proxies: list[str] = _cfg["inventory"]["servers"]["url"]
userstat_proxies: list[str] = _cfg["userstat"]["servers"]["url"]
contacts_proxies: list[str] = _cfg["contacts"]["servers"]["url"]
ugc_servers: list[str] = _cfg["ugc_settings"]["ugcServerUrl"]
del _resp, _cfg
if any(len(i) == 0 for i in [char_servers, inv_proxies, userstat_proxies, contacts_proxies, ugc_servers]):
	raise RuntimeError("Server URL lists did not get populated properly")
SERVER_URLS: dict[ServerPool, list[str]] = {
	ServerPool.CHAR: char_servers,
	ServerPool.INVENTORY: inv_proxies,
	ServerPool.USERSTAT: userstat_proxies,
	ServerPool.CONTACTS: contacts_proxies,
	ServerPool.UGC: ugc_servers,
	ServerPool.MARKET_JSON: ["https://market-proxy.gaijin.net/json"],
	ServerPool.MARKET_WEB: ["https://market-proxy.gaijin.net/web"],
	ServerPool.MARKET_CHAR: ["https://market-proxy.gaijin.net/char"],
	ServerPool.MARKET: ["https://market-proxy.gaijin.net/market"],
	ServerPool.MARKET_ASSET: ["https://market-proxy.gaijin.net/assetAPI"],
}
def get_server(action: Action|UserAction) -> str:
	return choice(SERVER_URLS[action.value[1]])
#endregion

class Request:
	"""Request framework for sending messages to Gaijin's servers"""
	user: UserTokenCache.Entry = None
	session = None

	body: dict[str, Any]
	headers: dict[str, Any]
	host: str|None = None
	method: str
	action: Action|UserAction
	def __init__(
		self,
		action: Action|UserAction, 
		body: dict[str, Any] | None = None,
		headers: dict[str, Any] | None = None,
		user: UserTokenCache.Entry = None,
		host:str|None = None,
		method:str = "POST",
		session:ClientSession|None=None
	):
		self.body = body
		self.headers = {
			"Accept": "*/*",
			"Accept-Encoding": "deflate, gzip, br, zstd",
			"User-Agent": "ThunderAPI/1.0",
			"transactid": "1",
			"platform": "PC",
			"platform_id": "9",
			"comprTypes": "lz4hc;lz4;snappy;bzip2;gzip;vromfs;zstd;zlib"
		}
		if headers:
			self.headers.update(headers)


		if host is not None:
			self.url = host
		else:
			self.url = get_server(action)

		self.action = action
		if self.action is None and self.url is None:
			raise RuntimeError("No action and no URL provided")

		self.method = method
		self.user = user
		self.session = session

	@classmethod
	async def from_template(cls, user:UserTokenCache.Entry, template: str, session:ClientSession|None=None, **data:str|dict[str, Any]) -> "Request":
		if user.timeLeft() <= timedelta(minutes=30):
			await user.refresh()
		if template not in TEMPLATES:
			raise ValueError(f"Unknown template '{template}'. Available: {TEMPLATES}")
		tpl = load_template(template)
		headers = tpl.get("headers", {})
		body = tpl.get("body", {})

		if "action" in tpl:
			action = getAction(tpl["action"])
		elif "action" in headers:
			action = getAction(headers["action"])
		elif "action" in body:
			action = getAction(body["action"])
		else:
			raise RuntimeError(f"No action provided for template {template}")

		self = cls(
			body=body, 
			headers=headers,
			user=user,
			host=tpl.get("host", None),
			method=tpl.get("method", "POST"),
			action=action,
			session=session
		)
		await self.add_auth_headers()
		for key, value in data.items():
			if key in self.body and key in self.headers:
				raise RuntimeError(f"Key `{key}` found in both headers and body for template `{template}`")
			elif key in self.body:
				self.body[key] = value
			elif key in self.headers:
				self.headers[key] = value
			else:
				raise RuntimeError(f"Unknown key `{key}` provided. Please edit template `{template}`")
		return self

	@staticmethod
	async def send_template(user:UserTokenCache.Entry, template: str, session:ClientSession|None=None, **data:str|dict[str, Any]) -> dict:
		cls = await Request.from_template(user, template, session=session, **data)
		return await cls.send()

	async def add_auth_headers(self):
		authTimeLeft = self.user.timeLeft()
		if authTimeLeft <= timedelta(minutes=30):
			await self.user.refresh()
		elif authTimeLeft < timedelta():
			raise AuthenticationError(status.HTTP_401_UNAUTHORIZED, "Your login has expired, please log in again to reauthenticate.")
		if self.user.jwt:
			if "Authorization" in self.body:
				self.body["Authorization"] = f"Bearer {self.user.jwt}"
			elif "token" in self.body:
				self.body["token"] = self.user.jwt
				self.body["uidHint"] = str(self.user.uidHint)
				self.body["transactid"] = str(randint(0, 999999999999))
			elif "Authorization" in self.headers:
				self.headers["Authorization"] = f"Bearer {self.user.jwt}"
			elif "token" in self.headers:
				self.headers["token"] = self.user.jwt
				self.headers["uidHint"] = str(self.user.uidHint)
				self.headers["transactid"] = str(randint(0, 999999999999))
			return
		else:
			raise AuthenticationError(status.HTTP_403_FORBIDDEN, "Authentication required for this request, but no token is available. Please ensure you have logged in successfully.")

	async def send(self) -> dict[str, Any]:
		if self.action is None and self.url is None: return
		kwargs: dict[str, Any] = {"headers": self.headers}
		for key, value in self.body.items():
			if value == "<replace>":
				raise HTTPException(
					status.HTTP_500_INTERNAL_SERVER_ERROR,
					f"[{self.action.name}] Body value `{key}` is not replaced by code"
				)
			elif key == "<replace>":
				raise HTTPException(
					status.HTTP_500_INTERNAL_SERVER_ERROR,
					f"[{self.action.name}] Body key with value `{value}` is not replaced by code"
				)

		for header, value in kwargs["headers"].items():
			if value == "<replace>":
				raise HTTPException(
					status.HTTP_500_INTERNAL_SERVER_ERROR,
					f"[{self.action.name}] Header value `{header}` is not replaced by code"
				)
			elif header == "<replace>": 
				raise HTTPException(
					status.HTTP_500_INTERNAL_SERVER_ERROR,
					f"[{self.action.name}] Header key with value `{value}` is not replaced by code"
				)
			if isinstance(value, (bytes, str)):
				continue
			elif isinstance(value, dict):
				kwargs["headers"][header] = "; ".join(f"{k}={v}" for k, v in value.items())
			elif isinstance(value, list):
				kwargs["headers"][header] = ";".join(str(i) for i in value)
			else:
				kwargs["headers"][header] = str(value)

		match self.headers.get("Content-Type"):
			case "application/x-www-form-urlencoded":
				if self.action == UserAction.market_view_item:
					kwargs["data"] = dumps(self.body)
				else:
					kwargs["data"] = self.body # TODO: New code
			case "application/octet-stream":
				kwargs["data"] = await Compress.async_init(self.body, self.headers.get("compr"))
			case "application/json":
				kwargs["json"] = self.body
			case None:
				pass
			case _:
				raise NotImplementedError(f"Content-Type value '{self.headers["Content-Type"]}' not implemented")
					

		if self.session is None:
			async with networkManager.request(self.method.upper(), self.url, **kwargs) as resp:
				response = await self._decode(resp)
		else:
			async with self.session.request(self.method.upper(), self.url, **kwargs) as resp:
				response = await self._decode(resp)

		return response

	async def _decode(self, response: ClientResponse) -> dict[str, Any]:
		"""Decode from compressed or raw .blk binary to json."""
		content = await response.read()
		if content == b"":
			return {}
		if content.startswith(b"!ERROR:"):
			GaijinErrorCodes.parse(content) # Throws an HTTPException
		if content.startswith(b"!OK"):
			return {
				"status": "success"
			}
		try:
			return loads(content)
		except (JSONDecodeError, UnicodeDecodeError):
			return (await Decompress.async_init(content)).as_dict()
