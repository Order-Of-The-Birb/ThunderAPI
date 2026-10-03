from datetime import datetime
from fastapi import HTTPException

def dtToTimestamp(dt:datetime) -> int:
	return int(dt.timestamp())
def dtToTimestampMs(dt:datetime) -> int:
	return int(dt.timestamp()*1000)

class AuthenticationError(HTTPException):
	def __init__(self, status_code, detail = None, headers = None):
		super().__init__(status_code, detail, headers)
