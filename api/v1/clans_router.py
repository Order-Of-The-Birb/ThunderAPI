from logging import getLogger
from os import getenv
from typing_extensions import Annotated
from fastapi import APIRouter, Path, Query, Form, HTTPException, Request as faRequest, status
from fastapi.responses import JSONResponse

from tools import Request
from utils.geo import lookup_city, lookup_utc_offset
from api.shared import limiter
from api.v1.shared import TokenBearer
from api.v1.models.clans import LogsModel, ClanModel, Roles, ApplicantModel, RolesDisplay, Actions, ClanPositionModel
from api.v1.models.base import SuccessEmptyDict
from api.v1.backends.clans import getClan, searchClan

_logger = getLogger(__name__)

squadronId = Annotated[int, Path(title="The squadron's ID", gt=0)]
gaijinUserId = Annotated[int, Path(title="The user's ID", gt=0)]

router = APIRouter(
	prefix="/clans",
	tags=["clans"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.post(
	"/apply/{clanId}", 
	summary="Sends an application to the squadron, if allowed",
	responses={
		status.HTTP_409_CONFLICT: {"description": "User is already in a squadron"}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def send_application(
	request: faRequest,
	user: TokenBearer,
	clanId: squadronId,
	comment: Annotated[str, Query(description="The message sent with the application. Doesn't appear ingame, only through this API, so if the squadron isn't using an API, they won't see it")]
) -> bool:
	response = await Request.send_template(
		user, 
		"clan_membership_request",
		remove_keys=("cancelRequest"),
		_id=clanId,
		comments=comment
	)
	return response.get("clanTag") is not None

@router.post(
	"/cancelApply/", 
	summary="Cancels the current squadron application",
	responses={
		status.HTTP_409_CONFLICT: {"description": "User is already accepted into the squadron. Use the `leave` endpoint instead"}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def unsend_application(
	request: faRequest,
	user: TokenBearer,
	comment: str = ""
) -> bool:
	response = await Request.send_template(
		user, 
		"clan_membership_request",
		remove_keys=("_id"),
		comments=comment,
		cancelRequest=True
	)
	return response.get("clanTag") is None

@router.get(
	"/applicants/{clanId}", 
	summary="Gets the currently applying members"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_applicants(
	request: faRequest,
	user: TokenBearer,
	clanId: squadronId
) -> list[ApplicantModel]:
	clanData = await getClan(user, clanId)
	data = []
	candidates = clanData.get("candidates")
	if candidates is None:
		return []
	if isinstance(candidates, dict):
		newdata = {
			"uid": candidates["uid"],
			"nickname": candidates["nick"],
			"timestamp": candidates["date"],
			"comment": candidates["comments"],				
		}

		geodata = lookup_city(candidates["ip"])
		if geodata:
			newdata["geodata"] = {
				"country": geodata.country.iso_code,
				"timezone": lookup_utc_offset(geodata.location.time_zone)
			}
		return [newdata,]
	for entry in clanData.get("candidates"):
		newdata = {
			"uid": entry["uid"],
			"nickname": entry["nick"],
			"timestamp": entry["date"],
			"comment": entry["comments"]
		}

		geodata = lookup_city(entry["ip"])
		if geodata:
			newdata["geodata"] = {
				"country": geodata.country.iso_code,
				"timezone": lookup_utc_offset(geodata.location.time_zone)
			}
		data.append(newdata)
	return data
@router.post(
	"/accept/{userId}",
	responses={
		status.HTTP_200_OK: {
			"model": SuccessEmptyDict,
			"description": "Successfully accepted the applicant",
		},
		status.HTTP_403_FORBIDDEN: {
			"description": "You do not have permission to accept applicants"
		},
		status.HTTP_404_NOT_FOUND: {
			"description": "The given user is not an applicant"
		}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def accept_applicant(
	request: faRequest,
	user: TokenBearer,
	userId: gaijinUserId,
	role:RolesDisplay = RolesDisplay.PRIVATE
):
	squadronId = await user.getSquadronId()
	if squadronId is None:
		raise HTTPException(403, "User is not part of a squadron")
	return await Request.send_template(
		user, 
		"clan_accept_membership_request",
		userId = userId,
		_id = squadronId,
		role=Roles[role.name.upper()].value
	)

@router.post(
	"/reject/{userId}",
	responses={
		status.HTTP_200_OK: {"model": SuccessEmptyDict, "description":"Successfully rejected user"},
		status.HTTP_404_NOT_FOUND: {"description":"Applicant could not be found"},
		status.HTTP_403_FORBIDDEN: {"description":"You do not have permission to reject applicants"}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def reject_applicant(
	request: faRequest,
	user: TokenBearer,
	userId: gaijinUserId,
	message: Annotated[str, Query(title="Message to include alongside rejection")] = "",
): 
	squadronId = await user.getSquadronId()
	if squadronId is None:
		raise HTTPException(403, "User is not part of a squadron")
	return await Request.send_template(
		user, 
		"clan_reject_membership_request",
		userId = userId,
		_id = squadronId,
		comments = message
	)

@router.post(
	"/role/{userId}", 
	summary="Set a member's role", 
	description="Requires `Deputy` or `Commander` level in squadron",
	responses={
		status.HTTP_200_OK: {"model": SuccessEmptyDict},
		status.HTTP_403_FORBIDDEN: {"description": "You do not have the required permissions"}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def change_role(
	request: faRequest,
	user: TokenBearer,
	userId: gaijinUserId,
	role: Annotated[RolesDisplay, Query(title="The role to assign")],
): 
	role = Roles[role.name]
	return await Request.send_template(
		user, 
		"clan_change_member_role",
		userid = userId,
		role = role.value
	)

@router.post(
	"/kick/{userId}",
	summary="Kicks the given user",
	description="Requires either `Officer`, `Deputy` or `Commander` rank to remove someone else"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def kick_member(
	request: faRequest,
	user: TokenBearer,
	userId: gaijinUserId,
	reason: Annotated[str, Form(title="The reason for kicking")] = "",
):
	return await Request.send_template(
		user, 
		"clan_dismiss_member",
		userid = userId,
		comments = reason
	)

@router.post(
	"/leave",
	summary="Leaves the current squadron"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def leave_squadron(
	request: faRequest,
	user: TokenBearer
) -> bool:
	response = await Request.send_template(
		user, 
		"clan_leave"
	)
	return response.get("clanTag") is None

@router.get(
	"/logs/{clanId}", 
	summary="Gets the squadron logs"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan_logs(
	request: faRequest,
	user: TokenBearer,
	clanId: squadronId, 
	limit: Annotated[int, Query(title="The max ammount to get at once", gt=0, le=50)] = 10,
	fromEntry: Annotated[str, Query(title="The last call's 'lastLog' value to begin searching from")] = None,
) -> LogsModel:
	allLogs = await user.getSquadronId() == clanId
	response = await Request.from_template(
		user, 
		"clan_get_log",
		_id = clanId,
		count = limit
	)
	if (allLogs):
		response.body.pop("events")
	if fromEntry:
		response.body["last"] = fromEntry

	response = await response.send()

	logs:list[dict[str, int|str]] = []
	for item in response["log"]:
		item:dict[str, int|str]
		try:
			action = Actions[item["ev"]]
		except KeyError:
			_logger.warning(f"Unhandled log type '{item["ev"]}' found")
			continue
		logEntry = {
			"timestamp": item["time"],
			"action": {
				"value": action.value[0],
				"detail": action.value[1]
			}
		}
		if item.get("uId") is not None and not (action == Actions.rem and item.get("uid") is not None and item["uId"] == item["uid"]):
			logEntry["admin"] = {
				"_id": item["uId"],
				"nickname": item["uN"]
			}
		if item.get("uid") is not None:
			logEntry["affected"] = {
				"_id": item["uid"],
				"nickname": item["nick"],
			}
		match action:
			case Actions.role:
				logEntry.update({
					"roleChange": {
						"old": item["old"],
						"new": item["new"]
					}
				})
			case Actions.info:
				for i in ["tag", "desc", "region", "status"]: 
					if (_ := item.get(i)):
						logEntry[i] = _
			case Actions.create:
				logEntry["info"] = {}
				for i in ["type", "name", "tag", "slogan", "desc", "region", "announcement"]:
					logEntry["info"][i] = item[i]
			case Actions.reject_candidate:
				logEntry["comment"] = item["comments"]
		logs.append(logEntry)

	return JSONResponse({
		"lastLog": response["lastMark"],
		"logs": logs
	})

@router.get("/search/", summary="Search for squadron")
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan_search(
	request: faRequest,
	user: TokenBearer,
	clanName: Annotated[str, Query(title="Squadron name to look up")] = None,
	clanTag: Annotated[str, Query(title="Squadron tag to look up")] = None,
	limit: Annotated[int, Query(title="Amount of squadrons to return", gt=0, lt=50)] = 10,
	page: Annotated[int, Query(title="The page to display. Count starts from 0", ge=0)] = 0,
) -> list[ClanModel]:
	return await searchClan(user, clanName=clanName, clanTag=clanTag, limit=limit, page=page)

@router.get(
	"/leaderboard",
	summary="Gets the leaderboard of squadrons.",
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan_leaderboard(
	request: faRequest,
	user: TokenBearer,
	limit: Annotated[int, Query(title="The max amount to get at once", gt=0, le=50)] = 20,
	page: Annotated[int, Query(title="The page to look up. Starts from 0.", ge=0)] = 0,
) -> list[ClanModel]:
	response = await Request.from_template(
		user, 
		"clan_get_leaderboard",
		count=limit,
		start=limit*page
	)
	response.headers.pop("clanId")
	response = await response.send()

	if response.get("clan") is None:
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not obtain leaderboard data from Gaijin")

	modified = []
	for clan in response["clan"]:
		clan["pos"] += 1 # Convert from zero-based to one-based indexing
		modified.append(clan)
	
	return modified

@router.get(
	"/leaderboard/{clanId}",
	summary="Gets the leaderboard position of a given squadron."
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan_leaderboard_position(
	request: faRequest,
	user: TokenBearer,
	clanId: Annotated[int, Path(title="The squadron's ID")],
) -> ClanPositionModel:
	response = await Request.send_template(
		user, 
		"clan_get_leaderboard",
		clanId=clanId
	)

	if response.get("clan") is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Could not obtain leaderboard position data from Gaijin")
	return {
		"pos": response["clan"]["pos"],
		"rating": response["clan"]["astat"]["dr_era5_hist"]
	}

@router.get(
	"/{clanId}",
	summary="Gets data about the given squadron"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan(
	request: faRequest,
	user: TokenBearer,
	clanId: Annotated[int, Path(title="The squadron's ID")],
) -> ClanModel:
	return await getClan(user, clanId)