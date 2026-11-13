import asyncio
from dataclasses import asdict, dataclass
from logging import getLogger
from pathlib import Path
from typing import Any, Literal

from orjson import loads

from . import shared

_logger = getLogger(__name__)

@dataclass(frozen=True, slots=True)
class _limit:
	maxValue: int|float
	minValue: int|float

	@classmethod
	def from_values(cls, value1:int|float, value2:int|float):
		return cls(
			max(value1, value2),
			min(value1, value2)
		)
	@classmethod
	def from_list(cls, data:list[int|float]|None):
		if data is None:
			return
		return cls.from_values(max(data), min(data))

	def to_json(self):
		return asdict(self)

@dataclass(frozen=True, slots=True)
class Sensor:
	@dataclass(frozen=True, slots=True)
	class Antenna:
		angleHalfSens: float
		sideLobesSensitivity: float

		def to_json(self):
			return asdict(self)
	@dataclass(slots=True)
	class _transiversEntry:
		type: str
		sideLobesAttenuation: float | None
		power: float
		pulseWidth: float | None
		bands: list[int]
		rcs: float
		ranges: dict[str, float]
		rangeMax: float
		multipathEffect: list[float]
		antenna: Sensor.Antenna | dict[str, Sensor.Antenna]
		visibilityType: Literal["infraRed", "radarIntercept", "optic"]
		@classmethod
		def from_json(cls, _type:str, data:dict[str, float|int]):
			if "power" in data:
				power = data["power"]
			elif "pulsePower" in data:
				power = data["pulsePower"]

			if "band" in data:
				if isinstance(data["band"], int):
					bands = [data["band"],]
				else:
					bands = data["band"]
			else:
				bands = []

			if ("receiver" in data):
				receiver:dict[str, float|dict] = data["receiver"]
				rcs = receiver.get("rcs", None)
				ranges = {}
				for k, v in receiver.items():
					if not k.startswith("range") and k != "rangeMax":
						continue
					ranges[k] = v
				rangeMax = receiver["rangeMax"]
			else:
				rcs = data.get("rcs", None)
				ranges = {}
				for k, v in data.items():
					if not k.startswith("range") and k != "rangeMax":
						continue
					ranges[k] = v
				rangeMax = data["rangeMax"]

			if "antenna" in data:
				if "sideLobesSensitivity" in data["antenna"]:
					antenna = Sensor.Antenna(
						data["antenna"]["angleHalfSens"],
						data["antenna"]["sideLobesSensitivity"]
					)
				elif "azimuth" in data["antenna"]:
					antenna = {
						"azimuth": Sensor.Antenna(
							data["antenna"]["azimuth"]["angleHalfSens"],
							data["antenna"]["azimuth"]["sideLobesSensitivity"]
						),
						"elevation": Sensor.Antenna(
							data["antenna"]["elevation"]["angleHalfSens"],
							data["antenna"]["elevation"]["sideLobesSensitivity"]
						),
					}

			return cls(
				_type,
				data.get("sideLobesAttenuation"),
				power,
				data.get("pulseWidth"),
				bands,
				rcs,
				ranges,
				rangeMax,
				[],
				antenna,
				data.get("visibilityType")
			)
		def to_json(self):
			obj = asdict(self)
			for key, value in obj.items():
				if isinstance(value, Sensor.Antenna):
					obj[key] = value.to_json()
				elif isinstance(value, dict):
					for antenna, entry in value.items():
						if not isinstance(entry, Sensor.Antenna):
							continue
						obj[key][antenna] = entry.to_json()

			return obj
	@dataclass(frozen=True, slots=True)
	class _illuminationTransmitter:
		power: float
		antenna: Sensor.Antenna

		def to_json(self):
			obj = asdict(self)
			for key, value in obj.items():
				if isinstance(value, Sensor.Antenna):
					obj[key] = value.to_json()

			return obj
	@dataclass(frozen=True, slots=True)
	class _signalEntry:
		@dataclass(frozen=True, slots=True)
		class _distance:
			presents: bool
			minValue: float
			maxValue: float
			width: float | None

			@classmethod
			def from_json(cls, data:dict[str, Any]|None) -> Sensor._signalEntry._distance | None:
				if data is None:
					return
				return cls(
					data["presents"],
					data["minValue"],
					data["maxValue"],
					data.get("width")
				)
			def to_json(self):
				return asdict(self)
		@dataclass(frozen=True, slots=True)
		class _dopplerSpeed:
			presents: bool
			minValue: float
			maxValue: float
			signalWidthMin: float # Yes i had to make a new dataclass for a single value
			width: float

			@classmethod
			def from_json(cls, data:dict[str, Any]|None) -> Sensor._signalEntry._dopplerSpeed | None:
				if data is None:
					return
				if not data["presents"]:
					return

				return cls(
					data["presents"],
					data["minValue"],
					data["maxValue"],
					data["signalWidthMin"],
					data["width"]
				)
			def to_json(self):
				return asdict(self)
		type: str
		groundClutter: bool
		aircraftAsTarget: bool
		IFF: bool
		targetId: bool
		mainBeamNotchWidth: float
		mainBeamNotchMaxElevation: float
		distance: _distance | None
		dopplerSpeed: _dopplerSpeed | None
		extras: dict[str, Any]

		@classmethod
		def from_json(cls, _type:str, data:dict[str, Any]):
			return cls(
				_type,
				data.get("groundClutter", True),
				data.get("aircraftAsTarget", True),
				data.get("friendFoeId", False),
				data.get("targetId", False),
				data.get("mainBeamNotchWidth"),
				data.get("mainBeamNotchMaxElevation"),
				cls._distance.from_json(data.get("distance")),
				cls._dopplerSpeed.from_json(data.get("dopplerSpeed")),
				{k:v for k, v in data.items() if k not in ["groundClutter", "aircraftAsTarget", "friendFoeId", "targetId", "mainBeamNotchWidth", "mainBeamNotchMaxElevation", "distance", "dopplerSpeed"]}
			)

		def to_json(self):
			obj = asdict(self)
			for key, value in obj.items():
				if isinstance(value, (self._distance, self._dopplerSpeed)):
					obj[key] = asdict(value)
			return obj
	@dataclass(frozen=True, slots=True)
	class _scanPattern:
		name: str
		scanPatternSet: str
		type: str
		azimuthLimits: _limit
		elevationLimits: _limit
		rollStabLimit: float
		pitchStabLimit: float
		period: float
		width: float
		barHeight: float
		barsCount: int
		rowMajor: bool

		@classmethod
		def from_data(cls, name: str, data:dict[str, Any], scanPatternSet:str):
			return cls(
				name,
				scanPatternSet,
				data.get("type"),
				_limit.from_list(data.get("azimuthLimits")),
				_limit.from_list(data.get("elevationLimits")),
				data.get("rollStabLimit"),
				data.get("pitchStabLimit"),
				data.get("period"),
				data.get("width"),
				data.get("barHeight"),
				data.get("barsCount"),
				data.get("rowMajor")
			)

		def to_json(self):
			obj = asdict(self)
			for key, value in obj.items():
				if isinstance(value, _limit):
					obj[key] = value.to_json()

			return obj
	@dataclass(frozen=True, slots=True)
	class _targetTypeId:
		name: str
		targetType: list[str]

		@classmethod
		def from_json(cls, data:dict[str, Any]):
			return cls(
				data.get("name"),
				data.get("targetType")
			)
		def to_json(self):
			return asdict(self)
	@dataclass(frozen=True, slots=True)
	class _vehicleTypeId:
		name: str
		propulsion: dict[str, str|int]

		@classmethod
		def from_json(cls, data:dict[str, Any]):
			return cls (
				data.get("name"),
				data.get("targetPropulsion")
			)

		def to_json(self):
			return asdict(self)

	type:str
	name:str
	displayName: str
	maxTargets:int
	transivers: tuple[_transiversEntry]
	illuminationTransmitter: _illuminationTransmitter | None
	signals: tuple[_signalEntry]
	signals_track:bool | None
	scopeRangeSets: dict[str, tuple[float]]
	scanPatterns: tuple[_scanPattern]
	targetTypeId: tuple[_targetTypeId]
	vehicleTypeId: tuple[_vehicleTypeId]
	sizeRanges: dict[str, _limit]

	@classmethod
	async def from_id(cls, sensor:str):
		for path in shared.DataLocations.SENSOR_DATA.rglob(f"{sensor}.blkx"):
			return await cls.from_path(path)
		_logger.error(f"Could not find sensor '{sensor}'")
		return None
	@classmethod
	async def from_path(cls, sensor: Path):
		if not sensor.exists():
			raise LookupError(f"Sensor file not found at {sensor}")
		data = await asyncio.to_thread(loads, await asyncio.to_thread(sensor.read_text))
		name = ".".join(sensor.name.split(".")[:-1])
		maxTargets = data.get("weaponTargetsMax", -1)

		transivers = []
		for k, v in data.get("transivers", {}).items():
			transivers.append(cls._transiversEntry.from_json(k, v))

		_ = data.get("illuminationTransmitter", {})
		if _:
			illuminationTransmitter = cls._illuminationTransmitter(
				_["power"],
				cls.Antenna(
					_["antenna"]["angleHalfSens"],
					_["antenna"]["sideLobesSensitivity"]
				)
			)
		else:
			illuminationTransmitter = None

		signals = []
		for k, v in data.get("signals", {}).items():
			if k.lower() == "track":
				track = v
				continue
			signals.append(cls._signalEntry.from_json(k, v))

		scopeRangeSets = {}
		for k, v in data.get("scopeRangeSets", {}).items():
			scopeRangeSets[k] = [i for i in v]

		tmp = {}
		for k, v in data.get("scanPatternSets", {}).items():
			tmp[k] = [i for i in v.values()]
		scanPatterns = []
		for k, v in data.get("scanPatterns", {}).items():
			patternSet = next((i for i, j in tmp.items() if k in j), None)
			scanPatterns.append(cls._scanPattern.from_data(k, v, patternSet))

		sizeRanges = {}
		vehicleTypeId = []
		targetTypeId = []
		for v in data.get("targetTypeId", []):
			name:str = v.get("name").removeprefix("hud/")
			if (_:=v.get("sizeRange", [])):
				sizeRanges[name] = _limit.from_list(_)
			elif name in ["helicopter", "single prop", "multi prop", "single jet", "multi jet", "rocket"]:
				vehicleTypeId.append(cls._vehicleTypeId.from_json(v))
			else:
				targetTypeId.append(cls._targetTypeId.from_json(v))

		self =  cls(
			data["type"],
			name,
			data.get("name"),
			maxTargets,
			tuple(transivers),
			illuminationTransmitter,
			tuple(signals),
			track,
			scopeRangeSets,
			tuple(scanPatterns),
			tuple(targetTypeId),
			tuple(vehicleTypeId),
			sizeRanges
		)
		shared.sensor_cache[sensor] = self
		return self

	def to_json(self):
		obj = asdict(self)
		for key, value in obj.items():
			if isinstance(value, self._illuminationTransmitter):
				obj[key] = value.to_json()
			elif isinstance(value, tuple):
				new = []
				for item in value:
					if isinstance(item, (self._transiversEntry, self._scanPattern, self._targetTypeId, self._targetTypeId, self._vehicleTypeId)):
						new.append(item.to_json())
					else:
						# Just in case
						new.append(item)
				obj[key] = tuple(new)
			elif isinstance(value, dict):
				for k, v in value.items():
					if isinstance(v, _limit):
						obj[key][k] = v.to_json()

		return obj
