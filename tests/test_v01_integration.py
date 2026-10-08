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
    def wire_audit(self, candidates, audit, profile):
        audited_claims = {item["record"]["claim_id"]: item for item in audit["claims"]}
        scoring = copy.deepcopy(candidates)
        now = datetime.fromisoformat(profile["audit_at"])
        for item in scoring:
            item["evidence_confidence"] = audit["candidate_summary"][item["candidate_id"]]["confidence"]
            # Every critical field is applicable in this synthetic case. A high
            # confidence label alone cannot substitute for a feasibility gate.
            self.assertEqual({gate["gate_id"] for gate in item["gates"]},
                             {"eligibility", "deadline", "program_availability", "degree_type"})
            for gate in item["gates"]:
                self.assertTrue(gate["critical"])
                bases = item["gate_bases"][gate["gate_id"]]
                supporting = [audited_claims[claim_id] for claim_id in bases]
                self.assertTrue(supporting)
                for claim in supporting:
                    self.assertEqual(claim["record"]["candidate_id"], item["candidate_id"])
                    self.assertEqual(claim["record"]["field"], gate["gate_id"])
                unresolved = [claim for claim in supporting if claim["effective_status"] != "confirmed"]
                gate["evidence_status"] = unresolved[0]["effective_status"] if unresolved else "confirmed"
                gate["status"] = "unknown"
                if unresolved:
                    continue
                self.assertEqual(len(supporting), 1)
                value = supporting[0]["record"]["value"]
                if gate["gate_id"] == "eligibility":
                    gate["status"] = value or "unknown"
                elif gate["gate_id"] == "deadline":
                    if item["deadline"] is not None:
                        self.assertEqual(item["deadline"], value)
                        self.assertTrue(item["deadline_feasibility_basis"].startswith("Synthetic "))
                        gate["status"] = "pass" if datetime.fromisoformat(value) > now else "fail"
                elif gate["gate_id"] == "program_availability":
                    gate["status"] = "pass" if value is True else ("fail" if value is False else "unknown")
                elif gate["gate_id"] == "degree_type" and value is not None:
                    gate["status"] = "pass" if value == item["degree_type"] else "fail"
        return scoring

    def test_stale_critical_deadline_forces_unknown_gate_and_monitor(self):
        fixture = Path(__file__).parent / "fixtures" / "baoyan_case"
        profile = load_json(fixture / "profile.json")
        candidates = load_json(fixture / "candidates.json")
        evidence = load_json(fixture / "evidence.json")
        audit = audit_evidence(evidence, datetime.fromisoformat(profile["audit_at"]))
        stale_id = next(key for key, summary in audit["candidate_summary"].items()
                        if "deadline" in summary["stale_official_fields"])
        scoring = self.wire_audit(candidates, audit, profile)
        portfolio = rank_candidates(scoring, profile["preferences"]["criterion_weights"])
        result = portfolio[stale_id]
        self.assertEqual(result["portfolio_group"], "monitor")
        self.assertEqual(result["eligibility"], "unknown")
        self.assertIsNone(result["rank"])
        self.assertIn("deadline", result["gate_evaluation"]["unknown_critical_gates"])
        deadline_gate = next(gate for gate in result["gate_evaluation"]["gates"]
                             if gate["gate_id"] == "deadline")
        self.assertEqual(deadline_gate["effective_status"], "unknown")
        self.assertEqual(deadline_gate["evidence_status"], "stale")

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
                               "unknown-synthetic", "conflicted-synthetic", "stale-synthetic"})
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
            "core-synthetic": "A", "reach-synthetic": "A", "excluded-synthetic": "A",
            "unknown-synthetic": "D", "conflicted-synthetic": "D", "stale-synthetic": "B"})
        self.assertEqual(audit["candidate_summary"]["stale-synthetic"]["stale_official_fields"],
                         ["deadline"])
        self.assertEqual(set(audit["conflicts"]), {"conflicted-synthetic-deadline-2027"})
        self.assertEqual(audit["conflicts"]["conflicted-synthetic-deadline-2027"]["values"],
                         ["2027-06-15T17:00:00+08:00", "2027-06-16T17:00:00+08:00"])

        # Wire audit results into scores, including gate evidence states; input
        # confidence labels cannot bypass fresh audit findings.
        scoring = self.wire_audit(candidates, audit, profile)
        weights = profile["preferences"]["criterion_weights"]
        portfolio = rank_candidates(scoring, weights)
        self.assertEqual(portfolio["core-synthetic"]["portfolio_group"], "core")
        self.assertEqual(portfolio["reach-synthetic"]["portfolio_group"], "reach")
        self.assertEqual(portfolio["excluded-synthetic"]["portfolio_group"], "excluded")
        self.assertEqual(portfolio["unknown-synthetic"]["portfolio_group"], "monitor")
        self.assertEqual(portfolio["conflicted-synthetic"]["portfolio_group"], "monitor")
        self.assertEqual(portfolio["stale-synthetic"]["portfolio_group"], "monitor")
        self.assertEqual(portfolio["reach-synthetic"]["gate_evaluation"]["unknown_critical_gates"], [])
        self.assertIn("deadline", portfolio["conflicted-synthetic"]["gate_evaluation"]["unknown_critical_gates"])
        self.assertNotIn("admission_probability", json.dumps(portfolio))
        sensitivity = analyze_sensitivity(scoring, weights)
        self.assertEqual(sensitivity["baseline_order"], ["core-synthetic", "reach-synthetic"])
        self.assertEqual(sensitivity["winner_set"], ["core-synthetic"])
        self.assertEqual(sensitivity["stability"], "stable")

        events = profile["synthetic_events"]
        for item in candidates:
            if item["candidate_id"] in {"stale-synthetic", "conflicted-synthetic"}:
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
        self.assertNotIn("stale-synthetic", calendar_text)
        self.assertEqual(calendar_text, render_ics(list(reversed(events)), "Synthetic baoyan case"))


if __name__ == "__main__":
    unittest.main()
