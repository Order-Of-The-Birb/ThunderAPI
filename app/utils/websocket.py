from asyncio import Lock
from fastapi import WebSocket, WebSocketDisconnect

class WebsocketManager:
    __CONN: set[WebSocket]
    __LOCK: Lock

    def __init__(self):
        self.__CONN = set()
        self.__LOCK = Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self.__LOCK:
            self.__CONN.add(ws)
        try:
            while True:
                await ws.receive()
        except (WebSocketDisconnect, RuntimeError):
            await self.disconnect(ws)
        
    async def disconnect(self, ws: WebSocket):
        async with self.__LOCK:
            self.__CONN.discard(ws)

    async def broadcast(self, message: dict):
        async with self.__LOCK:
            targets = list(self.__CONN)
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(ws)   # prune dead sockets