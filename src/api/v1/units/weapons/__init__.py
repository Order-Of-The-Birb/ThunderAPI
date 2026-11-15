from os import getenv

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi import Request as faRequest
from typing_extensions import Annotated

from api.shared import limiter
from api.v1.units.parser import shared
from api.v1.units.parser.localization import Languages, LanguagesCompat

router = APIRouter(
	tags = ["units"],
	responses = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix = "/weapon"
)

@router.get(
	"/{weapon}/localization"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def localize_weapon(
	request: faRequest,
	weapon: Annotated[str, Path(description = "The internal hash of the weapon")],
	language: Annotated[LanguagesCompat, Query(description = "The language to get the localization for (e.g. en, de, fr)")] = LanguagesCompat.en
):
	if weapon not in shared.WEAPON_LOC:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Weapon not found")
	lang = Languages[language.value]
	entry = shared.WEAPON_LOC[weapon]
	short = entry.get("short", {}).get(lang.value)
	long = entry.get("shop", {}).get(lang.value)
	if short is None and long is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Localization not found for weapon")
	return_dict = {
		"short": short if short is not None else long,
		"long": long if long is not None else short
	}
	return return_dict
