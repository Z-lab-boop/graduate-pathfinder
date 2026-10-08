import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_material_manifest import build_manifest, sha256_file


class MaterialManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case_root = self.root / "case"
        self.source = self.root / "transcript.PDF"
        self.source.write_bytes(b"synthetic material\n")

    def test_manifest_hashes_without_copying_source(self):
        before = self.source.read_bytes()
        stat = self.source.stat()
        entries = build_manifest([self.source], self.case_root)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.source.stat().st_mtime_ns, stat.st_mtime_ns)
        entry = entries[0]
        self.assertEqual(entry["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(entry["source_path"], str(self.source.resolve()))
        self.assertEqual(entry["size_bytes"], len(before))
        self.assertEqual(entry["extension"], ".pdf")
        self.assertEqual(entry["modified_at"], datetime.fromtimestamp(
            stat.st_mtime, timezone.utc).isoformat())
        self.assertEqual(entry["format_class"], "pdf")
        self.assertEqual(entry["document_class"], "unknown")
        self.assertEqual(entry["extraction_state"], "not_started")
        self.assertFalse(self.case_root.exists())
        self.assertEqual(entries, build_manifest([self.source], self.case_root))

    def test_sha256_spans_multiple_chunks(self):
        content = b"a" * (1024 * 1024 + 3)
        self.source.write_bytes(content)
        self.assertEqual(sha256_file(self.source), hashlib.sha256(content).hexdigest())

    def test_extension_only_format_classification(self):
        for suffix, expected in ((".docx", "docx"), (".xlsx", "xlsx"),
                                 (".JPEG", "image"), (".png", "image"),
                                 (".txt", "text"), (".md", "text"), (".bin", "unknown")):
            with self.subTest(suffix=suffix):
                source = self.root / ("certificate" + suffix)
                source.write_bytes(b"not inspected")
                entry = build_manifest([source], self.case_root)[0]
                self.assertEqual(entry["format_class"], expected)
                self.assertEqual(entry["document_class"], "unknown")

    def test_missing_files_and_directories_are_rejected(self):
        for source in (self.root / "missing", self.root):
            with self.subTest(source=source), self.assertRaises((OSError, ValueError)):
                build_manifest([source], self.case_root)

    def test_document_ids_are_content_addressed_and_preserve_distinct_paths(self):
        other = self.root / "other.pdf"
        other.write_bytes(self.source.read_bytes())
        entries = build_manifest([self.source, other], self.case_root)
        expected = "sha256:" + hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.assertEqual(entries[0]["document_id"], expected)
        self.assertEqual(entries[1]["document_id"], expected)
        self.assertNotEqual(entries[0]["source_path"], entries[1]["source_path"])

    def test_cli_writes_manifest_only_and_preserves_failed_previous_output(self):
        command = [sys.executable, "scripts/build_material_manifest.py", "--case-root",
                   str(self.case_root), "--file", str(self.source)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.case_root / "materials-manifest.json"
        before = target.read_bytes()
        self.assertEqual(json.loads(before)[0]["source_path"], str(self.source.resolve()))
        self.assertEqual(list(self.case_root.iterdir()), [target])
        result = subprocess.run(command + ["--file", str(self.root / "missing")],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), before)

    def test_cli_rejects_skill_root_and_symlink_into_it(self):
        skill_root = Path(__file__).resolve().parents[1]
        alias = self.root / "alias"
        alias.symlink_to(skill_root, target_is_directory=True)
        for root in (skill_root, alias):
            result = subprocess.run([sys.executable, "scripts/build_material_manifest.py",
                                     "--case-root", str(root), "--file", str(self.source)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the skill root", result.stderr)

    def test_cli_does_not_overwrite_a_selected_source_at_output_path(self):
        self.case_root.mkdir()
        source = self.case_root / "materials-manifest.json"
        source.write_bytes(b"original selected material")
        result = subprocess.run([sys.executable, "scripts/build_material_manifest.py",
                                 "--case-root", str(self.case_root), "--file", str(source)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(source.read_bytes(), b"original selected material")


if __name__ == "__main__":
    unittest.main()
