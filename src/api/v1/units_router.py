
from fastapi import APIRouter, status

#from utils.vehicleParser import

router = APIRouter(
	tags=["units"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix="/units"
)
