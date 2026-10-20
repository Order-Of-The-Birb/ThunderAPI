from __future__ import annotations
from re import sub as re_sub, search as re_search
from logging import getLogger
from asyncio import Lock, Task, get_running_loop, Event, wait_for, to_thread
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job
from aiosqlite import connect, Row, OperationalError
from os import getenv, urandom
from datetime import UTC, datetime, timedelta
from typing import ClassVar, Literal, Any
from fastapi import HTTPException, status
from hashlib import sha256, md5
from secrets import token_urlsafe
from enum import StrEnum
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict, field
from base64 import b64encode
from cryptography.fernet import Fernet

from utils.helper import dtToTimestamp, AuthenticationError
import utils.connection.network as Network 
from config import USERS_DB

_logger = getLogger(__name__)

#region User Tokens Cache and refresh
class dbSchema:
	class _table(StrEnum):
		__table__: ClassVar[str]

		@classmethod
		def t(cls) -> str:
			return cls.__table__
		@classmethod
		def q(cls, column: "dbSchema._table") -> str:
			return f"{cls.__table__}.{column.value}"
	class tokens(_table):
		__table__ = "tokens"

		HASH = "hash_token"
		EMAIL = "email"
		JWT = "jwt"
		EXPIRES = "jwt_expires"
		USER_TOKEN = "token"
		UID = "uidHint"
		REQUESTS_CNT = "requests_count"
		LAST_USED = "last_used"
		CREATED = "created_at"

	class sso_sessions(_table):
		__table__ = "sso_sessions"

		EMAIL = "email"
		SID = "sid"
		SID_EXP = "exp"

scheduler = AsyncIOScheduler()

_MACHINE_ID: str
if not USERS_DB.MACHINE_ID.exists():
	_logger.warning("No 'machine.id' file found, autogenerating a machine ID")
	_MACHINE_ID = md5(urandom(16)).hexdigest()
	USERS_DB.MACHINE_ID.write_text(_MACHINE_ID)
	USERS_DB.MACHINE_ID.chmod(0o600)
else:
	_MACHINE_ID = USERS_DB.MACHINE_ID.read_text().strip()

@dataclass(slots=True)
class _pending2FA:
	password_hash: str
	requestId: str
	userId: int
	password: str
	types: set[Literal["WTR", "GaijinPass", "Email"]]
	expires: datetime = field(default_factory=lambda: datetime.now(UTC) + timedelta(minutes=15))
	code: str = None
	await_task: Task = None
	provided: Event = field(default_factory=lambda: Event())
	login: Event = field(default_factory=lambda: Event())
	auth_data: dict[str, Any] = None
	login_data: dict[str, Any] = None

	def check_password(self, password: str):
		return self.password_hash == md5(password.encode()).hexdigest()
_PENDING_2FA: dict[str, _pending2FA] = {} # email -> {hashed_password, requestId, userId, types, code (after answering)}

@dataclass(slots=True, frozen=True)
class LoginEntry:
	jwt: str
	token: str
	uidHint: int

	entry: UserAuth.Entry | None = None

class UserAuth:
	_auth_used_cache = {}
	_auth_used_lock = Lock()

	@dataclass(frozen=True, slots=True)
	class _sidValue:
		sid: str
		sid_expires: datetime

	@dataclass(slots=True)
	class Entry: # Short lived data class with some helper methods
		@dataclass(slots=True)
		class sid_entry:
			sid: str
			exp: datetime
			@classmethod
			def from_row(cls, row:Row, parent:UserAuth.Entry):
				try:
					sid = row[dbSchema.sso_sessions.SID]
					if sid is None:
						return
					return cls(
						parent._parent._dec(sid),
						datetime.fromtimestamp(row[dbSchema.sso_sessions.SID_EXP], UTC)
					)
				except (IndexError, TypeError):
					return
			def to_json(self):
				return asdict(self)

		_parent: UserAuth

		hashed: str
		jwt: str # Session token
		expires: datetime
		user_token: str # User token
		last_used: datetime # Used for invalidating old tokens
		uidHint: int # uidHint value for refresh and other auth calls
		email:str # For contact purposes
		requests_count: int = 0 # For token statistics (and to find abuse)
		sid:sid_entry | None = None
		__saved:dict[str, str|int|datetime] = field(default_factory=dict) # Saved to file state, used for comparing what to change
	
		@classmethod
		async def from_hash(cls, parent:"UserAuth", hash:str):
			async with parent._transaction() as cur:
				row = await cur.execute(f"""
				SELECT * 
				FROM {dbSchema.tokens.t()} LEFT JOIN {dbSchema.sso_sessions.t()} ON ({dbSchema.tokens.q(dbSchema.tokens.EMAIL)} = {dbSchema.sso_sessions.q(dbSchema.sso_sessions.EMAIL)}) 
				WHERE {dbSchema.tokens.HASH} = ? AND {dbSchema.tokens.EXPIRES} > strftime('%s', 'now')""", (hash,))
				row = await row.fetchone()
				if row is None:
					return None
				return await cls.from_row(parent, row)
		@classmethod
		async def from_email(cls, parent:"UserAuth", email:str):
			async with parent._transaction() as cur:
				row = await cur.execute(f"""
				SELECT * 
				FROM {dbSchema.tokens.t()} LEFT JOIN {dbSchema.sso_sessions.t()} ON ({dbSchema.tokens.q(dbSchema.tokens.EMAIL)} = {dbSchema.sso_sessions.q(dbSchema.sso_sessions.EMAIL)}) 
				WHERE {dbSchema.tokens.EMAIL} = ? AND {dbSchema.tokens.EXPIRES} > strftime('%s', 'now')""", (email,))
				row = await row.fetchone()
				if row is None:
					return None
				return await cls.from_row(parent, row)
		@classmethod
		async def from_row(cls, parent:"UserAuth", row:Row):
			t = dbSchema.tokens
			jwt = parent._dec(str(row[t.JWT]))
			self = cls(
				hashed = str(row[t.HASH]),
				jwt=jwt,
				expires = datetime.fromtimestamp(int(row[t.EXPIRES]), UTC),
				user_token = parent._dec(str(row[t.USER_TOKEN])),
				last_used = datetime.fromtimestamp(int(row[t.LAST_USED]), UTC),
				requests_count = int(row[t.REQUESTS_CNT]),
				uidHint = int(row[t.UID]),
				email = str(row[t.EMAIL]),

				_parent = parent
			)

			self.sid = cls.sid_entry.from_row(row, self)
			self.__saved = self.to_json()
			return self

		def getEntry(self) -> LoginEntry:
			return LoginEntry(
				self.jwt,
				self.user_token,
				self.uidHint,
				self
			)

		async def refresh(self):
			_logger.debug(f"Refreshing entry for {self.email}")
			if datetime.now(UTC) > self.expires:
				raise AuthenticationError(status.HTTP_401_UNAUTHORIZED, "Login expired. Please reauthenticate.")

			async with Network.operation() as session:
				async with session.post(
					"https://auth.gaijinent.com/login_token.php", 
					data={"token": self.user_token}, 
					headers={
						"User-Agent": "ThunderAPI/1.0", 
						"Content-Type": "application/x-www-form-urlencoded"
					}
				) as r:
					content = await Network.handle_response(r)

			if content.get("status") == "LOGINERROR":
				if content.get("error") == "Wrong token":
					self.expires = datetime.now(UTC)
					return
				raise AuthenticationError(status.HTTP_400_BAD_REQUEST, f"An error occurred during authentication: {content}")

			self.expires = datetime.now(UTC) + timedelta(seconds=int(content["token_exp"]))

			if "jwt" in content:
				self.jwt = content["jwt"]

			await self._write_values()

		def timeLeft(self) -> timedelta:
			return self.expires - datetime.now(UTC)
		def usedWithin(self, minutes:int) -> bool:
			return self.last_used > (datetime.now(UTC) - timedelta(minutes=minutes)) 
		async def getSquadronId(self) -> int|None:
			from utils.connection import Request
			loginEntry = self.getEntry()
			userEntry = (await Request.send_template(
				loginEntry,
				"get_users_terse_info",
				usersList=str(self.uidHint)
			)).get(str(self.uidHint))

			if userEntry is None:
				raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
				
			if userEntry.get("clanName") is None:
				return None

			squadronData = await Request.send_template(
				loginEntry,
				"clan_find_by_prefix",
				namePrefix=userEntry["clanName"],
				tagPrefix=userEntry["clanTag"]
			)
			if "clan" in squadronData:
				for member in squadronData["clan"]["members"]: 
					# Extra check, when applying Gaijin already sets `clanName`, before being accepted
					if int(member["uid"]) == self.uidHint:
						return int(squadronData["clan"]["_id"])
				return
			elif isinstance(squadronData, dict):
				squadronData = [squadronData,]

			for squadron in squadronData:
				for member in squadron["members"]:
					if int(member["uid"]) == self.uidHint:
						return int(squadron["_id"])
			return None

		async def _write_values(self):
			changed:dict[str, int|str] = {}
			sso_changed:dict[str, str|int] = {}
			
			for key, value in self.to_json().items():
				if key == dbSchema.sso_sessions.t():
					if value is None:
						continue
					for k, v in value.items():
						if self.__saved[dbSchema.sso_sessions.t()].get(k) == v:
							continue
						if k == dbSchema.sso_sessions.SID:
							sso_changed[k] = self._parent._enc(v)
						elif isinstance(v, datetime):
							sso_changed[k] = dtToTimestamp(v)
						else:
							sso_changed[k] = v
					continue
				elif self.__saved[key] == value: 
					continue
				elif isinstance(value, datetime):
					value = dtToTimestamp(value)
				if key in [dbSchema.tokens.JWT, dbSchema.tokens.USER_TOKEN]:
					changed[key] = self._parent._enc(value)
				else:
					changed[key] = value

			async with self._parent._transaction() as cur:
				if changed:
					await cur.execute(f"""
						UPDATE {dbSchema.tokens.t()} 
						SET {", ".join([f"{k} = ?" for k in changed.keys()])}
						WHERE {dbSchema.tokens.HASH} = ?
					""",
					(
						*changed.values(),
						self.__saved[dbSchema.tokens.HASH]
					))
				if sso_changed:
					await cur.execute(f"""
						UPDATE {dbSchema.sso_sessions.t()} 
						SET {", ".join([f"{k} = ?" for k in sso_changed.keys()])}
						WHERE {dbSchema.sso_sessions.EMAIL} = ?
					""",
					(
						*sso_changed.values(),
						self.__saved[dbSchema.sso_sessions.EMAIL]
					))	

			self.__saved = self.to_json()
		
		def to_json(self) -> dict[str, str|int|datetime|dict[str, str|datetime]]:
			t = dbSchema.tokens
			s = dbSchema.sso_sessions
			obj = {
				t.HASH: self.hashed,
				t.JWT: self.jwt,
				t.EXPIRES: self.expires,
				t.USER_TOKEN: self.user_token,
				t.LAST_USED: self.last_used,
				t.UID:self.uidHint,
				t.EMAIL:self.email,
				t.REQUESTS_CNT:self.requests_count,
			}

			if self.sid	is not None:
				obj[s.t()] = self.sid.to_json()
			else:
				obj[s.t()] = {}

			return obj
	
	__autorefresh_job:Job = None

	def __init__(self):

		if not USERS_DB.KEY.exists():
			_logger.warning("No 'users.key' file found, autogenerating a key")
			enc_key = Fernet.generate_key().decode("utf-8")
			USERS_DB.KEY.write_text(enc_key)
			USERS_DB.KEY.chmod(0o600)
		else:
			enc_key = USERS_DB.KEY.read_text().strip()
		self.__fernet = Fernet(enc_key.encode())

		_logger.debug("User Token Cache initialized")

	async def get(self, token:str):
		hash = self._hash_token(token)
		return await self.Entry.from_hash(self, hash)
	
	async def login(self, email:str, password:str|None = None) -> tuple[str, int]:
		"""Gaijin login flow, returns a new user token for the given account"""
		data = await login(email, password)

		async with self._transaction() as cur:
			schema = dbSchema
			raw, hash = self._generate_hash()
			if await (await cur.execute(f"SELECT 1 FROM {schema.tokens.t()} WHERE {schema.tokens.EMAIL} = ?", (email,))).fetchone() is not None:
				_logger.debug(f"Overwriting old loginentry for {email}")
				await cur.execute(f"""
					UPDATE {schema.tokens.t()} 
					SET 
						{schema.tokens.HASH} = ?, 
						{schema.tokens.JWT} = ?,
						{schema.tokens.EXPIRES} = ?, 
						{schema.tokens.USER_TOKEN} = ?, 
						{schema.tokens.UID} = ?,
						{schema.tokens.LAST_USED} = ?
					WHERE {schema.tokens.EMAIL} = ?;
					""", 
					(hash, self._enc(data["jwt"]), dtToTimestamp(datetime.now(UTC) + timedelta(seconds=int(data["token_exp"]))), self._enc(data["token"]), data["user_id"], dtToTimestamp(datetime.now(UTC)), email)
				)
			else:
				await cur.execute(f"""
					INSERT INTO {schema.tokens.t()} 
					({schema.tokens.HASH}, {schema.tokens.JWT}, {schema.tokens.EXPIRES}, {schema.tokens.USER_TOKEN}, {schema.tokens.UID}, {schema.tokens.EMAIL}, {schema.tokens.LAST_USED}) 
					VALUES ({', '.join(["?" for i in range(7)])})""", 
					(hash, self._enc(data["jwt"]), dtToTimestamp(datetime.now(UTC) + timedelta(seconds=int(data["token_exp"]))), self._enc(data["token"]), data["user_id"], email, dtToTimestamp(datetime.now(UTC)))
				)		
		return raw, data["user_id"]

	async def get_sid(self, entry:Entry, password:str|None = None) -> _sidValue | None:
		"""Returns the identity_sid and its expiry time for the given user"""
		async with self._transaction() as cur:
			row = await (await cur.execute(f"SELECT * FROM {dbSchema.sso_sessions.t()} WHERE {dbSchema.sso_sessions.EMAIL} = ? AND {dbSchema.sso_sessions.SID_EXP} > strftime('%s', 'now')", (entry.email,))).fetchone()
			if row is not None:
				return self._sidValue(
					self._dec(row[dbSchema.sso_sessions.SID]),
					datetime.fromtimestamp(row[dbSchema.sso_sessions.SID_EXP])
				)
		async with Network.operation() as session:
			async with session.get("https://warthunder.com/") as response:
				await response.read()
				cookies = response.history[0].cookies
				sid = cookies.get("identity_sid")
				if sid is None:
					return
				sid = sid.value
			ssoURL = (
				f"https://login.gaijin.net/en/sso/reLogin/?"
				f"return_url={b64encode("https://warthunder.com/en/tournament/replay".encode()).decode()}"
				f"&crc=f07a293e4f798bf750bd92c4a1cc95da"
				f"&public_key=IwdDDrPgUfXo3CYkaiwR"
				f"&domain=warthunder.com"
				f"&base_return_url=1"
				f"&refresh_token=1"
			)
			async with session.get(ssoURL) as response:
				await response.read()
				cookies = response.cookies
				nsid = cookies.get("identity_sid", sid)
				if nsid != sid:
					sid = nsid.value

			async with session.post(
				"https://login.gaijin.net/en/sso/login/procedure/",
				data={
					"login": entry.email,
					"password": password,
					"action": "",
					"referer": "",
					"fingerprint": _MACHINE_ID,
					"app_id": "",
				},
				headers={
					"Content-Type": "application/x-www-form-urlencoded",
					"Referer": ssoURL,
					"Origin": "https://login.gaijin.net",
					"User-Agent": "ThunderAPI/1.0"
				},
				allow_redirects=False
			) as response:
				await response.read()
				if response.status == 200:
					body = await response.text()
					request_id = re_search(r'name="request_id".*?value="([^"]+)"', body)
					password_hidden = re_search(r'name="password_hidden".*?value="([^"]+)"', body)
					login_email = re_search(r'name="login".*?value="([^"]+)"', body)
					if request_id:
						async with session.ws_connect(f"wss://login.gaijin.net/ws/auth/status/?requestId={request_id.group(1)}") as ws:
							msg = await ws.receive_json(timeout=60)  # blocks until user approves
							if msg.get("Message") and msg.get("Message") != "cancel":
								# Re-POST with the 2FA code
								resp = await session.post(
									"https://login.gaijin.net/en/sso/login/procedure/",
									data={
										"login": login_email.group(1),
										"password_hidden": password_hidden.group(1),
										"code": msg["Message"],
										"request_id": msg["Request"],
										"action": "", 
										"referer": "", 
										"fingerprint": _MACHINE_ID, 
										"app_id": ""
									},
									headers={},
									allow_redirects=False,
								)
								c = await resp.read()
								location = resp.headers.get("Location")

				elif response.status not in (302, 303):
					_logger.error(f"Login failed with status {response.status}")
					raise HTTPException(500)
				else:
					location = response.headers.get("Location", "")
				if not location:
					_logger.error("No redirect URL in login response")
					raise HTTPException(500)

			if location.startswith("/"):
				location = f"https://login.gaijin.net{location}"
			async with session.get(
				location,
				cookies={"identity_sid": sid},
				allow_redirects=False
			) as response:
				await response.read()
				cookies = response.cookies
				nsid = cookies.get("identity_sid", sid)
				if nsid != sid:
					sid = nsid.value
		if not isinstance(sid, str):
			raise RuntimeError("identity_sid is not a string")
		if sid is not None:
			expiry = datetime.now(UTC)+timedelta(days=14)
			async with self._transaction() as cur:
				q = await cur.execute(f"SELECT 1 FROM {dbSchema.sso_sessions.t()} WHERE {dbSchema.sso_sessions.EMAIL} = ?", (entry.email,))
				if (await q.fetchone()) is None:
					await cur.execute(f"INSERT INTO {dbSchema.sso_sessions.t()} ({dbSchema.sso_sessions.EMAIL}, {dbSchema.sso_sessions.SID}, {dbSchema.sso_sessions.SID_EXP}) VALUES (?, ?, ?)", (entry.email, self._enc(sid), dtToTimestamp(expiry)))
			entry.sid = entry.sid_entry(sid, expiry)
			await entry._write_values()

	async def remove_entry(self, entry: Entry) -> bool:
		async with self._transaction() as cur:
			await cur.execute(f"DELETE FROM {dbSchema.sso_sessions.t()} WHERE {dbSchema.sso_sessions.EMAIL} = ?", (entry.email,))
			await cur.execute(f"DELETE FROM {dbSchema.tokens.t()} WHERE {dbSchema.tokens.HASH} = ?", (entry.hashed,))
			if await (await cur.execute(f"SELECT 1 FROM {dbSchema.tokens.t()} WHERE {dbSchema.tokens.HASH} = ?", (entry.hashed,))).fetchone() is None:
				_logger.debug(f"Removed entry {entry.email}")
				return True
		_logger.debug(f"Failed to remove entry {entry.email}")
		return False
	# region Helpers
	async def _force_write_used_cache(self):
		async with self._auth_used_lock:
			snapshot, self._auth_used_cache = self._auth_used_cache, {}

		for hashed, data in snapshot.items():
			if not data["cnt"]:
				continue

			entry = await self.Entry.from_hash(self, hashed)
			if entry is None:
				continue

			entry.requests_count += data["cnt"]
			entry.last_used = data["used"]
			await entry._write_values()

	async def _refresh(self):
		global _PENDING_2FA
		_PENDING_2FA = {k:v for k,v in _PENDING_2FA.items() if v.expires > datetime.now(UTC)}
		await self._force_write_used_cache()
		async with self._transaction() as cur:
			rows = await (await cur.execute(f"SELECT * FROM {dbSchema.tokens.t()} WHERE {dbSchema.tokens.EXPIRES} > strftime('%s', 'now')")).fetchall()

			for row in rows:
				entry = await self.Entry.from_row(self, row)
				try:
					if entry.usedWithin(24*60): # Used within the last day
						await entry.refresh()
					else:
						await self.remove_entry(entry)
				except AuthenticationError:
					_logger.error(f"Could not refresh entry {entry.email}")
					await self.remove_entry(entry)

			operation = await cur.execute(f"DELETE FROM {dbSchema.tokens.t()} WHERE {dbSchema.tokens.EXPIRES} <= strftime('%s', 'now')")
			if operation.rowcount > 0:
				_logger.info(f"Deleted {operation.rowcount} expired entries")	
		
	def _generate_hash(self) -> tuple[str, str]:
		raw_token = token_urlsafe(32)
		return raw_token, sha256(raw_token.encode()).hexdigest()
	def _hash_token(self, raw_token:str) -> str:
		return sha256(raw_token.encode()).hexdigest()
	
	def _enc(self, value:str) -> str:
		return self.__fernet.encrypt(value.encode()).decode()
	def _dec(self, value: str) -> str:
		return self.__fernet.decrypt(value.encode()).decode()

	@asynccontextmanager
	async def _transaction(self):
		con = await connect(USERS_DB.DB)
		con.row_factory = Row
		try:
			cur = await con.cursor()
			try:
				yield cur
				await con.commit()
			except Exception:
				await con.rollback()
				raise
			finally:
				await cur.close()
		finally:
			await con.close()
	
	async def start(self):
		global scheduler
		await self._init_db()
		if self.__autorefresh_job is None:
			self.__autorefresh_job = scheduler.add_job(
				self._refresh,
				IntervalTrigger(minutes=10)
			)
		if not scheduler.running:
			scheduler.start()

	async def close(self):
		global scheduler
		if self.__autorefresh_job is not None:
			self.__autorefresh_job.remove()
			self.__autorefresh_job = None

	async def _init_db(self):
		USERS_DB.DB.parent.mkdir(parents=True, exist_ok=True)

		if USERS_DB.DB.exists():
			if int(getenv("DEBUG_MODE", "0")) == 1:
				USERS_DB.DB.chmod(mode=0o644)
			else:
				USERS_DB.DB.chmod(mode=0o600)
			return

		if int(getenv("DEBUG_MODE", "0")) == 1:
			USERS_DB.DB.touch(mode=0o644)
		else:
			USERS_DB.DB.touch(mode=0o600)

		try:
			async with connect(USERS_DB.DB) as con:
				lines = re_sub("--.*\n", "", USERS_DB.INIT_SQL.read_text()).replace("\n", "").split(";")

				for line in lines:
					line = line.strip()
					if not line:
						continue

					await con.execute(line + ";")

				await con.commit()

			_logger.debug("Database successfully initialized")

		except OperationalError:
			USERS_DB.DB.unlink()
			_logger.exception("An error occurred during database setup")
			raise
	#endregion

class ServerAuth:
	__EMAIL: str
	__PASS: str

	_TOKEN: str
	_JWT: str
	_UID: int

	REFRESH_JOB: Job

	@classmethod
	async def start(cls) -> ServerAuth | None:
		self = cls()
		self.__EMAIL = getenv("SERVER_EMAIL")
		self.__PASS = getenv("SERVER_PASS")
		if self.__EMAIL is None or self.__PASS is None:
			_logger.warning("Server account could not be logged into. All endpoints act as having required login.")
			return
		try:
			data = await login(self.__EMAIL, self.__PASS)
		except HTTPException as e:
			if e.status_code == status.HTTP_206_PARTIAL_CONTENT:
				entry = _PENDING_2FA[self.__EMAIL]
				if "GaijinPass" not in entry.types:
					entry.code = await to_thread(input, "Please provide the 2FA code: ")
					entry.provided.set()
				await entry.provided.wait()
				data = await login(self.__EMAIL, self.__PASS)
			else:
				raise

		self._JWT = data["jwt"]
		self._TOKEN = data["token"]
		self._UID = data["user_id"]

		self.REFRESH_JOB = scheduler.add_job(
			self.refresh,
			IntervalTrigger(minutes=30)
		)

		if not scheduler.running:
			scheduler.start()

		return self

	def getLogin(self) -> LoginEntry | None:
		try:
			return LoginEntry(
				self._JWT,
				self._TOKEN,
				self._UID
			)
		except UnboundLocalError:
			return

	async def refresh(self) -> dict[str, Any]:
		async with Network.post(
			"https://auth.gaijinent.com/login_token.php", 
			data={"token": self._TOKEN}, 
			headers={
				"User-Agent": "ThunderAPI/1.0", 
				"Content-Type": "application/x-www-form-urlencoded"
			}
		) as r:
			content = await Network.handle_response(r)

		if content.get("status") == "LOGINERROR":
			if content.get("error") == "Wrong token":
				self.expires = datetime.now(UTC)
				return
			raise AuthenticationError(status.HTTP_400_BAD_REQUEST, f"An error occurred during authentication: {content}")

		if "jwt" in content:
			self._JWT = content["jwt"]

async def _await_2fa_code(email:str) -> dict[str, str|int] | None:
	tries = 0
	success = False
	entry = _PENDING_2FA.get(email)
	if entry is None:
		raise HTTPException(status.HTTP_400_BAD_REQUEST)

	data = {
		"requestId": entry.requestId,
		"userId": entry.userId
	}

	async with Network.operation() as session:
		while not success and tries < 10:
			async with session.get(f"https://auth.gaijinent.com/api/auth/requestTwoStep?requestId={data['requestId']}&userId={data['userId']}", timeout=60) as r:
				if "GaijinPass" in entry.types:
					try:
						data = await Network.handle_response(r)
						success = True
						entry.provided.set()
					except AuthenticationError:
						async with session.post(
							"https://auth.gaijinent.com/login.php", 
							data={
								"login": email,
								"password": entry.password,
								"game": "wt",
								"client": _MACHINE_ID
							},
							headers={
								"Content-Type": "application/x-www-form-urlencoded",
								"User-Agent": "ThunderAPI/1.0"
							}
						) as r:
							data = await Network.handle_response(r)
						entry.requestId = data["requestId"]
						tries += 1
						continue
				else: # UNTESTED PATH
					data = await Network.handle_response(r)
					await entry.provided.wait()
					
					success = True
	if not success or data.get("Message") == "cancel":
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA Request cancelled")

	entry.auth_data = data
	return await _login_2fa(email)

async def _login_2fa(email: str):
	if email not in _PENDING_2FA:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "2FA Entry not found")
	entry = _PENDING_2FA[email]
	await entry.provided.wait()
	async with Network.post(
		"https://auth.gaijinent.com/login.php",
		data={
			"login": email,
			"password": entry.password,
			"game": "wt",
			"2step": entry.auth_data["Message"],
			"requestId": entry.auth_data["Request"],
			"client": _MACHINE_ID
		},
		headers={
			"Content-Type": "application/x-www-form-urlencoded",
			"User-Agent": "ThunderAPI/1.0"
		}
	) as r:
		entry.login_data = await Network.handle_response(r)
	_PENDING_2FA.pop(email, None)
	entry.login.set()

async def login(email: str, password: str):
	if email in _PENDING_2FA:
		e = _PENDING_2FA[email]
		try:
			await wait_for(e.login.wait(), timeout=60)
		except TimeoutError:
			raise HTTPException(status.HTTP_408_REQUEST_TIMEOUT, "2FA timed out")
		if e.login_data["status"] == "2STEPERROR":
			raise AuthenticationError(status.HTTP_403_FORBIDDEN, "Invalid 2FA code provided.")
		if e.login_data["status"] == "LOGINERROR":
			raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Login failed: {e.login_data["error"]}")
		return e.login_data

	async with Network.operation() as session:
		async with session.post(
			"https://auth.gaijinent.com/login.php",
			data={
				"login": email,
				"password": password,
				"game": "wt",
				"client": _MACHINE_ID
			},
			headers={
				"Content-Type": "application/x-www-form-urlencoded",
				"User-Agent": "ThunderAPI/1.0"
			}
		) as r:
			data = await Network.handle_response(r)

		if data["status"] == "2STEP":
			two_factor_types = set()
			if data.get("hasGjPass"): two_factor_types.add("GaijinPass")
			if data.get("hasTwoStepEmail"): two_factor_types.add("Email")
			if data.get("hasWTR"): two_factor_types.add("WTR")
			_PENDING_2FA[email] = _pending2FA(
				password_hash= md5(password.encode()).hexdigest(),
				requestId= data['requestId'],
				userId= data["userId"],
				types= two_factor_types,
				password=password
			)

			_PENDING_2FA[email].await_task = get_running_loop().create_task(_await_2fa_code(email))
			raise HTTPException(status.HTTP_206_PARTIAL_CONTENT, "Please complete 2FA and call this endpoint again")

		if data["status"] == "LOGINERROR":
			raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Login failed: {data["error"]}")

	return data