from .const import ServerPool, Actions
from random import choice
from typing import Any

char_servers: list[str] = []
inv_proxies: list[str] = []
userstat_proxies: list[str] = []
contacts_proxies: list[str] = []
ugc_servers: list[str] = []
SERVER_URLS: dict[ServerPool, list[str]] = {}

def _populate_serverlist(data: dict[str, Any]):
	global char_servers, inv_proxies, userstat_proxies, contacts_proxies, ugc_servers, SERVER_URLS
	char_servers = data["charServer"]
	inv_proxies = data["inventory"]["servers"]["url"]
	userstat_proxies = data["userstat"]["servers"]["url"]
	contacts_proxies = data["contacts"]["servers"]["url"]
	ugc_servers = data["ugc_settings"]["ugcServerUrl"]
	matching_servers = data["matching"]["server"]
	if any(len(i) == 0 for i in [char_servers, inv_proxies, userstat_proxies, contacts_proxies, ugc_servers, matching_servers]):
		raise RuntimeError("Server URL lists did not get populated properly")

	SERVER_URLS = {
		ServerPool.CHAR: char_servers,
		ServerPool.INVENTORY: inv_proxies,
		ServerPool.USERSTAT: userstat_proxies,
		ServerPool.CONTACTS: contacts_proxies,
		ServerPool.UGC: ugc_servers,
		ServerPool.MARKET_JSON: ["https://market-proxy.gaijin.net/json"],
		ServerPool.MARKET_WEB: ["https://market-proxy.gaijin.net/web"],
		ServerPool.MARKET_CHAR: ["https://market-proxy.gaijin.net/char"],
		ServerPool.MARKET: ["https://market-proxy.gaijin.net/market"],
		ServerPool.MARKET_ASSET: ["https://market-proxy.gaijin.net/assetAPI"]
	}

def get_server(action: Actions) -> str:
	return choice(SERVER_URLS[action.value.pool])