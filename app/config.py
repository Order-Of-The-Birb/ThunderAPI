from os import getenv
from pathlib import Path


__DEBUG_MODE:bool = int(getenv("DEBUG_MODE", "0")) == 1

DATA_DIR = Path("/data/") if not __DEBUG_MODE else Path(__file__).parent.parent / "data"
TOOL_DIR = Path("/opt/tools/") if not __DEBUG_MODE else Path(__file__).parent.parent / "tools"

class _usersDB:
	DB = DATA_DIR / "users.db"
	KEY = DATA_DIR / "users.key"
	MACHINE_ID = DATA_DIR / "machine.id"
	INIT_SQL = Path(__file__).parent / "utils" / "users_create.sql"

USERS_DB = _usersDB()
VEHICLES = DATA_DIR / "vehicles"
NEWS_JSON = DATA_DIR / "news.json"

class _geoLitePaths:
	DB = DATA_DIR / "GeoLite2-City.mmdb"
	HASH = DATA_DIR / "GeoLite2-City.hash"
	TMP = DATA_DIR / "GeoLite2-City.mmdb.tmp"

GEOLITE = _geoLitePaths()

LOGS_DIR = DATA_DIR / "logs"

SWAGGER_JS = Path(__file__).parent / "swagger_ui_modify.js"
SWAGGER_CSS = Path(__file__).parent / "swagger_ui_modify.css"

DEFAULT_NETWORK_CFG = Path(__file__).parent / "tools" / "default_network_cfg.json"

WT_EXT_CLI = TOOL_DIR / "wt_ext_cli"
BINBLK = TOOL_DIR / "binBlk"

HOST: str = getenv("HOST", "127.0.0.1") if __DEBUG_MODE else "0.0.0.0"
PORT: int = int(getenv("PORT", "8000")) if __DEBUG_MODE else 8000