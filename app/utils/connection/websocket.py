from asyncio import Lock
from fastapi import WebSocket, WebSocketDisconnect, status
from collections.abc import AsyncGenerator
from typing import Awaitable, Callable
from datetime import datetime, UTC, timedelta

class WebsocketManager:
	__CONN: set[WebSocket]
	__LOCK: Lock
	__CLOSED: bool = False
	__ON_IDLE: Callable[[], Awaitable[None]] | None

	def __init__(self, on_idle: Callable[[], Awaitable[None]] | None = None):
		#TODO: Implement auth requiring for websockets
		self.__CONN = set()
		self.__LOCK = Lock()
		self.__ON_IDLE = on_idle

	async def connect(self, ws: WebSocket) -> AsyncGenerator[dict, None]:
		if self.__CLOSED:
			await ws.close(status.WS_1013_TRY_AGAIN_LATER)
			return

		await ws.accept()

		async with self.__LOCK:
			self.__CONN.add(ws)
		try:
			while True:
				yield await ws.receive_json()
		except (WebSocketDisconnect, RuntimeError):
			pass
		finally:
			await self.disconnect(ws)
		
	async def disconnect(self, ws: WebSocket):
		_idle: bool = False
		async with self.__LOCK:
			try:
				await ws.close(status.WS_1000_NORMAL_CLOSURE)
			except Exception:
				pass
			self.__CONN.discard(ws)
			if len(self.__CONN) == 0:
				_idle = True	
		if _idle and self.__ON_IDLE is not None:
			await self.__ON_IDLE()

	async def close(self):
		self.__CLOSED = True
		async with self.__LOCK:
			for ws in self.__CONN:
				await ws.close(status.WS_1000_NORMAL_CLOSURE)
			self.__CONN.clear()

	async def broadcast(self, message: dict):
		async with self.__LOCK:
			targets = tuple(self.__CONN)
		for ws in targets:
			try:
				await ws.send_json(message)
			except Exception:
				await self.disconnect(ws)   # prune dead sockets
