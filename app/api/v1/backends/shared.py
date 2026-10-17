from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing_extensions import Annotated
from pydantic import StringConstraints, Field
from datetime import datetime, UTC
import utils
from utils import users_auth
from utils.auth import LoginEntry

security = HTTPBearer(description="Get the token from `POST /v1/login`")
optional_security = HTTPBearer(auto_error=False)

class Authentication:
	@staticmethod
	async def _track_usage(user: LoginEntry):
		# move the existing flush/counter block here
		if user.entry is None:
			raise HTTPException(status.HTTP_409_CONFLICT, "You must be logged in")
		flush = False
		async with users_auth._auth_used_lock:
			cache = users_auth._auth_used_cache.setdefault(user.entry.hashed, {"cnt": 0})
			cache["cnt"] += 1
			cache["used"] = datetime.now(UTC)
			if cache["cnt"] >= 10:
				user.entry.requests_count += cache["cnt"]
				user.entry.last_used = cache["used"]
				cache["cnt"] = 0
				flush = True
		if flush:
			await user.entry._write_values()

	@staticmethod
	async def get_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
		user = await users_auth.get(credentials.credentials)
		if not user:
			raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
		user = user.getEntry()
		await Authentication._track_usage(user)
		return user

	@staticmethod
	async def get_server_auth() -> LoginEntry:
		if utils.server_auth is None:
			raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Server account not configured")

		entry = utils.server_auth.getLogin()
		if entry is None:
			raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Server account not configured")
		return entry

	@staticmethod
	async def get_optional_auth(
		credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
	) -> LoginEntry:
		if credentials is not None:
			user = await users_auth.get(credentials.credentials)
			if user is not None:
				user = user.getEntry()
				await Authentication._track_usage(user)
				return user
		return await Authentication.get_server_auth()


TokenBearer =	Annotated[LoginEntry, Depends(Authentication.get_auth)			]
ServerBearer =	Annotated[LoginEntry, Depends(Authentication.get_server_auth)	]
OptionalAuth =	Annotated[LoginEntry, Depends(Authentication.get_optional_auth)	]

IntString = Annotated[
	str,
	StringConstraints(pattern=r"^\d+$"),
	Field(description="Integer value represented as a string", examples=["10016", "652677", "62762477"]),
]
IpString = Annotated[
	str,
	StringConstraints(pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
	Field(description="IP address represented as a string", examples=["0.0.0.0", "192.168.0.1", "127.0.0.1"])
]
