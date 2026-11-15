import os

# `config.py` reads DEBUG_MODE at import time, so set it before importing `main`
os.environ["DEBUG_MODE"] = "1"

import pytest_asyncio

from utils.connection import network

@pytest_asyncio.fixture(autouse = True)
async def _autostart_network():
	"""Start the Network session before each test and close it afterwards."""
	await network.start()
	try:
		yield
	finally:
		await network.close()
