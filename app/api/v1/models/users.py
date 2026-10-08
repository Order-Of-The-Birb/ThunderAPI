from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from ..shared import IntString
from enum import Enum
from bisect import bisect_right
from .clans import PLATFORM_NAMES

COUNTRIES = Literal[
	"country_usa",
	"country_germany",
	"country_ussr",
	"country_britain",
	"country_japan",
	"country_china",
	"country_italy",
	"country_france",
	"country_sweden",
	"country_israel"
]
SIMPLE_COUNTRIES = Literal[
	"usa",
	"germany",
	"ussr",
	"britain",
	"japan",
	"china",
	"italy",
	"france",
	"sweden",
]
GAMEMODES = Literal[
	"arcade",
	"realistic",
	"hardcore"
]
SPECIFIC_GAMEMODES = Literal[
	"air_arcade",
	"air_realistic",
	"air_simulation",
	"tank_arcade",
	"tank_realistic",
	"tank_simulation",
	"test_ship_arcade",
	"test_ship_realistic",
	"helicopter_arcade"
]
VEHICLE_TYPES = Literal[
	"fighter",
	"bomber",
	"assault",
	"tank",
	"heavy_tank",
	"tank_destroyer",
	"SPAA",
	"ship",
	"torpedo_boat",
	"gun_boat",
	"torpedo_gun_boat",
	"submarine_chaser",
	"destroyer",
	"naval_ferry_barge",
	"helicopter",
	"cruiser",
	"human"
]

class getUserDirectModel(BaseModel):
	class summaryModel(BaseModel):
		class summaryGameModeModel(BaseModel):
			class vehicleModel(BaseModel):
				timePlayed: int
				air_kills: int
				ground_kills: int
				naval_kills: int
				respawns: int            
			missionsComplete: int
			victories: int
			fighter:vehicleModel
			bomber: vehicleModel
			assault: vehicleModel
			tank: vehicleModel
			heavy_tank: vehicleModel
			tank_destroyer: vehicleModel
			SPAA: vehicleModel
			ship: vehicleModel
			torpedo_boat: vehicleModel
			gun_boat: vehicleModel
			torpedo_gun_boat: vehicleModel
			submarine_chaser: vehicleModel
			destroyer: vehicleModel
			naval_ferry_barge: vehicleModel
			helicopter: vehicleModel
			cruiser: vehicleModel
			human: vehicleModel   
		single_played: dict[GAMEMODES, summaryGameModeModel]
		pvp_played: dict[GAMEMODES, summaryGameModeModel]
		skirmish_played: dict[GAMEMODES, summaryGameModeModel]
		campaign_played: dict[GAMEMODES, summaryGameModeModel]
		dynamic_played: dict[GAMEMODES, summaryGameModeModel]
		builder_played: dict[GAMEMODES, summaryGameModeModel]
		other_played: dict[GAMEMODES, summaryGameModeModel]

	nick: str
	lastDay: int
	registerDay: int
	userid: IntString
	exp: int
	expConverted: int
	numEliteUnits: int
	title: str
	icon: int
	iconName: str
	frame: str
	background: str
	shcType: str
	penaltyStatus: str
	era: dict[
		COUNTRIES, 
		dict[
			Literal[
				"Aircraft",
				"Tank",
				"Ship",
				"Helicopter",
				"Boat",
				"Human"
			], int
		]]
	unitsPerCountry: dict[COUNTRIES, dict[Literal["numUnits", "numEliteUnits"], int]]
	aircrafts: dict[COUNTRIES, dict[str, int]]
	slots: dict[COUNTRIES, dict[str, int]]
	summary: summaryModel
	unlocks: dict[str, dict[Literal["type"], Literal["achievement", "challenge"]]]
	closedUnlocks: dict
	titles: dict
	userstat: dict
	classinessAwards: dict
	leaderboard: dict[str, dict[str, dict]]

class TerseReturnModel(BaseModel):
	#region Showcase Models
	class Showcase_FavMode_Model(BaseModel): # Favorite Mode
		class ModeStatsModel(BaseModel): 
			each_player_session: int
			each_player_victories: int
			flyouts: int
			kills_ai: int
			kills_player_or_bot: int
			score: int
		mode: GAMEMODES
		modeValue: ModeStatsModel = Field(description="Key value is the value set for `mode`")
	class Showcase_BH_Model(BaseModel): # Battle-Hardened 
		class ModeStatsModel(BaseModel):
			average_score: float
			avg_rel_position: float
			each_player_session: int
			each_player_victories: int
			efficiency_vs_ai: float
			efficiency_vs_players: float
		h_mode: GAMEMODES
		h_modeValue: ModeStatsModel = Field(description="Key value is the value set for `h_mode`")
	class Showcase_FavUnit_Model(BaseModel): # Favorite vehicle
		difficulty: GAMEMODES
		vehicle: str = Field(
			description="Internal name of the vehicle", 
			examples=["saab_jas39e", "germ_leopard_2pl", "tiger_had_spain"]
		)
	class Showcase_NukeDrop_Model(BaseModel): # Atomic Ace
		atomic_ace__counter: int = Field(description="Number of times the user has dropped a nuke")
	class Showcase_NukeKill_Model(BaseModel): # Peacemaker
		peacemaker__counter: int = Field(description="Number of nuke carriers killed")
	class Showcase_unitCollector_Model(BaseModel): # Vehicle collector
		units: list[str] = Field(
			description="List of internal names of the vehicles showcased", 
			examples=[
				["ussr_object_279", "ussr_pt_76_57", "douglas_a_1h"], 
				["germ_panther_II","germ_pzkpfw_VI_ausf_b_tiger_IIh_kwk46","germ_flakpanzer_V_Coelian"]
				])
		counts: dict[COUNTRIES, int] = Field(description="Number of vehicles collected per country")
	class Showcase_AceOfSpades_Model(BaseModel): # Ace of spades 
		class AcedUnitsModel(BaseModel):
			filteredTotal: int
			Aircraft: dict[SIMPLE_COUNTRIES, int]
			Boat: dict[SIMPLE_COUNTRIES, int]
			Helicopter: dict[SIMPLE_COUNTRIES, int]
			Ship: dict[SIMPLE_COUNTRIES, int]
			Tank: dict[SIMPLE_COUNTRIES, int]
		aced_units: AcedUnitsModel
	class Showcase_Medalist_Model(BaseModel): # Medalist 
		medals: list[str]
		total_medals: int
	class Showcase_Achievement_Model(BaseModel): # Achievement Hunter 
		achievements: list[str]
		total_steam_achievements: int
	#endregion

	background: str
	clanName: str = Field(description="Name of the clan the user is in, if applicable", examples=["Order Of The Birb", ""])
	clanTag: str = Field(description="Clan tag of the clan the user is in, if applicable. Includes border. Key doesn't exist if user is not in a clan", examples=["┾PECK┿"])
	frame: str
	nick: str
	pilotIcon: str
	pilotId: int
	shcType: str
	title: str
	showcase: Showcase_FavMode_Model | Showcase_BH_Model | Showcase_FavUnit_Model | Showcase_NukeDrop_Model | Showcase_NukeKill_Model | Showcase_unitCollector_Model | Showcase_AceOfSpades_Model | Showcase_Medalist_Model | Showcase_Achievement_Model

class SelfUserDataModel(BaseModel):
	class LevelModel(BaseModel):
		name: Literal["Rookie", "Lieutenant", "Captain", "Major", "Colonel", "Commander", "Commodore", "General", "Marshal"]
		rank: int
	class UnitsDataModel(BaseModel):
		max_rank: dict[
			Literal[
				"Aircraft",
				"Tank",
				"Ship",
				"Helicopter",
				"Boat",
				"Human"
			], int
		]
		collection: dict[Literal["overall", "aced"], int]
	class SquadronModel(BaseModel):
		class SquadronUserModel(BaseModel):
			class SquadronRoleModel(BaseModel):
				name: Literal["Private", "Sergeant", "Officer", "Deputy", "Commander"]
				value: int
			class SquadronPlatformModel(BaseModel):
				name: PLATFORM_NAMES
				value: int
			initiator: IntString
			join_timestamp: int
			role: SquadronRoleModel
			platform: SquadronPlatformModel
			activity: int
			sqb_activity: int
			
		tag: str
		id: IntString
		name: str
		type: int
		user: SquadronUserModel

	nick: str
	userId: IntString
	penaltyStatus: str
	registerDay: int
	lastDay: int
	level: LevelModel
	acedVehicles: int
	unitsData: dict[COUNTRIES, UnitsDataModel]
	squadron: SquadronModel

USER_RANK: list[int] = [
	0, 500, 1800, 5000, 11600, 23500, 42700, 71700, 113200, 170100,
	245600, 322600, 401400, 482100, 564600, 648900, 735000, 822900, 912700, 1004300,
	1097700, 1192900, 1290000, 1388900, 1489600, 1592100, 1696500, 1802700, 1910700, 2020500,
	2132200, 2245700, 2361000, 2478100, 2597100, 2717900, 2840500, 2964900, 3091200, 3219300,
	3349200, 3480900, 3614500, 3749900, 3887100, 4026100, 4167000, 4309700, 4454200, 4600500,
	4748700, 4898700, 5050500, 5204100, 5359600, 5516900, 5676000, 5836900, 5999600, 6164200,
	6330600, 6498800, 6668800, 6840700, 7014400, 7189900, 7367200, 7546400, 7727400, 7910200,
	8094800, 8281300, 8469600, 8659700, 8851600, 9045400, 9241000, 9438400, 9637600, 9838700,
	10041600, 10246300, 10452800, 10661200, 10871400, 11083400, 11297200, 11512900, 11730400, 11949700,
	12170800, 12393800, 12618600, 12845200, 13073600, 13303900, 13536000, 13769900, 14005600, 14243100,
	14482500,
]

class PlayerRank(Enum):
	ROOKIE = 0, 11, "Rookie"
	LIEUTENANT = 12, 23, "Lieutenant"
	CAPTAIN = 24, 35, "Captain"
	MAJOR = 36, 47, "Major"
	COLONEL = 48, 59, "Colonel"
	COMMANDER = 60, 71, "Commander"
	COMMODORE = 72, 83, "Commodore"
	GENERAL = 84, 99, "General"
	MARSHAL = 100, 100, "Marshal"

	def __new__(cls, rank_from: int, rank_to: int, label: str):
		obj = object.__new__(cls)
		obj._value_ = rank_from          # `.value` == rank_from
		obj.rank_from = rank_from
		obj.rank_to = rank_to
		obj.label = label
		return obj

	@classmethod
	def from_level(cls, level: int) -> "PlayerRank":
		for rank in cls:
			if rank.rank_from <= level <= rank.rank_to:
				return rank
		raise ValueError(f"No rank for level {level}")

	@staticmethod
	def get_level(exp: int) -> int:
		"""Map raw account XP to the numeric player level (0–100)."""
		return bisect_right(USER_RANK, exp) - 1

	@staticmethod
	def get_rank(exp: int) -> tuple[int, PlayerRank]:
		"""Map raw account XP to (level, PlayerRank)."""
		level = PlayerRank.get_level(exp)
		return level, PlayerRank.from_level(level)
