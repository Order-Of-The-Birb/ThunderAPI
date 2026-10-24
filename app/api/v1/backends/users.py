from utils.connection import Request
from utils.auth import LoginEntry
from utils.helper import Keymod
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
		Keymod("clanId", convert=lambda x: int(x)),
		Keymod("shcType", rm=True),
		Keymod("background", rm=True),
		Keymod("frame", rm=True),
		Keymod("icon", rm=True),
		Keymod("iconName", rm=True),
		Keymod("title", rm=True),
		Keymod("closedUnlocks", rm=True),
		Keymod("unlocks", rm=True),
		Keymod("titles", rm=True),
		Keymod("classinessAwards", rm=True),
		Keymod("leaderboard", rm=True)
	)
	data = Keymod.run_all(data, SANITIZE)
	if "userstat" in data:
		VEHICLE_SANITIZE = (
			Keymod("was_in_session", rm=True),
			# No clue how this calculates to battles,
			# These numbers are different from the in-game "battles" values
			Keymod("flyouts", new_name="respawns"),
			Keymod("wp_total", new_name="total_sl"),
			Keymod("online_exp_total", new_name="total_rp")
		)

		data["userstat"] = Keymod("new", rm=True).run(data["userstat"])
		for mode in data["userstat"]:
			m_data: dict[str, dict[str, int]] = data["userstat"][mode].pop("total")
			for vehicle, v_data in m_data.items():
				m_data[vehicle] = Keymod.run_all(v_data, VEHICLE_SANITIZE)
			data["userstat"][mode] = m_data
			pass

	return data

