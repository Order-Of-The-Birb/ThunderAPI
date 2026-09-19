from os import getenv
from typing_extensions import Annotated
from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from hashlib import md5

from utils import users_cache
from utils.helper import dtToTimestamp
from api.shared import limiter
from api.v1.shared import TokenBearer
from api.v1.models.auth import Login, LoginToken

router = APIRouter(
	tags=["authentication"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.post(
	"/login", 
	summary="Get a token to use in other endpoints", 
	description="You can use this token for the endpoints. If given user has 2FA enabled, they must provide the 2FA code along with their credentials through either `Gaijin pass` or the `/v1/answer-2fa` endpoint. If you generated a token that hasn't expired yet, the endpoint will just give back the cached token.",
	responses={
		status.HTTP_200_OK: {"model": Login.LoginResponse},
		status.HTTP_401_UNAUTHORIZED: {"model": Login.Fail2FAResponse, "description": "Unauthorized. Account has 2FA enabled, and needs to go through the 2FA process."},
		status.HTTP_408_REQUEST_TIMEOUT: {"description": "Account has Two Factor Authentication, and authentication timed out"},
		status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Rate limit exceeded. Please wait a bit before trying again."},
	}
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def login_post(
	request: Request,
	email: Annotated[EmailStr, Form()],
	password: Annotated[str, Form(min_length=6, max_length=64, json_schema_extra={"format": "password"})]
):
	token = await users_cache.login(email, password)

	return JSONResponse({
		"status": "OK",
		"token": token
	}, status_code=status.HTTP_200_OK)

@router.post(
	"/refresh-token", 
	summary="Refresh your token so it stays alive for longer. This is essentially a 'No op', just to keep the token active.",
	description="If you are cached it will refresh the token. The game generally refreshes the token every 30 minutes. Returns an UNIX timestamp of the new token expiry",
	responses={
		status.HTTP_200_OK: {"model": LoginToken.LoginTokenResponse, "description": "Token refreshed successfully"},
		status.HTTP_404_NOT_FOUND: {"model": LoginToken.LoginFailResponse, "description": "Invalid token provided. The token is either expired or invalid."},
		status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Rate limit exceeded. Please wait a bit before trying again."}
	}
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def login_token(
	request: Request, 
	user: TokenBearer
):
	await user.refresh()
	return {
		"expires": dtToTimestamp(user.jwt_expires),
		"status": "OK"
	}

@router.post(
	"/answer-2fa",
	summary="Provide 2FA code to finish login in case of a 2FA account without gaijin pass"
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def answer_2fa(
	request: Request,
	email: Annotated[EmailStr, Form(title="The email address for the account")],
	password: Annotated[str, Form(title="The password of the account, used as a sort of protection")],
	code: Annotated[int, Form(title="The 2FA code")]
):
	if email not in users_cache._pending_2fa:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not pending 2FA verification. Please try to log in first.")
	if users_cache._pending_2fa[email].password_hash == md5(password.encode()).hexdigest():
		users_cache._pending_2fa[email].code = code
	else:
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid password")
	... # TODO: Implement. Due to the nature of the 2FA system, it is hard to implement

@router.post(
	"/get-sid",
	summary="Gets an 'identifier_sid' value, used for replay searching. Value is not displayed, but will be used in the requests that require it. Has to be refreshed every 14 days",
	responses={
		status.HTTP_200_OK: {},
		status.HTTP_400_BAD_REQUEST: {"description": "Generic fetch failure"},
		status.HTTP_404_NOT_FOUND: {"description": "User not found in database"}
	}
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def get_sid(
	request: Request,
	user: TokenBearer,
	password: Annotated[str, Form(min_length=6, max_length=64, json_schema_extra={"format": "password"}, description="Must be given, as we do not store passwords")]
):
	await users_cache.get_sid(user, password)
	if user.sid == None:
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not obtain sid value")
	return JSONResponse({"status": "success"}, status.HTTP_200_OK)

@router.delete(
	"/remove",
	summary="Removes your login entry from our system"
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def remove_login(
	request: Request,
	user: TokenBearer
):
	if (await users_cache.remove_entry(user)):
		return JSONResponse({"success": True})
	raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "An error occurred during login deletion")
