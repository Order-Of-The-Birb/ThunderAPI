from typing import Literal

from pydantic import BaseModel

class GenericEmptyResponse(BaseModel):
	"""Basic `{"success":true}` response"""
	success: bool
