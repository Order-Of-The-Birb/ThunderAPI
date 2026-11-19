from enum import StrEnum
from os import getenv

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi import Request as faRequest
from typing_extensions import Annotated

from api.shared import limiter
from utils.vehicleParser import shared
from utils.vehicleParser.localization import Languages

from .models import LocalizationModel

router = APIRouter(
	tags = ["units"],
	responses = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix = "/units"
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
	"/{unit}/localization",
	response_model=LocalizationModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def localize_unit(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
	language: Annotated[LanguagesCompat, Query(description = "The language to get the localization for (e.g. en, de, fr)")] = LanguagesCompat.en
):
	if unit not in shared.UNIT_LOC:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
	lang = Languages[language.value]
	unit_loc = shared.UNIT_LOC[unit]

	short = unit_loc.get("short", {})
	shop = unit_loc.get("shop", {})
	if (lang.value not in short or lang.value not in shop) or (short[lang.value] is None or shop[lang.value] is None):
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Localization not found for vehicle")
	return_dict = {
		"short": unit_loc["short"][lang.value],
		"long": unit_loc["shop"][lang.value]
	}
	if return_dict["short"] is None or return_dict["long"] is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Localization not found for vehicle")
	return return_dict
