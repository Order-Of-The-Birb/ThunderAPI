from asyncio import Event, Lock
from json import loads
from typing import Any, Literal, overload, Callable, Awaitable

from aiohttp import ClientResponse, ClientSession
from aiohttp.cookiejar import DummyCookieJar
from fastapi import HTTPException
from fastapi.concurrency import asynccontextmanager


class NetworkError(HTTPException):
	pass

__session: ClientSession | None = None
__closing = False
__active_ops = 0
__active_ops_done = Event()
__active_ops_done.set()
__lock = Lock()

type ResponseProvider = Callable[[Any], Awaitable[dict[str, Any]]]

@asynccontextmanager
async def post(url:str, response_provider: ResponseProvider | None = None, resp_state: str | None = None, autoconvert:bool = False, **kwargs):
	async with request("POST", url, response_provider=response_provider, resp_state=resp_state, autoconvert=autoconvert, **kwargs) as resp:
		yield resp

@asynccontextmanager
async def get(url:str, response_provider: ResponseProvider | None = None, resp_state: str | None = None, autoconvert:bool = False, **kwargs):
	async with request("GET", url, response_provider=response_provider, resp_state=resp_state, autoconvert=autoconvert, **kwargs) as resp:
		yield resp

@asynccontextmanager
async def request(method:str, url:str, response_provider: ResponseProvider | None = None, resp_state: str | None = None, autoconvert:bool = False, **kwargs):
	async with operation() as session:
		if response_provider is not None:
			yield await response_provider(resp_state)
		else:
			async with session.request(method, url, **kwargs) as resp:
				resp.raise_for_status()
				yield await handle_response(resp, autoconvert=autoconvert)

@asynccontextmanager
async def operation():
	session = await _enter_op()
	try:
		yield session
	finally:
		await _exit_op()

async def start():
	global __session, __closing
	async with __lock:
		if __session is not None and not __session.closed:
			return
		__closing = False
		__session = ClientSession(headers={"User-Agent": "ThunderAPI/1.0"}, cookie_jar=DummyCookieJar())

async def close():
	global __closing, __session
	async with __lock:
		__closing = True

	await __active_ops_done.wait()

	async with __lock:
		if __session is not None and not __session.closed:
			await __session.close()
		__session = None

#region handle_response
@overload
async def handle_response(resp: ClientResponse, autoconvert: Literal[True] = True) -> dict[str, Any]: ...
@overload
async def handle_response(resp: ClientResponse, autoconvert: Literal[False]) -> bytes: ...
@overload
async def handle_response(resp: ClientResponse, autoconvert: bool = True) -> dict[str, Any]|bytes: ...
async def handle_response(resp:ClientResponse, autoconvert:bool = True) -> dict[str, Any]|bytes:
	content = await resp.read()

	if resp.status >= 400:
		raise NetworkError(400, f"Request failed: {resp.status}")
	if content.startswith(b"!ERROR"):
		raise NetworkError(400, f"Request failed: {content}")

	if autoconvert:
		return loads(content)
	return content
#endregion

async def _enter_op():
	global __active_ops
	async with __lock:
		if __closing:
			raise RuntimeError("NetworkManager is shutting down")

		if __session is None or __session.closed:
			raise RuntimeError("NetworkManager is not started")

		__active_ops += 1
		__active_ops_done.clear()

		return __session

async def _exit_op():
	global __active_ops
	async with __lock:
		__active_ops -= 1

		if __active_ops <= 0:
			__active_ops = 0
			__active_ops_done.set()
