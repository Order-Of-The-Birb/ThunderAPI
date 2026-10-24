from typing import Literal
import utils.connection.network as Network

async def getLatestGameVer(branch: Literal["dev", "dev-stable"]|None):
	if branch is None: branch = ""
	async with Network.get(f"https://yupmaster.gaijinent.com/yuitem/get_version.php?proj=warthunder&tag={branch}") as response:
		response = await response.text()
	return response
