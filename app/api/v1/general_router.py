from os import getenv
from typing_extensions import Annotated
from typing import Literal
from fastapi import APIRouter, Query, Request, WebSocket, status

from utils import newsManager
from utils.news import NewsEntry
from api.shared import limiter
from api.v1.shared import TokenBearer, IpString
from api.v1.backends.general import getLatestGameVer


router = APIRouter(
	tags=["general"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.get("/latestGameVersion", summary="Get latest game version")
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "general")
async def get_latest_game_ver(
	request: Request, user: TokenBearer,
	branch: Annotated[Literal["dev", "dev-stable"], Query(title="The game version to get")] = None,
) -> IpString:
	return await getLatestGameVer(branch)

@router.get(
	"/news", 
	summary="Gets the latest news from gaijin", 
	description="Puts the pinned news first (Current update changelog + latest big news). There is additionally a `/v1/news_ws` websocket, that doesn't require any authentication, and provides the news through there. This websocket is the single exception to the 'token auth everywhere' rule. Websocket returns the same format for an entry like this endpoint"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "general")
async def get_news(request: Request, user: TokenBearer) -> list[NewsEntry]:
	return await newsManager.fetch()

@router.websocket(
	"/news_ws",
	name="News stream"
)
async def news_ws(websocket: WebSocket):
	await newsManager.websocket_mgr.connect(websocket)