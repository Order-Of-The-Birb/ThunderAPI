from os import getenv

from fastapi import APIRouter, Path, Query, status
from fastapi import Request as faRequest
from typing_extensions import Annotated

from api.shared import limiter
from api.v1.shared import ServerBearer, TokenBearer
from utils.connection import Request
from utils.helper import dictUtil

from .backend import get_self, get_terse, get_user
from .models import SIMPLE_COUNTRIES, GamemodesEnum, TerseReturnModel, getUserDirect

router = APIRouter(
	prefix = "/users",
	tags = ["users"],
	responses = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.get(
	"/terse",
	summary = "Get several users by ID",
	response_model=dict[str, TerseReturnModel]
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_users_terse_info(
	request: faRequest,
	user: ServerBearer,
	id: Annotated[list[int], Query(
		title = "The ID of the users to get information about",
		description = "Provide multiple IDs to get information about multiple users at once",
		min_length = 1,
		max_length = 50)
	],
):
	"""Get terse information about users by their IDs."""
	return await get_terse(user, *id)

@router.get(
	"/search/{nick}",
	summary = "Get users by name",
	responses = {},
	response_model=dict[str, TerseReturnModel]
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_users_search(
	request: faRequest,
	user: ServerBearer,
	nick: Annotated[str, Path(title = "The nickname to search for")],
	limit: Annotated[int, Query(title = "How many users to retrieve", ge = 2, le = 50)] = 10,
):
	response = await Request.send_template(
		user,
		"find_users_by_nick_prefix",
		nick = nick,
		maxCount = limit
	)

	return await get_terse(user, *list(response.keys()))

@router.get(
	"/self",
	summary = "Get metadata about the logged in user",
	responses = {
		200: {"model": getUserDirect.metaModel}
	},
	response_model = getUserDirect.metaModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_self_meta(
	request: faRequest,
	user: TokenBearer
):
	return await get_self(user)

@router.get(
	"/{userid}/meta",
 	summary = "Gets metadata about a user",
	response_model=getUserDirect.metaModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_user_direct_meta(
	request: faRequest,
	user: ServerBearer,
	userid: Annotated[int, Path(title = "The ID of the user to get information about", description = "The ID of the user to get information about", gt = 0)],
):
	data = await get_user(user, userid)
	SANITIZE = (
		dictUtil.KeyRem("summary", "statistics", "countries"),
	)
	return await dictUtil.run_all(data, SANITIZE)

@router.get(
	"/{userid}/stats",
	summary = "Gets per-vehicle statistics about a user",
	response_model=dict[str, getUserDirect.statisticsModel.unitStatModel]
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_user_direct_stats(
	request: faRequest,
	user: ServerBearer,
	userid: Annotated[int, Path(title = "The ID of the user to get information about", description = "The ID of the user to get information about", gt = 0)],
	mode: Annotated[GamemodesEnum, Query(title="The gamemode to query the data for")]
):
	return (await get_user(user, userid))["statistics"].get(mode, {})

@router.get(
	"/{userid}/countries",
	summary = "Gets country data about a user",
	response_model=dict[SIMPLE_COUNTRIES, getUserDirect.countriesModel]
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_user_direct_countries(
	request: faRequest,
	user: ServerBearer,
	userid: Annotated[int, Path(title = "The ID of the user to get information about", description = "The ID of the user to get information about", gt = 0)],
):
	return (await get_user(user, userid))["countries"]


@router.get(
	"/{userid}/summary",
	summary = "Gets a summary of a user's statistics per-difficulty and per-vehicle type",
	response_model=getUserDirect.summaryModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "users")
async def get_user_direct_summary(
	request: faRequest,
	user: ServerBearer,
	userid: Annotated[int, Path(title = "The ID of the user to get information about", description = "The ID of the user to get information about", gt = 0)],
):
	return (await get_user(user, userid))["summary"]
