from os import getenv
from typing_extensions import Annotated
from fastapi import APIRouter, Path, Query, Request as faRequest, status
from fastapi.responses import JSONResponse
from urllib.parse import unquote

from tools import Request
from api.shared import limiter
from api.v1.shared import TokenBearer
from api.v1.models.users import TerseReturnModel, getUserDirectModel
from api.v1.backends.users import get_terse


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
