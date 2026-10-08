"""Offline invented material workflow; no live applicant or admission evidence."""
import copy
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlparse

from scripts.assess_admission_outlook import assess_admission_outlook
from scripts.audit_evidence import audit_evidence
from scripts.audit_materials import audit_materials
from scripts.build_material_manifest import build_manifest
from scripts.calculate_historical_metrics import calculate_stage_metrics, reconstruct_timeline
from scripts.case_io import atomic_write_json, load_json
from scripts.rank_candidates import evaluate_gates, score_candidate
from scripts.redact_generated_text import redact_text
from scripts.validate_case import validate_applicant_claim


class V03IntegrationTests(unittest.TestCase):
    def test_conflicted_packet_cannot_gain_position_from_cross_scope_history(self):
        # Catches lost contradictions, draft-letter promotion, crossed historical
        # denominators, and private values leaking through generated reports.
        fixture = Path(__file__).parent / "fixtures" / "material_case"
        for name in ("manifest.json", "claims.json", "requirements.json", "history.json"):
            self.assertTrue((fixture / name).is_file(), f"Missing synthetic fixture: {name}")
        documents = load_json(fixture / "manifest.json")
        claims = load_json(fixture / "claims.json")
        requirements = load_json(fixture / "requirements.json")
        history = load_json(fixture / "history.json")
        before = copy.deepcopy((documents, claims, requirements, history))
        for claim in claims:
            self.assertEqual(validate_applicant_claim(claim), [])
        for record in history["evidence"]:
            self.assertEqual(urlparse(record["source_url"]).hostname, "example.invalid")
            self.assertTrue(record["publisher"].startswith("Fictional "))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = []
            for document in documents:
                path = root / document["filename"]
                path.write_text(document["synthetic_source"], encoding="utf-8")
                paths.append(path)
            originals = [path.read_bytes() for path in paths]
            manifest = build_manifest(paths, root / "case")
            for actual, reviewed in zip(manifest, documents):
                self.assertEqual(actual["document_id"], reviewed["document_id"])
                self.assertEqual(actual["document_class"], "unknown")
                self.assertEqual(actual["extraction_state"], "not_started")
                actual.update(document_class=reviewed["document_class"], extraction_state="reviewed")
            material = audit_materials(manifest, claims, requirements)
            self.assertEqual(material["items_by_id"]["recommendation-1"]["status"], "repairable")
            self.assertEqual(material["items_by_id"]["recommendation-1"]["missing_conditions"], ["signature"])
            self.assertEqual(material["contradictions"][0]["field"], "gpa")
            self.assertEqual([c["value"] for c in material["contradictions"][0]["claims"]], [3.8, 3.4])
            metrics = calculate_stage_metrics(history["counts"])
            self.assertEqual(metrics["rejected"][0]["reason"], "scope_mismatch")
            self.assertEqual(len(metrics["scopes"]), 2)
            self.assertEqual(metrics["scopes"][0]["metrics"], [])
            self.assertEqual(metrics["scopes"][0]["counts"][1]["stage"], "listed_shortlist")
            self.assertEqual(metrics["scopes"][1]["metrics"][0]["value"], 0.25)
            timeline = reconstruct_timeline(history["events"])
            evidence_ids = {record["claim_id"] for record in history["evidence"]}
            self.assertTrue(all(set(event["claim_ids"]) <= evidence_ids for event in timeline))
            self.assertEqual([e["event_type"] for e in timeline], ["application_deadline", "assessment", "result_pending"])
            self.assertEqual(timeline[1]["end"], "2026-06-21")
            self.assertIsNone(timeline[-1]["start"])
            audit = audit_evidence(history["evidence"], datetime.fromisoformat(history["audit_at"]))
            self.assertEqual(audit["errors"], [])
            candidate = copy.deepcopy(history["candidate"])
            candidate["evidence_confidence"] = audit["candidate_summary"][candidate["candidate_id"]]["confidence"]
            current_claims = {c["record"]["field"]: c for c in audit["claims"]
                              if c["record"]["applicable_admission_year"] == 2027}
            for gate in candidate["gates"]:
                gate["evidence_status"] = current_claims[gate["gate_id"]]["effective_status"]
            scoring = score_candidate(candidate, history["weights"])
            outlook = assess_admission_outlook({
                "candidate_id": candidate["candidate_id"], "admission_year": 2027,
                "target_scope": history["selected_scope"],
                "eligibility_result": evaluate_gates(candidate["gates"]),
                "material_audit": material, "candidate_scoring": scoring,
                "historical_metrics": metrics, "fit_result": history["fit_result"],
                "evidence_audit": audit,
            })
            self.assertEqual(outlook["eligibility"], "pass")
            self.assertEqual(outlook["packet_readiness"], "repairable")
            self.assertEqual(outlook["competitive_position"], "evidence_insufficient")
            self.assertEqual(outlook["evidence_confidence"], "D")
            self.assertIn("critical_applicant_conflict:gpa", outlook["uncertainties"])
            self.assertIn("no_comparable_cohort", outlook["uncertainties"])
            self.assertTrue(outlook["historical_context"]["descriptive_only"])
            self.assertNotIn("probability", json.dumps(outlook).lower())

            generated = json.dumps({"claims": claims, "audit": material, "outlook": outlook}, ensure_ascii=False)
            generated += "\n" + history["synthetic_sensitive_text"]
            redacted_report, findings = redact_text(generated)
            self.assertNotIn("13800138000", redacted_report)
            self.assertNotIn("synthetic.student@example.com", redacted_report)
            self.assertNotIn("000000000000000000", redacted_report)
            self.assertNotIn("SYNTHETIC2027001", redacted_report)
            self.assertNotIn("Fictional Signer", redacted_report)
            self.assertEqual({f["type"] for f in findings}, {"phone", "email", "identity", "student_number", "signature"})
            self.assertTrue(all(set(f) == {"type", "count", "review_required", "possible_over_redaction"} for f in findings))
            self.assertNotIn("13800138000", json.dumps(findings))
            case = root / "case"
            case.mkdir()
            atomic_write_json(case / "historical-cycle.json", {"events": timeline, "metrics": metrics})
            self.assertEqual(load_json(case / "historical-cycle.json")["metrics"]["rejected"][0]["reason"], "scope_mismatch")
            self.assertEqual([path.read_bytes() for path in paths], originals)
        self.assertEqual((documents, claims, requirements, history), before)


if __name__ == "__main__":
    unittest.main()
