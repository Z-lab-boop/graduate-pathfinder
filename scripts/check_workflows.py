#!/usr/bin/env python3
"""Check the repository's narrow CI and Pages workflow contract."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


CI_COMMANDS = (
    "python3 -m unittest discover -s tests -v",
    "python3 -m compileall -q scripts tests",
    "python3 scripts/check_skill_structure.py .",
    "npm --prefix web ci",
    "npx --prefix web playwright install chromium",
    "npm --prefix web run typecheck",
    "npm --prefix web run test:site",
    "node scripts/check-site-assets.mjs",
    "git diff --check",
)


def section(text: str, key: str) -> str:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line == f"{key}:"), None)
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index] and not lines[index][0].isspace():
            end = index
            break
    return "\n".join(lines[start + 1 : end])


def literal_shell_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(\s*)run:\s*\|\s*$", lines[index])
        if not match:
            index += 1
            continue
        parent_indent = len(match.group(1))
        index += 1
        captured: list[str] = []
        while index < len(lines):
            line = lines[index]
            indent = len(line) - len(line.lstrip())
            if line.strip() and indent <= parent_indent:
                break
            captured.append(line)
            index += 1
        nonempty = [len(line) - len(line.lstrip()) for line in captured if line.strip()]
        trim = min(nonempty) if nonempty else parent_indent + 2
        blocks.append("\n".join(line[trim:] if line.strip() else "" for line in captured) + "\n")
    return blocks


def shell_errors(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for index, block in enumerate(literal_shell_blocks(text), 1):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".sh") as handle:
            handle.write(block)
            handle.flush()
            result = subprocess.run(["bash", "-n", handle.name], capture_output=True, text=True, check=False)
        if result.returncode:
            detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "bash -n failed"
            errors.append(f"shell syntax ({path.name} block {index}): {detail}")
    return errors


def permission_values(text: str) -> set[str]:
    return {line.strip() for line in section(text, "permissions").splitlines() if line.strip()}


def active_shell_lines(text: str) -> set[str]:
    return {
        line.strip()
        for block in literal_shell_blocks(text)
        for line in block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def check_workflows(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    files = {name: workflow_dir / name for name in ("ci.yml", "pages.yml")}
    texts: dict[str, str] = {}
    for name, path in files.items():
        try:
            texts[name] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"required workflow missing: {name} ({exc})")
    if errors:
        return errors

    ci = texts["ci.yml"]
    pages = texts["pages.yml"]
    ci_shell = active_shell_lines(ci)
    pages_shell = active_shell_lines(pages)
    if permission_values(ci) != {"contents: read"}:
        errors.append("permissions: ordinary CI must grant only contents: read")
    for command in CI_COMMANDS:
        if command not in ci_shell:
            errors.append(f"ordinary CI gate missing: {command}")

    triggers = section(pages, "on")
    trigger_keys = {
        match.group(1)
        for line in triggers.splitlines()
        if (match := re.match(r"^  ([\w-]+):\s*$", line))
    }
    if trigger_keys != {"push", "workflow_dispatch"} or "      - main" not in triggers:
        errors.append("main branch trigger: Pages must use only main push and workflow_dispatch")
    branches = re.findall(r"^\s+-\s+([^\s#]+)\s*$", triggers, re.MULTILINE)
    if branches != ["main"]:
        errors.append("main branch trigger: Pages branch list must be exactly main")
    if permission_values(pages) != {"contents: read", "pages: write", "id-token: write"}:
        errors.append("permissions: Pages must grant contents read, pages write and id-token write only")

    concurrency = section(pages, "concurrency")
    if "  group: pages-${{ github.ref }}" not in concurrency:
        errors.append("ref-scoped concurrency: group must be pages-${{ github.ref }}")
    if "  cancel-in-progress: true" not in concurrency:
        errors.append("ref-scoped concurrency: cancellation must be enabled")
    if "    if: github.ref == 'refs/heads/main'" not in pages:
        errors.append("main guard: build job must require refs/heads/main")
    if not re.search(r"^  deploy:\s*$[\s\S]*?^    needs: build\s*$", pages, re.MULTILINE):
        errors.append("deployment dependency: deploy must need build")

    for command in CI_COMMANDS:
        if command not in pages_shell:
            errors.append(f"Pages build gate missing: {command}")
    for action in ("actions/configure-pages@", "actions/upload-pages-artifact@", "actions/deploy-pages@"):
        if action not in pages:
            errors.append(f"Pages action missing: {action}")

    upload_matches = list(re.finditer(r"^\s*- uses: actions/upload-pages-artifact@[^\n]+$", pages, re.MULTILINE))
    if len(upload_matches) != 1 or not re.search(
        r"- uses: actions/upload-pages-artifact@[^\n]+\n\s+with:\n\s+path: dist/site\s*$",
        pages,
        re.MULTILINE,
    ):
        errors.append("upload path: Pages artifact must be exactly dist/site")
    if upload_matches:
        before_upload = pages[: upload_matches[0].start()]
        previous_step = before_upload.rsplit("\n      - ", 1)[-1]
        if "run: |" not in previous_step or "npm --prefix web run build:site" not in previous_step:
            errors.append("final rebuild: final pre-upload step must rebuild dist/site")
        test_position = before_upload.find("npm --prefix web run test:site")
        build_position = before_upload.rfind("npm --prefix web run build:site")
        if test_position < 0 or build_position < test_position:
            errors.append("final rebuild: clean build must run after site tests")
    if re.search(r"\bCNAME\b|custom[-_ ]?domain", pages, re.IGNORECASE):
        errors.append("custom domain mutation: Pages workflow must not write CNAME or a custom domain")
    if re.search(r"^\s+enablement:\s*true\s*$", pages, re.MULTILINE):
        errors.append("Pages enablement: workflow must not enable Pages implicitly")

    errors.extend(shell_errors(files["ci.yml"], ci))
    errors.extend(shell_errors(files["pages.yml"], pages))
    return errors


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("usage: check_workflows.py [repository-root]", file=sys.stderr)
        return 2
    root = (Path(argv[1]) if len(argv) == 2 else Path.cwd()).resolve()
    errors = check_workflows(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Workflow contract check passed: CI gates, guarded Pages artifact and shell blocks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
