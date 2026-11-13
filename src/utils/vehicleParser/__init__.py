import asyncio
from logging import getLogger
from time import perf_counter

from . import shared
from .vehicle import Vehicle

_logger = getLogger(__name__)

async def getAllVehicleIDs() -> tuple[str, ...]:
	await shared.update_gamefiles()
	return [k for k in shared.WPCOST.keys() if k != "economicRankMax"]
async def processVehicles(*vehicle_ids:str) -> tuple[Vehicle, ...]:
	await shared.update_gamefiles()
	start_time = perf_counter()
	vehicle_entries = []
	for id in vehicle_ids:
		if id not in shared.WPCOST:
			_logger.error(f"Invalid vehicle ID: '{id}'")
			continue
		try:
			vehicle_entries.append(Vehicle.from_id(id))
		except LookupError:
			_logger.exception(f"Could not parse vehicle {id}")
	vehicle_entries = await asyncio.gather(*vehicle_entries)

	try:
		while True:
			vehicle_entries.remove(None)
	except ValueError:
		pass

	end_time = perf_counter()
	runtime = round(end_time-start_time, 2)
	_logger.debug(f"Vehicle parsing took {runtime} seconds and processed {len(vehicle_entries)} entries")
	return tuple(vehicle_entries)
