import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.case_io import atomic_write_json, load_json
from scripts.validate_case import validate_candidate, validate_case, validate_evidence, validate_profile


def profile():
    return {"case_label": "synthetic-cs-2027", "pathway": "baoyan", "admission_year": 2027,
            "preferences": {"risk_tolerance": "balanced"}}


def candidate():
    return {"candidate_id": "school-unit-program-master-summer-2027", "pathway": "baoyan",
            "admission_year": 2027, "institution": "Example University", "unit": "Computing",
            "program_code": None, "program_name": "Computer Science", "degree_type": "academic-master",
            "research_track": None, "round": "summer-camp", "deadline": None,
            "status": "discovered", "eligibility": "unknown", "evidence_confidence": "D",
            "data_completeness": 0.0, "sources": []}


def evidence():
    return {"claim_id": "deadline-a", "candidate_id": "school-unit-program-master-summer-2027",
            "field": "deadline", "value": "2027-06-15T17:00:00+08:00",
            "source_url": "https://example.edu.cn/notice", "source_title": "Synthetic notice",
            "publisher": "Example University", "published_at": "2027-05-01",
            "retrieved_at": "2027-05-02T10:00:00+08:00", "tier": "T1", "status": "confirmed",
            "scope": "program", "short_evidence": "Synthetic fixture", "conflict_group": None}


class CaseValidationTests(unittest.TestCase):
    def test_valid_records(self):
        self.assertEqual(validate_profile(profile()), [])
        self.assertEqual(validate_candidate(candidate()), [])
        self.assertEqual(validate_evidence(evidence()), [])

    def test_missing_admission_year(self):
        item = profile(); del item["admission_year"]
        self.assertIn("admission_year must be an integer", validate_profile(item))

    def test_invalid_evidence_tier_is_rejected(self):
        item = evidence(); item["tier"] = "T9"
        self.assertIn("tier must be one of T1, T2, T3, T4", validate_evidence(item))

    def test_invalid_eligibility(self):
        item = candidate(); item["eligibility"] = "likely"
        self.assertTrue(any("eligibility" in error for error in validate_candidate(item)))

    def test_invalid_types_and_enums(self):
        for validator, factory, field, value in [
            (validate_profile, profile, "admission_year", True),
            (validate_profile, profile, "pathway", "other"),
            (validate_profile, profile, "preferences", []),
            (validate_candidate, candidate, "sources", {}),
            (validate_candidate, candidate, "data_completeness", float("nan")),
            (validate_candidate, candidate, "deadline", "2027-06-15"),
            (validate_candidate, candidate, "deadline", "2027-06-15T17+08:00"),
            (validate_candidate, candidate, "status", "invented"),
            (validate_evidence, evidence, "status", "likely"),
            (validate_evidence, evidence, "retrieved_at", "2027-05-02T10:00:00"),
        ]:
            with self.subTest(field=field):
                item = factory(); item[field] = value
                self.assertTrue(validator(item))
        for validator in (validate_profile, validate_candidate, validate_evidence):
            self.assertTrue(validator([]))

    def write_case(self, directory):
        for name, payload in (("profile.json", profile()), ("candidates.json", [candidate()]),
                              ("evidence.json", [evidence()])):
            (directory / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_valid_case_and_aggregated_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); self.write_case(directory)
            self.assertEqual(validate_case(directory), [])
            item = candidate(); item["eligibility"] = "likely"
            (directory / "candidates.json").write_text(json.dumps([item, None]))
            errors = validate_case(directory)
            self.assertTrue(any(e.startswith("candidates.json[0]: eligibility") for e in errors))
            self.assertTrue(any(e.startswith("candidates.json[1]:") for e in errors))

    def test_missing_malformed_and_wrong_container(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.assertEqual(len(validate_case(directory)), 3)
            self.write_case(directory)
            (directory / "profile.json").write_text("{")
            (directory / "candidates.json").write_text("{}")
            self.assertEqual(len(validate_case(directory)), 2)

    def test_skill_root_and_resolved_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); case = root / "case"; case.mkdir(); self.write_case(case)
            alias = root / "alias"; alias.symlink_to(case, target_is_directory=True)
            self.assertTrue(validate_case(case, skill_root=root))
            self.assertTrue(validate_case(alias, skill_root=root))
            self.assertTrue(validate_case(root, skill_root=root))

    def test_cli_enforces_root_and_exit_status(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); self.write_case(directory)
            command = [sys.executable, "scripts/validate_case.py", str(directory)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            result = subprocess.run(command + ["--skill-root", str(directory)], capture_output=True)
            self.assertEqual(result.returncode, 1)

    def test_atomic_roundtrip_and_failure_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "case.json"
            atomic_write_json(target, {"label": "合成案例"})
            self.assertEqual(load_json(target), {"label": "合成案例"})
            with patch("scripts.case_io.os.replace", side_effect=OSError("synthetic failure")):
                with self.assertRaises(OSError):
                    atomic_write_json(target, {"label": "replacement"})
            self.assertEqual(load_json(target), {"label": "合成案例"})
            self.assertEqual(list(Path(temp).iterdir()), [target])


if __name__ == "__main__":
    unittest.main()
