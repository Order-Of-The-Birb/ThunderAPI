from datetime import datetime, UTC
from typing import Any
from utils.connection import Request
from utils.auth import LoginEntry
from utils.helper import dictUtil
from api.v1.backends.clans import getClan, Platforms
from api.v1.models.clans import RolesDisplay, Roles
from api.v1.models.users import TerseReturnModel, PlayerRank

async def get_terse(user:LoginEntry, *userIds:int|str) -> dict[str, TerseReturnModel]:
	data = await Request.send_template(
		user,
		"get_users_terse_info",
		usersList = ";".join(str(i) for i in userIds)
	)
	SANITIZE = (
		dictUtil.KeyRem(
			"background",
			"showcase",
			"title",
			"shcType",
			"pilotId",
			"pilotIcon",
			"frame"
		),
		dictUtil.KeyMod("nick", new_name="username")
	)
	for k in dict(data):
		data[int(k)] = await dictUtil.run_all(data.pop(k), SANITIZE)

	return data

async def get_self(user:LoginEntry):
	userData = await get_user(user, user.uidHint)

	return await dictUtil.KeyRem("summary", "statistics", "countries").run(userData)

async def get_user(user:LoginEntry, userid: int):
	data = await Request.send_template(
		user,
		"get_public_userstat",
		userId = userid
	)
	SANITIZE = (
		dictUtil.KeyMod("userid", new_name="id", convert=lambda x: int(x)),
		dictUtil.KeyMod("userstat", new_name="statistics"),
		dictUtil.KeyMod("lastDay", new_name="last_login", convert=lambda x: datetime.fromtimestamp(x, UTC).date()),
		dictUtil.KeyMod("registerDay", new_name="registered_at", convert=lambda x: datetime.fromtimestamp(x, UTC)),
		dictUtil.KeyRem(
			"shcType",
			"background",
			"frame",
			"icon",
			"iconName",
			"title",
			"closedUnlocks",
			"unlocks",
			"titles",
			"classinessAwards",
			"leaderboard",
			"aircrafts",
			"era",
			"slots",
			"unitsPerCountry",
			"clanId",
			"clanMemberRole",
			"clanName",
			"clanType",
			"clanTag",
			"exp",
			"expConverted"
		),
	)
	new_countries_data = {}
	for country in data["era"]:
		new_countries_data[country.removeprefix("country_")] = {
			"max_ranks": data["era"][country],
			"numUnits": data["unitsPerCountry"].get(country, {}).get("numUnits", 0),
			"numEliteUnits": data["unitsPerCountry"].get(country, {}).get("numEliteUnits", 0),
			"current_lineup": tuple(data["slots"].get(country, {}).keys()),
			"units": tuple(data["aircrafts"].get(country, {}).keys())
		}
	data["countries"] = new_countries_data
	del new_countries_data

	if "clanTag" in data: # User is a squadron member
		data["clan"] = {
			"tag": data["clanTag"],
			"name": data["clanName"],
			"type": data["clanType"],
			"role": data["clanMemberRole"],
			"id": int(data["clanId"])
		}

	level = PlayerRank.get_level(data["exp"])
	data["level"] = {
		"title": PlayerRank.from_level(level).name,
		"level": level
	}

	VEHICLE_SANITIZE = (
		dictUtil.KeyRem("was_in_session"),
		# No clue how this calculates to battles,
		# These numbers are different from the in-game "battles" values
		dictUtil.KeyMod("flyouts", new_name="respawns"),
		dictUtil.KeyMod("wp_total", new_name="total_sl"),
		dictUtil.KeyMod("online_exp_total", new_name="total_rp")
	)

	data["userstat"] = await dictUtil.KeyRem("new").run(data["userstat"])
	for mode in data["userstat"]:
		m_data: dict[str, dict[str, int]] = data["userstat"][mode].pop("total")
		for vehicle, v_data in m_data.items():
			m_data[vehicle] = await dictUtil.run_all(v_data, VEHICLE_SANITIZE)
		data["userstat"][mode] = m_data
		data["userstat"] = await dictUtil.KeyMod("simulation", new_name="simulator").run(data["userstat"])
	for mode in data["summary"]:
		data["summary"][mode] = await dictUtil.KeyMod("hardcore", new_name="simulator").run(data["summary"][mode])

	data = await dictUtil.run_all(data, SANITIZE)

	return data

