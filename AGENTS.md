# AGENTS instructions  
This repository contains a python application using FastAPI. This project acts as a "translation layer" between Gaijin Entertainment's proprietary `blk` format, and a usable `json` format. Due to the nature of this API it is very hard to automate testing, therefore all testing is to be done manually  

## Testing  
Manual testing can be done through the Swagger UI interface found on `/` or `/docs`  
The templates in `templates/` can NOT be used directly in curl requests, they are in a proprietary format  

## Structure  
The repository has the following directories at its root:  
- `api` - The FastAPI routers  
- `manual_extract` - A set of tools only used for development purposes, regular users will never trigger any code within this directory  
- `templates` - HTTP request templates, including a handler for fetching  
- `tools` - A set of tools used for getting and converting Gaijin Entertainment's responses into `json` format  
- `utils` - A set of utilities used in the code, like:  
	- `geo.py` - Geolocation utility  
	- `network.py` - Network connection manager utility  
	- `auth.py` - Database and authentication management utility  
	- `news.py` - News parsing  
	- `replayParser/` - Replay parsing  
	- `vehicleParser/` - Vehicle data parsing  
The root directory also includes the following files:  
- `gaijin_api_endpoints.md` - Documentation on Gaijin Entertainment's internal endpoints, their usage and response  
- `main.py` - Main entry point of the code  
- `requirements.txt` - PyPI package requirements for the server  
- `run` / `run.bat` - Bash/Batch file for running the server  
- `setup` / `setup.bat` - Bash/Batch file for setting up the .venv  
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
- `swagger_ui_modify.css` / `swagger_ui_modify.js` - Content used to modify the Swagger UI interface, to support websockets  
The following directories/files appear only after running the server at least once:  
- `.env` - The .env file used by the code  
- `logs/` - Logs directory  
- `utils/users.db` - Authentication database  
- `utils/news.json` - Last sent news storage  
- `utils/GeoLite2-City.*` - Geolocation database  

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
- Rate limiting via `api.shared.limiter`  
- Use the module-level `logger` for logging  
- In `utils/vehicleParser/`, trailing `pass` statements are intentional debug breakpoint anchors — do not remove them  

## Sensitive data  
Sensitive data, like session tokens and emails are stored, see `README.md#privacy-policy`  

## Running the server  
- `./setup` — creates `.venv` (defaults to `python3.14`)  
- `./run` — starts the server at `http://127.0.0.1:8001`; API docs at `/docs`  
- `main.py` auto-copies `.example.env` => `.env` on first start  

## Architecture  
Request flow: `api/v1` router => `api/v1/backends/` => `tools/blk_utils.py` (BLK <=>JSON) => Gaijin backend  
- `api/v1/backends/` — per-domain backend logic (clans, general, marketplace, replay, users)  
- `api/v1/models/` — Pydantic response/request models  
- `tools/blk_utils.py` — BLK fetch/conversion (depends on `wt_ext_cli` / `binBlk`)  
