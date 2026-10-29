from os import getenv

from fastapi import APIRouter, Path, Request, status
from typing_extensions import Annotated

from api.shared import limiter
from api.v1.backends.shared import ServerBearer
#from utils.vehicleParser import

router = APIRouter(
	tags=["units"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix="/units"
)
