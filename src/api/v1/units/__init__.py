from fastapi import APIRouter, status

from . import units, weapons

router = APIRouter(
	tags = ["units"],
	responses = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix = "/units"
)
router.include_router(weapons.router)
router.include_router(units.router)
