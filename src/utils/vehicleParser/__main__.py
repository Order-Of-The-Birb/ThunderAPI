import asyncio

from . import getAllVehicleIDs, processVehicles

if __name__ == '__main__':
	loop = asyncio.new_event_loop()
	ids = loop.run_until_complete(getAllVehicleIDs())
	pass
	vehicles = loop.run_until_complete(processVehicles(*ids))
	pass
