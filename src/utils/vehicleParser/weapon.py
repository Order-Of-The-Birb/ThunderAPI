import asyncio
from dataclasses import asdict, dataclass
from logging import getLogger
from pathlib import Path
from typing import Any

from orjson import loads

from utils.helper import getMultipleKeys

from . import shared
from .const import (
	BOMB_NAME,
	BOMB_TYPE,
	BOOSTER_NAME,
	BOOSTER_TYPE,
	CANNON_NAME,
	CANNON_TYPE,
	CONTAINER_NAME,
	CONTAINER_TYPE,
	EXTFUELTANK_NAME,
	EXTFUELTANK_TYPE,
	ROCKET_NAME,
	ROCKET_TYPE,
	TORPEDO_NAME,
	TORPEDO_TYPE,
)

_logger = getLogger(__name__)

@dataclass(slots=True)
class Weapon:
	@dataclass(frozen=True, slots=True)
	class _ammo:
		name: str = None
		type: str = None
		caliber: float = 0.0
		mass: float = 0.0
		speed: float = 0.0
		max_distance: float = 0.0
		explosive_type: str | None = None
		explosive_mass: float | None = 0.0

		@classmethod
		def from_json(cls, data:dict[str, Any]) -> Weapon._ammo | None:
			if not data:
				return
			return cls(
				getMultipleKeys(data, "bombName", "bulletName"),
				getMultipleKeys(data, "bombType", "bulletType"),
				data.get("caliber"),
				_[0] if isinstance(_:=data.get("mass"), list) else _,
				getMultipleKeys(data, "maxSpeedInWater", "speed", "maxSpeed"),
				getMultipleKeys(data, "distToLive", "maxDistance"),
				data.get("explosiveType"),
				data.get("explosiveMass")
			)

	name: str = None
	type: str = None
	ammo: tuple[_ammo] = tuple()

	@classmethod
	async def from_id(cls, weapon:str):
		for i in ["drop_tank","rocketguns","containers","bombguns","equipment"]:
			weapon = weapon.removeprefix(i+"_")
		for path in shared.DataLocations.WEAPON_DATA.rglob(f"{weapon}.blkx"):
			return await cls.from_path(path)
		_logger.error(f"Could not find weapon '{weapon}'")
		return None

	@classmethod
	async def from_path(cls, weapon:Path):

		self = cls()

		if not weapon.exists():
			raise LookupError(f"Weapon file not found at {weapon}")

		weapon_blk: dict = await asyncio.to_thread(loads, await asyncio.to_thread(weapon.read_text()))

		self.name = ".".join(weapon.name.split(".")[:-1])
		if (self.name == "dummy_weapon"):
			return

		weapon_type = weapon_blk.get("weaponType")

		lowercase_keys = [i.lower() for i in weapon_blk]

		if (weapon_blk.get(CANNON_NAME) or CANNON_TYPE in lowercase_keys or weapon_blk.get(CANNON_TYPE) or weapon_type == -1 or weapon_type == 1 or weapon_type == 3):
			self._get_ammo("bullet", weapon_blk)
			self.type = CANNON_NAME
		elif (weapon_blk.get(ROCKET_NAME) or ROCKET_TYPE in lowercase_keys or weapon_blk.get(ROCKET_TYPE)):
			self._get_ammo("rocket", weapon_blk)
			self.type = ROCKET_NAME
		elif (weapon_blk.get(TORPEDO_NAME) or TORPEDO_TYPE in lowercase_keys or weapon_blk.get(TORPEDO_TYPE) or weapon_type == 1):
			self._get_ammo("torpedo", weapon_blk)
			self.type = TORPEDO_NAME
		elif (weapon_blk.get(BOMB_NAME) or BOMB_TYPE in lowercase_keys or weapon_blk.get(BOMB_TYPE)):
			self._get_ammo("bomb", weapon_blk)
			self.type = BOMB_NAME
		elif (weapon_blk.get(BOOSTER_NAME) or BOOSTER_TYPE in lowercase_keys or weapon_blk.get(BOOSTER_TYPE)):
			self._get_ammo("payload", weapon_blk)
			self.type = BOOSTER_NAME
		elif (weapon_blk.get(CONTAINER_NAME) or CONTAINER_TYPE in lowercase_keys or weapon_blk.get(CONTAINER_TYPE)):
			self.type = CONTAINER_NAME
			return await self.from_path(shared.referenceToPath(weapon_blk["blk"]))
		elif (weapon_blk.get(EXTFUELTANK_NAME) or EXTFUELTANK_TYPE in lowercase_keys or weapon_blk.get(EXTFUELTANK_TYPE)):
			self._get_ammo("payload", weapon_blk)
			self.type = EXTFUELTANK_NAME
		else:
			_logger.error(f"Weapon {self.name}'s type is missing\n\n{weapon}\n\tType: {weapon_type}")
			return

		shared.weapon_cache[".".join(weapon.name.split(".")[:-1])] = self
		return self

	def _get_ammo(self, key:str, data:dict[str, Any]):
		ammo_list = []
		for k in data.keys():
			raw_ammo = None
			key_value = data.get(k)

			lowercase_keys = [i.lower() for i in data.keys()]

			if isinstance(key_value, dict) or isinstance(key_value, list) and k.lower() == key:
				raw_ammo = key_value
			elif isinstance(key_value, dict) and key in lowercase_keys:
				raw_ammo = key_value.get(key)

			if not raw_ammo:
				continue

			raw_ammo = raw_ammo if isinstance(raw_ammo, list) else [raw_ammo,]

			for ammos in raw_ammo:
				if "bullet" in ammos and isinstance(ammos["bullet"], list):
					for ammo in ammos["bullet"]:
						_ammo = self._ammo.from_json(ammo)
						ammo_list.append(_ammo)
				else:
					_ammo = self._ammo.from_json(ammos)
					ammo_list.append(_ammo)
		self.ammo = tuple(ammo_list)

	def to_json(self):
		return {
			"weapon": self.name,
			"type": self.type,
			"ammo": [asdict(i) for i in self.ammo]
		}
