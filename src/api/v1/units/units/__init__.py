from os import getenv

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi import Request as faRequest
from typing_extensions import Annotated

from api.shared import limiter
from api.v1.units.parser import shared, vehicle
from api.v1.units.parser.localization import Languages, LanguagesCompat

from .backend import get_vehicle
from .models import VehicleModel, VehicleStatsModel

router = APIRouter(
	tags = ["units"],
	responses = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix = "/unit"
)

@router.get(
	"/{unit}/localization"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_localization(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
	language: Annotated[LanguagesCompat, Query(description = "The language to get the localization for (e.g. en, de, fr)")] = LanguagesCompat.en
):
	if unit not in shared.UNIT_LOC:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
	lang = Languages[language.value]
	if lang.value not in shared.UNIT_LOC[unit]["short"] or lang.value not in shared.UNIT_LOC[unit]["shop"]:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Localization not found for vehicle")
	return_dict = {
		"short": shared.UNIT_LOC[unit]["short"][lang.value],
		"long": shared.UNIT_LOC[unit]["long"][lang.value]
	}
	return return_dict

@router.get(
	"/{unit}/economy"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_economy(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> vehicle.Vehicle._wpcost:
	return (await get_vehicle(unit)).economy.to_json()

@router.get(
	"/{unit}/computer"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_computer(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> vehicle.Vehicle._computer:
	return (await get_vehicle(unit)).computer.to_json()

@router.get(
	"/{unit}/presets/defaults"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_default_presets(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> tuple[vehicle.Vehicle._defaultPreset, ...] | None:
	return (await get_vehicle(unit)).default_presets

@router.get(
	"/{unit}/nvd"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_nvd(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> vehicle.Vehicle._nightvision:
	return (await get_vehicle(unit)).night_vision

@router.get(
	"/{unit}/sensors"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_sensors(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> list[str]:
	return (await get_vehicle(unit)).sensors

@router.get(
	"/{unit}/stats"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_stats(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> VehicleStatsModel:
	return (await get_vehicle(unit)).vehicle_stats

@router.get(
	"/{unit}/pylon_config"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_pylons(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> tuple[vehicle.Vehicle._pylonData, ...]:
	return (await get_vehicle(unit)).pylon_configurations

@router.get(
	"/{unit}/modifications"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit_mods(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> tuple[vehicle.Vehicle._modification, ...]:
	return (await get_vehicle(unit)).modifications


@router.get(
	"/{unit}/"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "units")
async def unit(
	request: faRequest,
	unit: Annotated[str, Path(description = "The internal hash of the vehicle")],
) -> VehicleModel:
	return (await get_vehicle(unit)).to_json()
