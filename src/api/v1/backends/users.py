from datetime import datetime, UTC
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
	return data

async def get_self(user:LoginEntry):
	data = {}
	userData = await Request.send_template(
		user,
		"get_public_userstat",
		userId = user.uidHint
	)
	data["nick"] = userData["nick"]
	data["userid"] = int(userData["userid"])
	data["penaltyStatus"] = userData["penaltyStatus"]
	data["registerDay"] = userData["registerDay"]
	data["lastDay"] = userData["lastDay"]
	level = PlayerRank.get_level(userData["exp"])
	data["level"] = {
		"name": PlayerRank.from_level(level).label,
		"rank": level
	}
	data["acedVehicles"] = userData["numEliteUnits"]

	data["unitsData"] = {}
	for k in userData["era"]:
		data["unitsData"].setdefault(k, {})
		data["unitsData"][k]["max_rank"] = userData["era"][k]
	for k in userData["unitsPerCountry"]:
		data["unitsData"].setdefault(k, {})
		data["unitsData"][k]["collection"] = {
			"overall": userData["unitsPerCountry"][k]["numUnits"],
			"aced": userData["unitsPerCountry"][k]["numEliteUnits"]
		}

	if "clanId" in userData:
		data["squadron"] = {
			"tag": userData["clanTag"],
			"id": int(userData["clanId"]),
			"name": userData["clanName"],
			"type": userData["clanType"]
		}
		data["squadron"]["user"] = {}
		clanData = await getClan(user, data["squadron"]["id"])
		for cuser in clanData["members"]:
			if cuser["uid"] != str(user.uidHint):
				continue

			role = Roles(cuser["role"])
			platform = Platforms(cuser["platform"])
			data["squadron"]["user"] = {
				"initiator": int(cuser["initiator"]) if isinstance(cuser["initiator"], str) else None,
				"join_timestamp": cuser["date"],
				"role": {
					"name": RolesDisplay[role.name].value,
					"value": role.value
				},
				"platform": {
					"name": platform.name,
					"value": platform.value
				}
			}
			break

		data["squadron"]["user"]["activity"] = clanData.get("activity", {}).get(str(user.uidHint), {}).get("total", 0)
		data["squadron"]["user"]["sqb_activity"] = clanData.get("member_ratings", {}).get(str(user.uidHint), {}).get("dr_era5_hist", 0.0)

	return data

async def get_user(user:LoginEntry, userid: int):
	data = await Request.send_template(
		user,
		"get_public_userstat",
		userId = userid
	)
	SANITIZE = (
		dictUtil.KeyMod("userid", new_name="id", convert=lambda x: int(x)),
		dictUtil.KeyRem("shcType"),
		dictUtil.KeyRem("background"),
		dictUtil.KeyRem("frame"),
		dictUtil.KeyRem("icon"),
		dictUtil.KeyRem("iconName"),
		dictUtil.KeyRem("title"),
		dictUtil.KeyRem("closedUnlocks"),
		dictUtil.KeyRem("unlocks"),
		dictUtil.KeyRem("titles"),
		dictUtil.KeyRem("classinessAwards"),
		dictUtil.KeyRem("leaderboard"),
		dictUtil.KeyRem("aircrafts"),
		dictUtil.KeyMod("userstat", new_name="statistics"),
		dictUtil.KeyRem("era"),
		dictUtil.KeyRem("slots"),
		dictUtil.KeyRem("unitsPerCountry"),
		dictUtil.KeyMod("lastDay", new_name="last_login", convert=lambda x: datetime.fromtimestamp(x, UTC).date()),
		dictUtil.KeyMod("registerDay", new_name="registered_at", convert=lambda x: datetime.fromtimestamp(x, UTC)),
		dictUtil.KeyRem("clanId"),
		dictUtil.KeyRem("clanMemberRole"),
		dictUtil.KeyRem("clanName"),
		dictUtil.KeyRem("clanType"),
		dictUtil.KeyRem("clanTag"),
		dictUtil.KeyRem("exp"),
		dictUtil.KeyRem("expConverted")
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

	data["userstat"] = dictUtil.KeyRem("new").run(data["userstat"])
	for mode in data["userstat"]:
		m_data: dict[str, dict[str, int]] = data["userstat"][mode].pop("total")
		for vehicle, v_data in m_data.items():
			m_data[vehicle] = dictUtil.run_all(v_data, VEHICLE_SANITIZE)
		data["userstat"][mode] = m_data

	data = dictUtil.run_all(data, SANITIZE)

	return data

