from asyncio import Task, Lock, CancelledError
from logging import getLogger, Logger
from aiohttp.client_exceptions import ClientResponseError
from utils.network import NetworkManager, WebsocketManager
from datetime import datetime, time, UTC
from asyncio import sleep
from pathlib import Path
from typing import Literal, Any
from dataclasses import dataclass, asdict
from enum import IntEnum, Enum
from re import search as re_search, IGNORECASE
from json import loads, dumps
from bs4 import BeautifulSoup, Tag
from utils.helper import dtToTimestamp

fasterUpdate = (
	time(hour=11, minute=0, tzinfo=UTC), # Start
	time(hour=21, minute=30, tzinfo=UTC) # End
)
excludeFastWeekdays = (5,6) # Zero-indexed number of weekday 
fastCheck = 5*60 # Every 5 mins
slowCheck = 30*60 # Every 30 mins

@dataclass(slots=True)
class NewsEntry:
	class ImportanceLevel(IntEnum):
		REGULAR = 0
		MINOR = 1
		EVENT = 2
		MAJOR = 3
	id:int
	anons:str # Short description
	title:str # Title
	link:str # URL
	pinned:bool
	images:list['Image'] # Attached images
	tags:list[Literal["Event", "Development", "Video", "Shop", "Fixed", "eSport", "Market", "Special", "Warbonds", "Fair Play", "Update"]] # Attached tags
	platforms:list[str] # Affected platforms
	project:str # Game (100% of the time War Thunder with different version numbers) 
	type:Literal["news", "changelog"] # Article Type
	created:datetime # Article Creation Time
	importance:ImportanceLevel = ImportanceLevel.REGULAR
	@dataclass(slots=True)
	class Image:
		src: str
		width: int
		height: int
		@classmethod
		def from_json(cls, data:dict[str, Any]):
			return cls(
				src=data["src"],
				width=int(data["width"]),
				height=int(data["height"])
			)
		def to_json(self):
			return asdict(self)
	@classmethod
	def from_json(cls, data:dict[str, Any]):
		self = cls(
			id = int(data['id']),
			anons = data['anons'], 
			title = data['title'],
			link = data['link'],
			pinned = data.get('pinned', False),
			images = [cls.Image.from_json(i) for i in data['images']],
			tags = data.get('tags', []),
			platforms = data.get('platforms', []),
			project = data.get('project', "warthunder_en"),
			type = data['type'],
			created = datetime.strptime(data['created'], "%Y-%m-%dT%H:%M:%S%z")
		)
		self.importance = self._getImportance()
		return self
	def to_json(self):
		obj = asdict(self)
		obj["created"] = dtToTimestamp(self.created)
		obj["importance"] = int(self.importance)
		return obj

	def _getImportance(self) -> ImportanceLevel:
			title = self.title.lower()
			if (
					(
						"Video" in self.tags and 
						(
							"trailer" in title or 
							"teaser" in title
						) 
					) or 
					(
						("Shop" in self.tags or "Event" in self.tags) and
						(
							(
								(
									any(i in title for i in ["winter", "summer", "may", "holiday"]) or 
									("war thunder" in title and "birthday" in title)
								) and
								any(i in title for i in ["sale", "discount", "celebrate"])  
							) or
							"black friday" in title
						)
					) or (
						re_search("Meet the “[A-z0-9 ]+” Major Update!", title, IGNORECASE) is not None and self.pinned 
					)
				):
				return self.ImportanceLevel.MAJOR
			if ("Event" in self.tags and "pages" not in title):
				return self.ImportanceLevel.EVENT
			if ("discount" in title and ("Shop" in self.tags or "Special" in self.tags)):
				return self.ImportanceLevel.MINOR
			return self.ImportanceLevel.REGULAR

_changelog_maintenance: bool = False
_news_endpoint_down: bool = False
class NewsManager:
	_API_URL = "http://newslist.gaijin.net:8080/news/warthunder/en/js"
	_CHANGELOG_URL = "https://warthunder.com/en/game/changelog/"
	class _IDTYPE(Enum):
		NEWS = 0, "lastNews"
		CHANGELOG = 1, "lastChangelog"
		MAJOR_CHLOG = 2, "lastMajorChLog"
	lastNews:int
	lastChangelog:int
	__logger: Logger
	_networkManager: NetworkManager
	task:Task
	_ids_json: Path
	_lock: Lock
	websocket_mgr: WebsocketManager

	def __init__(self, networkManager:NetworkManager):
		self.__logger = getLogger(__name__)
		self._lock = Lock()

		self._networkManager = networkManager
		self.websocket_mgr = WebsocketManager()

		self._ids_json = Path(__file__).parent / "news.json"
		if (not self._ids_json.exists()):
			self._ids_json.write_text(dumps({
				self._IDTYPE.NEWS.value[1]: 0,
				self._IDTYPE.CHANGELOG.value[1]: 0,
				self._IDTYPE.MAJOR_CHLOG.value[1]: 0
			}))
		content = loads(self._ids_json.read_text())
		self.lastNews = int(content.get(self._IDTYPE.NEWS.value[1], 0))
		self.lastChangelog = int(content.get(self._IDTYPE.CHANGELOG.value[1], 0))
		self.lastMajorChLog = int(content.get(self._IDTYPE.MAJOR_CHLOG.value[1], 0))

		self.__logger.debug("NewsAPI initialized")

	async def mainloop(self):
		while True:
			try:
				if (latest := await self._get_new_news()):
					self.__logger.debug("News have been posted since last check")
					for news in latest:
						await self.websocket_mgr.broadcast(news.to_json())
			except CancelledError:
				raise
			except Exception:
				self.__logger.exception("An exception occurred during news fetching")

			try:
				changelogs = await self.fetchChangelogs()

				try:
					if (latest := await self._get_new_changelogs(changelogs)):
						self.__logger.debug("Changelogs have been posted since last check")
						for news in latest:
							await self.websocket_mgr.broadcast(news.to_json())
				except CancelledError:
					raise
				except Exception:
					self.__logger.exception("An exception occurred during changelog processing")

				try:
					if (latest := await self._get_major_changelog(changelogs)):
						self.__logger.debug("New major update changelog posted")
						await self.websocket_mgr.broadcast(latest.to_json())
				except CancelledError:
					raise
				except Exception:
					self.__logger.exception("An exception occurred during major changelog processing")

			except CancelledError:
				raise
			except Exception:
				self.__logger.exception("An exception occurred during changelog fetching")
			
			await sleep(self.__calcDelay())

	async def fetch(self) -> list[NewsEntry]:
		"""Merges news and changelogs into one list"""
		all_news = await self.fetchNews()
		all_changelogs = await self.fetchChangelogs()

		pinned: list[NewsEntry] = []
		unpinned: list[NewsEntry] = []
		for news in all_news:
			if news.pinned:
				pinned.append(news)
			else:
				unpinned.append(news)
		for changelog in all_changelogs:
			if changelog.pinned:
				pinned.append(changelog)
			else:
				unpinned.append(changelog)

		pinned.sort(key=lambda x: x.created, reverse=True)
		unpinned.sort(key=lambda x: x.created, reverse=True)
		combined = pinned + unpinned
		return combined

	async def fetchNews(self) -> list[NewsEntry]:
		"""Gets all the latest news"""
		global _news_endpoint_down
		news:list[NewsEntry] = []
		try:
			async with self._networkManager.get(self._API_URL) as response:
				if _news_endpoint_down:
					self.__logger.info("Gaijin's news endpoint is back online")
					_news_endpoint_down = False
				data = await response.json()
				for item in data["items"]:
					news.append(NewsEntry.from_json(item))
		except ClientResponseError:
			if not _news_endpoint_down:
				self.__logger.error("Gaijin's news endpoint is currently down. Returning emptry until it is back")
				_news_endpoint_down = True
		return news
	async def fetchChangelogs(self) -> list[NewsEntry]:
		"""Gets the latest changelog"""
		global _changelog_maintenance
		final_changelogs = []
		try:
			async with self._networkManager.get(self._CHANGELOG_URL) as resp:
				if _changelog_maintenance:
					self.__logger.info("Changelog page is no longer under maintenance")
					_changelog_maintenance = False

				parsed = BeautifulSoup(await resp.text(), 'html.parser')
				changelogs = parsed.select("div.showcase__content-wrapper>div.showcase__item.widget")
				if len(changelogs) < 2:
					raise RuntimeError("Less, than 2 changelogs found (somehow)")
				async def processChangelog(chlog:Tag) -> NewsEntry:
					ChLogURL:str = chlog.select_one("a.widget__link")["href"]
					content = chlog.select_one("div.widget__content")
					title = content.select_one("div.widget__title").get_text(strip=True)
					anons = content.select_one("div.widget__comment").get_text(strip=True)
					datetext = content.select_one("ul.widget__meta.widget-meta").select_one("li.widget-meta__item.widget-meta__item--right").get_text(strip=True)
					date = datetime.strptime(datetext, "%d %B %Y").replace(tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%S%z")
					del datetext
					src = chlog.select_one("div.widget__poster>img").attrs["data-src"]
					pinned = chlog.select_one("div.widget__pin") is not None
					return NewsEntry.from_json({
						"id":int(ChLogURL.split("/")[-1]),
						"anons":anons,
						"title":title,
						"link":f"https://warthunder.com{ChLogURL}",
						"tags":["Update"],
						"images":[{
							"src":src,
							"width": 0,
							"height": 0
						}],
						"type":"changelog",
						"created":date,
						"pinned": pinned
					})
				for chlog in changelogs:
					final_changelogs.append(await processChangelog(chlog))
			return final_changelogs
		except ClientResponseError:
			if not _changelog_maintenance:
				self.__logger.error("Changelogs page is under maintenance, returning empty until maintenance is over")
				_changelog_maintenance = True
			return []
		except RuntimeError:
			if not _changelog_maintenance:
				self.__logger.exception("An error occurred while parsing changelogs")
			return []
	async def _get_major_changelog(self, changelogs:list[NewsEntry]) -> None|NewsEntry:
		"""Returns `None` if no new major update changelog has been posted"""
		# i[0] is the pinned major update changelog
		if not changelogs: 
			return None
		majorChLog = changelogs[0]
		if majorChLog.id != self.lastMajorChLog:
			await self._writeID(majorChLog.id, self._IDTYPE.MAJOR_CHLOG)
			return majorChLog
		return None

	async def _get_new_changelogs(self, changelogs:list[NewsEntry]):
		# i[1:] is the latest actual changelogs
		if not changelogs or len(changelogs) <= 1:
			return []
		changelogs = changelogs[1:]

		for i, item in enumerate(changelogs):
			if item.id == self.lastChangelog: 
				await self._writeID(changelogs[0], self._IDTYPE.CHANGELOG)
				return changelogs[:i]

		# None of the changelogs have been posted yet
		await self._writeID(changelogs[0], self._IDTYPE.CHANGELOG)
		return []
	async def _get_new_news(self):
		news = await self.fetchNews()

		if len(news) == 0:
			return []

		for i, item in enumerate(news):
			if item.id == self.lastNews: 
				await self._writeID(news[0], self._IDTYPE.NEWS)
				return news[:i]

		# None of the news have been posted yet
		await self._writeID(news[0], self._IDTYPE.NEWS)
		return []

	async def _writeID(self, ID:int|NewsEntry, _type:_IDTYPE):
		ID = ID if isinstance(ID, int) else ID.id
		self.__logger.debug(f"Writing value {ID} for {_type.name}")

		async with self._lock:
			content = loads(self._ids_json.read_text())
			content[_type.value[1]] = ID
			self._ids_json.write_text(dumps(content, indent=4))

			self.__setattr__(_type.value[1], ID)

	def __calcDelay(self) -> int:
		rn = datetime.now(UTC)
		weekday = rn.weekday()
		rn = rn.timetz()
		start, end = fasterUpdate
		if start <= rn <= end and weekday not in excludeFastWeekdays:
			return fastCheck
		return slowCheck
