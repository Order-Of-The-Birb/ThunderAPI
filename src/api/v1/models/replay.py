from typing import Literal

from pydantic import BaseModel, Field

from ..backends.shared import IntString, IpString


class SearchModel(BaseModel):
	class ReplayEntry(BaseModel):
		class PlayerEntry(BaseModel):
			userId: IntString
			name: str
			fakeName: str
		sessionId: str
		sessionIdHex: str
		policy: int
		title: str
		missionName: str
		missionDescription: str
		tournamentName: str
		startTime: int
		endTime: int
		totalViews: int
		statisticGroup: str
		url: str
		version: int
		teamNames: None
		gameVersion: IpString
		clanBattle: bool
		isCompleted: bool
		isNewbies: bool
		gameType: str
		gameMode: str
		players: dict[Literal["team_1", "team_2"], list[PlayerEntry]]

	class PaginationModel(BaseModel):
		nextNum: int
		first_page: int
		items: list[int]
		sumPages: int
	offset: int
	limit: int
	items: list[ReplayEntry]
	count: int
	total_count: int
	pagination: PaginationModel
	partsCount: int
	visible: int
	id: str

class ResultsModel(BaseModel):
	class UserModel(BaseModel):
		class StatsModel(BaseModel):
			kills: int
			groundKills: int
			humanKills: int
			navalKills: int
			teamKills: int
			aiKills: int
			aiGroundKills: int
			aiNavalKills: int
			assists: int
			deaths: int
			captureZone: int
			damageZone: int
			score: int
			awardDamage: int
			missileEvades: int
			ammoInterceptions: int
		class LineupModel(BaseModel):
			class VehicleModel(BaseModel):
				rank: int
				battlerating: float
			vehicles: dict[str, VehicleModel] = Field(
				description="Vehicles in the lineup of the player. Key is the internal name of the vehicle, such as `germ_leopard_2pl`",
				examples=[
				{
					"ef_2000_block_10": {
						"rank": 9,
						"battlerating": 13.3
					},
				}, {
					"germ_leopard_2pl": {
						"rank": 8,
						"battlerating": 11.3
					},
				}, {
					"tiger_had_spain": {
						"rank": 7,
						"battlerating": 9.7
					}
				}]
			)
			maxBr: float = Field(description="Maximum battle rating of the user's lineup", examples=[6.7, 8.0, 9.7])
		clanTag: str | None = Field(default=None, description="Clan tag of the user, if applicable. Includes border", examples=["┾PECK┿", ""])
		userId: int
		autosquad: bool = Field(description="Whether the user was assigned into a squad automatically")
		squadId: int = Field(description="Squad ID of the user. Number is still generated if not in a squad. Looks like 4000+ are players playing alone", examples=[1001, 1002, 1000, 4096, 4097, 4098])
		stats: StatsModel
		lineup: LineupModel

	team1: dict[str, UserModel]
	team2: dict[str, UserModel]
class MatchModel(BaseModel):
		version: int = Field(description="Game version of the match, represented as an integer.", examples=[101374])
		map: str = Field(description="Map of the match. Uses internal name", examples=["levels/avg_abandoned_factory.bin", "levels/avg_tunisia_desert.bin"])
		mapSettings: str = Field(description="Map settings of the match.", examples=["gamedata/missions/cta/tanks/abandoned_factory/abandoned_factory_dom.blk", "gamedata/missions/cta/tanks/tunisia/tunisia_02_bttl.blk"])
		mapType: str = Field(description="Gamemode of the match, seems to be derived from `mapSettings`", examples=["tunisia_02_Bttl", "abandoned_factory_dom"])
		difficulty: str = Field(description="Gamemode of the match, such as `Arcade`, `Realistic`, `Simulator`", examples=["Arcade", "Realistic", "Simulator"])
		battleType: str
class DataModel(BaseModel):
	status: Literal["OK"] = "OK"


	matchId: int
	match: MatchModel = Field(exclude_if=lambda x: x is None)
	results: ResultsModel = Field(exclude_if=lambda x: x is None)
class ReplayNotFoundModel(BaseModel):
	detail: str = "Replay could not be found"
	status: Literal["NOT_FOUND"] = "NOT_FOUND"
