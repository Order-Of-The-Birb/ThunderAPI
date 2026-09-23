from __future__ import annotations
from dotenv import set_key
from re import sub as re_sub, search as re_search
from logging import getLogger
from asyncio import Lock
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job
from aiosqlite import connect, Row, OperationalError
from os import getenv, urandom
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar, Literal
from fastapi import HTTPException, status
from hashlib import sha256, md5
from secrets import token_urlsafe
from pathlib import Path
from enum import StrEnum
from contextlib import asynccontextmanager
from jwt import decode as jwt_decode
from dataclasses import dataclass, asdict, field
from base64 import b64encode
from cryptography.fernet import Fernet

from utils.helper import dtToTimestamp, AuthenticationError
from utils.network import NetworkManager

_logger = getLogger(__name__)

@dataclass(frozen=True, slots=True)
class jwtData:
	auth: str
	cntry: str
	exp: datetime
	fac: str
	iat: datetime
	lng: str
	loc: str
	nick: str
	slt: str
	tgs: tuple[str]
	uid: int
	extras: dict[str, Any]

	@classmethod
	def from_jwt(cls, jwt:str) -> jwtData:
		data = jwt_decode(jwt, options={"verify_signature": False})
		return cls(
			data["auth"],
			data["cntry"],
			datetime.fromtimestamp(data["exp"], UTC),
			data["fac"],
			datetime.fromtimestamp(data["iat"], UTC),
			data["lng"],
			data["loc"],
			data["nick"],
			data["slt"],
			tuple(data["tgs"].split(",")),
			data["uid"],
			extras={k:v for k, v in data.items() if k not in ["auth","cntry","exp","fac","iat","lng","loc","nick","slt","tgs","uid"]}
		)
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
		JWT_EXPIRES = "jwt_expires"
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

class UserAuth:
	scheduler: AsyncIOScheduler
	_auth_used_cache = {}
	_auth_used_lock = Lock()

	@dataclass(frozen=True, slots=True)
	class _sidValue:
		sid: str
		sid_expires: datetime
	@dataclass(slots=True)
	class _pending2FA:
		password_hash: str
		requestId: str
		userId: int
		types: set[Literal["WTR", "GaijinPass", "Email"]]
		expires: datetime = field(default_factory=lambda: datetime.fromtimestamp((datetime.now(UTC) + timedelta(minutes=15)).timestamp()))
		code: str = None
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
		jwt_expires: datetime # Inferred from jwt
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
				WHERE {dbSchema.tokens.HASH} = ? AND {dbSchema.tokens.JWT_EXPIRES} > strftime('%s', 'now')""", (hash,))
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
				WHERE {dbSchema.tokens.EMAIL} = ? AND {dbSchema.tokens.JWT_EXPIRES} > strftime('%s', 'now')""", (email,))
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
				jwt_expires = jwtData.from_jwt(jwt).exp,
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

		async def refresh(self):
			_logger.debug(f"Refreshing entry for {self.email}")
			if datetime.now(UTC) > self.jwt_expires:
				raise AuthenticationError(status.HTTP_401_UNAUTHORIZED, "Login expired. Please reauthenticate.")

			async with self._parent._networkManager.operation() as session:
				async with session.post(
					"https://auth.gaijinent.com/login_token.php", 
					data={"token": self.user_token}, 
					headers={
						"User-Agent": "ThunderAPI/1.0", 
						"Content-Type": "application/x-www-form-urlencoded"
					}
				) as r:
					content = await self._parent._networkManager.handle_response(r)

			if content.get("status") == "LOGINERROR":
				if content.get("error") == "Wrong token":
					self.jwt_expires = datetime.now(UTC)
					return
				raise AuthenticationError(status.HTTP_400_BAD_REQUEST, f"An error occurred during authentication: {content}")

			if "jwt" not in content:
				raise AuthenticationError(status.HTTP_401_UNAUTHORIZED, f"Unexpected refresh response: {content}")
			if self.jwt != content["jwt"]:
				self.jwt = content["jwt"]
				self.jwt_expires = jwtData.from_jwt(self.jwt).exp
			await self._write_values()

		def timeLeft(self) -> timedelta:
			return self.jwt_expires - datetime.now(UTC)
		def usedWithin(self, minutes:int) -> bool:
			return self.last_used > (datetime.now(UTC) - timedelta(minutes=minutes)) 
		async def getSquadronId(self) -> int|None:
			from tools import Request
			userEntry = (await Request.send_template(
				self,
				"get_users_terse_info",
				usersList=str(self.uidHint)
			)).get(str(self.uidHint))

			if userEntry is None:
				raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
				
			if userEntry.get("clanName") is None:
				return None

			squadronData = await Request.send_template(
				self,
				"clan_find_by_prefix",
				namePrefix=userEntry["clanName"],
				tagPrefix=userEntry["clanTag"]
			)
			if "clan" in squadronData:
				return int(squadronData["clan"]["_id"])
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
				t.JWT_EXPIRES: self.jwt_expires,
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
	__db_path:Path = None
	_machine_id:str = None
	_pending_2fa:dict[str, _pending2FA] # email -> {hashed_password, requestId, userId, types, code (after answering)}
	_networkManager:NetworkManager

	def __init__(self, networkManager:NetworkManager):
		self._networkManager = networkManager
		self.scheduler = AsyncIOScheduler()

		self._pending_2fa = {}
		self.__db_path = Path(__file__).parent / "users.db"
		key = getenv("TOKEN_ENC_KEY")
		if not key:
			_logger.warning("No 'TOKEN_ENC_KEY' env variable found, autogenerating a key")
			key = Fernet.generate_key().decode("utf-8")
			set_key(".env", "TOKEN_ENC_KEY", key)
		self.__fernet = Fernet(key.encode())

		key = getenv("MACHINE_ID")
		if not key:
			_logger.warning("No 'MACHINE_ID' env variable found, autogenerating a machine id")
			key = md5(urandom(16)).hexdigest()
			set_key(".env", "MACHINE_ID", key)
		self._machine_id = key
		

		_logger.debug("User Token Cache initialized")

	async def get(self, token:str):
		hash = self._hash_token(token)
		return await self.Entry.from_hash(self, hash)
	
	async def login(self, email:str, password:str|None = None):
		"""Gaijin login flow, returns a new user token for the given account"""
		logindata = {
			"login": email,
			"password": password,
			"game": "wt",
			"client": self._machine_id
		}

		async with self._networkManager.operation() as session:
			#region Auth flow
			async with session.post(
				"https://auth.gaijinent.com/login.php",
				data=logindata,
				headers={
					"Content-Type": "application/x-www-form-urlencoded",
					"User-Agent": "ThunderAPI/1.0"
				}
			) as r:
				data = await self._networkManager.handle_response(r)

			if data["status"] == "2STEP":
				two_factor_types = set()
				if data.get("hasGjPass"): two_factor_types.add("GaijinPass")
				if data.get("hasTwoStepEmail"): two_factor_types.add("Email")
				if data.get("hasWTR"): two_factor_types.add("WTR")
				self._pending_2fa[email] = self._pending2FA(
					password_hash= md5(password.encode()).hexdigest(),
					requestId= data['requestId'],
					userId= data["userId"],
					types= two_factor_types
				)

				tries = 0
				success = False
				while not success and tries < 10:
					async with session.get(f"https://auth.gaijinent.com/api/auth/requestTwoStep?requestId={data['requestId']}&userId={data['userId']}", timeout=60) as r:
						if "GaijinPass" in two_factor_types:
							try:
								data = await self._networkManager.handle_response(r)
								success = True
							except AuthenticationError:
								async with session.post(
									"https://auth.gaijinent.com/login.php", 
									data=logindata, 
									headers={
										"Content-Type": "application/x-www-form-urlencoded",
										"User-Agent": "ThunderAPI/1.0"
									}
								) as r:
									data = await self._networkManager.handle_response(r)
								tries += 1
								continue
						else: # UNTESTED PATH
							if self._pending_2fa[email].code is None:
								tries += 1
								continue
							data = {
								"Message": self._pending_2fa[email].code,
								"Request": self._pending_2fa[email].requestId
							}
							success = True

				if not success:
					raise AuthenticationError(status.HTTP_408_REQUEST_TIMEOUT, "Could not get 2FA login in time")

				if data.get("Message") == "cancel":
					raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA Request cancelled")

				async with session.post(
					"https://auth.gaijinent.com/login.php",
					data={
						"login": email,
						"password": password,
						"game": "wt",
						"2step": data["Message"],
						"requestId": data["Request"],
						"client": self._machine_id
					},
					headers={
						"Content-Type": "application/x-www-form-urlencoded",
						"User-Agent": "ThunderAPI/1.0"
					}
				) as r:
					data = await self._networkManager.handle_response(r)

				if data["status"] == "2STEPERROR":
					self._pending_2fa.pop(email, None)
					raise AuthenticationError(status.HTTP_403_FORBIDDEN, "Invalid 2FA code provided.")

			if data["status"] == "LOGINERROR":
				raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Login failed: {data["error"]}")
			#endregion

		async with self._transaction() as cur:
			schema = dbSchema
			raw, hash = self._generate_hash()
			jwt_decoded = jwtData.from_jwt(data["jwt"])
			if await (await cur.execute(f"SELECT 1 FROM {schema.tokens.t()} WHERE {schema.tokens.EMAIL} = ?", (email,))).fetchone() is not None:
				_logger.debug(f"Overwriting old loginentry for {email}")
				await cur.execute(f"""
					UPDATE {schema.tokens.t()} 
					SET 
						{schema.tokens.HASH} = ?, 
						{schema.tokens.JWT} = ?,
						{schema.tokens.JWT_EXPIRES} = ?, 
						{schema.tokens.USER_TOKEN} = ?, 
						{schema.tokens.UID} = ?,
						{schema.tokens.LAST_USED} = ?
					WHERE {schema.tokens.EMAIL} = ?;
					""", 
					(hash, self._enc(data["jwt"]), dtToTimestamp(jwt_decoded.exp), self._enc(data["token"]), data["user_id"], dtToTimestamp(datetime.now(UTC)), email)
				)
			else:
				await cur.execute(f"""
					INSERT INTO {schema.tokens.t()} 
					({schema.tokens.HASH}, {schema.tokens.JWT}, {schema.tokens.JWT_EXPIRES}, {schema.tokens.USER_TOKEN}, {schema.tokens.UID}, {schema.tokens.EMAIL}, {schema.tokens.LAST_USED}) 
					VALUES ({', '.join(["?" for i in range(7)])})""", 
					(hash, self._enc(data["jwt"]), dtToTimestamp(jwt_decoded.exp), self._enc(data["token"]), data["user_id"], email, dtToTimestamp(datetime.now(UTC)))
				)		
		return raw

	async def get_sid(self, entry:Entry, password:str|None = None) -> _sidValue | None:
		"""Returns the identity_sid and its expiry time for the given user"""
		async with self._transaction() as cur:
			row = await (await cur.execute(f"SELECT * FROM {dbSchema.sso_sessions.t()} WHERE {dbSchema.sso_sessions.EMAIL} = ? AND {dbSchema.sso_sessions.SID_EXP} > strftime('%s', 'now')", (entry.email,))).fetchone()
			if row is not None:
				return self._sidValue(
					self._dec(row[dbSchema.sso_sessions.SID]),
					datetime.fromtimestamp(row[dbSchema.sso_sessions.SID_EXP])
				)
		async with self._networkManager.operation() as session:
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
					"fingerprint": self._machine_id,
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
										"fingerprint": self._machine_id, 
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
		self._pending_2fa = {k:v for k,v in self._pending_2fa.items() if v.expires > datetime.now(UTC)}
		await self._force_write_used_cache()
		async with self._transaction() as cur:
			rows = await (await cur.execute(f"SELECT * FROM {dbSchema.tokens.t()} WHERE {dbSchema.tokens.JWT_EXPIRES} > strftime('%s', 'now')")).fetchall()

			for row in rows:
				entry = await self.Entry.from_row(self, row)
				try:
					if entry.usedWithin(24*60): # Used within the last day
						await entry.refresh()
					else:
						await self.remove_entry(entry)
				except AuthenticationError:
					await self.remove_entry(entry)

			operation = await cur.execute(f"DELETE FROM {dbSchema.tokens.t()} WHERE {dbSchema.tokens.JWT_EXPIRES} <= strftime('%s', 'now')")
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
		con = await connect(self.__db_path)
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
		await self._init_db(self.__db_path)
		if self.__autorefresh_job is None:
			self.__autorefresh_job = self.scheduler.add_job(
				self._refresh,
				IntervalTrigger(minutes=10)
			)
		if not self.scheduler.running:
			self.scheduler.start()

	async def close(self):
		if self.__autorefresh_job is not None:
			self.__autorefresh_job.remove()
			self.__autorefresh_job = None
		if self.scheduler.running:
			self.scheduler.shutdown(wait=True)

	@staticmethod
	async def _init_db(dbPath:Path):
		if dbPath.exists():
			dbPath.chmod(mode=0o600)
			return

		init_script = dbPath.parent / (".".join(dbPath.name.split(".")[:-1]) + "_create.sql")
		dbPath.touch(mode=0o600)

		try:
			async with connect(dbPath) as con:
				lines = re_sub("--.*\n", "", init_script.read_text()).replace("\n", "").split(";")

				for line in lines:
					line = line.strip()
					if not line:
						continue

					await con.execute(line + ";")

				await con.commit()

			_logger.debug("Database successfully initialized")

		except OperationalError:
			dbPath.unlink()
			_logger.exception("An error occurred during database setup")
			raise
	#endregion
