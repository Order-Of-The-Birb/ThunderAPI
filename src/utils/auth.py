from __future__ import annotations

import sys
from asyncio import (
	Future,
	Lock,
	Task,
	create_subprocess_exec,
	gather,
	get_running_loop,
	shield,
	sleep,
	timeout,
	wait_for,
)
from asyncio.subprocess import PIPE
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import md5, sha256
from logging import getLogger
from os import getenv, urandom
from re import sub as re_sub
from secrets import compare_digest, token_urlsafe
from typing import ClassVar
from weakref import WeakValueDictionary

from aiohttp import ClientConnectionError, ClientResponseError
from aiosqlite import OperationalError, Row, connect
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from cryptography.fernet import Fernet
from fastapi import HTTPException, status

import utils.connection.network as Network
from config import USERS_DB
from utils.helper import AuthenticationError, dtToTimestamp

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

scheduler = AsyncIOScheduler()

_MACHINE_ID: str
if not USERS_DB.MACHINE_ID.exists():
	_logger.warning("No 'machine.id' file found, autogenerating a machine ID")
	_MACHINE_ID = md5(urandom(16)).hexdigest()
	USERS_DB.MACHINE_ID.write_text(_MACHINE_ID)
	USERS_DB.MACHINE_ID.chmod(0o600)
else:
	_MACHINE_ID = USERS_DB.MACHINE_ID.read_text().strip()

_CHALLENGE_LIFETIME = timedelta(minutes = 15)

@dataclass(slots = True)
class _Pending2FA:
	password_hash: bytes
	code: Future[str] | None
	await_task: Task[dict]
	expires: datetime

_PENDING_2FA: dict[str, _Pending2FA] = {}
_login_locks: WeakValueDictionary[str, Lock] = WeakValueDictionary()

@dataclass(slots = True, frozen = True)
class LoginEntry:
	jwt: str
	token: str
	uidHint: int

	entry: UserAuth.Entry | None = None

class UserAuth:
	_auth_used_cache = {}
	_auth_used_lock = Lock()

	@dataclass(slots = True)
	class Entry: # Short lived data class with some helper methods
		_parent: UserAuth

		hashed: str
		jwt: str # Session token
		expires: datetime
		user_token: str # User token
		last_used: datetime # Used for invalidating old tokens
		uidHint: int # uidHint value for refresh and other auth calls
		email:str # For contact purposes
		requests_count: int = 0 # For token statistics (and to find abuse)
		__saved:dict[str, str|int|datetime] = field(default_factory = dict) # Saved to file state, used for comparing what to change

		@classmethod
		async def from_hash(cls, parent:"UserAuth", hash:str):
			async with parent._transaction() as cur:
				row = await cur.execute(f"""
				SELECT *
				FROM {dbSchema.tokens.t()}
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
				FROM {dbSchema.tokens.t()}
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
				jwt = jwt,
				expires = datetime.fromtimestamp(int(row[t.EXPIRES]), UTC),
				user_token = parent._dec(str(row[t.USER_TOKEN])),
				last_used = datetime.fromtimestamp(int(row[t.LAST_USED]), UTC),
				requests_count = int(row[t.REQUESTS_CNT]),
				uidHint = int(row[t.UID]),
				email = str(row[t.EMAIL]),

				_parent = parent
			)

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
					data = {"token": self.user_token},
					headers = {
						"User-Agent": "ThunderAPI/1.0",
						"Content-Type": "application/x-www-form-urlencoded"
					}
				) as r:
					if r.status == status.HTTP_429_TOO_MANY_REQUESTS:
						raise HTTPException(r.status, "Gaijin is rate limiting token refreshes. Please try again later.")
					content = await Network.handle_response(r, Network.ReturnType.JSON)

			if content.get("status") == "LOGINERROR":
				if content.get("error") == "Wrong token":
					self.expires = datetime.now(UTC)
					return
				raise AuthenticationError(status.HTTP_400_BAD_REQUEST, f"An error occurred during authentication: {content}")

			self.expires = datetime.now(UTC) + timedelta(seconds = int(content["token_exp"]))

			if "jwt" in content:
				self.jwt = content["jwt"]

			await self._write_values()

		def timeLeft(self) -> timedelta:
			return self.expires - datetime.now(UTC)
		def usedWithin(self, minutes:int) -> bool:
			return self.last_used > (datetime.now(UTC) - timedelta(minutes = minutes))
		async def getSquadronId(self) -> int|None:
			from utils.connection import Request
			loginEntry = self.getEntry()
			userEntry = (await Request.send_template(
				loginEntry,
				"get_users_terse_info",
				usersList = str(self.uidHint)
			)).get(str(self.uidHint))

			if userEntry is None:
				raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

			if userEntry.get("clanName") is None:
				return None

			squadronData = await Request.send_template(
				loginEntry,
				"clan_find_by_prefix",
				namePrefix = userEntry["clanName"],
				tagPrefix = userEntry["clanTag"]
			)
			if "clan" in squadronData:
				clans = squadronData["clan"]
				if isinstance(clans, dict):
					clans = [clans]

				for squadron in clans:
					for member in squadron["members"]:
						# Extra check, when applying Gaijin already sets `clanName`, before being accepted
						if int(member["uid"]) == self.uidHint:
							return int(squadron["_id"])
			return None

		async def _write_values(self):
			changed:dict[str, int|str] = {}

			for key, value in self.to_json().items():
				if self.__saved[key] == value:
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

			self.__saved = self.to_json()

		def to_json(self) -> dict[str, str|int|datetime|dict[str, str|datetime]]:
			t = dbSchema.tokens
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

	async def login(self, email:str, password:str, /, *, code: str | None = None) -> tuple[str, int]:
		"""Gaijin login flow, returns a new user token for the given account"""
		data = await login(email, password, code = code)

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
					(hash, self._enc(data["jwt"]), dtToTimestamp(datetime.now(UTC) + timedelta(seconds = int(data["token_exp"]))), self._enc(data["token"]), data["user_id"], dtToTimestamp(datetime.now(UTC)), email)
				)
			else:
				await cur.execute(f"""
					INSERT INTO {schema.tokens.t()}
					({schema.tokens.HASH}, {schema.tokens.JWT}, {schema.tokens.EXPIRES}, {schema.tokens.USER_TOKEN}, {schema.tokens.UID}, {schema.tokens.EMAIL}, {schema.tokens.LAST_USED})
					VALUES ({', '.join(["?" for i in range(7)])})""",
					(hash, self._enc(data["jwt"]), dtToTimestamp(datetime.now(UTC) + timedelta(seconds = int(data["token_exp"]))), self._enc(data["token"]), data["user_id"], email, dtToTimestamp(datetime.now(UTC)))
				)
		return raw, int(data["user_id"])

	async def remove_entry(self, entry: Entry) -> bool:
		async with self._transaction() as cur:
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
		now = datetime.now(UTC)
		for email in [k for k, v in _PENDING_2FA.items() if v.expires <= now]:
			_PENDING_2FA.pop(email, None)
		await self._force_write_used_cache()
		async with self._transaction() as cur:
			rows = await (await cur.execute(f"SELECT * FROM {dbSchema.tokens.t()} WHERE {dbSchema.tokens.EXPIRES} > strftime('%s', 'now')")).fetchall()

		for row in rows:
			entry = await self.Entry.from_row(self, row)
			if not entry.usedWithin(24*60):
				await self.remove_entry(entry)
				continue
			try:
				await entry.refresh()
			except AuthenticationError:
				_logger.error(f"Could not refresh entry {entry.email}")
				await self.remove_entry(entry)
			except HTTPException as e:
				if e.status_code != status.HTTP_429_TOO_MANY_REQUESTS:
					raise
				_logger.warning("Gaijin rate limited a token refresh. Deferring it until the next refresh cycle.")
			except (ClientResponseError, ClientConnectionError, TimeoutError) as e:
				_logger.warning("Gaijin token refresh failed (%s). Skipping this account for this run.", type(e).__name__)

		async with self._transaction() as cur:
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
				IntervalTrigger(minutes = 10)
			)
		if not scheduler.running:
			scheduler.start()

	async def close(self):
		global scheduler
		tasks = [entry.await_task for entry in _PENDING_2FA.values()]
		_PENDING_2FA.clear()
		for task in tasks:
			task.cancel()
		await gather(*tasks, return_exceptions = True)
		if self.__autorefresh_job is not None:
			self.__autorefresh_job.remove()
			self.__autorefresh_job = None

	async def _init_db(self):
		USERS_DB.DB.parent.mkdir(parents = True, exist_ok = True)

		if USERS_DB.DB.exists():
			if int(getenv("DEBUG_MODE", "0")) == 1:
				USERS_DB.DB.chmod(mode = 0o644)
			else:
				USERS_DB.DB.chmod(mode = 0o600)
			return

		if int(getenv("DEBUG_MODE", "0")) == 1:
			USERS_DB.DB.touch(mode = 0o644)
		else:
			USERS_DB.DB.touch(mode = 0o600)

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
	__EXP: datetime

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

		await self.__login()

		self.REFRESH_JOB = scheduler.add_job(
			self.__refresh,
			IntervalTrigger(minutes = 45)
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
		except AttributeError:
			return

	async def __refresh(self):
		if self.__EXP < datetime.now(UTC):
			return await self.__login()
		elif (datetime.now(UTC) + timedelta(minutes = 50)) < self.__EXP: # 5 extra minutes for buffer
			return
		async with Network.post(
			"https://auth.gaijinent.com/login_token.php",
			Network.ReturnType.JSON,
			data = {"token": self._TOKEN},
			headers = {
				"User-Agent": "ThunderAPI/1.0",
				"Content-Type": "application/x-www-form-urlencoded"
			}
		) as r:
			content = r

		if content.get("status") == "LOGINERROR":
			if content.get("error") == "Wrong token":
				return await self.__login()
			raise AuthenticationError(status.HTTP_400_BAD_REQUEST, f"An error occurred during authentication: {content}")

		if "jwt" in content:
			self._JWT = content["jwt"]
		self.__EXP = datetime.now(UTC) + timedelta(seconds = content["token_exp"])

	async def __login(self):
		data = await _request_login(self.__EMAIL, self.__PASS)
		if data["status"] == "2STEP":
			data = await _complete_2fa(self.__EMAIL, self.__PASS, data)

		self._JWT = data["jwt"]
		self._TOKEN = data["token"]
		self._UID = int(data["user_id"])
		self.__EXP = datetime.now(UTC) + timedelta(seconds = int(data["token_exp"]))

async def _request_login(email: str, password: str, *, request_id: str | None = None, code: str | None = None):
	form = {"login": email, "password": password, "game": "wt", "client": _MACHINE_ID}
	if code is not None:
		form["2step"] = code
		if request_id is not None:
			form["requestId"] = request_id

	try:
		async with Network.post(
			"https://auth.gaijinent.com/login.php",
			resp_state = "init" if code is None else "2fa_login",
			data = form,
			headers = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "ThunderAPI/1.0"}
		) as data:
			return _checked_login(data, allow_challenge = code is None)
	except ClientResponseError as err:
		if err.status == 429:
			raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Gaijin is rate limiting login attempts. Please try again later.") from err
		raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Gaijin login failed") from err
	except (ClientConnectionError, TimeoutError) as err:
		raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not reach Gaijin login") from err

def _checked_login(data: dict, *, allow_challenge: bool):
	if isinstance(data, dict):
		match data.get("status"):
			case "2STEP" if allow_challenge and data.get("requestId") and data.get("userId") is not None:
				return data
			case "2STEPERROR":
				raise AuthenticationError(status.HTTP_403_FORBIDDEN, "Invalid 2FA code provided.")
			case "LOGINERROR":
				reason = data.get("error", "Unknown login error")
				raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Login failed: {reason}")
			case "OK" if isinstance(data.get("jwt"), str) and isinstance(data.get("token"), str) and data["jwt"] and data["token"]:
				try:
					int(data["user_id"])
					int(data["token_exp"])
				except (KeyError, TypeError, ValueError) as err:
					raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Incomplete Gaijin login response") from err
				return data
	raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Unexpected Gaijin login response")

async def _read_server_code() -> str:
	if sys.stdin is None or not sys.stdin.isatty():
		raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Server account email 2FA requires an interactive terminal.")

	print("Please provide the 2FA code: ", end = "", flush = True)
	# A child can release the terminal when the login expires, even during a blocking read.
	reader = await create_subprocess_exec(
		sys.executable, "-I", "-S", "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.readline())",
		stdin = sys.stdin, stdout = PIPE
	)
	try:
		line, _ = await reader.communicate()
	finally:
		if reader.returncode is None:
			with suppress(ProcessLookupError):
				reader.kill()
			await reader.communicate()
	if reader.returncode or not line.strip():
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "No 2FA code was entered for the server account.")
	return line.decode().strip()

async def _complete_2fa(email: str, password: str, challenge: dict, manual_code: Future[str] | None = None):
	try:
		async with timeout(_CHALLENGE_LIFETIME.total_seconds()):
			if challenge.get("hasGjPass"):
				for attempt in range(10):
					try:
						async with Network.get(
							"https://auth.gaijinent.com/api/auth/requestTwoStep",
							params = {"requestId": challenge["requestId"], "userId": challenge["userId"]},
							timeout = 60,
							resp_state = "await_2fa"
						) as approval:
							code = approval.get("Message") if isinstance(approval, dict) else None
					except (ClientConnectionError, ClientResponseError, TimeoutError, HTTPException) as err:
						if attempt == 9:
							raise HTTPException(status.HTTP_408_REQUEST_TIMEOUT, "2FA approval timed out") from err
						await sleep(min(2**attempt, 4))
						challenge = await _request_login(email, password)
						if challenge["status"] == "OK":
							return challenge
						if not challenge.get("hasGjPass"):
							raise HTTPException(status.HTTP_409_CONFLICT, "The 2FA method changed. Please log in again.") from err
						continue
					if code == "cancel":
						raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA request cancelled")
					if not code:
						raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Missing Gaijin Pass approval")
					break
			elif manual_code is not None:
				code = await manual_code
			else:
				code = await _read_server_code()

			return await _request_login(email, password, request_id = challenge["requestId"], code = code)
	except TimeoutError as err:
		raise HTTPException(status.HTTP_408_REQUEST_TIMEOUT, "2FA challenge expired") from err

def _observe_challenge(task: Task):
	# A client can abandon a challenge before its background request fails.
	if not task.cancelled():
		task.exception()

async def login(email: str, password: str, /, *, code: str | None = None):
	password_hash = sha256(password.encode()).digest()
	# Concurrent initial logins must not issue competing requests for the same account.
	lock = _login_locks.setdefault(email, Lock())
	async with lock:
		entry = _PENDING_2FA.get(email)
		if entry is not None and entry.expires <= datetime.now(UTC):
			del _PENDING_2FA[email]
			entry = None
		if entry is None:
			if code is not None:
				raise HTTPException(status.HTTP_404_NOT_FOUND, "No active 2FA verification. Please log in first.")
			data = await _request_login(email, password)
			if data["status"] == "OK":
				return data

			loop = get_running_loop()
			manual_code = None if data.get("hasGjPass") else loop.create_future()
			task = loop.create_task(_complete_2fa(email, password, data, manual_code))
			task.add_done_callback(_observe_challenge)
			_PENDING_2FA[email] = _Pending2FA(password_hash, manual_code, task, datetime.now(UTC) + _CHALLENGE_LIFETIME)
			if manual_code is None:
				raise HTTPException(status.HTTP_206_PARTIAL_CONTENT, "Please complete 2FA and call this endpoint again")
			raise HTTPException(status.HTTP_206_PARTIAL_CONTENT, "Please submit your code to /v1/answer-2fa")

		if not compare_digest(entry.password_hash, password_hash):
			raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid password")
		if entry.await_task.done() and entry.await_task.exception() is not None:
			del _PENDING_2FA[email]
			entry.await_task.result()
		if entry.code is not None:
			if code is None:
				raise HTTPException(status.HTTP_206_PARTIAL_CONTENT, "Please submit your code to /v1/answer-2fa")
			if not entry.code.done():
				entry.code.set_result(code)
			elif entry.code.cancelled() or entry.code.result() != code:
				raise HTTPException(status.HTTP_409_CONFLICT, "A code has already been submitted for this challenge")
		elif code is not None:
			raise HTTPException(status.HTTP_400_BAD_REQUEST, "Approve this login using Gaijin Pass")

	try:
		data = await wait_for(shield(entry.await_task), timeout = 60)
	except TimeoutError as err:
		raise HTTPException(status.HTTP_408_REQUEST_TIMEOUT, "2FA is still pending. Please try again.") from err
	except Exception:
		if _PENDING_2FA.get(email) is entry:
			del _PENDING_2FA[email]
		raise

	if _PENDING_2FA.get(email) is not entry:
		raise HTTPException(status.HTTP_409_CONFLICT, "The 2FA challenge is no longer active")
	del _PENDING_2FA[email]
	return data
