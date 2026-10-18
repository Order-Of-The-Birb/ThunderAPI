from os import getenv
from typing_extensions import Annotated
from fastapi import APIRouter, Path, Query, Form, HTTPException, Request as faRequest, status

from utils.connection.http import Request
from api.shared import limiter
from api.v1.backends.shared import ServerBearer, OptionalAuth, TokenBearer
from api.v1.models.clans import LogsModel, ClanModel, Roles, ApplicantModel, RolesDisplay, ClanLeaderboardModel, ClanSearchResultModel
from api.v1.models.base import SuccessEmptyDict
from api.v1.backends.clans import getClan, searchClan, getLeaderboard, getLogs


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
	"/cancelApply", 
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
	"/applicants/{clanId}", 
	summary="Gets the currently applying members"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_applicants(
	request: faRequest,
	user: ServerBearer,
	clanId: squadronId
) -> list[ApplicantModel]:
	clanData = await getClan(user, clanId)
	applicants = clanData.get("applicants")
	if applicants is None:
		return []

	return applicants
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
	squadronId = await user.entry.getSquadronId()
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
	squadronId = await user.entry.getSquadronId()
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

@router.get(
	"/logs/{clanId}", 
	summary="Gets the squadron logs"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan_logs(
	request: faRequest,
	user: OptionalAuth,
	clanId: squadronId, 
	limit: Annotated[int, Query(title="The max ammount to get at once", gt=0, le=50)] = 10,
	fromEntry: Annotated[str, Query(title="The last call's 'lastLog' value to begin searching from")] = None,
) -> LogsModel:
	return await getLogs(user, clanId, limit, fromEntry)

@router.get(
	"/search", 
	summary="Search for squadron"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan_search(
	request: faRequest,
	user: ServerBearer,
	clanName: Annotated[str, Query(title="Squadron name to look up")] = None,
	clanTag: Annotated[str, Query(title="Squadron tag to look up")] = None,
	limit: Annotated[int, Query(title="Amount of squadrons to return", gt=0, lt=50)] = 10,
	page: Annotated[int, Query(title="The page to display. Count starts from 0", ge=0)] = 0,
) -> list[ClanSearchResultModel]:
	return await searchClan(user, clanName=clanName, clanTag=clanTag, limit=limit, page=page)

@router.get(
	"/leaderboard",
	summary="Gets the leaderboard of squadrons.",
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan_leaderboard(
	request: faRequest,
	user: ServerBearer,
	limit: Annotated[int, Query(title="The max amount to get at once", gt=0, le=50)] = 20,
	page: Annotated[int, Query(title="The page to look up. Starts from 0.", ge=0)] = 0,
) -> list[ClanLeaderboardModel]:
	return await getLeaderboard(user, limit, page)

@router.get(
	"/leaderboard/{clanId}",
	summary="Gets the leaderboard position of a given squadron.",
	responses={
		404: {"description": "Clan not found"}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan_leaderboard_position(
	request: faRequest,
	user: ServerBearer,
	clanId: Annotated[int, Path(title="The squadron's ID")],
) -> ClanLeaderboardModel:
	r = await getLeaderboard(user, clanId=clanId)

	if r is None or len(r) < 1:
		raise HTTPException(404, "Clan not found")

	return r[0]

@router.get(
	"/sqb"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_sqb_brackets(
	request: faRequest,
	user: ServerBearer
):
	pass


@router.get(
	"/sqb/current"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_sqb_current_br(
	request: faRequest,
	user: ServerBearer
):
	pass

@router.get(
	"/{clanId}",
	summary="Gets data about the given squadron"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "clans")
async def get_clan(
	request: faRequest,
	user: ServerBearer,
	clanId: Annotated[int, Path(title="The squadron's ID")],
) -> ClanModel:
	return await getClan(user, clanId)