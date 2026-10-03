from json import load as _load
from pathlib import Path
from copy import deepcopy

__root = Path(__file__).parent

# Auto-discovered template names for autocomplete.
# If your IDE doesn't resolve these, run `python -m templates` to print
# a Literal[...] you can paste into the `action` parameter annotation.
_tpls = sorted(p.stem for p in __root.glob("*.json") if not p.stem.startswith("_"))
TEMPLATES: list[str] = _tpls

_cache: dict[str, dict] = {}

def load(action: str) -> dict:
	if action in _cache:
		return deepcopy(_cache[action])
	path = __root / f"{action}.json"
	if not path.is_file():
		raise FileNotFoundError(f"Unknown template '{action}'. Available: {TEMPLATES}")
	with open(path) as f:
		data = _load(f)
	_cache[action] = data
	return deepcopy(data)

def reload() -> None:
	_cache.clear()

if __name__ == "__main__":
	print("Available:", TEMPLATES)
	if TEMPLATES:
		print(f"\nLiteral for action parameter:\n    Literal[{', '.join(repr(t) for t in TEMPLATES)}]")
