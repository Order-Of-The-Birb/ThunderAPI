from typing import Literal
from pydantic import BaseModel

class SuccessEmptyDict(BaseModel):
	status:Literal["success"] = "success"
class GenericEmptyResponse(BaseModel):
	"""Basic `{"success":true}` response"""
	success: bool
