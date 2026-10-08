from __future__ import annotations
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from utils.vehicleParser.vehiclesProcessor import Vehicle, Weapon, Sensor
from vars import VEHICLES

_logger = getLogger(__name__)

class DatabasePaths:
	@dataclass(frozen=True, slots=True)
	class _dbpaths:
		ROOT: Path
		VEHICLES: Path
		WEAPONS: Path
		SENSORS: Path
		ALL: Path

	DATABASE:_dbpaths = _dbpaths(
		VEHICLES / "database",
		VEHICLES / "database" / "units",
		VEHICLES / "database" / "weapons",
		VEHICLES / "database" / "sensors",
		VEHICLES / "database" / "all.json"
	)
	GAMEFILES:Path = VEHICLES / "gamefiles"

class Vehicles:
	def __init__(self):
		_logger.debug("Vehicles object created")

	async def setup(self):
		DatabasePaths.GAMEFILES.mkdir(mode=0o755, exist_ok=True)

		if not (DatabasePaths.GAMEFILES / ".git").exists():
			
			_logger.info(f"Set up git repo in {DatabasePaths.GAMEFILES}")

		if (not DatabasePaths.DATABASE.ROOT.exists()):
			if (not DatabasePaths.DATABASE.ALL.exists()):
				DatabasePaths.DATABASE.ALL.write_text("{}")

	async def getVehicle(self, unit:str) -> Vehicle|None:
		try:
			vehicle = await Vehicle.from_id(unit)
		except LookupError:
			return
		return vehicle

	async def getWeapon(self, weapon:str) -> Weapon|None:
		try:
			weapon = Weapon.from_id(weapon)
		except LookupError:
			return
		return weapon

	async def getSensor(self, sensor:str) -> Sensor|None:
		try:
			sensor = await Sensor.from_id(sensor)
		except LookupError:
			return
		return sensor