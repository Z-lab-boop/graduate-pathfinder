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

    def test_rejects_inline_extra_pages_trigger(self) -> None:
        result = self.run_check(pages=PAGES.replace(
            "  workflow_dispatch:\n",
            "  workflow_dispatch:\n  schedule: {cron: '0 0 * * *'}\n",
        ))
        self.assert_contract_failure(result, "Pages trigger allowlist")

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

    def test_public_release_gates_do_not_publish_a_machine_home_path(self) -> None:
        text = (REPO_ROOT / "docs" / "public-site-release-gates.md").read_text(encoding="utf-8")
        self.assertNotIn("/Users/", text)
        self.assertIn("optional maintainer-local", text)
        self.assertIn("SKILL_CREATOR_QUICK_VALIDATE", text)


if __name__ == "__main__":
    unittest.main()
