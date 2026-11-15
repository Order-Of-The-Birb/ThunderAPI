from typing import Literal

from pydantic import BaseModel

from api.v1.shared import IpString
from api.v1.units.parser.vehicle import Vehicle


class VehicleStatsModel(BaseModel):
    maxAltitude: float
    maxSpeed: float
    turnTime: float
    airfieldLen: float
    climbTime: float
    maxSpeedAlt: float
    climbAlt: float
    climbSpeed: float
    wingLoading: float
    thrustToWeightRatio: float
    rollRate: float

class VehicleModel(BaseModel):
    id: str
    data_version: IpString
    economy: Vehicle._wpcost
    modifications: list[Vehicle._modification]
    nightvision: Vehicle._nightvision
    computers: Vehicle._computer
    release_date: str
    type: str
    subtypes: list[str]
    operator: str
    tags: list[str]
    stats: VehicleStatsModel
    default_presets: tuple[Vehicle._defaultPreset, ...]
    pylon_configurations: tuple[Vehicle._pylonData, ...]
    localizations: dict[str, dict[Literal["short", "long"], str]]
    sensors: list[str]
