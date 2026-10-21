# AGENTS instructions  
This repository contains a python application using FastAPI. This project acts as a "translation layer" between Gaijin Entertainment's proprietary `blk` format, and a usable `json` format. Due to the nature of this API it is very hard to automate testing, therefore all testing is to be done manually  

## Testing  
Manual testing can be done through the Swagger UI interface found on `/` or `/docs`  
The templates in `app/utils/connection/http/templates/` (and `app/utils/connection/tcp/templates/`) can NOT be used directly in curl requests, they are in a proprietary format  

## Structure  
The repository has the following directories at its root:  
- `app` - The application source code:  
	- `api` - The FastAPI routers (`v1`, `backends/`, `models/`)  
	- `utils` - A set of utilities used in the code, like:  
		- `connection/` - Network + BLK conversion (`network.py`, `blk_utils.py`, `const.py`, `http/`, `tcp/`, `default_network_cfg.json`)  
		- `geo.py` - Geolocation utility  
		- `auth.py` - Database and authentication management utility  
		- `news.py` - News parsing  
		- `helper.py` - Shared helpers  
		- `websocket.py` - WebSocket handling  
		- `replayParser/` - Replay parsing  
		- `vehicleParser/` - Vehicle data parsing  
	- `main.py` - Main entry point of the code  
	- `config.py` - Configuration / path constants  
- `tools` - External binaries (`wt_ext_cli`, `binBlk`) used for BLK conversion  
- `dev_tools` - Development-only tooling, regular users will never trigger any code within this directory  
- `data` - Runtime data (logs, users.db, news.json, GeoLite2 DB, vehicle cache)  
The root directory also includes the following files:  
- `gaijin_api_endpoints.md` - Documentation on Gaijin Entertainment's internal endpoints, their usage and response  
- `app/main.py` - Main entry point of the code  
- `requirements.txt` - PyPI package requirements for the server  
- `Dockerfile` - Docker image definition  
- `compose.yml` - Docker Compose definition (also referenced by `systemd.service`)  
- `.example.env` - Example .env file, that can be copied. Includes the following variables:  
	- `PORT` - The port to run on  
	- `HOST` - The IP to be listening on  
	- `MACHINE_ID` - Value sent when logging in, doesn't matter much  
	- `TOKEN_ENC_KEY` - Encryption key used in the database. Do not lose this, as losing it will mean the code can't decrypt sensitive values used in the backend logic  
	- `WT_EXT_CLI_PATH` - wt_ext_cli path, if not found in `tools/` or is named differently  
	- `BINBLK_PATH` - binBlk path, if not found in `tools/` or is named differently  
	- `LOGIN_RATE_LIMIT` - Rate limit for the login endpoints  
	- `REGULAR_RATE_LIMIT` - Rate limit for the rest of the endpoints  
	- `LOG_LEVEL` - The log level of the logger. For hosting `WARNING` is fine, as it still shows issues that have to be handled  
- `LICENSE` - The license the repository falls under  
- `README.md` - The README of the repository, contains some extra context  
- `app/swagger_ui_modify.css` / `app/swagger_ui_modify.js` - Content used to modify the Swagger UI interface, to support websockets  
The following directories/files appear only after running the server at least once:  
- `.env` - The .env file used by the code  
- `data/logs/` - Logs directory  
- `data/users.db` - Authentication database  
- `data/news.json` - Last sent news storage  
- `data/GeoLite2-City.*` - Geolocation database  

## External tools  
This project uses the following external binaries:  
- `wt_ext_cli`  
	- Autodiscovered in the `tools` directory  
	- If not in said directory, it will look at the `WT_EXT_CLI_PATH` environment variable  
	- The program will stop if this binary is not found at startup  
	- Found at `https://github.com/Warthunder-Open-Source-Foundation/wt_ext_cli`  
- `binBlk`  
	- Gaijin Entertainment's uploaded `blk` tool  
	- Autodiscovered in the `tools` directory  
	- If not in said directory, it will look at the `BINBLK_PATH` environment variable  
	- The program will stop if this binary is not found at startup  
	- Found at `https://github.com/GaijinEntertainment/DagorEngine/releases/latest` release body, as `tools-prebuilt-${platform}-${arch}.7z`  

## Gaijin-imposed restrictions  
- Tokens have to be refreshed once every hour. The refreshing is done by the code itself, the token just has to be used on any endpoint, and the backend handles the rest  

## File conventions  
- Files use `tabs` for indentation, not spaces  
- Importing is generally done with `from ... import ...`, to reduce the extra entries in IntelliSense  
- Rate limiting via `app.api.shared.limiter`  
- Use the module-level `logger` for logging  
- In `app/utils/vehicleParser/`, trailing `pass` statements are intentional debug breakpoint anchors — do not remove them  

## Sensitive data  
Sensitive data, like session tokens and emails are stored, see `README.md#privacy-policy`  

## Running the server  
- Copy `.example.env` to `.env` (`cp ./.example.env ./.env`) and edit as needed  
- `docker compose up -d` — builds and starts the server; API docs at `/` and `/docs`  
- Or run directly: `python app/main.py`  

## Architecture  
Request flow: `app/api/v1` router => `app/api/v1/backends/` => `app/utils/connection/blk_utils.py` (BLK <=> JSON) => Gaijin backend  
- `app/api/v1/backends/` — per-domain backend logic (clans, general, marketplace, replay, users)  
- `app/api/v1/models/` — Pydantic response/request models  
- `app/utils/connection/blk_utils.py` — BLK fetch/conversion (depends on `wt_ext_cli` / `binBlk`)  
