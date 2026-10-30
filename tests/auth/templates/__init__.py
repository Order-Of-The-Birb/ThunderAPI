from json import load as _load, loads as _loads
from pathlib import Path
from enum import Enum
from fastapi import HTTPException, status

__ROOT = Path(__file__).parent

# Auto-discovered template names for autocomplete.
# If your IDE doesn't resolve these, run `python -m templates` to print
# a Literal[...] you can paste into the `action` parameter annotation.
_tpls = sorted(p.stem for p in __ROOT.glob("**/*.json") if not p.stem.startswith("_"))
TEMPLATES: list[str] = _tpls
del _tpls

class _Group(Enum):
	"""Base for template groups. Each member points to a template file or a subdirectory of states."""
	__GROUP__: str

class Groups:
	class LOGIN(_Group):
		__GROUP__ = "login"
		FAILURE = ("failure1.json", HTTPException(status.HTTP_400_BAD_REQUEST))
		SUCCESS = ("success.json", None)
		TWO_FACTOR = ("2factor", HTTPException(status.HTTP_206_PARTIAL_CONTENT))


def load(file: _Group) -> dict[str, dict]:
	group_path = __ROOT / file.__GROUP__
	if not group_path.is_dir():
		raise FileNotFoundError(f"Unknown group '{file.__GROUP__}'")

	target: Path = group_path / file.value[0]

	if target.is_dir():
		states = {}
		for f in target.glob("*.*"):
			text = f.read_text()
			if text.strip():
				states[f.stem] = _loads(text)
		return states

	if not target.is_file():
		raise FileNotFoundError(f"Unknown file '{file.value[0]}' in group '{file.__GROUP__}'")

	with open(target) as f:
		return {"init": _load(f)}

if __name__ == "__main__":
	print("Available files:", TEMPLATES)
