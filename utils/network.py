from aiohttp import ClientResponse, ClientSession
from aiohttp.cookiejar import DummyCookieJar
from fastapi.concurrency import asynccontextmanager 
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from asyncio import Lock, Event
from typing import Any, Literal, overload
from json import loads

class NetworkError(HTTPException): pass

class WebsocketManager:
	_connections: set[WebSocket]
	_lock: Lock

	def __init__(self):
		self._connections = set()
		self._lock = Lock()

	async def connect(self, ws: WebSocket):
		await ws.accept()
		async with self._lock:
			self._connections.add(ws)
		try:
			while True:
				await ws.receive()
		except (WebSocketDisconnect, RuntimeError):
			await self.disconnect(ws)
		
	async def disconnect(self, ws: WebSocket):
		async with self._lock:
			self._connections.discard(ws)

	async def broadcast(self, message: dict):
		async with self._lock:
			targets = list(self._connections)
		for ws in targets:
			try:
				await ws.send_json(message)
			except Exception:
				await self.disconnect(ws)   # prune dead sockets

class NetworkManager:
	def __init__(self):
		self.__session: ClientSession | None = None
		self.__closing = False
		self.__active_ops = 0
		self.__active_ops_done = Event()
		self.__active_ops_done.set()
		self.__lock = Lock()

	@asynccontextmanager
	async def post(self, url:str, **kwargs):
		async with self.request("POST", url, **kwargs) as resp:
			yield resp
	@asynccontextmanager
	async def get(self, url:str, **kwargs):
		async with self.request("GET", url, **kwargs) as resp:
			yield resp
	@asynccontextmanager
	async def request(self, method:str, url:str, **kwargs):
		async with self.operation() as session:
			async with session.request(method, url, **kwargs) as resp:
				resp.raise_for_status()
				yield resp

	@asynccontextmanager
	async def operation(self):
		session = await self._enter_op()
		try:
			yield session
		finally:
			await self._exit_op()

	async def start(self):
		async with self.__lock:
			if self.__session is not None and not self.__session.closed:
				return
			self.__closing = False
			self.__session = ClientSession(headers={"User-Agent": "ThunderAPI/1.0"}, cookie_jar=DummyCookieJar())
	async def close(self):
		async with self.__lock:
			self.__closing = True

		await self.__active_ops_done.wait()

		async with self.__lock:
			if self.__session is not None and not self.__session.closed:
				await self.__session.close()
			self.__session = None

	#region handle_response
	@overload
	@staticmethod
	async def handle_response(resp: ClientResponse, autoconvert: Literal[True] = True) -> dict[str, Any]: ...
	@overload
	@staticmethod
	async def handle_response(resp: ClientResponse, autoconvert: Literal[False]) -> bytes: ...
	@overload
	@staticmethod
	async def handle_response(resp: ClientResponse, autoconvert: bool = True) -> dict[str, Any]|bytes: ...
	@staticmethod
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

	async def _enter_op(self):
		async with self.__lock:
			if self.__closing:
				raise RuntimeError("NetworkManager is shutting down")

			if self.__session is None or self.__session.closed:
				raise RuntimeError("NetworkManager is not started")

			self.__active_ops += 1
			self.__active_ops_done.clear()

			return self.__session
	
	async def _exit_op(self):
		async with self.__lock:
			self.__active_ops -= 1

			if self.__active_ops <= 0:
				self.__active_ops = 0
				self.__active_ops_done.set()