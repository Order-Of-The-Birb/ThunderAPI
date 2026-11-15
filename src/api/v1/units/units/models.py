from pydantic import BaseModel

class VehicleStats(BaseModel):
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
