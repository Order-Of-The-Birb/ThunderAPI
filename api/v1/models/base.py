from typing import Literal
from pydantic import BaseModel

class SuccessEmptyDict(BaseModel):
	status:Literal["success"] = "success"
class GenericEmptyResponse(BaseModel):
	success: bool