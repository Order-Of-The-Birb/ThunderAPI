from enum import StrEnum
from typing import ClassVar

class _tableColumns(StrEnum):
	__table__: ClassVar[str]

	@classmethod
	def t(cls) -> str:
		return cls.__table__
	@classmethod
	def q(cls, column: "_tableColumns") -> str:
		return f"{cls.__table__}.{column.value}"

#region Versioning
class GitVerions(_tableColumns):
	__table__ = "git_versions"

	VER = "version"
	HASH = "git_hash"
#endregion

#region Weapons
class Weapons(_tableColumns):
	__table__ = "weapons"

	NAME = "name"
	TYPE = "type"
class Ammo(_tableColumns):
	__table__ = "ammo"

	WEAPON = "weapon"
	AMMO_INDEX = "ammo_index"
	NAME = "name"
	TYPE = "type"
	CALIBER = "caliber"
	MASS = "mass"
	SPEED = "speed"
	MAX_DISTANCE = "max_distance"
	EXPLOSIVE_TYPE = "explosive_type"
	EXPLOSIVE_MASS = "explosive_mass"
#endregion

#region Sensors
class Sensors(_tableColumns):
	__table__ = "sensors"

	NAME = "name"
	TYPE = "type"
	MAX_TGT = "max_targets"
	MSL_AIM_LEAD = "missile_aim_lead"
class Sensor_signals(_tableColumns):
	__table__ = "sensor_signals"

	SENSOR = "sensor"
	MODE = "mode"
	GROUNDCLUTTER = "ground_clutter"
	AIRCRAFT_AS_TGT = "aircraft_as_target"
	IFF = "iff"
	TGT_ID = "target_id"
	MIN_DIST = "min_distance"
	MAX_DIST = "max_distance"
	MIN_PD_SPD = "min_doppler_speed"
	MAX_PD_SPD = "max_doppler_speed"
	RANGEFINDER = "rangefinder"
class Sensor_scan_patterns(_tableColumns):
	__table__ = "sensor_scan_patterns"

	SENSOR = "sensor"
	NAME = "name"
	TYPE = "type"
	AZ_MIN = "azimuthMin"
	AZ_MAX = "azimuthMax"
	EL_MIN = "elevationMin"
	EL_MAX = "elevationMax"
	ROLL_STAB_LIMIT = "roll_stab_limit"
	PITCH_STAB_LIMIT = "pitch_stab_limit"
	PATTERN = "pattern"
class Sensor_unitId(_tableColumns):
	__table__ = "sensor_unit_id"

	SENSOR = "sensor"
	TGT_NAME = "target_name"
#endregion

#region Units
class Units(_tableColumns):
	__table__ = "units"

	UNIT = "id"
	COUNTRY = "country"
	TYPE = "type"
	RELEASE = "release_date"
	VER = "version"
	RANK = "rank"
	EVENT = "event"
	CREW_CNT = "crew_count"
	VISIBILITY = "visibility"
	HULL_ARMOR = "hull_armor"
	TURRET_ARMOR = "turret_armor"
	MASS = "mass"
	REQUIRED_VEHICLE = "required_vehicle"
	HAS_CUSTOMIZABLE_WEAPONS = "has_customizable_weapons"
	DATA_VER = "data_version"
class UnitSubtypes(_tableColumns):
	__table__ = "unit_subtypes"

	UNIT = "unit"
	TYPE = "type"
class UnitBattleratings(_tableColumns):
	__table__ = "unit_battleratings"

	UNIT = "unit"
	ARCADE = "arcade"
	REALISTIC = "realistic"
	REALISTIC_G = "realistic_ground"
	SIMULATOR = "simulator"
	SIMULATOR_G = "simulator_ground"
class UnitEconomy(_tableColumns):
	__table__ = "unit_economy"

	UNIT = "unit"
	IS_PREMIUM = "is_premium"
	IS_PACK = "is_pack"
	IS_MARKETPLACE = "is_marketplace"
	IS_SQUADRON = "is_squadron"
	PRICE = "price"
	RP_COST = "rp_cost"
	GE_COST = "ge_cost"
	TRAIN_COST = "train_cost"
	EXPERT = "expert_cost"
	ACE_GE = "ace_cost_ge"
	ACE_RP = "ace_cost_rp"
	SL_MULT_A = "sl_mul_arcade"
	SL_MULT_R = "sl_mul_realistic"
	SL_MULT_S = "sl_mul_simulator"
	EXP_MULT = "exp_mult"
	REPAIR_T_A = "repair_time_arcade"
	REPAIR_T_R = "repair_time_realistic"
	REPAIR_T_S = "repair_time_simulator"
	REPAIR_TNC_A = "repair_time_no_crew_arcade"
	REPAIR_TNC_R = "repair_time_no_crew_realistic"
	REPAIR_TNC_S = "repair_time_no_crew_simulator"
	REPAIR_C_A = "repair_cost_arcade"
	REPAIR_C_R = "repair_cost_realistic"
	REPAIR_C_S = "repair_cost_simulator"
	REPAIR_CPM_A = "repair_cost_per_min_arcade"
	REPAIR_CPM_R = "repair_cost_per_min_realistic"
	REPAIR_CPM_S = "repair_cost_per_min_simulator"
	REPAIR_CFU_A = "repair_cost_full_upgraded_arcade"
	REPAIR_CFU_R = "repair_cost_full_upgraded_realistic"
	REPAIR_CFU_S = "repair_cost_full_upgraded_simulator"
class UnitEngines(_tableColumns):
	__table__ = "unit_engines"

	UNIT = "unit"
	HP_A = "hp_ab"
	HP_RS = "hp_rb_sb"
	MAX_RPM = "max_rpm"
	MIN_RPM = "min_rpm"
	MAX_SPEED_A = "max_speed_ab"
	MAX_RSPEED_A = "max_reverse_speed_ab"
	MAX_SPEED_RS = "max_speed_rb_sb"
	MAX_RSPEED_RS = "max_reverse_speed_rb_sb"
class UnitModifications(_tableColumns):
	__table__ = "unit_modifications"

	UNIT = "unit"
	NAME = "name"
	TIER = "tier"
	REPAIR_COEFF = "repair_coeff"
	PRICE = "price"
	RP_COST = "rp_cost"
	GE_COST = "ge_cost"
	REQ_MOD = "required_modification"
	MOD_CLASS = "mod_class"
	ICON = "icon"
class UnitNV(_tableColumns):
	__table__ = "unit_nv"

	UNIT = "unit"
	COMMANDER = "commander"
	DRIVER = "driver"
	PILOT = "pilot"
	SIGHT = "sight"
	TGT_POD = "tgt_pod"
	GUNNER = "gunner"
class UnitThermal(_tableColumns):
	__table__ = "unit_thermal"

	UNIT = "unit"
	COMMANDER = "commander"
	DRIVER = "driver"
	PILOT = "pilot"
	SIGHT = "sight"
	TGT_POD = "tgt_pod"
	GUNNER = "gunner"
class UnitComputers(_tableColumns):
	__table__ = "unit_ballistic_computer"

	UNIT = "unit"
	GUN_CCIP = "gun_ccip"
	TURRET_CCIP = "turret_ccip"
	BOMBS_CCIP = "bombs_ccip"
	ROCKET_CCIP = "rocket_ccip"
	GUN_CCRP = "gun_ccrp"
	TURRET_CCRP = "turret_ccrp"
	BOMBS_CCRP = "bombs_ccrp"
	ROCKET_CCRP = "rocket_ccrp"
	LASER_DESIGNATOR = "laser_designator"
	POI_DESIGNATOR = "poi_designator"
	POI_MEM = "poi_memory"
	AIMING_POINT_MEM = "aiming_point_memory"
	GYRO_SIGHT = "gyro_sight"

class UnitAero(_tableColumns):
	__table__ = "unit_aerodynamics"

	UNIT = "unit"
	LENGTH = "length"
	WINGSPAN = "wingspan"
	WING_AREA = "wing_area"
	EMPTY_WEIGHT = "empty_weight"
	MAX_TAKEOFF_WEIGHT = "max_takeoff_weight"
	MAX_ALTITUDE = "max_altitude"
	TURN_TIME = "turn_time"
	RUNWAY_LENGTH_REQ = "runway_length_req"
	MAX_SPEED_AT_ALTITUDE = "max_speed_at_altitude"

class UnitPresets(_tableColumns):
	__table__ = "unit_presets"

	UNIT = "unit"
	NAME = "name"
class UnitPresetsWeapons(_tableColumns):
	__table__ = "unit_presets_weapons"

	PRESET = "preset"
	WEAPON = "weapon"
	COUNT = "count"
class UnitCustomizablePresetsMeta(_tableColumns):
	__table__ = "unit_customizable_presets_meta"

	UNIT = "unit"
	MAX_LOAD = "max_load"
	MAX_LOAD_LEFT_WING = "max_load_left_wing"
	MAX_LOAD_RIGHT_WING = "max_load_right_wing"
	MAX_DISBALANCE = "max_disbalance"
class UnitCustomizablePresetsPylons(_tableColumns):
	__table__ = "unit_customizable_presets_pylons"

	UNIT = "unit"
	PYLON_INDEX = "pylon_index"
	USED_FOR_DISBALANCE = "used_for_disbalance"
class UnitCustomizablePresetsPylonsWeapons(_tableColumns):
	__table__ = "unit_customizable_presets_pylons_weapons"

	UNIT = "unit"
	PYLON_INDEX = "pylon_index"
	WEAPON = "weapon"
	COUNT = "count"
#endregion
#region Localization
class UnitLoc(_tableColumns):
	__table__ = "unit_localization"

	UNIT = "unit"
	LANG = "lang"
	VALUE = "value"
class WeaponLoc(_tableColumns):
	__table__ = "weapon_localization"

	WEAPON = "weapon"
	LANG = "lang"
	VALUE = "value"
class AmmoLoc(_tableColumns):
	__table__ = "ammo_localization"

	AMMO = "ammo"
	LANG = "lang"
	VALUE = "value"
class ExplosivesLoc(_tableColumns):
	__table__ = "explosives_localization"

	EXPLOSIVE = "explosive"
	LANG = "lang"
	VALUE = "value"
#endregion