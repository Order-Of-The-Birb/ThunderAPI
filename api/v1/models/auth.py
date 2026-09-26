from typing import Literal
from pydantic import Field, BaseModel

class Login: # /v1/login endpoint
	class LoginResponse(BaseModel):
		status: Literal["OK"] = "OK"
		token: str
	class Fail2FAResponse(BaseModel):
		types: set[Literal["GaijinPass", "Email", "WTR"]] = Field(description="The types of 2FA that the account has enabled.")
		status: Literal["2STEP"] = "2STEP"
		requestId: str = Field(description="The requestId to be used in the 2FA process")
		userId: int = Field(description="The userId of the account")
class LoginToken: # /v1/login-token endpoint
	class LoginTokenResponse(BaseModel):
		expires: int = Field(description="UNIX timestamp of the new token expiry")
		status: Literal["OK"] = "OK"
	class LoginFailResponse(BaseModel):
		status: Literal["FAIL"] = "FAIL"
		detail: str