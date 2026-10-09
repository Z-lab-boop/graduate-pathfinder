import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_workflows.py"

CI = """
name: CI
on:
  push:
  pull_request:

permissions:
  contents: read
jobs:
  verify:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Verify repository
        run: |
          python3 -m unittest discover -s tests -v
          python3 -m compileall -q scripts tests
          python3 scripts/check_skill_structure.py .
          python3 scripts/check_workflows.py .
          npm --prefix web ci
          npx --prefix web playwright install chromium
          npm --prefix web run typecheck
          npm --prefix web run test:site
          node scripts/check-site-assets.mjs
          git diff --check
"""

PAGES = """
name: Pages
on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages-${{ github.ref }}
  cancel-in-progress: true
jobs:
  build:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - name: Verify repository
        run: |
          python3 -m unittest discover -s tests -v
          python3 -m compileall -q scripts tests
          python3 scripts/check_skill_structure.py .
          python3 scripts/check_workflows.py .
          npm --prefix web ci
          npx --prefix web playwright install chromium
          npm --prefix web run typecheck
          npm --prefix web run test:site
          node scripts/check-site-assets.mjs
          git diff --check
      - name: Rebuild clean Pages artifact
        run: |
          npm --prefix web run build:site
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist/site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy
        id: deployment
        uses: actions/deploy-pages@v4
"""


class WorkflowContractTests(unittest.TestCase):
    def run_check(self, ci: str = CI, pages: str = PAGES) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "ci.yml").write_text(textwrap.dedent(ci).lstrip(), encoding="utf-8")
            (workflows / "pages.yml").write_text(textwrap.dedent(pages).lstrip(), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(CHECKER), str(root)],
                capture_output=True,
                text=True,
                check=False,
            )

    def assert_contract_failure(self, result: subprocess.CompletedProcess[str], invariant: str) -> None:
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(invariant, result.stderr)

    def test_accepts_minimal_valid_workflows(self) -> None:
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Workflow contract check passed", result.stdout)

    def test_rejects_missing_pages_permission(self) -> None:
        result = self.run_check(pages=PAGES.replace("  pages: write\n", ""))
        self.assert_contract_failure(result, "permissions")

    def test_rejects_wrong_pages_branch(self) -> None:
        result = self.run_check(pages=PAGES.replace("      - main\n", "      - develop\n"))
        self.assert_contract_failure(result, "main branch trigger")

    def test_rejects_static_concurrency_group(self) -> None:
        result = self.run_check(pages=PAGES.replace("pages-${{ github.ref }}", "pages"))
        self.assert_contract_failure(result, "ref-scoped concurrency")

    def test_rejects_absent_main_guard(self) -> None:
        result = self.run_check(pages=PAGES.replace("    if: github.ref == 'refs/heads/main'\n", ""))
        self.assert_contract_failure(result, "main guard")

    def test_rejects_conditioned_deploy_job(self) -> None:
        for value in ("false", "'false'", '"false"', "${{ false }}", "true", "always()", ""):
            for key in ("if", "if "):
                with self.subTest(key=key, value=value):
                    pages = PAGES.replace("    needs: build\n", f"    needs: build\n    {key}: {value}\n")
                    self.assert_contract_failure(self.run_check(pages=pages), "deploy job condition")

    def test_rejects_quoted_or_escaped_deploy_job_condition_keys(self) -> None:
        for key in ('"if"', "'if'", '"\\u0069f"', '"\\x69f"', '? "\\u0069f"\n    '):
            with self.subTest(key=key):
                pages = PAGES.replace("  deploy:\n", f"  deploy:\n    {key}: false\n")
                self.assert_contract_failure(self.run_check(pages=pages), "quoted or escaped structural key")

    def test_requires_main_guard_on_build_job_only(self) -> None:
        guard = "    if: github.ref == 'refs/heads/main'\n"
        pages = PAGES.replace(guard, "").replace("  deploy:\n", "  deploy:\n" + guard)
        self.assert_contract_failure(self.run_check(pages=pages), "main guard")

    def test_rejects_additional_build_job_condition(self) -> None:
        pages = PAGES.replace("  build:\n", "  build:\n    if: false\n")
        self.assert_contract_failure(self.run_check(pages=pages), "main guard")

    def test_rejects_wrong_upload_path(self) -> None:
        result = self.run_check(pages=PAGES.replace("          path: dist/site\n", "          path: dist\n"))
        self.assert_contract_failure(result, "upload path")

    def test_rejects_missing_final_rebuild(self) -> None:
        result = self.run_check(
            pages=PAGES.replace(
                "      - name: Rebuild clean Pages artifact\n        run: |\n          npm --prefix web run build:site\n",
                "",
            )
        )
        self.assert_contract_failure(result, "final rebuild")

    def test_rejects_invalid_literal_shell_block(self) -> None:
        result = self.run_check(ci=CI.replace("          git diff --check\n", "          printf '%s\\n broken\n"))
        self.assert_contract_failure(result, "shell syntax")

    def test_rejects_gate_present_only_as_a_comment(self) -> None:
        result = self.run_check(ci=CI.replace(
            "          node scripts/check-site-assets.mjs\n",
            "          # node scripts/check-site-assets.mjs\n",
        ))
        self.assert_contract_failure(result, "ordinary CI gate")

    def test_rejects_pages_auto_enablement(self) -> None:
        result = self.run_check(pages=PAGES.replace(
            "      - uses: actions/configure-pages@v5\n",
            "      - uses: actions/configure-pages@v5\n        with:\n          enablement: true\n",
        ))
        self.assert_contract_failure(result, "Pages enablement")

    def test_rejects_required_commands_hidden_by_shell_structure(self) -> None:
        mutations = {
            "heredoc": CI.replace(
                "        run: |\n          python3 -m unittest",
                "        run: |\n          cat <<'CONTRACT_ONLY'\n          python3 -m unittest",
            ).replace("          git diff --check\n", "          git diff --check\n          CONTRACT_ONLY\n"),
            "control flow": CI.replace(
                "        run: |\n          python3 -m unittest",
                "        run: |\n          if false; then\n          python3 -m unittest",
            ).replace("          git diff --check\n", "          git diff --check\n          fi\n"),
            "redirection": CI.replace(
                "          npm --prefix web run typecheck\n",
                "          npm --prefix web run typecheck > /dev/null\n",
            ),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                self.assert_contract_failure(self.run_check(ci=mutation), "ordinary CI gate")

    def test_rejects_final_rebuild_hidden_by_shell_structure(self) -> None:
        mutations = {
            "heredoc": PAGES.replace(
                "        run: |\n          npm --prefix web run build:site\n",
                "        run: |\n          cat <<'CONTRACT_ONLY'\n          npm --prefix web run build:site\n          CONTRACT_ONLY\n",
            ),
            "control flow": PAGES.replace(
                "        run: |\n          npm --prefix web run build:site\n",
                "        run: |\n          if false; then\n          npm --prefix web run build:site\n          fi\n",
            ),
            "redirection": PAGES.replace(
                "          npm --prefix web run build:site\n",
                "          npm --prefix web run build:site > /dev/null\n",
            ),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                self.assert_contract_failure(self.run_check(pages=mutation), "final rebuild")

    def test_rejects_ci_job_level_permissions_override(self) -> None:
        result = self.run_check(ci=CI.replace(
            "  verify:\n",
            "  verify:\n    permissions: write-all\n",
        ))
        self.assert_contract_failure(result, "job-level permissions")

    def test_rejects_pages_job_level_permissions_override(self) -> None:
        result = self.run_check(pages=PAGES.replace(
            "  build:\n",
            "  build:\n    permissions:\n      contents: write\n",
        ))
        self.assert_contract_failure(result, "job-level permissions")

    def test_rejects_quoted_job_level_permissions_overrides(self) -> None:
        mutations = {
            "CI double quoted": (CI.replace(
                "  verify:\n",
                '  verify:\n    "permissions": write-all\n',
            ), PAGES),
            "CI single quoted": (CI.replace(
                "  verify:\n",
                "  verify:\n    'permissions': write-all\n",
            ), PAGES),
            "Pages double quoted": (CI, PAGES.replace(
                "  build:\n",
                '  build:\n    "permissions":\n      contents: write\n',
            )),
            "Pages single quoted": (CI, PAGES.replace(
                "  build:\n",
                "  build:\n    'permissions': write-all\n",
            )),
        }
        for label, (ci, pages) in mutations.items():
            with self.subTest(label=label):
                self.assert_contract_failure(self.run_check(ci=ci, pages=pages), "job-level permissions")

    def test_rejects_escaped_workflow_mapping_keys(self) -> None:
        mutations = {
            "CI escaped permissions": (CI.replace(
                "  verify:\n",
                '  verify:\n    "permis\\u0073ions": write-all\n',
            ), PAGES),
            "Pages hex-escaped permissions": (CI, PAGES.replace(
                "  build:\n",
                '  build:\n    "permis\\x73ions": write-all\n',
            )),
            "quoted structural key": (CI.replace(
                "    runs-on: ${{ matrix.os }}\n",
                '    "runs-on": ${{ matrix.os }}\n',
            ), PAGES),
            "CI explicit escaped permissions key": (CI.replace(
                "  verify:\n",
                '  verify:\n    ? "permis\\u0073ions"\n    : write-all\n',
            ), PAGES),
        }
        for label, (ci, pages) in mutations.items():
            with self.subTest(label=label):
                self.assert_contract_failure(
                    self.run_check(ci=ci, pages=pages),
                    "quoted or escaped structural key",
                )

    def test_rejects_inline_extra_pages_trigger(self) -> None:
        result = self.run_check(pages=PAGES.replace(
            "  workflow_dispatch:\n",
            "  workflow_dispatch:\n  schedule: {cron: '0 0 * * *'}\n",
        ))
        self.assert_contract_failure(result, "Pages trigger allowlist")

    def test_rejects_anchor_alias_permission_keys(self) -> None:
        for workflow, source, job in (("ci", CI, "verify"), ("pages", PAGES, "build"),
                                      ("pages", PAGES, "deploy")):
            for value in ("write-all", "\n      contents: write"):
                with self.subTest(workflow=workflow, job=job, value=value):
                    mutation = source.replace(source.splitlines()[1], "name: &permission_key permissions")
                    mutation = mutation.replace(f"  {job}:\n", f"  {job}:\n    *permission_key: {value}\n")
                    self.assert_contract_failure(self.run_check(**{workflow: mutation}), "anchors or aliases")

    def test_rejects_other_anchor_alias_locations(self) -> None:
        mutations = (
            CI.replace("name: CI", "name: &title CI"),
            CI.replace("name: CI", "name: *title"),
            CI.replace("os: [ubuntu-latest, macos-latest]", "os: [&runner ubuntu-latest, *runner]"),
            CI.replace("  verify:\n", "  verify: &job\n"),
            CI.replace("  verify:\n", "  verify:\n    env: {LEVEL: &level write-all, COPY: *level}\n"),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_contract_failure(self.run_check(ci=mutation), "anchors or aliases")

    def test_rejects_compact_block_scalar_hiding_required_action_conditions(self) -> None:
        for action, version in (("configure-pages", "v5"), ("upload-pages-artifact", "v3"),
                                ("deploy-pages", "v4")):
            for scalar in ("|", ">", "|-", ">+", "|2", ">2-"):
                for key in ('"\\u0069f"', '"\\x69f"', "'if'"):
                    with self.subTest(action=action, scalar=scalar, key=key):
                        original = f"      - uses: actions/{action}@{version}\n"
                        if action == "deploy-pages":
                            original = "      - name: Deploy\n        id: deployment\n        uses: actions/deploy-pages@v4\n"
                        replacement = (f"      - name: {scalar}\n"
                                       f"        uses: actions/{action}@{version}\n"
                                       f"        {key}: false\n")
                        self.assert_contract_failure(
                            self.run_check(pages=PAGES.replace(original, replacement)),
                            "unsupported block scalar",
                        )

    def test_rejects_block_scalars_outside_canonical_run_fields(self) -> None:
        for header in ("name: |", "name: >", "name: |2-", "name: !!str |", "name: !<tag:yaml.org,2002:str> |"):
            with self.subTest(header=header):
                mutation = CI.replace("name: CI", header + "\n  CI")
                self.assert_contract_failure(self.run_check(ci=mutation), "unsupported block scalar")
        for header in ("      - run: |", "        run: >", "        run: |-", "        run: |2"):
            with self.subTest(header=header):
                mutation = CI + "      - name: Additional shell\n" + header + "\n          echo okay\n"
                self.assert_contract_failure(self.run_check(ci=mutation), "unsupported block scalar")

    def test_rejects_noncanonical_shell_body_indentation(self) -> None:
        for indent in (9, 11, 12):
            with self.subTest(indent=indent):
                mutation = CI + "      - name: Additional shell\n        run: |\n" + " " * indent + "echo okay\n"
                self.assert_contract_failure(self.run_check(ci=mutation), "shell block indentation")

    def test_accepts_yaml_metacharacters_inside_literal_shell(self) -> None:
        mutation = CI + '''      - name: Additional shell
        run: |
          printf '%s\\n' '&anchor *alias ? key: | >'
          printf '%s\\n' '\\u0069f'
          if true; then
            echo okay
          fi
'''
        result = self.run_check(ci=mutation)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_configure_action_present_only_in_comment(self) -> None:
        result = self.run_check(pages=PAGES.replace(
            "      - uses: actions/configure-pages@v5\n",
            "      # actions/configure-pages@v5\n",
        ))
        self.assert_contract_failure(result, "configure-pages step")

    def test_rejects_deploy_action_present_only_in_comment(self) -> None:
        result = self.run_check(pages=PAGES.replace(
            "        uses: actions/deploy-pages@v4\n",
            "        # actions/deploy-pages@v4\n",
        ))
        self.assert_contract_failure(result, "deploy-pages step")

    def test_rejects_conditioned_required_pages_actions(self) -> None:
        mutations = {
            "configure false": PAGES.replace(
                "      - uses: actions/configure-pages@v5\n",
                "      - uses: actions/configure-pages@v5\n        if: false\n",
            ),
            "upload single-quoted false": PAGES.replace(
                "      - uses: actions/upload-pages-artifact@v3\n",
                "      - uses: actions/upload-pages-artifact@v3\n        if: 'false'\n",
            ),
            "deploy double-quoted false": PAGES.replace(
                "        uses: actions/deploy-pages@v4\n",
                "        uses: actions/deploy-pages@v4\n        if: \"false\"\n",
            ),
        }
        for label, pages in mutations.items():
            with self.subTest(label=label):
                result = self.run_check(pages=pages)
                self.assertNotEqual(result.returncode, 0)
                self.assertRegex(result.stderr, r"(?:configure|upload|deploy)-pages step")

    def test_rejects_escaped_condition_keys_on_required_pages_actions(self) -> None:
        mutations = {
            "configure unicode escape": PAGES.replace(
                "      - uses: actions/configure-pages@v5\n",
                '      - uses: actions/configure-pages@v5\n        "\\u0069f": false\n',
            ),
            "upload hex escape": PAGES.replace(
                "      - uses: actions/upload-pages-artifact@v3\n",
                '      - uses: actions/upload-pages-artifact@v3\n        "\\x69f": false\n',
            ),
            "deploy unicode escape": PAGES.replace(
                "        uses: actions/deploy-pages@v4\n",
                '        uses: actions/deploy-pages@v4\n        "\\u0069f": false\n',
            ),
            "configure explicit unicode escape": PAGES.replace(
                "      - uses: actions/configure-pages@v5\n",
                '      - uses: actions/configure-pages@v5\n        ? "\\u0069f"\n        : false\n',
            ),
        }
        for label, pages in mutations.items():
            with self.subTest(label=label):
                self.assert_contract_failure(
                    self.run_check(pages=pages),
                    "quoted or escaped structural key",
                )

    def test_public_release_gates_do_not_publish_a_machine_home_path(self) -> None:
        text = (REPO_ROOT / "docs" / "public-site-release-gates.md").read_text(encoding="utf-8")
        self.assertNotIn("/Users/", text)
        self.assertIn("optional maintainer-local", text)
        self.assertIn("SKILL_CREATOR_QUICK_VALIDATE", text)


if __name__ == "__main__":
    unittest.main()
