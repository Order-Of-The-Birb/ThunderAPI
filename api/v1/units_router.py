from os import getenv
from typing_extensions import Annotated
from fastapi import APIRouter, Path, Request, status

from utils import vehicle_cache
from api.shared import limiter
from api.v1.shared import TokenBearer
#from api.models.units import # Currently no models have been implemented

router = APIRouter(
	tags=["units"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix="/units"
)

@router.get(
	"/{vehicleId}",
	summary="Gets a specific vehicle's data",
	responses={
		status.HTTP_200_OK: {}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def getVehicle(
	request: Request, 
	user: TokenBearer, 
	vehicleId: Annotated[str, Path(title="The vehicle's ID", examples=["saab_jas39e", "yak-7k"])]
):
	await vehicle_cache.getVehicle(vehicleId)
	pass

