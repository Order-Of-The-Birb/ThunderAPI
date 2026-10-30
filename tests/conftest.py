import os

# `config.py` reads DEBUG_MODE at import time, so set it before importing `main`
os.environ["DEBUG_MODE"] = "1"

import pytest, pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app
from src.utils.connection import Network

@pytest_asyncio.fixture(autouse=True)
async def _autostart_network():
	"""Start the Network session before each test and close it afterwards."""
	await Network.start()
	try:
		yield
	finally:
		await Network.close()
