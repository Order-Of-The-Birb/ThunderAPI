from dataclasses import dataclass
from fastapi import status
from fastapi.exceptions import HTTPException
from json import JSONDecodeError
from typing import Any
from tools import Decompress
from enum import IntEnum, Enum, auto

@dataclass
class _ReplayHeader:
	class ReplayStructure(Enum): # Based on the hexpat
		class ByteSizes(IntEnum):
			u32 = 4
			char = 1
			difficulty = 1
			padding = 1
			u64 = 8
		magic = (auto(), ByteSizes.u32 , int) # (index, size, type)
		version = (auto(), ByteSizes.u32, int)
		level = (auto(), ByteSizes.char * 128, str)
		levelSettings = (auto(), ByteSizes.char * 260, str)
		battleType = (auto(), ByteSizes.char * 128, str)
		environment = (auto(), ByteSizes.char * 128, str)
		visibility = (auto(), ByteSizes.char * 32, str)
		rezOffset = (auto(), ByteSizes.u32, int)
		diff = (auto(), ByteSizes.difficulty, '_Difficulty')
		_pad1 = (auto(), ByteSizes.padding * 35, None)
		sessionType = (auto(), ByteSizes.u32, int)
		_pad2 = (auto(), ByteSizes.padding * 4, None)
		sessionIdHex = (auto(), ByteSizes.u64, int)
		_pad3 = (auto(), ByteSizes.padding * 4, None)
		mSetSize = (auto(), ByteSizes.u32, int)
		_pad4 = (auto(), ByteSizes.padding * 32, None)
		locName = (auto(), ByteSizes.char * 128, str)
		startTime = (auto(), ByteSizes.u32, int)
		timeLimit = (auto(), ByteSizes.u32, int)
		scoreLimit = (auto(), ByteSizes.u32, int)
		_pad5 = (auto(), ByteSizes.padding * 48, None)
		battleClass = (auto(), ByteSizes.char * 128, str)
		battleKillStreak = (auto(), ByteSizes.char * 128, str)

	class _Difficulty:
		unk_nib: int # 4 bits
		difficulty: int # 4 bits
		def __init__(self, byte:int):
			self.unk_nib = byte >> 4
			self.difficulty = byte & 0x0F
	#region header fields
	magic: int
	version: int
	level: str
	levelSettings: str
	battleType: str
	environment: str
	visibility: str
	rezOffset: int 
	diff: _Difficulty
	sessionType: int
	sessionIdHex: int
	mSetSize: int
	locName: str
	startTime: int
	timeLimit: int
	scoreLimit: int
	battleClass: str
	battleKillStreak: str
	#endregion
	def __init__(self, data:bytes):
		fields = sorted(self.ReplayStructure, key=lambda f: f.value[0]) # Sort by index
		offset = 0
		for field in fields:
			index, size, field_type = field.value

			if field_type == '_Difficulty':
				value = self._Difficulty(data[offset])
			elif field_type == str:
				value = data[offset:offset+size].split(b'\x00')[0].decode('ascii')
			elif field_type == int:
				value = int.from_bytes(data[offset:offset+size.value], 'little')
			elif field_type is None: # Padding
				offset += size
				continue

			setattr(self, field.name, value)
			offset += size

class ReplayParser:
	header: _ReplayHeader
	body: dict[str, Any]
	@classmethod
	async def from_replay(cls, replay:bytes):
		self = cls()

		self.header = _ReplayHeader(replay)
		try:
			self.body = (await Decompress.async_init(replay[self.header.rezOffset:])).as_dict()
		except RuntimeError:
			self.body = {}
		except JSONDecodeError:
			raise HTTPException(status.HTTP_425_TOO_EARLY, "Replay hasn't ended yet, or is not parseable for some reason")
		return self

