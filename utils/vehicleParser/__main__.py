# This file is purely used for debugging the units database unit
from asyncio import new_event_loop, set_event_loop

async def runtime():
	from . import Vehicles
	vehicles = Vehicles()
	#await vehicles.setup()
	result = await vehicles.getVehicle("saab_jas39e")
	tmp1 = result.get_sensors()
	tmp2 = result.get_weapons()
	pass # Used for breakpoint
	...
def main():
	loop = new_event_loop()
	set_event_loop(loop)
	loop.run_until_complete(runtime())
	pass # Used for breakpoint

if __name__ == '__main__':
	main()
