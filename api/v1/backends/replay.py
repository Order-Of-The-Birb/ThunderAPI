from fastapi import HTTPException, status
from enum import StrEnum, Enum
from datetime import datetime, UTC
from tools import Request
from utils.auth import UserAuth

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
	user: UserAuth.Entry,
	uid: int | None = None,
	nickname: str | None = None,
	gameType: ReplayType = ReplayType.RANDOM_BATTLE,
	techType: ReplayTechType = ReplayTechType.ALL,
	mode: set[ReplayMode] | None = None,
	limit: int = 25,
	page: int = 0
):
	if user.sid is not None and user.sid.exp < datetime.now(UTC):
		raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, "Identity SID expired. Please re-login to get a new one.")
	elif user.sid is None:
		raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, "Identity SID not found. Please generate one using the `/v1/get-sid` endpoint")
	response = await Request.from_template(user, "replays_search")
	response.body["limit"] = limit
	response.body["page"] = page
	if uid is not None:
		response.body["findUserType"] = "ID"
		response.body["findUserValue"] = str(uid)
	elif nickname is not None:
		response.body["findUserType"] = "USERNAME"
		response.body["findUserValue"] = nickname
	else:
		response.body["findUserType"] = "USERNAME"
		response.body["findUserValue"] = ""

	response.body["gameType"] = gameType.value
	response.body["techType"] = techType.value
	if mode is not None:
		response.body["gameMode"] = [m.value for m in mode]

	response.headers["cookie"] = f"identity_sid={user.sid.sid};identity_id={user.uidHint}"

	resp = await response.send()

	return resp