from logging import getLogger
from utils.replayParser.parser import ReplayParser
from utils import networkManager
from fastapi import HTTPException, status
from asyncio import sleep

_logger = getLogger(__name__)

difficultyDict = {
	0: "Arcade",
	5: "Realistic",
	10: "Simulator"
}
sessionTypeDict = {
	0: "SQB"
}

class Replay(dict):
	def __init__(self):
		super().__init__({})
	@classmethod
	async def get(cls, replay_id:int|str):
		self = cls()
		if isinstance(replay_id, str): replay_id = int(replay_id, 16) # Forces lowercase hex
		replay_id = f"{replay_id:016x}"

		#region wrpl download
		async def get_data():
			async with networkManager.operation() as session:
				wrpl_num = 0
				wait_time = 1
				while True:
					url = f"https://wt-replays-cdnnow.cdn.gaijin.net/{replay_id}/{wrpl_num:04d}.wrpl"
					async with session.head(url) as r:
						if r.status == 429:
							if wait_time == 60:
								raise HTTPException(429, detail="Replay server rate limit exceeded. Please try again later.")
							await sleep(wait_time)
							wait_time = min(wait_time * 2, 60) # Exponential backoff, max 60 seconds
							continue
						wait_time = 1 # Reset wait time on successful request
						if r.status == 404:
							if wrpl_num == 0:
								raise HTTPException(404, detail="Replay could not be found")
							wrpl_num -= 1
							break

						if r.status >= 400:
							raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Replay server gave an error")

						wrpl_num += 1
				while True:
					async with session.get(f"https://wt-replays-cdnnow.cdn.gaijin.net/{replay_id}/{wrpl_num:04d}.wrpl") as r:
						if r.status == 429:
							if wait_time == 60:
								raise HTTPException(429, detail="Replay server rate limit exceeded. Please try again later.")

							await sleep(wait_time)
							wait_time = min(wait_time * 2, 60) # Exponential backoff, max 60 seconds
							continue

						if r.status >= 400:
							raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Replay server gave an error")

						data = await r.read()
						return ReplayParser(data)

		#endregion
		#region Parse gaijin JSON to proper JSON
		resultsData = await get_data()
		
		self.update({
			"status": "OK",
			"matchId": resultsData.header.sessionIdHex,
			"match": {
				"version": resultsData.header.version,
				"map": resultsData.header.level,
				"mapSettings": resultsData.header.levelSettings,
				"type": resultsData.header.battleType,
				"difficulty": difficultyDict.get(resultsData.header.diff.difficulty, "Unknown"),
				"sessionType": resultsData.header.sessionType,
				"timeLimit": resultsData.header.timeLimit * 60,
				"scoreLimit": resultsData.header.scoreLimit,
				"battleClass": resultsData.header.battleClass
			},
			"results": {
				"team1": {},
				"team2": {}
			}
		})
		if self["match"]["difficulty"] == "Unknown":
			_logger.warning(f"Unhandled difficulty type found in replay {replay_id}: {resultsData.header.diff.difficulty}")
		_ = resultsData.body
		for user in _["player"]:

			if user["userId"] == '-1':
				continue

			user:dict[str, str|int|bool]
			add_obj = {
				"clanTag": user.get("clanTag", None),
				"userId": int(user["userId"]),
				"autosquad": user.get("autosquad", False),
				"squadId": user.get("squadId", None),
				"stats": {
					"kills": user.get("kills", 0),
					"groundKills": user.get("groundKills", 0),
					"humanKills": user.get("humanKills", 0),
					"navalKills": user.get("navalKills", 0),
					"teamKills": user.get("teamKills", 0),
					"aiKills": user.get("aiKills", 0),
					"aiGroundKills": user.get("aiGroundKills", 0),
					"aiNavalKills": user.get("aiNavalKills", 0),
					"assists": user.get("assists", 0),
					"deaths": user.get("deaths", 0),
					"captureZone": user.get("captureZone", 0),
					"damageZone": user.get("damageZone", 0),
					"score": user.get("score", 0),
					"awardDamage": user.get("awardDamage", 0),
					"missileEvades": user.get("missileEvades", 0),
					"ammoInterceptions": user.get("shellIntgerceptions", 0)
				},
				"lineup" : {}
			}
			lineupData = _["matchingInfo"].get(f"{add_obj["userId"]}")
			add_obj["lineup"]["vehicles"] = {}
			if lineupData is not None:
				for key, value in lineupData["crafts_info"].items():
					if key == "__array": continue
					add_obj["lineup"]["vehicles"][value["name"]] = {
						"rank": value["rank"],
						"battlerating": round(value["mrank"] / 3, 1) 
					}
				try:
					add_obj["lineup"]["maxBr"] = round(lineupData["mrank"] / 3, 1)
				except KeyError:
					add_obj["lineup"]["maxBr"] = max(i["battlerating"] for i in add_obj["lineup"]["vehicles"].values())
			self["results"][f"team{user["team"]}"][user["name"]] = add_obj
		# endregion
		return self