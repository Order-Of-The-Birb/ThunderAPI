from fastapi import HTTPException, status
from enum import StrEnum, Enum
from utils.auth import LoginEntry

class ReplayType(StrEnum):
	RANDOM_BATTLE = "randomBattle"
	SQUADRON_TOURNAMENT = "squadron_tournament"
	CLAN_BATTLE = "clanBattle"
	TOURNAMENTS = "tournaments"
class ReplayTechType(StrEnum):
	ALL = "all"
	AIRCRAFT = "aircraft"
	HELICOPTER = "helicopter"
	TANK = "tank"
	SHIP = "ship"
	MIXED = "mixed"
class ReplayMode(Enum):
	ARCADE = "arcade"
	REALISTIC = "realistic"
	SIMULATOR = "simulation"

async def search_replay(
	user: LoginEntry,
	uid: int | None = None,
	nickname: str | None = None,
	gameType: ReplayType = ReplayType.RANDOM_BATTLE,
	techType: ReplayTechType = ReplayTechType.ALL,
	mode: set[ReplayMode] | None = None,
	limit: int = 25,
	page: int = 0
):
	raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "This code is disabled") # TODO: Create new code for replay searching
