import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_skill_structure.py"


class SkillStructureCheckTests(unittest.TestCase):
    def run_check(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER), str(root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def make_skill(self, parent: Path, frontmatter: str | None = None) -> Path:
        root = parent / "skill"
        root.mkdir()
        (root / "SKILL.md").write_text(
            frontmatter
            or "---\nname: graduate-pathfinder\ndescription: Evidence-first admissions support.\n---\n\n# Skill\n",
            encoding="utf-8",
        )
        (root / "references").mkdir()
        (root / "scripts").mkdir()
        (root / "tests").mkdir()
        (root / "agents").mkdir()
        (root / "agents" / "openai.yaml").write_text("name: Graduate Pathfinder\n", encoding="utf-8")
        return root

    def test_accepts_the_valid_repository(self) -> None:
        result = self.run_check(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill structure check passed", result.stdout)

    def test_rejects_missing_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_skill(Path(directory), "# No frontmatter\n")
            result = self.run_check(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frontmatter", result.stderr)

    def test_rejects_wrong_skill_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_skill(
                Path(directory),
                "---\nname: another-skill\ndescription: Present.\n---\n",
            )
            result = self.run_check(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("name must be graduate-pathfinder", result.stderr)

    def test_rejects_empty_block_description(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_skill(
                Path(directory),
                "---\nname: graduate-pathfinder\ndescription: >-\n---\n",
            )
            result = self.run_check(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("description must be nonempty", result.stderr)

    def test_rejects_whitespace_only_quoted_description(self) -> None:
        for value in ('"   "', "'   '"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = self.make_skill(
                    Path(directory),
                    f"---\nname: graduate-pathfinder\ndescription: {value}\n---\n",
                )
                result = self.run_check(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("description must be nonempty", result.stderr)

    def test_rejects_malformed_top_level_frontmatter_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_skill(
                Path(directory),
                "---\nname: graduate-pathfinder\ndescription: Present.\nthis is not yaml\n---\n",
            )
            result = self.run_check(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("malformed top-level line", result.stderr)

    def test_accepts_supported_quoted_frontmatter_scalars(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_skill(
                Path(directory),
                "---\nname: 'graduate-pathfinder'\ndescription: \"Evidence-first: admissions support.\"\n---\n",
            )
            result = self.run_check(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_malformed_frontmatter_scalars(self) -> None:
        invalid_values = (
            '\"unterminated',
            "'unterminated",
            "[unterminated",
            "{unterminated",
            "present: invalid",
            "[closed]",
            "{key: value}",
        )
        for value in invalid_values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = self.make_skill(
                    Path(directory),
                    f"---\nname: graduate-pathfinder\ndescription: {value}\n---\n",
                )
                result = self.run_check(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frontmatter scalar", result.stderr)

    def test_rejects_yaml_implicit_and_explicit_non_string_scalars(self) -> None:
        invalid_values = (
            "# absent",
            "null",
            "~",
            "true",
            "42",
            "3.14",
            "1e3",
            "0x10",
            "2026-10-10",
            "2026-10-10T10:30:00Z",
            ".nan",
            ".inf",
            "-.inf",
            "[]",
            "{}",
            "!!null null",
            "!!bool true",
            "!!int 1",
        )
        for value in invalid_values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = self.make_skill(
                    Path(directory),
                    f"---\nname: graduate-pathfinder\ndescription: {value}\n---\n",
                )
                result = self.run_check(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frontmatter scalar", result.stderr)

    def test_rejects_non_string_or_comment_only_name(self) -> None:
        for value in ("# absent", "null", "false", "2026-10-10", ".nan", "[]"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = self.make_skill(
                    Path(directory),
                    f"---\nname: {value}\ndescription: Present.\n---\n",
                )
                result = self.run_check(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frontmatter scalar", result.stderr)

    def test_rejects_missing_required_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_skill(Path(directory))
            (root / "agents" / "openai.yaml").unlink()
            result = self.run_check(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required path missing: agents/openai.yaml", result.stderr)

    def test_rejects_broken_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_skill(Path(directory))
            (root / "references" / "broken.md").symlink_to("missing.md")
            result = self.run_check(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("broken symlink: references/broken.md", result.stderr)

    def test_rejects_symlink_escaping_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = self.make_skill(parent)
            outside = parent / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            (root / "references" / "escape.md").symlink_to(outside)
            result = self.run_check(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink escapes repository: references/escape.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
