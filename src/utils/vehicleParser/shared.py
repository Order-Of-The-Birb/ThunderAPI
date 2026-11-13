import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from logging import getLogger
from pathlib import Path
from subprocess import PIPE, run
from typing import TYPE_CHECKING, Any, Literal

from orjson import loads
from packaging.version import Version
from pandas import read_csv

from config import VEHICLES

from .. import cache as Cache

if TYPE_CHECKING:
	from .sensor import Sensor
	from .vehicle import Vehicle
	from .weapon import Weapon

_logger = getLogger(__name__)

GAMEFILES = VEHICLES / "gamefiles"
GAMEFILES.mkdir(exist_ok=True, parents=True)

REMOTE_VERSION_URL = "https://raw.githubusercontent.com/gszabi99/War-Thunder-Datamine/refs/heads/master/version"

class DataLocations:
	@dataclass(frozen=True, slots=True)
	class VehicleData:
		DATA:Path
		IMAGE:Path
		PRESETS:Path
		SENSORS:Path

	TT_IMAGES = GAMEFILES / "atlases.vromfs.bin_u" / "units"
	AIR_DATA: VehicleData = VehicleData(
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "flightmodels",
		GAMEFILES / "tex.vromfs.bin_u" / "aircrafts",
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "flightmodels" / "weaponpresets",
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "sensors"
	)
	GROUND_DATA: VehicleData = VehicleData(
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "units" / "tankmodels",
		GAMEFILES / "tex.vromfs.bin_u" / "tanks",
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "units" / "weaponpresets",
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "sensors"
	)
	NAVY_DATA: VehicleData = VehicleData(
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "units" / "ships",
		GAMEFILES / "tex.vromfs.bin_u" / "ships",
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "units" / "weaponpresets",
		GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "sensors" / "naval"
	)
	WEAPON_DATA = GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "weapons"
	VEHICLE_DATA = GAMEFILES / "char.vromfs.bin_u" / "config" / "unittags.blkx"
	SENSOR_DATA = GAMEFILES / "aces.vromfs.bin_u" / "gamedata" / "sensors"
	TT_LINES = GAMEFILES / "char.vromfs.bin_u" / "config" / "shop.blkx"
	WPCOST = GAMEFILES / "char.vromfs.bin_u" / "config" / "wpcost.blkx"
	LOC_META = GAMEFILES / "lang.vromfs.bin_u" / "lang" / "localization.blkx"
	VEHICLE_LOC = GAMEFILES / "lang.vromfs.bin_u" / "lang" / "units.csv"
	WEAPON_LOC = GAMEFILES / "lang.vromfs.bin_u" / "lang" / "units_weaponry.csv"
	MODIFICATION_LOC = GAMEFILES / "lang.vromfs.bin_u" / "lang" / "units_modifications.csv"
	VERSION = GAMEFILES / "version"

async def setup():
	GAMEFILES.mkdir(exist_ok=True)
	if not (GAMEFILES / ".git").exists():
		_logger.warning(f"{GAMEFILES} doesn't have a git repository set up. Setting up automatically")
		tracked_paths = [ # Put a / before single files
			"aces.vromfs.bin_u/gamedata/flightmodels",
			"aces.vromfs.bin_u/gamedata/units/tankmodels",
			"aces.vromfs.bin_u/gamedata/units/ships",
			"aces.vromfs.bin_u/gamedata/sensors",
			"aces.vromfs.bin_u/gamedata/weapons",
			"atlases.vromfs.bin_u/units",
			"/char.vromfs.bin_u/config/shop.blkx",
			"/char.vromfs.bin_u/config/unittags.blkx",
			"/char.vromfs.bin_u/config/wpcost.blkx",
			"/lang.vromfs.bin_u/lang/localization.blkx",
			"/lang.vromfs.bin_u/lang/units.csv",
			"/lang.vromfs.bin_u/lang/units_weaponry.csv",
			"/lang.vromfs.bin_u/lang/units_modifications.csv",
			"tex.vromfs.bin_u/aircrafts",
			"tex.vromfs.bin_u/ships",
			"tex.vromfs.bin_u/tanks",
			"/version"
		]

		await asyncio.to_thread(
			run,
			"git clone --filter=blob:none --sparse https://github.com/gszabi99/War-Thunder-Datamine.git ./ &&" +
			f"git sparse-checkout set --no-cone {" ".join(tracked_paths)}",
			check=True,
			shell=True,
			cwd=GAMEFILES
		)
	pass
async def check_git():
	git_ver = await asyncio.to_thread(
		run,
		["git", "version"],
		stdout=PIPE,
		stderr=PIPE
	)
	if git_ver.returncode != 0:
		raise EnvironmentError("No git installed on this system. Install it before running the server")
	_logger.debug(git_ver.stdout.decode())

LAST_CHECK: datetime = datetime.fromtimestamp(0, UTC)
async def check_update():
	global VERSION, LAST_CHECK
	if (datetime.now(UTC)-LAST_CHECK) < timedelta(minutes=10):
		return
	LAST_CHECK = datetime.now(UTC)
	await check_git()
	await setup()
	result = await asyncio.to_thread(run, "git pull", cwd=GAMEFILES, shell=True, stdout=PIPE, stderr=PIPE)
	if result.returncode == 0:
		pass
	elif result.returncode == 1:
		_logger.warning(result.stderr)
	else:
		raise EnvironmentError("Fetching ran into an issue")
	new_ver = Version(await asyncio.to_thread(DataLocations.VERSION.read_text))
	if new_ver == VERSION:
		return # Nothing changed
	VERSION = new_ver
	await Cache.get("units").clear()

def referenceToPath(reference:str) -> Path:
	if not reference.endswith(".blk"):
		reference += ".blk"
	return GAMEFILES / "aces.vromfs.bin_u" / (reference.lower().replace("blk", "blkx"))

def _load_unit_loc() -> dict[str, dict[Literal["short", "shop"], dict[str, str]]]:
	df = read_csv(DataLocations.VEHICLE_LOC, delimiter=";", encoding="utf-8")
	df.set_index("<ID|readonly|noverify>", inplace=True)
	unit_loc: dict[str, dict[Literal["short", "shop"], dict[str, str]]] = {}
	for idx, row in df.to_dict(orient="index").items():
		base, _, variant = str(idx).rpartition("_")
		if variant == "0":
			key = "short"
		elif variant == "shop":
			key = "shop"
		else:
			continue
		unit_loc.setdefault(base, {})[key] = row
	return unit_loc
async def update_gamefiles():
	global VERSION, CACHED_VALIDITY_UNTIL, UNIT_LOC, WEAPON_LOC, MOD_LOC, WPCOST, VEHICLE_DATA, LOC_META, weapon_cache, sensor_cache, vehicle_cache
	if (CACHED_VALIDITY_UNTIL >= int(datetime.now(UTC).timestamp())):
		return
	CACHED_VALIDITY_UNTIL = int(datetime.now(UTC).timestamp()) + 10*60 # 10 minutes of cached version data
	await setup()
	await asyncio.to_thread(run, "git pull", cwd=GAMEFILES, shell=True, check=True)

	new_ver = Version(await asyncio.to_thread(DataLocations.VERSION.read_text))
	if VERSION == new_ver:
		return # Nothing changed

	VERSION = new_ver

	WPCOST = await asyncio.to_thread(loads, await asyncio.to_thread(DataLocations.WPCOST.read_text))
	VEHICLE_DATA = await asyncio.to_thread(loads, await asyncio.to_thread(DataLocations.VEHICLE_DATA.read_text))
	LOC_META = await asyncio.to_thread(loads, await asyncio.to_thread(DataLocations.LOC_META.read_text))

	UNIT_LOC = await asyncio.to_thread(_load_unit_loc)

	WEAPON_LOC = await asyncio.to_thread(read_csv, DataLocations.WEAPON_LOC, delimiter=";", encoding="utf-8")
	WEAPON_LOC.set_index("<ID|readonly|noverify>", inplace=True)

	MOD_LOC = await asyncio.to_thread(read_csv, DataLocations.MODIFICATION_LOC, delimiter=";", encoding="utf-8")
	MOD_LOC.set_index("<ID|readonly|noverify>", inplace=True)

	weapon_cache = {}
	sensor_cache = {}
	vehicle_cache = {}


VERSION: Version | None = None
CACHED_VALIDITY_UNTIL: int = 0
WPCOST: dict[str, dict[str, Any]] = {}
VEHICLE_DATA: dict[str, dict[str, Any]] = {}
LOC_META: dict[str, str | list[str] | dict] = {}
UNIT_LOC: dict[str, dict[Literal["short", "shop"], dict[str, str]]] = {}
WEAPON_LOC: Any = None
MOD_LOC: Any = None
weapon_cache: dict[str, Weapon] = {}
sensor_cache: dict[str, Sensor] = {}
vehicle_cache: dict[str, Vehicle] = {}
