from os import getenv
from typing_extensions import Annotated
from fastapi import APIRouter, Path, Query, Request as faRequest, status
from fastapi.responses import JSONResponse
from urllib.parse import unquote

from tools import Request
from api.shared import limiter
from api.v1.shared import TokenBearer
from api.v1.models.users import TerseReturnModel, getUserDirectModel, PlayerRank, SelfUserDataModel
from api.v1.models.clans import Roles, RolesDisplay, Platforms
from api.v1.backends.users import get_terse
from api.v1.backends.clans import getClan

router = APIRouter(
	prefix="/users",
	tags=["users"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.get("/terse", summary="Get several users by ID")
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_users_terse_info(
	request: faRequest,
	user: TokenBearer,
	id: Annotated[list[int], Query(
		title="The ID of the users to get information about",
		description="Provide multiple IDs to get information about multiple users at once",
		min_length=1,
		max_length=50)
	],
) -> dict[str, TerseReturnModel]:
	"""Get terse information about users by their IDs."""
	return JSONResponse(await get_terse(user, *id))

@router.get(
	"/self", 
	summary="Get metadata about the logged in user",
	responses={
		200: {"model": SelfUserDataModel}
	},
	response_model=SelfUserDataModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_self_meta(
	request: faRequest,
	user: TokenBearer
):
	data = {}
	userData = await Request.send_template(
		user,
		"get_public_userstat",
		userId = user.uidHint
	)
	data["nick"] = userData["nick"]
	data["userid"] = int(userData["userid"])
	data["penaltyStatus"] = userData["penaltyStatus"]
	data["registerDay"] = userData["registerDay"]
	data["lastDay"] = userData["lastDay"]
	level = PlayerRank.get_level(userData["exp"])
	data["level"] = {
		"name": PlayerRank.from_level(level).label,
		"rank": level
	}
	data["acedVehicles"] = userData["numEliteUnits"]
	
	data["unitsData"] = {}
	for k in userData["era"]:
		data["unitsData"].setdefault(k, {})
		data["unitsData"][k]["max_rank"] = userData["era"][k]
	for k in userData["unitsPerCountry"]:
		data["unitsData"].setdefault(k, {})
		data["unitsData"][k]["collection"] = {
			"overall": userData["unitsPerCountry"][k]["numUnits"],
			"aced": userData["unitsPerCountry"][k]["numEliteUnits"]
		}

	userSquadronID = await user.getSquadronId()
	if userSquadronID:
		data["squadron"] = {
			"tag": userData["clanTag"],
			"id": int(userData["clanId"]),
			"name": userData["clanName"],
			"type": userData["clanType"]
		}
		data["squadron"]["user"] = {}
		clanData = await getClan(user, userSquadronID)
		for cuser in clanData["members"]:
			if cuser["uid"] != str(user.uidHint):
				continue

			role = Roles(cuser["role"])
			platform = Platforms(cuser["platform"])
			data["squadron"]["user"] = {
				"initiator": cuser["initiator"],
				"join_timestamp": cuser["date"],
				"role": {
					"name": RolesDisplay[role.name],
					"value": role.value
				},
				"platform": {
					"name": platform.name,
					"value": platform.value
				}
			}
			break

		data["squadron"]["user"]["activity"] = clanData.get("activity", {}).get(str(user.uidHint), {}).get("total", 0)
		data["squadron"]["user"]["sqb_activity"] = clanData.get("member_ratings", {}).get(str(user.uidHint), {}).get("dr_era5_hist", 0.0)

	return data

@router.get("/{userid}", summary="Get user by ID")
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_user_direct(
	request: faRequest,
	user: TokenBearer,
	userid: Annotated[int, Path(title="The ID of the user to get information about", description="The ID of the user to get information about", gt=0)],
) -> getUserDirectModel:
	return JSONResponse(
		await Request.send_template(
			user,
			"get_public_userstat",
			userId = userid
		)
	)

@router.get(
	"/search/{nick}",
	summary="Get users by name",
	responses={}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_users_search(
	request: faRequest,
	user: TokenBearer,
	nick: Annotated[str, Path(title="The nickname to search for")],
	limit: Annotated[int, Query(title="How many users to retrieve", ge=2, le=50)] = 10,
) -> dict[str, TerseReturnModel]:
	response = await Request.send_template(
		user,
		"find_users_by_nick_prefix",
		nick = unquote(nick),
		maxCount = limit
	)

	terseInfo = await get_terse(user, *list(response.keys()))
	return JSONResponse(terseInfo)
