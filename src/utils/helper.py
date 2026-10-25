from inspect import isawaitable
from datetime import datetime
from fastapi import HTTPException
from typing import Any, Callable, Coroutine
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
		keys: tuple[str, ...]

		def __init__(self, *keys: str):
			self.keys = tuple(keys)

		async def run(self, obj: dict[str, Any]):
			for key in self.keys:
				obj.pop(key, None)
			return obj

	class KeyAdd:
		key: str
		value: Any | Callable[[dict[str, Any]], Any]

		def __init__(self, key: str, value: Any | Callable[[dict[str, Any]], Any], /):
			self.key = key
			self.value = value

		def _resolve(self) -> Any:
			return self.value() if callable(self.value) else self.value

		async def run(self, obj: dict[str, Any]):
			if self.key in obj:
				raise KeyError(f"Key '{self.key}' already in object")

			obj[self.key] = dictUtil._await_maybe(self.value)
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

		async def run(self, obj: dict[str, Any]):
			if self.key not in obj:
				if self.default is not ...:
					obj[self.new_name] = self.convert(self.default)
				return obj

			new_val = self.convert(obj.pop(self.key))

			obj[self.new_name] = new_val
			return obj

	@staticmethod
	async def run_all(obj: dict[str, Any], changes:Iterable[KeyMod|KeyRem|KeyAdd|None]):
		for change in changes:
			if change is None:
				continue
			tmp = await change.run(obj)

		return obj

	@staticmethod
	async def _await_maybe(value):
		if isawaitable(value):
			return await value
		return value
