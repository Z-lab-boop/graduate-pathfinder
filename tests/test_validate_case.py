import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.case_io import atomic_write_json, load_json
from scripts.validate_case import (validate_applicant_claim, validate_candidate, validate_case,
                                   validate_evidence, validate_profile)


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
    def test_applicant_claim_states_and_required_fields(self):
        claim = {"claim_id": "gpa", "field": "gpa", "value": None,
                 "state": "missing", "source_document_ids": [], "notes": ""}
        for state in ("document_verified", "user_asserted", "derived", "inferred", "missing", "conflicted"):
            item = dict(claim, state=state, source_document_ids=["document-1"])
            self.assertEqual(validate_applicant_claim(item), [])
        for field in claim:
            with self.subTest(field=field):
                item = claim.copy(); del item[field]
                self.assertTrue(any(field in error for error in validate_applicant_claim(item)))
        self.assertTrue(validate_applicant_claim([]))
        self.assertTrue(validate_applicant_claim(dict(claim, state="confirmed")))

    def test_document_verified_requires_document_reference(self):
        claim = {"claim_id": "gpa", "field": "gpa", "value": 3.5,
                 "state": "document_verified", "source_document_ids": [], "notes": ""}
        self.assertTrue(any("source_document_ids" in error for error in validate_applicant_claim(claim)))
        for refs in (None, "document-1", [""], [1]):
            self.assertTrue(validate_applicant_claim(dict(claim, source_document_ids=refs)))
        self.assertTrue(validate_applicant_claim(dict(claim, notes=[])))

    def test_optional_applicant_claims_require_real_manifest_references(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); self.write_case(directory)
            claim = {"claim_id": "gpa", "field": "gpa", "value": 3.5,
                     "state": "document_verified", "source_document_ids": ["document-1"], "notes": ""}
            (directory / "applicant-claims.json").write_text(json.dumps([claim]))
            self.assertTrue(validate_case(directory))
            manifest = directory / "materials-manifest.json"
            manifest.write_text(json.dumps([{"document_id": "document-1"}]))
            self.assertEqual(validate_case(directory), [])
            manifest.write_text(json.dumps([{"document_id": "document-2"}]))
            self.assertTrue(any("document-1" in error for error in validate_case(directory)))
            for malformed in ({}, [None], [{"document_id": []}]):
                manifest.write_text(json.dumps(malformed))
                self.assertTrue(validate_case(directory))
            (directory / "applicant-claims.json").write_text("{}")
            self.assertTrue(validate_case(directory))

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

    def test_json_ingestion_rejects_nonfinite_numbers_with_file_and_field(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e400", "-1e400"):
            for template, location in (("TOKEN", "$"),
                                       ('[{"value": {"nested": [TOKEN]}}]', '$[0]["value"]["nested"][0]')):
                with self.subTest(token=token, location=location), tempfile.TemporaryDirectory() as temp:
                    target = Path(temp) / "evidence.json"
                    target.write_text(template.replace("TOKEN", token), encoding="utf-8")
                    with self.assertRaises(ValueError) as raised:
                        load_json(target)
                    self.assertIn("evidence.json", str(raised.exception))
                    self.assertIn(location, str(raised.exception))
                    self.assertIn("finite", str(raised.exception))

    def test_nonfinite_evidence_value_is_rejected_before_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); self.write_case(directory)
            item = evidence(); item["value"] = float("nan")
            (directory / "evidence.json").write_text(json.dumps([item]), encoding="utf-8")
            errors = validate_case(directory)
            self.assertTrue(any("evidence.json" in error and '$[0]["value"]' in error
                                and "finite" in error for error in errors), errors)

    def test_json_ingestion_preserves_finite_values_and_nonfinite_text(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "case.json"
            payload = {"value": [1.5, 10**400, None, True, "NaN", "Infinity", "1e400"]}
            target.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(load_json(target), payload)

    def test_candidate_and_evidence_reject_invalid_or_unresolved_offsets(self):
        for timestamp in ("2027-05-02T10:00:00+08:60", "2027-05-02T10:00:00+08:99",
                          "2027-05-02T10:00:00-08:60", "2027-05-02T10:00:00+24:00",
                          "2027-05-02T10:00:00-00:00",
                          "0001-01-01T00:00:00+08:00", "9999-12-31T23:59:59-08:00"):
            for validator, factory, field in ((validate_candidate, candidate, "deadline"),
                                              (validate_evidence, evidence, "retrieved_at")):
                with self.subTest(timestamp=timestamp, field=field):
                    item = factory(); item[field] = timestamp
                    self.assertTrue(any(field in error for error in validator(item)))

    def test_candidate_and_evidence_accept_resolved_offsets_and_fractional_seconds(self):
        for timestamp in ("2027-05-02T10:00:00Z", "2027-05-02T10:00:00+00:00",
                          "2027-05-02T10:00:00+23:59", "2027-05-02T10:00:00-23:59",
                          "2027-05-02T10:00:00.125+08:00"):
            for validator, factory, field in ((validate_candidate, candidate, "deadline"),
                                              (validate_evidence, evidence, "retrieved_at")):
                with self.subTest(timestamp=timestamp, field=field):
                    item = factory(); item[field] = timestamp
                    self.assertEqual(validator(item), [])

    def test_huge_completeness_integer_returns_error_and_continues_aggregation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); self.write_case(directory)
            first = candidate(); first["data_completeness"] = 10**400
            second = candidate(); second["eligibility"] = "likely"
            (directory / "candidates.json").write_text(json.dumps([first, second]))
            errors = validate_case(directory)
            self.assertIn("candidates.json[0]: data_completeness must be a finite number between 0 and 1", errors)
            self.assertTrue(any(error.startswith("candidates.json[1]: eligibility") for error in errors))

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
