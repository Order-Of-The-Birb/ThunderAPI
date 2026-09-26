from typing import Literal
from pydantic import BaseModel, Field
from ..shared import IntString, IpString

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
class DataModel(BaseModel):
	status: Literal["OK"] = "OK"
	class MatchModel(BaseModel):
		version: int = Field(description="Game version of the match, represented as an integer.", examples=[101374])
		map: str = Field(description="Map of the match. Uses internal name", examples=["levels/avg_abandoned_factory.bin", "levels/avg_tunisia_desert.bin"])
		mapSettings: str = Field(description="Map settings of the match.", examples=["gamedata/missions/cta/tanks/abandoned_factory/abandoned_factory_dom.blk", "gamedata/missions/cta/tanks/tunisia/tunisia_02_bttl.blk"])
		type: str = Field(description="Gamemode of the match, seems to be derived from `mapSettings`", examples=["tunisia_02_Bttl", "abandoned_factory_dom"])
		difficulty: str = Field(description="Gamemode of the match, such as `Arcade`, `Realistic`, `Simulator`", examples=["Arcade", "Realistic", "Simulator"])
		sessionType: int = Field(description="Unknown integer", examples=[0])
		timeLimit: int = Field(description="Time limit in seconds", examples=[1500])
		scoreLimit: int
		battleClass: str
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

	matchId: int
	match: MatchModel
	results: ResultsModel
class ReplayNotFoundModel(BaseModel):
	detail: str = "Replay could not be found"
	status: Literal["NOT_FOUND"] = "NOT_FOUND"