import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from orjson import loads
from packaging.version import Version

from utils.helper import getMultipleKeys

from . import shared
from .const import IR_VISION_GENERATIONS, THERMAL_VISION_GENERATIONS
from .sensor import Sensor
from .weapon import Weapon


@dataclass(frozen=True, slots=True)
class VehiclePaths:
	vehicle_id:str
	@dataclass(frozen=True, slots=True)
	class Images:
		techtree: Path
		statcard: Path
	images: Images
	vehicleData: Path
	presets: tuple[Path]
def get_vehicle_paths(vehicle_id:str) -> VehiclePaths|None:
	def ext(text:str, ext:Literal["png", "blkx"]): return text+"."+ext

	#region Vehicle type assessment
	vtype:shared.DataLocations.VehicleData|None = None
	if ((_ := shared.DataLocations.AIR_DATA).DATA / ext(vehicle_id, "blkx")).exists():
		vtype = _
	elif ((_ := shared.DataLocations.GROUND_DATA).DATA / ext(vehicle_id, "blkx")).exists():
		vtype = _
	elif ((_ := shared.DataLocations.NAVY_DATA).DATA / ext(vehicle_id, "blkx")).exists():
		vtype = _

	if vtype is None:
		return None
	vehiclePath = vtype.DATA / ext(vehicle_id, "blkx")
	#endregion

	return VehiclePaths(
		vehicle_id,
		VehiclePaths.Images(
			shared.DataLocations.TT_IMAGES / ext(vehicle_id, "png"),
			vtype.IMAGE / ext(vehicle_id, "blkx")
		),
		vehiclePath,
		tuple(vtype.PRESETS.rglob(fr"{vehicle_id}_*.blkx"))
	)
class Vehicle:
	version: Version
	identifier: str
	type: str
	subtypes: list[str]
	operator: str
	tags: list[str]
	vehicle_stats: dict[str, float]
	release_date:datetime
	sensors: list[str]

	@dataclass(frozen=True, slots=True)
	class _weapon:
		"""A shorter, less computationally intensive weapon class. Holds less data"""
		id: str
		totalMass: int
		totalCount: int
		damage: int|None
		weaponmask: int
		reqModification: str|None = None
		usedForCustomSlot: bool = False
		guidance: str|None = None

		@classmethod
		def from_json(cls, id:str, data:dict[str, Any]):
			guidance = getMultipleKeys(data, "aamGuidanceType", "atgmVisibilityType", "guidedBombVisibilityType")
			if guidance == "default":
				if "aamGuidanceType" in data:
					guidance = "infraRed"
				elif "atgmVisibilityType" in data:
					guidance = "laser"
				elif "guidedBombVisibilityType" in data:
					raise NotImplementedError("Didn't implement default for this one yet")
					guidance = ""
			return cls(
				id,
				getMultipleKeys(data, "totalGuidedBombMass", "totalBombRocketMass"),
				getMultipleKeys(data, "totalBombCount"),
				data.get("weaponDamage"),
				data.get("weaponmask"),
				data.get("reqModification"),
				data.get("isWeaponForCustomSlot", False),
				guidance
			)
		def to_json(self):
			return asdict(self)

	@dataclass(frozen=True, slots=True)
	class _defaultPreset:
		id: str
		totalDamage: int
		mass: int|None
		ammoCount: int|None
		hasCountermeasures: bool
		mass_per_sec: int
		weaponmask: int
		weapons: dict[str, dict[str, Vehicle._weapon|int]]

		@classmethod
		def from_json(cls, key:str, data:dict[str, Any], full_weapon_data:dict[str, dict[str, Any]]):
			if any(key.startswith(i) for i in ["rocketguns", "containers", "bombguns", "equipment", "drop_tank", "custom_presets"]):
				raise RuntimeError(f"Invalid key for default preset: {key}")
			weapons = {}
			for k,v in data.get("sum_weapons", {}).items():
				weapons[k] = {
					"weapon": Vehicle._weapon.from_json(k, full_weapon_data[k]),
					"count": v
				}

			return cls(
				key,
				data.get("weaponDamage"),
				getMultipleKeys(data, "totalGuidedBombMass", "totalBombRocketMass"),
				getMultipleKeys(data, "totalBombCount"),
				data.get("hasCountermeasures", False),
				data.get("mass_per_sec", 0),
				data.get("weaponmask"),
				weapons
			)
		def to_json(self):
			obj = asdict(self)
			for id, data in self.weapons.items():
				for key, value in data.items():
					if isinstance(value, Vehicle._weapon):
						obj["weapons"][id][key] = value.to_json()

			return obj
	default_presets: tuple[_defaultPreset] | None = None

	@dataclass(frozen=True, slots=True)
	class _pylonData:
		index: int
		weapons: tuple[dict[str, Vehicle._weapon|int|dict[str, int]]]

		@classmethod
		def from_json(cls, data:dict[str, int|dict[str, int]], all_data:dict[str, Any]):
			index = data.get("index")
			if (index is None):
				raise LookupError("No index value for pylon")

			weapons = []
			for k, v in data.items():
				if k == "index":
					continue
				entry = {}
				entry[k] = {}
				for key, value in v.items():
					if key == "DependentWeaponPreset":
						entry[k]["dependsOn"] = {}
						for name, idx in value.items():
							entry[k]["dependsOn"][name] = idx
					elif key == "BannedWeaponPreset":
						entry[k]["bannedPreset"] = {}
						for name, idx in value.items():
							entry[k]["bannedPreset"][name] = idx
					else:
						entry[k][key] = Vehicle._weapon.from_json(value, all_data[key])
				weapons.append(entry)
			return cls(index, tuple(weapons))
		def to_json(self):
			new_weapons = []
			for idx, weapon in enumerate(self.weapons):
				new_weapons.append({})
				for k, v in weapon.items():
					if k == "dependsOn":
						new_weapons[idx][k]["dependsOn"] = v
					elif k == "bannedPreset":
						new_weapons[idx][k]["bannedPreset"] = v
					elif isinstance(v, Vehicle._weapon):
						new_weapons[idx][k] = v.to_json()
					else:
						new_weapons[idx][k] = v

			return {
				"index": self.index,
				"weapons": tuple(new_weapons)
			}
	pylon_configurations: tuple[_pylonData]

	@dataclass(frozen=True, slots=True)
	class _computer:
		gun_ccip: bool
		turret_ccip: bool
		bombs_ccip: bool
		rocket_ccip: bool
		gun_ccrp: bool
		turret_ccrp: bool
		bombs_ccrp: bool
		rocket_ccrp: bool
		laser_designator: bool
		poi_designator: bool
		poi_memory: bool
		aiming_point_memory: bool
		gyro_sight: bool

		def to_json(self):
			return asdict(self)
	computer:_computer

	@dataclass(frozen=True, slots=True)
	class _nightvision:
		@dataclass(frozen=True, slots=True)
		class entry:
			resolution: tuple[int, int]
			generation: str
			noise: float
			index: int
			ghosting: float | None = None
			lightMult: float | None = None
		sightThermal: entry|None
		sightTgtPodThermal: entry|None
		gunnerIr: entry|None
		pilotIr: entry|None

		def to_json(self):
			obj = asdict(self)
			for key, value in obj.items():
				if isinstance(value, self.entry):
					obj[key] = asdict(value)
			return obj
	night_vision: _nightvision

	@dataclass(frozen=True, slots=True)
	class _preset:
		name: str = None
		weapons: tuple[Weapon] = ()

		def to_json(self):
			_ = asdict(self)
			_["weapons"] = tuple([i.to_json() for i in self.weapons])
			return _

	@dataclass(frozen=True, slots=True)
	class _modification:
		id: str
		prevModification: str | None
		reqModification: str | None
		tier: int | None
		effects: dict[str, float]
		modClass: str | None
		extras: dict[str, Any]
		@classmethod
		def from_json(cls, mod_id:str, data:dict[str, Any]):
			extras = {k:v for k, v in data.items() if k not in ["prevModification","reqModification","tier","effects","modClass"]}
			return cls(
				mod_id,
				data.get("prevModification"),
				data.get("reqModification"),
				data.get("tier"),
				data.get("effects", {}),
				data.get("modClass"),
				extras
			)
		def to_json(self):
			return asdict(self)
	modifications:tuple[_modification]

	@dataclass(frozen=True, slots=True)
	class _wpcost:
		@dataclass(frozen=True, slots=True)
		class _GamemodesSplit:
			arcade: float
			realistic: float
			simulator: float|None = None
			realistic_ground: float|None = None
			simulator_ground: float|None = None
			@classmethod
			def from_json(cls, data:dict[str, Any], base:str):
				return cls(
					float(data[f"{base}Arcade"]),
					float(data[f"{base}Historical"]),
					float(data[f"{base}Simulation"]) if f"{base}Simulation" in data else None,
					float(data[f"{base}TankHistorical"]) if f"{base}TankHistorical" in data else None,
					float(data[f"{base}TankSimulation"]) if f"{base}TankSimulation" in data else None
				)
		price: int
		requiredRP: int
		trainCost: int
		expertCost: int
		aceCostGE: int
		aceCostRP: int
		repairTimeHrs: _GamemodesSplit
		repairTimeHrsNoCrew: _GamemodesSplit
		repairCost: _GamemodesSplit
		repairCostPerMin: _GamemodesSplit
		repairCostFullUpgraded: _GamemodesSplit | None
		battleTimeAward: _GamemodesSplit
		avgAward: _GamemodesSplit
		rewardMultiplier: _GamemodesSplit
		RpMultiplier: float
		battleTime: _GamemodesSplit
		rank: int
		battleRating: _GamemodesSplit
		country: str
		unitClass: str
		speed: float | None
		maxAmmo: int | None
		maxFlightTimeMinutes: int | None
		requiredUnit: str | None
		crewCount: int | None
		givesNationBonus: bool
		has_customizable_weapons:bool
		turretSpeed: tuple[int, int] | None
		hideUnlessOwned: bool

		@classmethod
		def from_json(cls, data:dict[str, Any]):
			return cls(
				data["value"],
				data.get("reqExp", 0),
				data["trainCost"],
				data["train2Cost"],
				data["train3Cost_gold"],
				data["train3Cost_exp"],
				cls._GamemodesSplit.from_json(data, "repairTimeHrs"),
				cls._GamemodesSplit.from_json(data, "repairTimeHrsNoCrew"),
				cls._GamemodesSplit.from_json(data, "repairCost"),
				cls._GamemodesSplit.from_json(data, "repairCostPerMin"),
				cls._GamemodesSplit.from_json(data, "repairCostFullUpgraded") if "repairCostFullUpgradedArcade" in data else None,
				cls._GamemodesSplit.from_json(data, "battleTimeAward"),
				cls._GamemodesSplit.from_json(data, "avgAward"),
				cls._GamemodesSplit.from_json(data, "rewardMul"),
				data["expMul"],
				cls._GamemodesSplit.from_json(data, "battleTime"),
				data["rank"],
				cls._GamemodesSplit.from_json(data, "economicRank"),
				Vehicle.convert_country(data["country"]),
				data["unitClass"],
				data.get("speed"),
				data.get("maxAmmo"),
				data.get("maxFlightTimeMinutes"),
				data.get("reqAir"),
				data.get("crewTotalCount"),
				data.get("doesItGiveNationBonus", False),
				data.get("hasWeaponSlots", False),
				tuple(_) if (_:=data.get("turretSpeed")) is not None else None,
				data.get("showOnlyWhenBought", False)
			)

		def to_json(self):
			obj = asdict(self)

			for key, value in obj.items():
				if isinstance(value, self._GamemodesSplit):
					obj[key] = asdict(value)

			return obj
	economy: _wpcost

	@dataclass(frozen=True, slots=True)
	class Localization:
		language: str
		short: str
		long: str

		def to_json(self):
			return {self.language: {
				"short": self.short,
				"long": self.long
			}}

	localizations: tuple[Localization]
	statcard_image: Path
	techtree_image: Path

	def __init__(
		self,
		vehicle_paths:VehiclePaths,
		data:dict[str, Any]
	):
		self.identifier = vehicle_paths.vehicle_id
		self.version = shared.VERSION

		self.sensors = []
		self.tags = []
		self.subtypes = []
		self.modifications = []

		self._parse_economy()
		self._parse_unittags()
		self._parse_data(data)
		self._parse_localization()

		self.statcard_image = vehicle_paths.images.statcard
		self.techtree_image = vehicle_paths.images.techtree

	@classmethod
	async def from_id(cls, vehicle_id:str):
		await shared.check_update()
		paths = get_vehicle_paths(vehicle_id)
		if paths is None:
			return None
			raise LookupError(f"Could not find vehicle '{vehicle_id}'")
		data:dict[str, Any] = await asyncio.to_thread(loads, await asyncio.to_thread(paths.vehicleData.read_text))
		return cls(paths, data)

	@staticmethod
	def convert_country(country_code:str) -> str:
		return country_code.removeprefix("country_")

	async def get_sensors(self) -> tuple[Sensor]:
		sensors = []
		for sensor in self.sensors:
			sensors.append(await Sensor.from_id(sensor))
		return tuple(sensors)

	async def get_weapons(self) -> dict[str, dict[str, Weapon]]:
		weapons = {
			"default": {},
			"custom": {}
		}
		for preset in self.default_presets:
			for weapon in preset.weapons:
				if weapon in weapons["default"]:
					continue
				weapons["default"][weapon] = await Weapon.from_id(weapon)
		for pylon in self.pylon_configurations:
			for preset in pylon.weapons:
				for loadout in preset.values():
					for name in loadout:
						if name in ["dependsOn", "BannedPreset"]:
							continue
						weapons["custom"][name] = await Weapon.from_id(name)

		return weapons

	def _parse_localization(self):
		localizations = []

		entry = shared.UNIT_LOC.get(self.identifier)
		if entry is None:
			self.localizations = tuple()
			return
		long_line = entry["shop"]
		short_line = entry["short"]
		languages = shared.LOC_META["text_translation"]["lang"]
		for lang in languages:
			localizations.append(self.Localization(
				lang,
				short_line.get(f"<{lang}>"),
				long_line.get(f"<{lang}>")
			))

		self.localizations = tuple(localizations)

	def _parse_unittags(self):
		vehicleDataEntry:dict[str, str|dict] = shared.VEHICLE_DATA.get(self.identifier)
		if (vehicleDataEntry is None):
			return
		self.vehicle_stats = vehicleDataEntry.get("Shop")
		tags:dict[str, bool] = vehicleDataEntry["tags"]

		self.type = vehicleDataEntry["type"]
		for tag in tags:
			if tag.startswith("country_") or tag == self.type:
				continue
			elif tag.startswith("type_"):
				self.subtypes.append(tag.removeprefix("type_"))
			else:
				self.tags.append(tag)

		release = vehicleDataEntry.get("releaseDate", "1970-01-01 00:00:00")
		if release == '':
			release = "1970-01-01 00:00:00"
		self.release_date = datetime.fromisoformat(release)

		if ("operatorCountry" in vehicleDataEntry):
			if isinstance(vehicleDataEntry["operatorCountry"], list):
				self.operator = [self.convert_country(i) for i in vehicleDataEntry["operatorCountry"]]
			else:
				self.operator = self.convert_country(vehicleDataEntry["operatorCountry"])
		else:
			self.operator = self.economy.country or None

	def _parse_economy(self):
		self.economy = self._wpcost.from_json(shared.WPCOST[self.identifier])

		weaponry = shared.WPCOST[self.identifier]["weapons"]
		def_presets = []
		pylons = []
		for k, v in weaponry.items():
			if (k.startswith(self.identifier)): # Default presets
				def_presets.append(self._defaultPreset.from_json(k, v, weaponry))
			elif (k == "custom_presets"): # Custom Presets
				if isinstance(v["slot"], dict):
					pylons.append(self._pylonData.from_json(v["slot"], weaponry))
				else:
					for pylon in v["slot"]:
						pylons.append(self._pylonData.from_json(pylon, weaponry))
		self.default_presets = tuple(def_presets)
		self.pylon_configurations = tuple(pylons)
		#endregion

	def _parse_data(self, data: dict):
		self.computer = self._computer(
			gun_ccip = data.get("haveCCIPForGun", False),
			turret_ccip = data.get("haveCCIPForTurret", False),
			bombs_ccip = data.get("haveCCIPForBombs", False),
			rocket_ccip = data.get("haveCCIPForRocket", False),
			gun_ccrp = data.get("haveCCRPForGun", False),
			turret_ccrp = data.get("haveCCRPForTurret", False),
			bombs_ccrp = data.get("haveCCRPForBombs", False),
			rocket_ccrp = data.get("haveCCRPForRocket", False),
			laser_designator = data.get("laserDesignator", False),
			poi_designator = data.get("havePointOfInterestDesignator", False),
			poi_memory = data.get("hasPointOfInterestMemory", False),
			aiming_point_memory = data.get("hasAimingPointsMemory", False),
			gyro_sight = data.get("gyroSight", False)
		)

		#region NVDs
		tmp:dict[str, list[dict[str, Any]]] = data.get("nightVision", {})
		for k, v in tmp.items():
			if "ir" in k.lower():
				tmp[k]["generation"] = IR_VISION_GENERATIONS.get(tuple(v["resolution"]), "Unknown")
			elif "thermal" in k.lower():
				tmp[k]["generation"] = THERMAL_VISION_GENERATIONS.get(tuple(v["resolution"]), "Unknown")
			elif "nightvisiondmpart" in k.lower():
				pass
			else:
				raise KeyError(f"Type of night vision '{k}' not found")

		self.night_vision = self._nightvision(
			self._nightvision.entry(
				tuple(tmp["sightThermal"]["resolution"]),
				tmp["sightThermal"]["generation"],
				tmp["sightThermal"]["noiseFactor"],
				tmp["sightThermal"].get("index", -1)
			) if tmp.get("sightThermal") is not None else None,
			self._nightvision.entry(
				tuple(tmp["sightTPodThermal"]["resolution"]),
				tmp["sightTPodThermal"]["generation"],
				tmp["sightTPodThermal"]["noiseFactor"],
				tmp["sightTPodThermal"].get("index", -1)
			) if tmp.get("sightTPodThermal") is not None else None,
			self._nightvision.entry(
				tuple(tmp["gunnerIr"]["resolution"]),
				tmp["gunnerIr"]["generation"],
				tmp["gunnerIr"]["noiseFactor"],
				-1,
				tmp["gunnerIr"]["ghosting"],
				tmp["gunnerIr"]["lightMult"]
			) if tmp.get("gunnerIr") is not None else None,
			self._nightvision.entry(
				tuple(tmp["pilotIr"]["resolution"]),
				tmp["pilotIr"]["generation"],
				tmp["pilotIr"]["noiseFactor"],
				-1,
				tmp["pilotIr"]["ghosting"],
				tmp["pilotIr"]["lightMult"]
			) if tmp.get("pilotIr") is not None else None
		)
		#endregion

		#region Sensors
		sensorsData = data.get("sensors", {"sensor":[]})
		if not isinstance(sensorsData, dict):
			raise RuntimeError("Sensors entry not a dict")
		if "sensor" in sensorsData:
			if isinstance(sensorsData["sensor"], dict):
				blkname = sensorsData["sensor"].get("blk")
				if blkname is not None:
					self.sensors.append(shared.referenceToPath(blkname).name.removesuffix(".blkx"))
			else:
				for sensor in sensorsData["sensor"]:
					blkname:str = sensor.get("blk")
					if blkname is None:
						continue
					self.sensors.append(shared.referenceToPath(blkname).name.removesuffix(".blkx"))
		elif "fireDirecting" in sensorsData:
			pass # TODO: Navy stuff, no data retrieved currently
		#endregion

		self.modifications = tuple([self._modification.from_json(k, v) for k,v in data.get("modifications", {}).items()])
		pass

	def to_json(self):
		langs = {}
		for loc in self.localizations:
			langs.update(loc.to_json())
		obj = {
			"id": self.identifier,
			"data_version": self.version,
			"economy": self.economy.to_json(),
			"modifications": [i.to_json() for i in self.modifications],
			"nightvision": self.night_vision.to_json(),
			"computers": self.computer.to_json(),
			"release_date": self.release_date,
			"type": self.type,
			"subtypes": self.subtypes,
			"operator": self.operator,
			"tags": self.tags,
			"stats": self.vehicle_stats,
			"default_presets": tuple([i.to_json() for i in self.default_presets]) if self.default_presets else None,
			"pylon_configurations": tuple([i.to_json() for i in self.pylon_configurations]) if self.pylon_configurations else None,
			"localizations": langs,
			"sensors": self.sensors
		}
		return obj
