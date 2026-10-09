#!/usr/bin/env python3
"""Validate the repository-owned Graduate Pathfinder Skill structure."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_PATHS = (
    ("references", "directory"),
    ("scripts", "directory"),
    ("tests", "directory"),
    ("agents/openai.yaml", "file"),
)


def parse_frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, [f"SKILL.md unreadable: {exc}"]
    if not lines or lines[0].strip() != "---":
        return {}, ["frontmatter must begin with --- on the first line"]
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, ["frontmatter closing --- is missing"]

    values: dict[str, str] = {}
    body = lines[1:end]
    for index, line in enumerate(body):
        if not line.strip() or line[:1].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if value in {"|", "|-", "|+", ">", ">-", ">+"}:
            continuation: list[str] = []
            for nested in body[index + 1 :]:
                if nested.strip() and not nested[:1].isspace():
                    break
                if nested.strip():
                    continuation.append(nested.strip())
            value = " ".join(continuation)
        if key in values:
            errors.append(f"frontmatter field is duplicated: {key}")
        else:
            values[key] = value
    return values, errors


def check_skill_structure(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        repository = root.resolve(strict=True)
    except OSError as exc:
        return [f"repository root unavailable: {exc}"]
    if not repository.is_dir():
        return [f"repository root is not a directory: {repository}"]

    skill_file = repository / "SKILL.md"
    if not skill_file.is_file():
        errors.append("required path missing: SKILL.md")
    else:
        values, frontmatter_errors = parse_frontmatter(skill_file)
        errors.extend(frontmatter_errors)
        name = values.get("name", "")
        description = values.get("description", "")
        if not name:
            errors.append("frontmatter name must be nonempty")
        elif name != "graduate-pathfinder":
            errors.append("frontmatter name must be graduate-pathfinder")
        if not description:
            errors.append("frontmatter description must be nonempty")

    for relative, kind in REQUIRED_PATHS:
        path = repository / relative
        valid = path.is_dir() if kind == "directory" else path.is_file()
        if not valid:
            errors.append(f"required path missing: {relative}")

    for path in repository.rglob("*"):
        if not path.is_symlink():
            continue
        relative = path.relative_to(repository).as_posix()
        if not path.exists():
            errors.append(f"broken symlink: {relative}")
            continue
        target = path.resolve()
        if not target.is_relative_to(repository):
            errors.append(f"symlink escapes repository: {relative}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("usage: check_skill_structure.py [repository-root]", file=sys.stderr)
        return 2
    root = Path(argv[1]) if len(argv) == 2 else Path.cwd()
    errors = check_skill_structure(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Skill structure check passed: frontmatter, required paths and symlink boundaries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
