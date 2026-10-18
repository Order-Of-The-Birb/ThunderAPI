from .const import ServerPool, Actions
from random import choice
from typing import Any

SERVER_URLS: dict[ServerPool, list[str]] = {}

def _populate_serverlist(data: dict[str, Any]):
	global SERVER_URLS
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
		ServerPool.MARKET_JSON: "https://market-proxy.gaijin.net/json",
		ServerPool.MARKET_WEB: "https://market-proxy.gaijin.net/web",
		ServerPool.MARKET_CHAR: "https://market-proxy.gaijin.net/char",
		ServerPool.MARKET: "https://market-proxy.gaijin.net/market",
		ServerPool.MARKET_ASSET: "https://market-proxy.gaijin.net/assetAPI",
		ServerPool.MATCHING: matching_servers
	}

def get_server(action: Actions) -> str:
	pool = SERVER_URLS[action.value.pool]
	if isinstance(pool, list):
		return choice(pool)
	return pool