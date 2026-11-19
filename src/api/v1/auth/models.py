from typing import Literal

from pydantic import BaseModel, Field


class Login: # /v1/login endpoint
	class LoginResponse(BaseModel):
		status: Literal["OK"] = "OK"
		token: str
		user_id: int
class LoginToken: # /v1/login-token endpoint
	class LoginTokenResponse(BaseModel):
		expires: int = Field(description = "UNIX timestamp of the new token expiry")
		status: Literal["OK"] = "OK"
	class LoginFailResponse(BaseModel):
		status: Literal["FAIL"] = "FAIL"
		detail: str
