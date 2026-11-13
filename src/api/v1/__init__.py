from fastapi import APIRouter

from .auth import router as authRouter
from .clans import router as clanRouter
from .general import router as generalRouter
from .marketplace import router as tradeRouter
from .replays import router as replayRouter
from .units import router as unitRouter
from .users import router as userRouter

router = APIRouter(
    prefix="/v1"
)
router.include_router(authRouter)
router.include_router(clanRouter)
router.include_router(generalRouter)
router.include_router(tradeRouter)
router.include_router(replayRouter)
router.include_router(unitRouter)
router.include_router(userRouter)
