"""Inventory user-selected materials in place; hashes do not certify authenticity.

format_class uses only the extension. Semantic document_class stays unknown
until a separate review, and this tool does not extract or copy document content.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path

if __package__:
    from .case_io import atomic_write_json
else:
    from case_io import atomic_write_json

SKILL_ROOT = Path(__file__).resolve().parents[1]
FORMAT_CLASSES = {
    ".pdf": "pdf", ".docx": "docx", ".xlsx": "xlsx",
    **dict.fromkeys((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"), "image"),
    **dict.fromkeys((".txt", ".md", ".csv", ".json", ".yaml", ".yml"), "text"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(paths: list[Path], case_root: Path) -> list[dict]:
    root = Path(case_root).resolve()
    if root.is_relative_to(SKILL_ROOT):
        raise ValueError("case directory must be outside the skill root")
    records = []
    for path in paths:
        source = Path(path).resolve(strict=True)
        if source == (root / "materials-manifest.json").resolve():
            raise ValueError("manifest output must not overwrite a selected source material")
        if not source.is_file():
            raise ValueError(f"material must be a file: {source}")
        stat = source.stat()
        digest = sha256_file(source)
        extension = source.suffix.lower()
        records.append({
            "document_id": f"sha256:{digest}",
            "source_path": str(source),
            "sha256": digest,
            "size_bytes": stat.st_size,
            "extension": extension,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "format_class": FORMAT_CLASSES.get(extension, "unknown"),
            "document_class": "unknown",
            "extraction_state": "not_started",
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, action="append", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        records = build_manifest(args.file, args.case_root)
        root = args.case_root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(root / "materials-manifest.json", records)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Inventoried {len(records)} material(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
