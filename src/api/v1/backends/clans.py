import asyncio
from datetime import UTC, datetime, time
from logging import getLogger as _gL
from re import IGNORECASE
from re import search as re_search
from typing import Any

from bs4 import BeautifulSoup
from fastapi import HTTPException, status

import utils.connection.network as Network
from api.v1.models.clans import Actions, ClanLeaderboardModel, ClanModel, ClanSearchResultModel, Platforms, Roles
from utils.auth import LoginEntry
from utils.connection import Request
from utils.geo import lookup_city, lookup_utc_offset
from utils.helper import dictUtil

_logger = _gL(__name__)

async def getLeaderboard(user: LoginEntry, limit: int = 20, page: int = 0, clanId: int | None = None) -> list[ClanLeaderboardModel]:
	response = await Request.from_template(
		user,
		"clan_get_leaderboard",
		count=limit,
		start=limit*page
	)

	if clanId is None:
		response.headers.pop("clanId", Network)
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
				"id": item["uId"],
				"nickname": item["uN"]
			}
		if item.get("uid") is not None:
			logEntry["affected"] = {
				"id": item["uid"],
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
	if clanName is None and clanTag is None:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "You must provide either a clanName or clanTag")
	response = await Request.from_template(
		user,
		"clan_find_by_prefix",
		count=limit,
		start=limit*page
	)
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
			"members": await sanitizeMembers(clan["members"]),
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
		dictUtil.KeyMod("candidates", new_name="applicants", convert=lambda x: sanitizeApplicants(x)),
		dictUtil.KeyMod("members", convert=lambda x: sanitizeMembers(x)),
		dictUtil.KeyMod("_id", new_name="id"),
		dictUtil.KeyRem(
			"transactions",
			"namel",
			"regionl",
			"tagl",
			"currentTagRegalia",
			"interlockid",
			"type"
		),
	)
	data = await dictUtil.run_all(data, SANITIZE)

	return data

SQB_BRACKET_TIMES = (
	(
		time(hour=1, minute=0, tzinfo=UTC),
		time(hour=7, minute=0, tzinfo=UTC)
	),
	(
		time(hour=14, minute=0, tzinfo=UTC),
		time(hour=22, minute=0, tzinfo=UTC)
	)
)
SQB_BRACKET_CACHE: tuple[dict[str, datetime|float]] | None = None
SQB_BRACKET_CACHE_LOCK = asyncio.Lock()

async def get_sqb_brackets() -> tuple[dict[str, datetime|float]]:
	async def get_brackets():
		async with Network.get(
			"https://forum.warthunder.com/t/season-schedule-for-squadron-battles/4446",
			Network.ReturnType.TEXT,
			headers={
				"User-Agent": "Thunderapi/1.0"
			}
		) as resp:
			document = BeautifulSoup(resp, 'lxml')

		post = document.select_one("div.topic-body.crawler-post")
		meta = post.select_one("span.crawler-post-infos>meta[itemprop='dateModified']")
		if not meta:
			raise RuntimeError()

		body = post.select("div.post>p")
		if len(body) < 2:
			raise RuntimeError()


		title = document.find("meta", itemprop="headline").get("content")
		year = re_search(r"\([0-9\. ]+ - ([0-9]+\.[0-9]+\.[0-9]+)\)", title, IGNORECASE)
		if not year:
			raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not fetch forum post title")
		end_date = datetime.strptime(year.group(1), "%d.%m.%Y").date()

		if end_date < datetime.now(UTC).date():
			raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Forum post data is outdated. Please try again later.")

		post = str(document.find("div", class_="post").find_all("p")[1]).removeprefix("<p>").removesuffix("</p>").replace("<br/>","").split("\n")
		del document

		weeks = []
		for week in post:
			find = re_search(r"мах (?:BR|БР) ([0-9.]+) \(([0-9.]+)\D+([0-9.]+)\)", week, IGNORECASE)
			if not find:
				_logger.warning("regex could not find bracket data")
				raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not retrieve SQB brackets")
			br = float(find.group(1))
			start_time = datetime.combine(datetime.strptime(f"{find.group(2)}.{end_date.year}", "%d.%m.%Y").date(), SQB_BRACKET_TIMES[0][0], UTC)
			end_time = datetime.combine(datetime.strptime(f"{find.group(3)}.{end_date.year}", "%d.%m.%Y").date(), SQB_BRACKET_TIMES[1][1], UTC)
			weeks.append({
				"start": start_time,
				"end": end_time,
				"br": br
			})
		return tuple(weeks)

	global SQB_BRACKET_CACHE
	async with SQB_BRACKET_CACHE_LOCK:
		if SQB_BRACKET_CACHE and SQB_BRACKET_CACHE[-1]["end"] >= datetime.now(UTC):
			return SQB_BRACKET_CACHE

	weeks = await get_brackets()

	async with SQB_BRACKET_CACHE_LOCK:
		SQB_BRACKET_CACHE = weeks
	return SQB_BRACKET_CACHE

async def current_sqb_br() -> dict[str, datetime|float]:
	weeks = await get_sqb_brackets()
	rn = datetime.now(UTC)
	for week in weeks:
		if week["start"] <= rn <= week["end"]:
			return week
	for week in weeks:
		if week["start"] > rn:
			return week
	raise HTTPException(status.HTTP_404_NOT_FOUND, "Could not find current bracket data")

async def sanitizeMembers(members:dict|list):
	if members is None:
		return []

	if isinstance(members, dict):
		members = [members,]

	SANITIZATION = (
		dictUtil.KeyMod("uid", convert=lambda x: int(x)),
		dictUtil.KeyMod("nick", new_name="nickname"),
		dictUtil.KeyMod("role", new_name="rank", convert=lambda x: {
			"name": Roles(x).name,
			"value": x
		}),
		dictUtil.KeyMod("platform", convert=lambda x: {
			"name": Platforms(x).name,
			"value": x
		}, default=Platforms.PC.value),
		dictUtil.KeyMod("initiator", new_name="accepted_by", convert=lambda x: int(x) if x is not None else x, default=None),
		dictUtil.KeyMod("initiator_nick", new_name="accepted_by_nick", default=None),
		dictUtil.KeyMod("date", new_name="joined_at")
	)

	for i, member in enumerate(members):
		members[i] = await dictUtil.run_all(member, SANITIZATION)

	return members

async def sanitizeApplicants(applicants:dict|list|None):
	if applicants is None:
		return []

	if isinstance(applicants, dict):
		applicants = [applicants,]

	async def _ip_to_geo(x: str) -> dict[str, Any] | None:
		try:
			geo = await asyncio.to_thread(lookup_city, x)
			if geo is None:
				return None

			return {
				"offset": await asyncio.to_thread(lookup_utc_offset, geo.location.time_zone),
				"city": geo.city.name,
				"country": geo.country.iso_code
			}
		except Exception:
			return None

	SANITIZATION = (
		dictUtil.KeyMod("uid", convert=lambda x: int(x)),
		dictUtil.KeyMod("nick", new_name="nickname"),
		dictUtil.KeyMod("comments", new_name="comment", default=""),
		dictUtil.KeyMod("date", new_name="timestamp"),
		dictUtil.KeyMod("ip", new_name="geo", convert=_ip_to_geo)
	)

	for i, applicant in enumerate(applicants):
		applicants[i] = await dictUtil.run_all(applicant, SANITIZATION)

	return applicants
