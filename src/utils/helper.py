from datetime import datetime
from fastapi import HTTPException
from typing import Any, Callable
from collections.abc import Iterable

def dtToTimestamp(dt:datetime) -> int:
	return int(dt.timestamp())
def dtToTimestampMs(dt:datetime) -> int:
	return int(dt.timestamp()*1000)

class AuthenticationError(HTTPException):
	def __init__(self, status_code, detail = None, headers = None):
		super().__init__(status_code, detail, headers)

class dictUtil:
	class KeyRem:
		key: str

		def __init__(self, key: str, /):
			self.key = key

		def run(self, obj: dict[str, Any]):
			obj.pop(self.key, None)
			return obj

	class KeyAdd:
		key: str
		value: Any

		def __init__(self, key: str, value: Any, /):
			self.key = key
			self.value = value

		def run(self, obj: dict[str, Any]):
			if self.key in obj:
				raise KeyError(f"Key '{self.key}' already in object")
			obj[self.key] = self.value
			return obj

	class KeyMod:
		key: str
		new_name: str
		convert: Callable[[Any], Any]
		default: Any

		def __init__(self, key: str, /, *, new_name: str = None, convert: Callable[[Any], Any] = lambda x: x, default: Any = ...):
			self.key = key
			if new_name:
				self.new_name = new_name
			else:
				self.new_name = key
			self.convert = convert
			self.default = default

		def run(self, obj: dict[str, Any]):
			if self.key not in obj:
				if self.default is not ...:
					obj[self.new_name] = self.convert(self.default)
				return obj

			new_val = self.convert(obj.pop(self.key))

			obj[self.new_name] = new_val
			return obj

	@staticmethod
	def run_all(obj: dict[str, Any], changes:Iterable[KeyMod|KeyRem|KeyAdd]):
		for change in changes:
			obj = change.run(obj)
		return obj
