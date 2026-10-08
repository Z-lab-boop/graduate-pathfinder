"""UTF-8 JSON reads and atomic writes for local case artifacts."""
import json
import os
import tempfile
from pathlib import Path


def load_json(path: Path) -> dict:
    """Read JSON; callers validate the object or array shape they require."""
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


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
