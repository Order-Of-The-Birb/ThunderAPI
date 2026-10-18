from logging import getLogger as _gL
from fastapi import HTTPException, status
from typing import Any

from utils.connection.http import Request
from utils.auth import LoginEntry
from utils.geo import lookup_city, lookup_utc_offset
from utils.helper import Keymod
from api.v1.models.clans import ClanModel, Roles, Platforms, Actions, ClanLeaderboardModel, ClanSearchResultModel

_logger = _gL(__name__)

async def getLeaderboard(user: LoginEntry, limit: int = 20, page: int = 0, clanId: int | None = None) -> list[ClanLeaderboardModel]:
	response = await Request.from_template(
		user, 
		"clan_get_leaderboard",
		count=limit,
		start=limit*page
	)

	if clanId is None:
		response.headers.pop("clanId")
	else:
		response.replace("count", 1)
		response.replace("start", 0)
		response.headers["clanId"] = clanId

	response = await response.send()

	if "clan" not in response:
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not obtain leaderboard data from Gaijin")
	
	clans = response["clan"]
	if isinstance(clans, dict):
		clans = [clans,]

	def sanitizeClan(clan: dict[str, Any]):
		new = {
			"id": int(clan["_id"]),
			"pos": clan["pos"]+1,
			"stats": {
				"rating": clan["astat"].get("dr_era5_hist", 0),
				"flight_time": clan["astat"].get("ftime_hist", 0),
				"air_kills": clan["astat"].get("akills_hist", 0),
				"ground_kills": clan["astat"].get("gkills_hist", 0),
				"battles": clan["astat"].get("battles_hist", 0),
				"wins": clan["astat"].get("wins_hist", 0),
				"deaths": clan["astat"].get("deaths_hist", 0),
				"activity": clan["astat"].get("activity", 0)
			},
			"name": clan["name"],
			"tag": clan["tag"]
		}

		return new

	for i, clan in enumerate(clans):
		clans[i] = sanitizeClan(clan)

	return clans

async def getLogs(user: LoginEntry, clanId: int, limit: int = 10, fromEntry: str | None = None):
	allLogs = user.entry is not None and await user.entry.getSquadronId() == clanId

	response = await Request.from_template(
		user, 
		"clan_get_log",
		_id = clanId,
		count = limit
	)
	if (allLogs):
		response.body.pop("events")
	if fromEntry:
		response.body["last"] = fromEntry

	response = await response.send()

	logs:list[dict[str, int|str]] = []
	for item in response["log"]:
		item:dict[str, int|str]
		try:
			action = Actions[item["ev"]]
		except KeyError:
			_logger.warning(f"Unhandled log type '{item["ev"]}' found")
			continue
		logEntry = {
			"timestamp": item["time"],
			"action": {
				"value": action.value[0],
				"detail": action.value[1]
			}
		}
		if item.get("uId") is not None and not (action == Actions.rem and item.get("uid") is not None and item["uId"] == item["uid"]):
			logEntry["admin"] = {
				"_id": item["uId"],
				"nickname": item["uN"]
			}
		if item.get("uid") is not None:
			logEntry["affected"] = {
				"_id": item["uid"],
				"nickname": item["nick"],
			}
		match action:
			case Actions.role:
				logEntry.update({
					"roleChange": {
						"old": item["old"],
						"new": item["new"]
					}
				})
			case Actions.info:
				for i in ["tag", "desc", "region", "status"]: 
					if (_ := item.get(i)):
						logEntry[i] = _
			case Actions.create:
				logEntry["info"] = {}
				for i in ["type", "name", "tag", "slogan", "desc", "region", "announcement"]:
					logEntry["info"][i] = item[i]
			case Actions.reject_candidate:
				logEntry["comment"] = item["comments"]
		logs.append(logEntry)

	return {
		"lastLog": response["lastMark"],
		"logs": logs
	}

async def searchClan(user: LoginEntry, clanName: str | None = None, clanTag: str | None = None, limit: int = 10, page:int = 0) -> list[ClanSearchResultModel]:
	response = await Request.from_template(
		user, 
		"clan_find_by_prefix",
		count=limit,
		start=limit*page
	)
	if clanName is None and clanTag is None: 
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "You must provide either a clanName or clanTag")
	if clanName:
		response.headers["namePrefix"] = clanName
	else:
		del response.headers["namePrefix"]
	if clanTag:
		response.headers["tagPrefix"] = clanTag
	else:
		del response.headers["tagPrefix"]
	response = await response.send()
	if isinstance(response["clan"], dict):
		response["clan"] = [response["clan"],]

	for i, clan in enumerate(response["clan"]):
		response["clan"][i] = {
			"id": int(clan["_id"]),
			"name": clan["name"],
			"tag": clan["tag"],
			"members": sanitizeMembers(clan["members"]),
			"desc": clan["desc"],
			"slogan": clan["slogan"],
			"region": clan["region"]
		}

	return response["clan"]

async def getClan(user: LoginEntry, clanId: int) -> ClanModel:
	data = await Request.send_template(
		user,
		"clan_get",
		clanId=clanId
	)

	SANITIZE = (
		Keymod("candidates", new_name="applicants", convert=lambda x: sanitizeApplicants(x)),
		Keymod("members", convert=lambda x: sanitizeMembers(x)),
		Keymod("transactions", rm=True),
		Keymod("namel", rm=True),
		Keymod("regionl", rm=True),
		Keymod("tagl", rm=True),
		Keymod("currentTagRegalia", rm=True),
		Keymod("interlockid", rm=True),
		Keymod("type", rm=True)
	)
	data = Keymod.run_all(data, SANITIZE)
	
	return data

def sanitizeMembers(members:dict|list):
	if members is None:
		return []

	if isinstance(members, dict):
		members = [members,]

	SANITIZE = (
		Keymod("uid", convert=lambda x: int(x)),
		Keymod("nick", new_name="nickname"),
		Keymod("role", new_name="rank", convert=lambda x: {
			"name": Roles(x).name,
			"value": x
		}),
		Keymod("platform", convert=lambda x: {
			"name": Platforms(x).name,
			"value": x
		}, default=Platforms.PC.value),
		Keymod("initiator", new_name="accepted_by", convert=lambda x: int(x) if x is not None else x, default=None),
		Keymod("initiator_nick", new_name="accepted_by_nick", default=None),
		Keymod("date", new_name="joined_at")
	)

	for i, member in enumerate(members):
		members[i] = Keymod.run_all(member, SANITIZE)

	return members

def sanitizeApplicants(applicants:dict|list|None):
	if applicants is None:
		return []

	if isinstance(applicants, dict):
		applicants = [applicants,]

	def _ip_to_geo(x: str) -> dict[str, Any] | None:
		geo = lookup_city(x)
		if geo is None:
			return

		return {
			"offset": lookup_utc_offset(geo.location.time_zone),
			"city": geo.city.name,
			"country": geo.country.iso_code
		}

	SANITIZATION = (
		Keymod("uid", convert=lambda x: int(x)),
		Keymod("nick", new_name="nickname"),
		Keymod("comments", new_name="comment", default=""),
		Keymod("date", new_name="timestamp"),
		Keymod("ip", new_name="geo", convert=lambda x: _ip_to_geo(x))
	)
	def sanitize(applicant:dict[str, Any]):
		for SAN in SANITIZATION:
			applicant = SAN.run(applicant)
		return applicant

	for i, applicant in enumerate(applicants):
		applicants[i] = sanitize(applicant)

	return applicants