"""Offline synthetic kaoyan evidence-to-shortlist release case."""
import copy
from datetime import datetime
from pathlib import Path
import json
import shutil
import tempfile
import unittest
from urllib.parse import urlparse

from scripts.assess_kaoyan import (
    assess_kaoyan_candidate, build_kaoyan_shortlist,
    compare_score_scenario, validate_subject_match,
)
from scripts.audit_evidence import audit_evidence
from scripts.case_io import load_json
from scripts.rank_candidates import rank_candidates
from scripts.sensitivity_analysis import analyze_sensitivity
from scripts.validate_case import validate_case


class V02IntegrationTests(unittest.TestCase):
    def test_synthetic_catalog_threshold_and_preference_decisions(self):
        # Catches scope upgrades, unresolved catalog promotion, mismatch bypass,
        # and loss of real preference-dependent choices in the shortlist.
        fixture = Path(__file__).parent / "fixtures" / "kaoyan_case"
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary)
            for name in ("profile.json", "candidates.json", "evidence.json"):
                self.assertTrue((fixture / name).is_file(), f"Missing fixture: {name}")
                shutil.copyfile(fixture / name, case / name)
            self.assertEqual(validate_case(case), [])
            profile = load_json(case / "profile.json")
            candidates = load_json(case / "candidates.json")
            evidence = load_json(case / "evidence.json")
        before = copy.deepcopy((profile, candidates, evidence))
        ids = {item["candidate_id"] for item in candidates}
        self.assertEqual(ids, {"research-first", "location-first", "subject-mismatch",
                               "catalog-unknown", "national-only"})
        claims = {item["claim_id"]: item for item in evidence}
        self.assertEqual(len(claims), len(evidence))
        for record in evidence:
            self.assertEqual(urlparse(record["source_url"]).hostname, "example.invalid")
            self.assertEqual(record["applicable_admission_year"], 2026)
            self.assertTrue(record["short_evidence"].startswith("Synthetic "))
        for candidate in candidates:
            self.assertTrue(candidate["institution"].startswith("Fictional "))
            self.assertEqual(set(candidate["sources"]), {r["claim_id"] for r in evidence
                             if r["candidate_id"] == candidate["candidate_id"]})
            self.assertEqual(candidate["current_catalog"],
                             claims[candidate["current_catalog"]["claim_id"]])
            for line in candidate["thresholds"]:
                self.assertEqual(line["evidence"], claims[line["source_ref"]])
                self.assertEqual(line["subject_codes"], line["evidence"]["value"]["subject_codes"])

        audit = audit_evidence(evidence, datetime.fromisoformat(profile["audit_at"]))
        self.assertEqual(audit["errors"], [])
        scoring = copy.deepcopy(candidates)
        for candidate in scoring:
            cid = candidate["candidate_id"]
            candidate["evidence_confidence"] = audit["candidate_summary"][cid]["confidence"]
            for gate in candidate["gates"]:
                record = claims[candidate["gate_bases"][gate["gate_id"]]]
                claim = next(c for c in audit["claims"] if c["record"]["claim_id"] == record["claim_id"])
                gate["evidence_status"] = claim["effective_status"]
                gate["status"] = "pass" if claim["effective_status"] == "confirmed" else "unknown"
                gate["evidence"] = [copy.deepcopy(record)]
                gate["source_refs"] = [record["claim_id"]]
            subjects = validate_subject_match(profile, candidate, audit)
            candidate["gates"].append({"gate_id": "subject_match", "critical": True,
                                      "status": subjects["status"],
                                      "evidence_status": "confirmed" if subjects["status"] != "unknown" else "missing",
                                      "evidence": copy.deepcopy(candidate["subject_combination"]["evidence"])})
            scenario = compare_score_scenario(profile, candidate, audit)
            compatible = scenario["status"] in {"above", "overlaps", "below"}
            candidate["gates"].append({"gate_id": "scoped_comparison", "critical": True,
                                      "status": "pass" if compatible else "unknown",
                                      "evidence_status": "confirmed" if compatible else "missing",
                                      "evidence": [copy.deepcopy(line["evidence"]) for line in candidate["thresholds"]]})
        sensitivity = analyze_sensitivity(scoring, profile["preferences"]["criterion_weights"])
        self.assertEqual(sensitivity["baseline_order"][:2], ["research-first", "location-first"])
        self.assertEqual(sensitivity["stability"], "fragile")
        self.assertEqual(sensitivity["winner_set"], ["location-first", "research-first"])
        raised = next(s for s in sensitivity["scenarios"]
                      if s["criterion"] == "location_fit" and s["direction"] == "increase")
        self.assertEqual(raised["order"][:2], ["location-first", "research-first"])
        baseline = rank_candidates(scoring, profile["preferences"]["criterion_weights"])
        changed = rank_candidates(scoring, raised["weights"])
        self.assertLess(baseline["research-first"]["rank"], baseline["location-first"]["rank"])
        self.assertLess(changed["location-first"]["rank"], changed["research-first"]["rank"])

        for candidate in scoring:
            candidate["sensitivity"] = copy.deepcopy(sensitivity)
        results = {c["candidate_id"]: assess_kaoyan_candidate(profile, c, audit) for c in scoring}
        self.assertEqual(results["subject-mismatch"]["risk_band"], "excluded")
        self.assertEqual(results["catalog-unknown"]["risk_band"], "monitor")
        self.assertEqual(results["national-only"]["risk_band"], "monitor")
        national = results["national-only"]["score_scenario"]
        self.assertEqual(national["status"], "insufficient_evidence")
        self.assertEqual(national["comparisons"], [])
        self.assertEqual(national["excluded_thresholds"][0]["threshold"]["scope"], "national")
        national_profile = copy.deepcopy(profile)
        national_profile["score_scenario"]["scope"] = "national"
        national_candidate = next(c for c in scoring if c["candidate_id"] == "national-only")
        national_comparison = compare_score_scenario(national_profile, national_candidate, audit)
        self.assertEqual(national_comparison["status"], "above")
        self.assertEqual(national_comparison["comparisons"][0]["threshold"]["scope"], "national")
        self.assertFalse(national_comparison["comparisons"][0]["threshold"]["is_program_specific"])
        for field in ("area", "category", "institution", "unit", "program_code", "research_track"):
            wrong_target = copy.deepcopy(national_candidate)
            wrong_target[field] = "different synthetic applicability"
            self.assertEqual(compare_score_scenario(national_profile, wrong_target, audit)["status"],
                             "insufficient_evidence")
        for cid in ("research-first", "location-first"):
            self.assertEqual(results[cid]["subject_match"]["status"], "pass")
            self.assertEqual(results[cid]["risk_band"], "conservative")
            comparison = results[cid]["score_scenario"]["comparisons"][0]
            self.assertEqual(comparison["threshold"]["scope"], "program")
            self.assertEqual(comparison["total_margin"], [20, 40])
            self.assertEqual(comparison["subject_margins"]["201"], [10, 20])
            self.assertIn(cid + "-threshold", results[cid]["source_refs"])
            self.assertIn(cid + "-program_availability", results[cid]["source_refs"])

        shortlist = build_kaoyan_shortlist(results)
        self.assertIsNone(shortlist["primary"])
        self.assertEqual(shortlist["decision_set"], ["location-first", "research-first"])
        self.assertTrue(shortlist["requires_user_decision"])
        self.assertEqual(shortlist["monitor"], ["catalog-unknown", "national-only"])
        self.assertEqual(shortlist["excluded"], ["subject-mismatch"])
        self.assertNotIn("admission_probability", json.dumps(shortlist))
        self.assertNotIn("admission_probability", json.dumps(results))
        # Source provenance is mandatory even if summary confidence is copied.
        no_provenance = assess_kaoyan_candidate(profile, scoring[0], audit["candidate_summary"])
        self.assertEqual(no_provenance["risk_band"], "monitor")
        altered = copy.deepcopy(scoring[0])
        altered["current_catalog"]["short_evidence"] += " altered after audit"
        self.assertEqual(assess_kaoyan_candidate(profile, altered, audit)["risk_band"], "monitor")
        self.assertEqual(build_kaoyan_shortlist(dict(reversed(list(results.items())))), shortlist)
        self.assertEqual((profile, candidates, evidence), before)


if __name__ == "__main__":
    unittest.main()
