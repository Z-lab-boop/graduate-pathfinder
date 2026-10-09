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
    "python3 scripts/check_workflows.py .",
    "npm --prefix web ci",
    "npx --prefix web playwright install chromium",
    "npm --prefix web run typecheck",
    "npm --prefix web run test:site",
    "node scripts/check-site-assets.mjs",
    "git diff --check",
)
FINAL_BUILD_COMMANDS = ("npm --prefix web run build:site",)


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


def literal_shell_entries(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    blocks: list[tuple[int, str]] = []
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
        block = "\n".join(line[trim:] if line.strip() else "" for line in captured) + "\n"
        blocks.append((parent_indent, block))
    return blocks


def literal_shell_blocks(text: str) -> list[str]:
    return [block for _, block in literal_shell_entries(text)]


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


def job_section(text: str, job: str) -> str:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line == f"  {job}:"), None)
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if re.match(r"^  [\w-]+:\s*$", lines[index]):
            end = index
            break
        if lines[index] and not lines[index][0].isspace():
            end = index
            break
    return "\n".join(lines[start + 1 : end])


def step_blocks(job: str) -> list[str]:
    lines = job.splitlines()
    starts = [index for index, line in enumerate(lines) if re.match(r"^      -\s+", line)]
    return ["\n".join(lines[start : starts[position + 1] if position + 1 < len(starts) else len(lines)])
            for position, start in enumerate(starts)]


def has_execution_override(text: str, *, job: bool = False) -> bool:
    # Structural validation rejects quoted/escaped/explicit keys before these
    # contracts run. Match every supported plain spelling, including a step's
    # first field and YAML spaces/tabs before the mapping colon.
    prefix = r"    " if job else r"(?:        |      -[ \t]+)"
    return bool(re.search(rf"^{prefix}(?:if|continue-on-error)[ \t]*:", text, re.MULTILINE))


def action_step_indexes(job: str, action: str) -> list[int]:
    pattern = re.compile(rf"^(?:      - uses|        uses): {re.escape(action)}@[^\s#]+\s*$", re.MULTILINE)
    return [
        index for index, step in enumerate(step_blocks(job))
        if pattern.search(step) and not has_execution_override(step)
    ]


def exact_run_step_indexes(job: str, commands: tuple[str, ...]) -> list[int]:
    indexes: list[int] = []
    for index, step in enumerate(step_blocks(job)):
        entries = [(indent, block) for indent, block in literal_shell_entries(step) if indent == 8]
        if len(entries) != 1:
            continue
        lines = tuple(line.strip() for line in entries[0][1].splitlines() if line.strip())
        if lines == commands and not has_execution_override(step):
            indexes.append(index)
    return indexes


def workflow_syntax_errors(text: str) -> list[str]:
    """Enforce the supported YAML subset before using text-based contracts.

    Only canonical step run blocks may contain opaque text. Anchors, aliases,
    tags, explicit/quoted keys and other block scalars are unsupported, even in
    quoted scalar values. This deliberately trades YAML flexibility for a small
    auditable grammar; it is not a general YAML parser.
    """
    errors: list[str] = []
    parents: list[tuple[int, str]] = []
    in_shell = False
    first_shell_line = False
    for line in text.splitlines():
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if "\t" in line[:indent]:
            errors.append("workflow indentation: use spaces only")
        if in_shell:
            if not stripped:
                continue
            if indent > 8:
                if indent < 10 or (first_shell_line and indent != 10):
                    errors.append("shell block indentation: first content must use ten spaces; later content must use at least ten")
                first_shell_line = False
                continue
            in_shell = False
        if not stripped or stripped.startswith("#"):
            continue
        while parents and parents[-1][0] >= indent:
            parents.pop()
        candidate = stripped[2:].lstrip() if stripped.startswith("- ") else stripped
        if candidate.startswith(('"', "'")) or re.match(r"\?(?:\s|$)", candidate):
            errors.append("quoted or escaped structural key: workflow keys must use plain ASCII spelling")
        if re.search(r"[&*]", stripped):
            errors.append("YAML anchors or aliases: unsupported in workflow structure")
        if "|" in stripped or ">" in stripped:
            canonical_run = (
                line == "        run: |"
                and len(parents) == 4
                and parents[0] == (0, "jobs:")
                and parents[1][0] == 2
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*:", parents[1][1])
                and parents[2] == (4, "steps:")
                and parents[3][0] == 6
                and parents[3][1].startswith("- ")
            )
            if canonical_run:
                in_shell = True
                first_shell_line = True
            else:
                errors.append("unsupported block scalar: only canonical step run: | fields are supported")
        if "!" in stripped:
            errors.append("YAML tags: unsupported in workflow structure")
        parents.append((indent, stripped))
    return list(dict.fromkeys(errors))


def has_job_level_permissions(text: str) -> bool:
    return bool(re.search(
        r'''^[ \t]+(?:permissions|"permissions"|'permissions')[ \t]*:''',
        text,
        re.MULTILINE,
    ))


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
    errors.extend(workflow_syntax_errors(ci))
    errors.extend(workflow_syntax_errors(pages))
    if permission_values(ci) != {"contents: read"}:
        errors.append("permissions: ordinary CI must grant only contents: read")
    if has_job_level_permissions(ci):
        errors.append("job-level permissions: ordinary CI must not override top-level permissions")
    ci_job = job_section(ci, "verify")
    if has_execution_override(ci_job, job=True):
        errors.append("ordinary CI execution: verify must not have job-level if or continue-on-error")
    if len(exact_run_step_indexes(ci_job, CI_COMMANDS)) != 1:
        errors.append("ordinary CI gate: required commands must be one exact executable run step")

    triggers = section(pages, "on")
    trigger_keys = {
        match.group(1)
        for line in triggers.splitlines()
        if (match := re.match(r"^  ([\w-]+):(?:\s+.*)?$", line))
    }
    malformed_trigger_lines = [
        line for line in triggers.splitlines()
        if line.startswith("  ") and not line.startswith("    ") and line.strip()
        and not line.lstrip().startswith("#") and not re.match(r"^  [\w-]+:(?:\s+.*)?$", line)
    ]
    if trigger_keys != {"push", "workflow_dispatch"} or malformed_trigger_lines:
        errors.append("Pages trigger allowlist: only main push and workflow_dispatch are permitted")
    branches = re.findall(r"^\s+-\s+([^\s#]+)\s*$", triggers, re.MULTILINE)
    if branches != ["main"]:
        errors.append("main branch trigger: Pages branch list must be exactly main")
    if permission_values(pages) != {"contents: read", "pages: write", "id-token: write"}:
        errors.append("permissions: Pages must grant contents read, pages write and id-token write only")
    if has_job_level_permissions(pages):
        errors.append("job-level permissions: Pages jobs must not override top-level permissions")

    concurrency = section(pages, "concurrency")
    if "  group: pages-${{ github.ref }}" not in concurrency:
        errors.append("ref-scoped concurrency: group must be pages-${{ github.ref }}")
    if "  cancel-in-progress: true" not in concurrency:
        errors.append("ref-scoped concurrency: cancellation must be enabled")
    if not re.search(r"^  deploy:\s*$[\s\S]*?^    needs: build\s*$", pages, re.MULTILINE):
        errors.append("deployment dependency: deploy must need build")

    build_job = job_section(pages, "build")
    deploy_job = job_section(pages, "deploy")
    if any(re.search(r"^    continue-on-error[ \t]*:", job, re.MULTILINE)
           for job in (build_job, deploy_job)):
        errors.append("Pages job execution: jobs must not have continue-on-error")
    job_condition = re.compile(r"^    if[ \t]*:.*$", re.MULTILINE)
    if job_condition.findall(build_job) != ["    if: github.ref == 'refs/heads/main'"]:
        errors.append("main guard: build job must have only the exact refs/heads/main condition")
    if job_condition.search(deploy_job):
        errors.append("deploy job condition: deploy must not have any job-level if condition")
    gate_steps = exact_run_step_indexes(build_job, CI_COMMANDS)
    if len(gate_steps) != 1:
        errors.append("Pages build gate: required commands must be one exact executable run step")
    configure_steps = action_step_indexes(build_job, "actions/configure-pages")
    if len(configure_steps) != 1:
        errors.append("configure-pages step: require one uncommented action in the build job")
    upload_steps = action_step_indexes(build_job, "actions/upload-pages-artifact")
    if len(upload_steps) != 1:
        errors.append("upload-pages step: require one uncommented action in the build job")
    deploy_steps = action_step_indexes(deploy_job, "actions/deploy-pages")
    if len(deploy_steps) != 1:
        errors.append("deploy-pages step: require one uncommented action in the deploy job")

    build_steps = step_blocks(build_job)
    upload_step = build_steps[upload_steps[0]] if len(upload_steps) == 1 else ""
    if not re.search(r"^          path: dist/site\s*$", upload_step, re.MULTILINE):
        errors.append("upload path: Pages artifact must be exactly dist/site")
    final_build_steps = exact_run_step_indexes(build_job, FINAL_BUILD_COMMANDS)
    if (len(upload_steps) != 1 or len(final_build_steps) != 1
            or final_build_steps[0] + 1 != upload_steps[0]
            or not gate_steps or gate_steps[0] >= final_build_steps[0]):
        errors.append("final rebuild: exact clean build step must follow tests immediately before upload")
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
