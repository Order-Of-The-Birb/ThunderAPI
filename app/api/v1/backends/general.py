from typing import Literal
from utils import networkManager

async def getLatestGameVer(branch: Literal["dev", "dev-stable"]|None):
	if branch is None: branch = ""
	async with networkManager.get(f"https://yupmaster.gaijinent.com/yuitem/get_version.php?proj=warthunder&tag={branch}") as response:
		response = await response.text()
	return response