from api.v1.units.parser import vehicle
from fastapi import HTTPException, status

async def get_vehicle(unit: str):
	unit_ = await vehicle.Vehicle.from_id(unit)
	if unit_ is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
	return unit_
