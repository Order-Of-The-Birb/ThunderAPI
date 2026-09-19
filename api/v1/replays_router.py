from os import getenv
from typing_extensions import Annotated
from fastapi import APIRouter, Path, Request as faRequest, Query, status

from utils.replayParser import Replay
from api.shared import limiter
from api.v1.shared import TokenBearer
from api.v1.backends.replay import search_replay, ReplayType, ReplayMode, ReplayTechType
from api.v1.models.replay import SearchModel, DataModel, ReplayNotFoundModel


router = APIRouter(
	prefix="/replay",
	tags=["replays"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.get(
	"/search",
	summary="Searches for replays based on given parameters",
	responses={
		status.HTTP_200_OK: {"model": SearchModel},
		status.HTTP_403_FORBIDDEN: {"description": "The token has no associated `identity_sid` value associated, required for replay lookup. Get one from `/v1/get-sid`"},
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "replays")
async def search_replays(
	request: faRequest,
	user: TokenBearer,
	uid: Annotated[
		int, 
		Query(title="The UID of the user to search replays for")
	] = None,
	nickname: Annotated[
		str, 
		Query(title="The nickname of the user to search replays for")
	] = None,
	gameType: Annotated[
		ReplayType,
		Query(
			title="The type of game to search replays for",
			description="If not provided, will search for random battles",
			min_length=1
		)
	] = ReplayType.RANDOM_BATTLE,
	techType: Annotated[
		ReplayTechType,
		Query(
			title="The type of tech to search replays for",
			description="If not provided, will search for all tech types",
			min_length=1
		)
	] = ReplayTechType.ALL,
	mode: Annotated[
		set[ReplayMode] | None,
		Query(
			title="The game modes to filter by",
			description="If not provided, will search for all game modes",
		)
	] = None,
	limit: Annotated[
		int, 
		Query(
			title="The maximum number of replays to return",
			description="Must be between 1 and 100",
			ge=1,
			le=100
		)
	] = 25,
	page: Annotated[
		int, 
		Query(
			title="The page of results to return",
			description="Must be 0 or greater",
			ge=0
		)
	] = 0,
):
	return await search_replay(user, uid, nickname, gameType, techType, mode, limit, page)

@router.get(
	"/{replayId}", 
	summary="Gets data from a specified replay",
	responses={
		status.HTTP_200_OK: {"model": DataModel},
		status.HTTP_404_NOT_FOUND: {"model": ReplayNotFoundModel, "description": "Replay not found"},
		status.HTTP_425_TOO_EARLY: {"description": "Replay probably hasn't ended yet, since it isn't properly parseable yet"}
	})
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "replays")
async def get_replay(
	request: faRequest,
	user: TokenBearer,
	replayId: Annotated[
		str, 
		Path(
			title="The replay's ID to get",
			pattern=r"^[0-9a-fA-F]{1,16}$",
			description="Must be given in HEX format"
		),
	],
):
	return await Replay.get(replayId)
