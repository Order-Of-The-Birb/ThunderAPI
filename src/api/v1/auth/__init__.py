from os import getenv

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from typing_extensions import Annotated

from api.shared import limiter
from api.v1.models import GenericEmptyResponse
from api.v1.shared import TokenBearer
from utils import users_auth
from utils.helper import dtToTimestamp

from .models import Login, LoginToken

router = APIRouter(
	tags = ["authentication"],
	responses = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.post(
	"/login",
	summary = "Get a token to use in other endpoints",
	description = "You can use this token for the endpoints. If given user has 2FA enabled, they must provide the 2FA code along with their credentials through either `Gaijin pass` or the `/v1/answer-2fa` endpoint. If you generated a token that hasn't expired yet, the endpoint will just overwrite the previous token.",
	responses = {
		status.HTTP_200_OK: {"model": Login.LoginResponse},
		status.HTTP_206_PARTIAL_CONTENT: {"description": "The account has 2FA enabled. Go through the 2FA process to log in."},
		status.HTTP_408_REQUEST_TIMEOUT: {"description": "Account has Two Factor Authentication, and authentication timed out"},
		status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Rate limit exceeded. Please wait a bit before trying again."},
	},
	response_model=Login.LoginResponse
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def login_post(
	request: Request,
	email: Annotated[EmailStr, Form()],
	password: Annotated[str, Form(min_length = 6, max_length = 64, json_schema_extra = {"format": "password"})]
):
	token, uidHint = await users_auth.login(email, password)

	return Login.LoginResponse(token = token, user_id = uidHint)

@router.post(
	"/refresh-token",
	summary = "Refresh your token so it stays alive for longer. This is essentially a 'No op', just to keep the token active.",
	description = "If you are cached it will refresh the token. The game generally refreshes the token every 30 minutes. Returns an UNIX timestamp of the new token expiry",
	responses = {
		status.HTTP_200_OK: {"model": LoginToken.LoginTokenResponse, "description": "Token refreshed successfully"},
		status.HTTP_401_UNAUTHORIZED: {"model": LoginToken.LoginFailResponse, "description": "Invalid token provided. The token is either expired or invalid."},
		status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Rate limit exceeded. Please wait a bit before trying again."}
	},
	response_model=LoginToken.LoginTokenResponse
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def login_token(
	request: Request,
	user: TokenBearer
):
	await user.entry.refresh()
	return {
		"expires": dtToTimestamp(user.entry.expires),
		"status": "OK"
	}

@router.post(
	"/answer-2fa",
	summary = "Provide 2FA code to finish login in case of a 2FA account without Gaijin Pass",
	responses={
		status.HTTP_200_OK: {"model": Login.LoginResponse, "description": "Successful 2FA Authentication"}
	},
	response_model=Login.LoginResponse
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def answer_2fa(
	request: Request,
	email: Annotated[EmailStr, Form(title = "The email address for the account")],
	password: Annotated[str, Form(title = "The password of the account, used as a sort of protection")],
	code: Annotated[str, Form(title = "The 2FA code")]
):
	token, uidHint = await users_auth.login(email, password, code = code)
	return Login.LoginResponse(token = token, user_id = uidHint)

@router.delete(
	"/remove",
	summary = "Removes your login entry from our system",
	response_model=GenericEmptyResponse
)
@limiter.limit(getenv("LOGIN_RATE_LIMIT", "5/minute"))
async def remove_login(
	request: Request,
	user: TokenBearer
):
	if (await users_auth.remove_entry(user.entry)):
		return JSONResponse({"success": True})
	raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "An error occurred during login deletion")
