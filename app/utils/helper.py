from datetime import datetime
from fastapi import HTTPException
from typing import Any, Callable
from dataclasses import dataclass

def dtToTimestamp(dt:datetime) -> int:
	return int(dt.timestamp())
def dtToTimestampMs(dt:datetime) -> int:
	return int(dt.timestamp()*1000)

class AuthenticationError(HTTPException):
	def __init__(self, status_code, detail = None, headers = None):
		super().__init__(status_code, detail, headers)

@dataclass
class KeyRename:
	_from: str
	_to: str
	convert: Callable[[Any]] = lambda x: x
	default: Any = ...

	def rename(self, obj:dict[str, Any]) -> dict[str, Any]:
		obj[self._to] = self.convert(obj.pop(self._from, self.default))
		return obj