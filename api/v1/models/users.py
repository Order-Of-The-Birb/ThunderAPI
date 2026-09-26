from typing import Literal
from pydantic import BaseModel, Field
from ..shared import IntString

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
    class UnlockModel(BaseModel):
        item: str
        cachedIndex: int
        earned: bool
        progress: int
        progressMax: int

    class UnlocksModel(BaseModel):
        unlock: SelfUserDataModel.UnlockModel

    class EntitlementModel(BaseModel):
        count: int
        goldSpent: int | None = Field(default=None)
        wpConverted: int | None = Field(default=None)

    class ComplaintsDataModel(BaseModel):
        dayMark: int

    class FreeSparesStateModel(BaseModel):
        lastDayId: int

    class UserLogEntryModel(BaseModel):
        type: int
        time: int
        disabled: bool | None = Field(default=None)
        body: dict

    class ShowcaseModel(BaseModel):
        type: str
        ucFavorites: list[str]
        favoriteUnitDifficulty: str
        favoriteUnit: str | None = Field(default=None)
        favoriteGameMode: str | None = Field(default=None)
        hardenedMode: str | None = Field(default=None)
        medals: list[str]
        achievements: list[str]
        acesFilter: dict[str, str | list[str]] = Field(default_factory=dict)

    class BinaryDataMetainfoModel(BaseModel):
        class BinaryDataInfoModel(BaseModel):
            hash: str
            hint: str

        currentTag: str
        compressionSupported: str
        aces: BinaryDataInfoModel
        char: BinaryDataInfoModel
        game: BinaryDataInfoModel
        gui: BinaryDataInfoModel
        lang: BinaryDataInfoModel
        mis: BinaryDataInfoModel
        webUi: BinaryDataInfoModel
        wwdata: BinaryDataInfoModel
        regional: BinaryDataInfoModel
        regionalLang: BinaryDataInfoModel | None = Field(default=None, alias="regional-lang")

    # Preferences
    eulaVersionAccepted: int
    ndaVersionAccepted: int
    autoRefillWeapons: bool
    autoRepairAircrafts: bool
    autoBuyModifications: bool
    onlineSaveVersion: int
    allowToBeAddedToContacts: bool
    allowToBeAddedToLB: bool

    # Machine / session
    curMachineHash: str
    curMachineFingerprintHash: str

    # Penalty
    penaltyStart: int
    penaltyTill: int
    penaltyCategory: str
    penaltyComment: str

    # Timing
    serverTime: int
    registerTime: int
    expiredTimeCorrection: int
    currDayId: int
    removeTimeLimit: int

    # Economy / presentation
    presented: int
    valUnlocks: int
    goldBalance: int
    unitMaxRank: int
    premiumSavedTime: int

    # Clan
    clanTag: str
    clanName: str
    storedRequestClanId: int
    clanDuelNextReward: int
    clanSeasonStart: int
    clanSeasonInYear: int
    clanSeasonOrdinal: int

    # Platform
    currentPlatform: int
    registerPlatform: int
    rawPlatformID: int
    registerRawPlatformID: int
    charServerVersionOnLogin: int

    # Profile
    cacheProfileUniqueSessionId: int
    profileVersion: int
    remoteSuccessSaveAsyncTaskId: str
    classinessMarkPriorities: int
    pilotIcon: str
    chardToken: int
    voiceToken: str
    actualEntitlementPriceMD5: str
    actualPriceMD5: str
    actualAdverMD5: str
    entitlementPriceRefferalName: str
    isFirstBattleForDay: bool
    charDrivenNick: str

    # Nested payloads
    unlocks: UnlocksModel
    entitlementsInfo: dict[str, EntitlementModel]
    complaintsData: ComplaintsDataModel
    FreeSparesState: FreeSparesStateModel
    userlogs: dict[str, UserLogEntryModel]
    showcase: ShowcaseModel
    entitlementGiftDependencies: dict
    binaryDataMetainfo: BinaryDataMetainfoModel