from fastapi import APIRouter

from .auth_router import router as authRouter
from .clans_router import router as clanRouter
from .general_router import router as generalRouter
from .marketplace_router import router as tradeRouter
from .replays_router import router as replayRouter
from .units_router import router as unitRouter
from .users_router import router as userRouter

router = APIRouter(
    prefix="/v1"
)
router.include_router(authRouter)
router.include_router(clanRouter)
router.include_router(generalRouter)
router.include_router(tradeRouter)
router.include_router(replayRouter)
#router.include_router(unitRouter)
router.include_router(userRouter)
