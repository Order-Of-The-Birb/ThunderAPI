from fastapi import HTTPException, status
from typing import Any

from tools import Request
from utils.auth import UserAuth
from utils.geo import lookup_city, lookup_utc_offset
from utils.helper import KeyRename
from api.v1.models.clans import ClanModel

async def searchClan(user: UserAuth.Entry, clanName: str | None = None, clanTag: str | None = None, limit: int = 10, page:int = 0) -> list[ClanModel]:
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
	return response["clan"]

async def getClan(user: UserAuth.Entry, clanId: int) -> dict[str, Any]:
	data = await Request.send_template(
		user,
		"clan_get",
		clanId=clanId
	)

	data["applicants"] = sanitizeApplicants(data.pop("candidates", None))

	return data

def sanitizeApplicants(applicants:dict|list):
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

	SANITIZATION = [
		KeyRename("uid", "uid", lambda x: int(x)),
		KeyRename("nick", "nickname"),
		KeyRename("comments", "comment", default=""),
		KeyRename("date", "timestamp"),
		KeyRename("ip", "geo", convert=lambda x: _ip_to_geo(x))
	]
	def sanitizeApplicant(applicant:dict[str, Any]):
		for SAN in SANITIZATION:
			applicant = SAN.rename(applicant)
		return applicant

	for i, applicant in enumerate(applicants):
		applicants[i] = sanitizeApplicant(applicant)

	return applicants
	