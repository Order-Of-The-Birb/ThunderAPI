from asyncio import Lock, wait_for
from fastapi import WebSocket, WebSocketDisconnect, status
from collections.abc import AsyncGenerator
from utils import users_auth
from utils.auth import UserAuth
from typing import Awaitable, Callable
from datetime import datetime, UTC, timedelta

class WebsocketManager:
	__CONN: set[WebSocket]
	__LOCK: Lock
	__CLOSED: bool = False
	__REQ_AUTH: UserAuth.Entry | None = None
	__ON_IDLE: Callable[[], Awaitable[None]] | None
	__TIMEOUT: dict[str, datetime]

	def __init__(self, require_auth:UserAuth.Entry | None = None, on_idle: Callable[[], Awaitable[None]] | None = None):
		#TODO: Implement auth requiring for websockets
		self.__CONN = set()
		self.__LOCK = Lock()
		self.__REQ_AUTH = require_auth # server websocket (no auth) if None
		self.__ON_IDLE = on_idle
		self.__TIMEOUT = {}

	async def connect(self, ws: WebSocket) -> AsyncGenerator[dict, None]:
		if self.__CLOSED:
			await ws.close(status.WS_1013_TRY_AGAIN_LATER)
			return
		
		identifier = f"ip:{ws.client.host if ws.client else "unknown"}"
		if self.is_timed_out(identifier):
			await ws.close(
				status.WS_1008_POLICY_VIOLATION,
				"Temporarily blocked"
			)
			return
		await ws.accept()

		if self.__REQ_AUTH is not None:
			tries = 0
			MAX_RETRIES = 3
			await ws.send_text(f"You must authenticate before sending data. Please send your token to the websocket for authentication\nIf you fail to provide a valid token {MAX_RETRIES} times you will be timed out for 15 minutes\nToken must be sent in the format: " + '\{"token": "[INSERT TOKEN]"\}')
			try:
				while True:
					token = await wait_for(ws.receive_json(), 60)

					if "token" in token:
						user = await users_auth.get(token["token"])
					else:
						tries += 1
						if tries == MAX_RETRIES:
							await ws.close(status.WS_1003_UNSUPPORTED_DATA, "Invalid format")
							self.timeout(identifier, timedelta(minutes=15))
							return
						await ws.send_text(f"Invalid format. Try {tries} out of {MAX_RETRIES}")
						continue
					if user is None or user.uidHint != self.__REQ_AUTH.uidHint:
						tries += 1
						if tries == MAX_RETRIES:
							await ws.close(status.WS_1008_POLICY_VIOLATION, "Too many tries")
							self.timeout(identifier, timedelta(minutes=15))
							return
						await ws.send_text(f"Invalid token. Try {tries} out of {MAX_RETRIES}")
						continue

					break
			except (WebSocketDisconnect, RuntimeError):
				return # Reject websocket
			except TimeoutError:
				await ws.close(status.WS_1013_TRY_AGAIN_LATER, "Request timed out")
				return

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

	def is_timed_out(self, identifier: str) -> bool:
		expires = self.__TIMEOUT.get(identifier)

		if expires is None:
			return False

		if datetime.now(UTC) >= expires:
			del self.__TIMEOUT[identifier]
			return False

		return True

	def timeout(self, identifier: str, time: timedelta):
		self.__TIMEOUT[identifier] = (
			datetime.now(UTC) + time
		)
