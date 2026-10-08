"""Fully synthetic, offline evidence-to-portfolio/calendar release case."""
import copy
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.parse import urlparse

from scripts.audit_evidence import audit_evidence
from scripts.case_io import load_json
from scripts.detect_schedule_conflicts import detect_conflicts
from scripts.generate_calendar import render_ics
from scripts.rank_candidates import rank_candidates
from scripts.sensitivity_analysis import analyze_sensitivity
from scripts.validate_case import validate_case


class V01IntegrationTests(unittest.TestCase):
    def test_synthetic_evidence_drives_conservative_portfolio_and_calendar(self):
        fixture = Path(__file__).parent / "fixtures" / "baoyan_case"
        # Copy into a user-case boundary; fixtures intentionally live in the skill.
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary)
            for name in ("profile.json", "candidates.json", "evidence.json"):
                self.assertTrue((fixture / name).is_file(), f"Missing fixture: {name}")
                shutil.copyfile(fixture / name, case / name)
            self.assertEqual(validate_case(case), [])
            profile = load_json(case / "profile.json")
            candidates = load_json(case / "candidates.json")
            evidence = load_json(case / "evidence.json")

        ids = {item["candidate_id"] for item in candidates}
        self.assertEqual(ids, {"core-synthetic", "reach-synthetic", "excluded-synthetic",
                               "unknown-synthetic", "conflicted-synthetic"})
        self.assertEqual(len(candidates), len(ids))
        claims = {item["claim_id"]: item for item in evidence}
        self.assertEqual(len(claims), len(evidence))
        for item in evidence:
            self.assertIn(item["candidate_id"], ids)
            self.assertEqual(urlparse(item["source_url"]).hostname, "example.edu.cn")
            self.assertEqual(item["applicable_admission_year"], profile["admission_year"])
        for item in candidates:
            self.assertEqual(item["admission_year"], profile["admission_year"])
            self.assertTrue(item["institution"].startswith("Fictional "))
            self.assertEqual(set(item["sources"]), {
                record["claim_id"] for record in evidence
                if record["candidate_id"] == item["candidate_id"]})

        audit = audit_evidence(evidence, datetime.fromisoformat(profile["audit_at"]))
        self.assertEqual(audit["errors"], [])
        self.assertEqual({key: value["confidence"]
                          for key, value in audit["candidate_summary"].items()}, {
            "core-synthetic": "A", "reach-synthetic": "B", "excluded-synthetic": "A",
            "unknown-synthetic": "D", "conflicted-synthetic": "D"})
        self.assertEqual(audit["candidate_summary"]["reach-synthetic"]["stale_official_fields"],
                         ["deadline"])
        self.assertEqual(set(audit["conflicts"]), {"conflicted-synthetic-deadline-2027"})
        self.assertEqual(audit["conflicts"]["conflicted-synthetic-deadline-2027"]["values"],
                         ["2027-06-15T17:00:00+08:00", "2027-06-16T17:00:00+08:00"])

        # Wire audit results into scores, including gate evidence states; input
        # confidence labels cannot bypass fresh audit findings.
        audited_claims = {item["record"]["claim_id"]: item for item in audit["claims"]}
        scoring = copy.deepcopy(candidates)
        for item in scoring:
            item["evidence_confidence"] = audit["candidate_summary"][item["candidate_id"]]["confidence"]
            for gate in item["gates"]:
                bases = item["gate_bases"][gate["gate_id"]]
                self.assertEqual(len(bases), 1)
                claim = audited_claims[bases[0]]
                self.assertEqual(claim["record"]["candidate_id"], item["candidate_id"])
                self.assertEqual(claim["record"]["field"], "eligibility")
                self.assertEqual(gate["status"], claim["record"]["value"] or "unknown")
                gate["evidence_status"] = claim["effective_status"]
        weights = profile["preferences"]["criterion_weights"]
        portfolio = rank_candidates(scoring, weights)
        self.assertEqual(portfolio["core-synthetic"]["portfolio_group"], "core")
        self.assertEqual(portfolio["reach-synthetic"]["portfolio_group"], "reach")
        self.assertEqual(portfolio["excluded-synthetic"]["portfolio_group"], "excluded")
        self.assertEqual(portfolio["unknown-synthetic"]["portfolio_group"], "monitor")
        self.assertEqual(portfolio["conflicted-synthetic"]["portfolio_group"], "monitor")
        self.assertNotIn("admission_probability", json.dumps(portfolio))
        sensitivity = analyze_sensitivity(scoring, weights)
        self.assertEqual(sensitivity["baseline_order"], ["core-synthetic", "reach-synthetic"])
        self.assertEqual(sensitivity["winner_set"], ["core-synthetic"])
        self.assertEqual(sensitivity["stability"], "stable")

        events = profile["synthetic_events"]
        for item in candidates:
            if item["candidate_id"] in {"reach-synthetic", "conflicted-synthetic"}:
                self.assertIsNone(item["deadline"])
        for event in events:
            self.assertIn(event["candidate_id"], ids)
            self.assertEqual(portfolio[event["candidate_id"]]["eligibility"], "pass")
            self.assertTrue(event["user_basis"].startswith("Synthetic "))
        conflicts = detect_conflicts(events)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["candidate_ids"], ["core-synthetic", "reach-synthetic"])
        self.assertEqual(conflicts[0]["overlap_minutes"], 30)
        calendar_text = render_ics(events, "Synthetic baoyan case")
        self.assertIn("BEGIN:VCALENDAR", calendar_text)
        self.assertEqual(calendar_text.count("BEGIN:VEVENT"), 2)
        self.assertNotIn("conflicted-synthetic", calendar_text)
        self.assertEqual(calendar_text, render_ics(list(reversed(events)), "Synthetic baoyan case"))


if __name__ == "__main__":
    unittest.main()
