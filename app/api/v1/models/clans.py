from enum import Enum, IntEnum
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
from ..backends.shared import IpString, IntString

PLATFORM_NAMES = Literal["PC", "PSN_TRANSFER_PC", "PSN", "XBOX_TRANSFER_PC", "XBOX"]
class Actions(Enum):
	rem = (0, "Kick user/Leave")
	add = (1, "Accept membership request")
	role = (2, "Role change")
	reject_candidate = (3, "Rejected membership request")
	info = (4, "Squadron info changed")
	create = (5, "Squadron created")
class Roles(IntEnum):
	COMMANDER = 1
	OFFICER = 2
	PRIVATE = 3
	NONE = 4
	DEPUTY = 5
	SERGEANT = 6
class RolesDisplay(Enum):
	COMMANDER = "Commander"
	OFFICER = "Officer"
	PRIVATE = "Private"
	NONE = "Unknown"
	DEPUTY = "Deputy"
	SERGEANT = "Sergeant"
class Platforms(Enum):
	PC = 2
	PSN_TRANSFER_PC = 5
	PSN = 7
	XBOX_TRANSFER_PC = 9
	XBOX = 12

class ApplicantModel(BaseModel):
	uid: int
	nickname: str
	timestamp: int
	comment: str
	class GeolocationDataModel(BaseModel):
		offset: float
		country: str
		city: str
	geo:GeolocationDataModel = Field(default=None)

class MemberModel(BaseModel):
	class enumModel(BaseModel):
		name: str
		value: int
	uid: int
	nickname: str
	rank: enumModel
	platform: enumModel | None = None
	max_unit_rank: int | None = None
	accepted_by: int | None = None
	accepted_by_nick: str | None = None
	joined_at: int

class LogsModel(BaseModel):
	lastLog: str
	logs: list[ClanLogs]
	class ClanLogs(BaseModel):
		class _userEntry(BaseModel):
			_id: int
			nickname: str
		class _action(BaseModel):
			value: int
			detail: str
		
		class _roleChange(BaseModel):
			old: str | None = Field(default=None, description="Previous role. Only present for role-change log entries.")
			new: str | None = Field(default=None, description="New role. Only present for role-change log entries.")


		timestamp: int
		affected: _userEntry | None = Field(default=None, exclude_if=lambda x: x is None)
		action: _action
		admin: _userEntry | None = Field(default=None, exclude_if=lambda x: x is None)
		roleChange: _roleChange | None = Field(default=None, exclude_if=lambda x: x is None)

class ClanLeaderboardModel(BaseModel):
	class ClanStatsModel(BaseModel):
		rating: int
		flight_time: float
		air_kills: int
		ground_kills: int
		battles: int
		wins: int
		deaths: int
		activity: int
	id: int
	pos: int
	stats: ClanStatsModel
	name: str
	tag: str

class ClanModel(BaseModel):
	class ClanSeasonRatingRewardsModel(BaseModel):
		t: int | None = None
		seasonId: int | None = None
		seasonStartTimestamp: int | None = None
		seasonEndTimestamp: int | None = None
		numInYear: int | None = None
		regaliaTags: str | None = None
	
	class astatModel(BaseModel):
		deaths_hist: int | None = None
		ftime_hist: int | None = None
		akills_hist: int | None = None
		dr_era5_hist: int | None = None
		gkills_hist: int | None = None
		battles_hist: int | None = None
		wins_hist: int | None = None
		dr_era0_arc: int | None = None
		dr_era0_hist: int | None = None
		dr_era0_sim: int | None = None
		dr_era1_arc: int | None = None
		dr_era1_hist: int | None = None
		dr_era1_sim: int | None = None
		dr_era2_arc: int | None = None
		dr_era2_hist: int | None = None
		dr_era2_sim: int | None = None
		dr_era3_arc: int | None = None
		dr_era3_hist: int | None = None
		dr_era3_sim: int | None = None
		dr_era4_arc: int | None = None
		dr_era4_hist: int | None = None
		dr_era4_sim: int | None = None
		dr_era5_arc: int | None = None
		dr_era5_sim: int | None = None
		dr_era6_arc: int | None = None
		dr_era6_hist: int | None = None
		dr_era6_sim: int | None = None
		dr_era7_arc: int | None = None
		dr_era7_hist: int | None = None
		dr_era7_sim: int | None = None
		dr_era8_arc: int | None = None
		dr_era8_hist: int | None = None
		dr_era8_sim: int | None = None
		dr_era9_arc: int | None = None
		dr_era9_hist: int | None = None
		dr_era9_sim: int | None = None
		activity: int
		clan_activity_by_periods: int    
	pos: int | None = None
	_id: int | None = None
	autoaccept: bool | None = None
	cdate: int | None = None
	changed_by_uid: int | None = None
	changed_time: int | None = None
	creator_uid: int | None = None
	desc: str | None = None
	members_cnt: int | None = None
	name: str | None = None
	region: str | None = None
	slogan: str | None = None
	status: str | None = None
	tag: str | None = None
	clanSeasonRatingRewards: ClanSeasonRatingRewardsModel | dict | None = None
	members: list[MemberModel] | None = None
	membership_req: dict | None = None
	astat: astatModel | None = None
	applicants: list[ApplicantModel] | None = Field(default=None, exclude_if=lambda x: x is None)

	class Config:
		extra = "allow"

class ClanSearchResultModel(BaseModel):
	id: int
	name: str
	tag: str
	members: list[MemberModel]
	desc: str
	slogan: str
	region: str

class SQBTimeBracket(BaseModel):
	_from: datetime
	_to: datetime
	br: float