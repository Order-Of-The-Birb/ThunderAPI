from datetime import datetime
from fastapi import HTTPException
from typing import Any, Callable

def dtToTimestamp(dt:datetime) -> int:
	return int(dt.timestamp())
def dtToTimestampMs(dt:datetime) -> int:
	return int(dt.timestamp()*1000)

class AuthenticationError(HTTPException):
	def __init__(self, status_code, detail = None, headers = None):
		super().__init__(status_code, detail, headers)

class Keymod:
	key: str
	new_name: str
	convert: Callable[[Any], Any]
	default: Any
	rm: bool 

	def __init__(self, key: str, /, *, new_name: str = None, convert: Callable[[Any], Any] = lambda x: x, default: Any = ..., rm: bool = False):
		self.key = key
		if new_name:
			self.new_name = new_name
		else:
			self.new_name = key
		self.convert = convert
		self.rm = rm
		if not self.rm:
			self.default = default
		else:
			self.default = None

	def run(self, obj:dict[str, Any]) -> dict[str, Any]:
		if self.key not in obj:
			if self.default is not ... and not self.rm:
				obj[self.new_name] = self.convert(self.default)
			return obj
		new_val = self.convert(obj.pop(self.key, self.default))
		if not self.rm:
			obj[self.new_name] = new_val
		return obj