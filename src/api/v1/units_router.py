from os import getenv

from fastapi import APIRouter, Path, Query, status, HTTPException
from typing_extensions import Annotated
from fastapi import Request as faRequest
from enum import StrEnum

from api.shared import limiter
from api.v1.backends.shared import ServerBearer, TokenBearer
from utils.vehicleParser.vehiclesProcessor import UNIT_LOC, Languages

router = APIRouter(
	tags=["units"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix="/units"
)

class LanguagesCompat(StrEnum):
	en = "en"
	fr = "fr"
	it = "it"
	de = "de"
	es = "es"
	ru = "ru"
	pl = "pl"
	cs = "cs"
	tr = "tr"
	zh = "zh"
	ja = "ja"
	pt = "pt"
	uk = "uk"
	sr = "sr"
	hu = "hu"
	kr = "kr"
	be = "be"
	ro = "ro"
	zh_tw = "zh_tw"
	zh_cn = "zh_cn"
	vi = "vi"

@router.get(
    "/{unit}/localization"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def localize_unit(
    request: faRequest,
    unit: Annotated[str, Path(description="The internal hash of the vehicle")],
    language: Annotated[LanguagesCompat, Query(description="The language to get the localization for (e.g. en, de, fr)")] = "en"
):
	if unit not in UNIT_LOC:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
	if language not in Languages.__members__:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Language not found")
	lang = Languages[language.value]
	if lang.value not in UNIT_LOC[unit]["short"] or lang.value not in UNIT_LOC[unit]["shop"]:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Localization not found for vehicle")
	return_dict = {
		"short": UNIT_LOC[unit]["short"][lang.value],
		"long": UNIT_LOC[unit]["shop"][lang.value]
	}
	return return_dict
