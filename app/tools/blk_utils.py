import struct
from asyncio import to_thread
from logging import getLogger
from os import getenv
from shutil import which
from pathlib import Path
from enum import IntEnum
from sys import platform
from subprocess import run as run_process
from json import loads
from lz4.block import compress as lz4compress, decompress as lz4decompress
from bz2 import compress as bzcompress, decompress as bzdecompress

_logger = getLogger(__name__)

def _find_wtextcli() -> Path:
	"""Locate the wt_ext_cli executable."""
	explicit_path = getenv("WT_EXT_CLI_PATH")
	if explicit_path:
		try:
			p = Path(explicit_path)
			if p.is_file():
				return p
		except FileNotFoundError:
			system_ext = which(explicit_path)
			if system_ext:
				try:
					return Path(system_ext)
				except FileNotFoundError:
					raise LookupError(f"wt_ext_cli not found at: {explicit_path}")

	# Check tools/ directory next to this script
	script_dir = Path(__file__).resolve().parent
	if platform == "win32":
		local = script_dir / 'wt_ext_cli.exe'
	else:
		local = script_dir / 'wt_ext_cli'

	if local.is_file():
		return local

	# Check PATH
	system_bin = which('wt_ext_cli')
	if system_bin:
		return Path(system_bin)

	raise LookupError(
		'Missing dependency: Install wt_ext_cli from '
		'https://github.com/Warthunder-Open-Source-Foundation/wt_ext_cli/releases'
	)
def _find_binblk() -> Path:
	"""Locate the binBlk executable."""
	explicit_path = getenv("BINBLK_PATH")
	if explicit_path:
		p = Path(explicit_path)
		if p.is_file():
			return p
		raise LookupError(f'binBlk not found at: {explicit_path}')

	# Check tools/ directory next to this script
	script_dir = Path(__file__).resolve().parent
	if platform == "win32":
		local = script_dir / 'binBlk.exe'
	else:
		local = script_dir / 'binBlk'

	if local.is_file():
		return local

	# Check PATH
	system_bin = which('binBlk')
	if system_bin:
		return Path(system_bin)

	raise LookupError(
		'Missing dependency: Install binBlk from\n'
		'https://github.com/GaijinEntertainment/DagorEngine/releases/latest'
	)

wt_ext_cli: Path = _find_wtextcli()
binBlk: Path = _find_binblk()

class Decompress(dict):
	def __init__(self, data: bytes):
		decompressed = None
		if b'BZh' in data[:20]:
			decompressed = self.bzip_decompress_try(data)
		if decompressed is None:
			decompressed = self.lz4_decompress_try(data)

		payload = decompressed or data
		unpacked = run_process(
			[str(wt_ext_cli), 'unpack_raw_blk', '--stdin', '--stdout', '--format', 'Json'],
			input=payload, 
			capture_output=True,
			timeout=60
		)
		super().__init__(loads(unpacked.stdout))
	@classmethod
	async def async_init(cls, data:bytes):
		return await to_thread(cls, data)

	@staticmethod
	def lz4_decompress_try(data) -> None|bytes:
		if len(data) < 4:
			return None

		candidates = []

		# Standard lz4 frame with 0x4C marker byte
		if data[:1] == b'\x4c':
			if len(data) < 5:
				return None
			candidates.append(("marker+size", struct.unpack('>I', data[1:5])[0], data[5:]))

		# Game wire format: [4-byte BE uncompressed size][raw lz4hc block]
		if not candidates:
			be_size = struct.unpack('>I', data[:4])[0]
			# Sanity check: decompressed size should be between 100 and 100MB
			if 100 <= be_size <= 100 * 1024 * 1024 and len(data) > 4:
				candidates.append(("be-size prefix", be_size, data[4:]))

		for label, uncompressed_size, compressed_payload in candidates:
			try:
				_logger.debug(f"Trying LZ4 {label}; potential uncompressed size: {uncompressed_size}")
				return lz4decompress(compressed_payload, uncompressed_size=uncompressed_size)
			except Exception as e:
				_logger.debug(f"LZ4 {label} decompression failed: {e}")

		return None

	@staticmethod
	def bzip_decompress_try(data) -> None|bytes:
		offset = data[:20].find(b'BZh')
		if offset == -1:
			offset = 0

		try:
			return bzdecompress(data[offset:])
		except Exception as e:
			raise ValueError(f"BZip2 decompression failed: {e}")

	def as_dict(self):
		return dict(self)

class Compress(bytes):
	class Algorithm(IntEnum):
		NONE = 0
		LZ4 = 1
		BZIP = 2

		@staticmethod
		def from_str(text: str|None) -> Compress.Algorithm:
			if text is None:
				return Compress.Algorithm.NONE
			match text.strip().lower():
				case "lz4hc":
					return Compress.Algorithm.LZ4
				case "bzip":
					return Compress.Algorithm.BZIP
				case _:
					raise NotImplementedError(f"Compression algorithm '{text}' is not implemented")
	def __new__(cls, data: dict, algo: Algorithm|str|None = Algorithm.NONE):
		if isinstance(algo, str):
			algo = cls.Algorithm.from_str(algo)
		elif algo is None:
			algo = cls.Algorithm.NONE
		return bytes.__new__(cls, cls.convert(data, algo))

	@classmethod
	async def async_init(cls, data:dict, algo: Algorithm|str|None = Algorithm.NONE):
		return await to_thread(cls, data, algo)

	def as_bytes(self):
		return bytes(self)

	@staticmethod
	def convert(data: dict, algo: Algorithm):
		"""Converts a JSON-compatible dict to a BLK (Optionally compressed)"""
		lines = []

		for key, value in data.items():
			if value is None:
				continue

			if isinstance(value, bool):
				lines.append(f'{key}:b = {str(value).lower()}')
			elif isinstance(value, int):
				lines.append(f'{key}:i = {value}')
			elif isinstance(value, float):
				# Format float to avoid scientific notation for whole numbers
				if value == int(value) and abs(value) < 1e15:
					lines.append(f'{key}:i = {int(value)}')
				else:
					lines.append(f'{key}:r = {value}')
			elif isinstance(value, str):
				escaped = value.replace('\\', '\\\\').replace('"', '\\"')
				lines.append(f'{key}:t = "{escaped}"')
			elif isinstance(value, list):
				# Serialize list as comma-separated string in quotes
				items = []
				for item in value:
					if isinstance(item, str):
						items.append(item.replace('\\', '\\\\').replace('"', '\\"'))
					else:
						items.append(str(item))
				joined = ', '.join(items)
				lines.append(f'{key}:t = "{joined}"')
			else:
				_logger.warning(f'Skipping key "{key}" with unsupported type {type(value).__name__}')

		blkx_text = ('\n'.join(lines) + '\n').encode("utf-8")

		result = run_process(
			[str(binBlk), '-', '-', '-b'],
			input=blkx_text,
			capture_output=True,
			timeout=60
		)
		if result.returncode != 0:
			stderr_msg = result.stderr.decode('utf-8', errors='replace').strip()
			raise RuntimeError(f'binBlk failed: {stderr_msg}')

		if algo == Compress.Algorithm.LZ4:
			compressed = lz4compress(result.stdout, mode='high_compression', store_size=False)
			return struct.pack('>I', len(result.stdout)) + compressed
		elif algo == Compress.Algorithm.BZIP:
			return bzcompress(result.stdout)
		elif algo == Compress.Algorithm.NONE or algo is None:
			return result.stdout
		else:
			raise NotImplementedError(f"No such algorithm supported: {algo}")
