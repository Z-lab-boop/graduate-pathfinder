"""UTF-8 JSON reads and atomic writes for local case artifacts."""
import json
import math
import os
import tempfile
from pathlib import Path


def load_json(path: Path) -> dict:
    """Read finite JSON; callers validate the object or array shape they require."""
    path = Path(path)
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    # Python's decoder accepts NaN/Infinity and overflows numbers such as 1e400.
    # Inspect the decoded tree before returning it so errors retain field paths.
    def check_finite(value, location):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{path}: {location}: number must be finite")
        if isinstance(value, dict):
            for key, item in value.items():
                check_finite(item, f"{location}[{json.dumps(key, ensure_ascii=False)}]")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                check_finite(item, f"{location}[{index}]")

    check_finite(payload, "$")
    return payload


def atomic_write_json(path: Path, payload: dict) -> None:
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
