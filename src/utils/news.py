import asyncio
import re
from asyncio import sleep
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, time
from enum import IntEnum
from logging import Logger, getLogger
from typing import Any, Literal

from aiohttp.client_exceptions import ClientResponseError
from bs4 import BeautifulSoup, Tag

import utils.cache as Cache
import utils.connection.network as Network
from utils.connection.websocket import WebsocketManager
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
	tags:set[Literal["Event", "Development", "Video", "Shop", "Fixed", "eSport", "Market", "Special", "Warbonds", "Fair Play", "Update"]] # Attached tags
	platforms:set[Literal["pc", "ps4", "ps5"]] # Affected platforms
	project:str # Game (100% of the time War Thunder with different version numbers)
	type:Literal["news", "changelog", "forum"] # Article Type
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
		tags = set(data.get('tags', []))
		title:str = data["title"]
		while title.strip()[0] == "[":
			tag = re.search(r"\[([A-z]+)\]", title, re.IGNORECASE)
			if tag is not None:
				title = re.sub(r"\[([A-z]+)\]", "", title, count=1, flags=re.IGNORECASE)
				tags.add(tag.group(1))
			else:
				raise RuntimeError(f"Somehow the first character is still '[' in \"{title}\", with no tags left")

		self = cls(
			id = int(data['id']),
			anons = data['anons'],
			title = title.strip(),
			link = data['link'],
			pinned = data.get('pinned', False),
			images = [cls.Image.from_json(i) for i in data['images']],
			tags = tags,
			platforms = set(data.get('platforms', [])),
			project = data.get('project', "warthunder_en"),
			type = data['type'],
			created = datetime.strptime(data['created'], "%Y-%m-%dT%H:%M:%S%z")
		)
		self.importance = self._getImportance()
		return self
	@classmethod
	async def from_forum(cls, id: int):
		"""### Technical limitation: Only works on "Planned Battle Rating Changes" posts"""
		async with Network.get(f"https://forum.warthunder.com/t/{id}") as resp:
			document = BeautifulSoup(await resp.text(), "lxml")

		post = document.select_one("div>div.topic-body")
		# select first div, which is main post

		title =	document.select_one("div#topic-title>h1>a")

		meta = post.select_one("div.crawler-post-meta>span.crawler-post-infos")
		created = datetime.fromisoformat(meta.select_one("time.post-time").get("datetime"))

		desc = post.select_one("div.post")

		# first paragraph is image
		# last 2 paragraphs are junk
		# 3rd from last paragraph's wording only works with the site's implementation
		desc_text = "\n\n".join([i.text for i in desc.select("p")[1:-3]])

		img = post.select("img")
		images = []
		for image in img:
			images.append(cls.Image(
				src=image.get("src"),
				width=int(image.get("width", -1)),
				height=int(image.get("height", -1))
			))

		return cls(
			id=id,
			anons=desc_text,
			title=title.get_text(),
			link=f"https://forum.warthunder.com/t/{id}",
			pinned=False,
			images=images,
			tags=set(["Development",]),
			platforms=set(),
			project="warthunder",
			type="forum",
			created=created,
			importance=cls.ImportanceLevel.REGULAR
		)

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
						re.search("Meet the “[A-z0-9 ]+” Major Update!", title, re.IGNORECASE) is not None and self.pinned
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
	@dataclass(slots=True)
	class LastSentIDs:
		NEWS: int = 0
		CHANGELOG: int = 0
		MAJOR_CHANGELOG: int = 0
		PLANNED_BR_CHANGES: int = 0

	_API_URL = "http://newslist.gaijin.net:8080/news/warthunder/en/js"
	_CHANGELOG_URL = "https://warthunder.com/en/game/changelog/"
	__logger: Logger
	_sentIDs: LastSentIDs
	task:asyncio.Task
	websocket_mgr: WebsocketManager

	def __init__(self):
		self.__logger = getLogger(__name__)
		self.websocket_mgr = WebsocketManager()
		self._sentIDs = self.LastSentIDs()

		self.__logger.debug("NewsAPI initialized")

	async def mainloop(self):
		while True:
			latest_news: list[NewsEntry] = []
			latest_changelogs: list[NewsEntry] = []
			latest_major_chlog: NewsEntry | None = None
			latest_forum: list[NewsEntry] = []
			try:
				changelogs = await self.fetchChangelogs()
				latest_news, latest_changelogs, latest_major_chlog, latest_forum = await asyncio.gather(
					self._get_new_news(),
					self._get_new_changelogs(changelogs),
					self._get_major_changelog(changelogs),
					self._get_new_forum(),
					return_exceptions=True
				)
			except asyncio.CancelledError:
				raise
			except Exception:
				self.__logger.exception("An exception occurred during data fetching")

			for _name, _result in (
				("news", latest_news),
				("changelogs", latest_changelogs),
				("major changelog", latest_major_chlog),
				("forum", latest_forum)
			):
				if isinstance(_result, BaseException):
					self.__logger.exception(f"An exception occurred during {_name} fetching", exc_info=_result)

			latest_news = [] if isinstance(latest_news, BaseException) else latest_news
			latest_changelogs = [] if isinstance(latest_changelogs, BaseException) else latest_changelogs
			latest_major_chlog = None if isinstance(latest_major_chlog, BaseException) else latest_major_chlog
			latest_forum = [] if isinstance(latest_forum, BaseException) else latest_forum

			if latest_news or latest_changelogs or latest_major_chlog or latest_forum:
				await Cache.get("news").clear()

			try:
				if latest_news:
					self.__logger.debug("News have been posted since last check")
					for news in latest_news:
						await self.websocket_mgr.broadcast(news.to_json())
			except asyncio.CancelledError:
				raise
			except Exception:
				self.__logger.exception("An exception occurred during news processing")

			try:
				if latest_changelogs:
					self.__logger.debug("Changelogs have been posted since last check")
					for news in latest_changelogs:
						await self.websocket_mgr.broadcast(news.to_json())
			except asyncio.CancelledError:
				raise
			except Exception:
				self.__logger.exception("An exception occurred during changelogs processing")

			try:
				if latest_major_chlog:
					self.__logger.debug("New major update changelog posted")
					await self.websocket_mgr.broadcast(latest_major_chlog.to_json())
			except asyncio.CancelledError:
				raise
			except Exception:
				self.__logger.exception("An exception occurred during changelogs processing")

			try:
				if latest_forum:
					self.__logger.debug("New planned battle rating changes posted")
					for post in latest_forum:
						await self.websocket_mgr.broadcast(post.to_json())
			except asyncio.CancelledError:
				raise
			except Exception:
				self.__logger.exception("An exception occurred during forum processing")

			await sleep(self.__calcDelay())

	async def fetch(self) -> list[NewsEntry]:
		"""Merges news and changelogs into one list"""
		cache = Cache.get("news")
		if cache is None:
			raise RuntimeError("Could not retrieve cache")

		return list(await cache.get_or_compute("news", self._compute_news))

	async def _compute_news(self) -> list[NewsEntry]:
		all_news, all_changelogs, planned_changes = await asyncio.gather(
			self.fetchNews(),
			self.fetchChangelogs(),
			self.fetchForum(),
		)

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
		if planned_changes is not None:
			unpinned.append(planned_changes)

		pinned.sort(key=lambda x: x.created, reverse=True)
		unpinned.sort(key=lambda x: x.created, reverse=True)
		return pinned + unpinned

	#region News
	async def fetchNews(self) -> list[NewsEntry]:
		"""Gets all the latest news"""
		global _news_endpoint_down
		news:list[NewsEntry] = []
		try:
			async with Network.get(self._API_URL) as response:
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
	async def _get_new_news(self):
			news = await self.fetchNews()

			if len(news) == 0:
				return []

			if self._sentIDs.NEWS == 0:
				self._sentIDs.NEWS = news[0].id
				return []

			for i, item in enumerate(news):
				if item.id == self._sentIDs.NEWS:
					self._sentIDs.NEWS = news[0].id
					return news[:i]

			# None of the news have been posted yet
			self._sentIDs.NEWS = news[0].id
			return []
	#endregion
	#region Changelogs
	async def fetchChangelogs(self) -> list[NewsEntry]:
		"""Gets the latest changelog"""
		global _changelog_maintenance
		final_changelogs = []
		try:
			async with Network.get(self._CHANGELOG_URL) as resp:
				if _changelog_maintenance:
					self.__logger.info("Changelog page is no longer under maintenance")
					_changelog_maintenance = False

				parsed = BeautifulSoup(await resp.text(), 'lxml')
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
	async def _get_major_changelog(self, changelogs:list[NewsEntry]) -> NewsEntry | None:
		"""Returns `None` if no new major update changelog has been posted"""
		# i[0] is the pinned major update changelog
		if not changelogs:
			return None
		majorChLog = changelogs[0]

		if self._sentIDs.MAJOR_CHANGELOG == 0:
			self._sentIDs.MAJOR_CHANGELOG = majorChLog.id
			return None

		if majorChLog.id != self._sentIDs.MAJOR_CHANGELOG:
			self._sentIDs.MAJOR_CHANGELOG = majorChLog.id
			return majorChLog

		return None
	async def _get_new_changelogs(self, changelogs:list[NewsEntry]) -> list[NewsEntry]:
		# i[1:] is the latest actual changelogs
		if not changelogs or len(changelogs) <= 1:
			return []
		changelogs = changelogs[1:]

		if self._sentIDs.CHANGELOG == 0:
			self._sentIDs.CHANGELOG = changelogs[0].id
			return []

		for i, item in enumerate(changelogs):
			if item.id == self._sentIDs.CHANGELOG:
				self._sentIDs.CHANGELOG = changelogs[0].id
				return changelogs[:i]

		# None of the changelogs have been posted yet
		self._sentIDs.CHANGELOG = changelogs[0].id
		return []
	#endregion
	#region Forum
	async def fetchForumIDs(self) -> tuple[int, ...]:
		"""Gets the latest "planned battle rating changes" post's ID"""
		async with Network.get("https://forum.warthunder.com/tag/br-changes") as resp:
			document = BeautifulSoup(await resp.text(), "lxml")
		rows = document.select("tr.topic-list-item")
		# Ordered by date by default

		ids = []
		for row in rows:

			tags = row.select("div.discourse-tags>a")
			# Includes update posts, that are handled by other code, so they get filtered out
			# Update posts always have other tags with them (e.g. 'server-update', 'client-update')
			if len(tags) > 1:
				continue

			title = row.select_one("a.title.raw-link")
			if title is None:
				continue
			href = title.get("href")
			if href is None:
				continue
			try:
				# URL is formatted as "https://forum.warthunder.com/t/planned-battle-rating-changes-october-2026-aircraft-and-ground-vehicle-decompression/360129"
				ids.append(int(href.split("/")[-1]))
			except ValueError:
				continue

		return tuple(ids)
	async def fetchForum(self) -> NewsEntry | None: # HTTP: just the latest
		"""Gets the latest planned battle rating changes"""
		try:
			ids = await self.fetchForumIDs()
			return await NewsEntry.from_forum(ids[0]) if ids else None
		except Exception:
			self.__logger.exception("An exception occurred during forum fetching")
			return None
	async def _get_new_forum(self) -> list[NewsEntry]: # WS: only the new ones
		ids = await self.fetchForumIDs()
		if not ids:
			return []
		if self._sentIDs.PLANNED_BR_CHANGES == 0:
			self._sentIDs.PLANNED_BR_CHANGES = ids[0]
			return []
		new = []
		for i in ids:
			if i == self._sentIDs.PLANNED_BR_CHANGES:
				break
			new.append(i)
		else:
			# Sentinel fell off the listing — advance without re-broadcasting everything
			self._sentIDs.PLANNED_BR_CHANGES = ids[0]
			return []
		entries = await asyncio.gather(*(NewsEntry.from_forum(i) for i in new))
		self._sentIDs.PLANNED_BR_CHANGES = ids[0]
		return entries
	#endregion

	def __calcDelay(self) -> int:
		rn = datetime.now(UTC)
		weekday = rn.weekday()
		rn = rn.timetz()
		start, end = fasterUpdate
		if start <= rn <= end and weekday not in excludeFastWeekdays:
			return fastCheck
		return slowCheck
