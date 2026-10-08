"""Synthetic integration fixtures exercise real upstream audit/scoring outputs."""
import copy
from datetime import datetime
import math
import unittest

from scripts.assess_admission_outlook import assess_admission_outlook
from scripts.audit_evidence import audit_evidence
from scripts.audit_materials import audit_materials
from scripts.calculate_historical_metrics import calculate_stage_metrics
from scripts.rank_candidates import evaluate_gates, score_candidate
from tests.test_validate_case import evidence


TARGET = "synthetic-target"
SCOPE = dict(admission_year=2026, institution="Synthetic University", unit="Engineering",
             program_code="081200", degree_type="academic", research_track="AI",
             admission_round="summer_camp")
NOW = datetime.fromisoformat("2027-05-03T10:00:00+08:00")
DOC = "sha256:" + "a" * 64


def source(claim_id, field, value, year=2027, **updates):
    return {**evidence(), "candidate_id": TARGET, "claim_id": claim_id,
            "field": field, "value": value, "applicable_admission_year": year, **updates}


def packet(position=90, history_tier="T1", gate="pass", signature=True):
    records = [source(field, field, value) for field, value in
               (("eligibility", "pass"), ("deadline", "2027-06-15"),
                ("program_availability", True), ("degree_type", "academic"))]
    letter_policy = {"requirement_id": "letter", "target_id": TARGET,
                     "item_type": "recommendation", "necessity": "required",
                     "conditions": {"signature": True}}
    records += [source("letter-policy", "material_requirement_policy", letter_policy),
                source("attendance", "historical_count",
                       {**SCOPE, "stage": "confirmed_attended", "count": 80}, 2026, tier=history_tier),
                source("admitted", "historical_count",
                       {**SCOPE, "stage": "final_admitted", "count": 20}, 2026, tier=history_tier)]
    gates = [{"gate_id": "language", "status": gate, "critical": True,
              "evidence_status": "confirmed" if gate != "unknown" else "missing"}]
    candidate = {"candidate_id": TARGET, "gates": gates,
                 "dimensions": {"competitive_position": position, "research_fit": 95},
                 "evidence_confidence": "A", "data_completeness": 1}
    manifest = [{"document_id": DOC, "document_class": "recommendation",
                 "extraction_state": "reviewed"}]
    claims = [{"claim_id": "signed", "field": "signature", "value": signature,
               "state": "document_verified", "source_document_ids": [DOC], "scope": "document"}]
    requirements = [{"requirement_id": "letter", "target_id": TARGET,
                     "item_type": "recommendation", "necessity": "required",
                     "conditions": {"signature": True}, "source_claim_ids": ["letter-policy"]}]
    counts = [{**SCOPE, "stage": stage, "count": count, "claim_ids": [claim_id],
               "evidence_tier": history_tier} for stage, count, claim_id in
              (("confirmed_attended", 80, "attendance"), ("final_admitted", 20, "admitted"))]
    return {"candidate_id": TARGET, "admission_year": 2027, "target_scope": SCOPE.copy(),
            "eligibility_result": evaluate_gates(gates),
            "material_audit": audit_materials(manifest, claims, requirements),
            "candidate_scoring": score_candidate(candidate, {"competitive_position": 1, "research_fit": 1}),
            "historical_metrics": calculate_stage_metrics(counts),
            "fit_result": {"score": 95.0, "reasons": ["Synthetic research alignment"]},
            "evidence_audit": audit_evidence(records, NOW), "critical_applicant_fields": ["gpa", "ranking"]}


class AdmissionOutlookTests(unittest.TestCase):
    def test_strong_packet_returns_five_independent_results_and_context(self):
        payload = packet()
        self.assertEqual(payload["material_audit"]["items_by_target"][TARGET][0]["policy_binding"],
                         {"requirement_id": "letter", "target_id": TARGET,
                          "item_type": "recommendation", "necessity": "required",
                          "conditions": {"signature": True}})
        result = assess_admission_outlook(payload)
        self.assertEqual(set(result), {"eligibility", "packet_readiness", "competitive_position",
                                      "program_fit", "evidence_confidence", "historical_context",
                                      "uncertainties", "band_change_conditions"})
        self.assertEqual(result["eligibility"], "pass")
        self.assertEqual(result["packet_readiness"], "complete")
        self.assertEqual(result["competitive_position"], "strong")
        self.assertEqual(result["program_fit"], {"score": 95.0, "reasons": ["Synthetic research alignment"]})
        self.assertEqual(result["evidence_confidence"], "A")
        self.assertEqual(result["historical_context"]["scopes"][0]["metrics"][0]["value"], 0.25)
        self.assertTrue(result["historical_context"]["descriptive_only"])
        self.assertEqual(result["band_change_conditions"], [])

    def test_confirmed_failure_is_preserved_without_collapsing_other_results(self):
        result = assess_admission_outlook(packet(gate="fail"))
        self.assertEqual(result["eligibility"], "fail")
        self.assertEqual(result["competitive_position"], "strong")
        self.assertEqual(result["packet_readiness"], "complete")
        self.assertEqual(result["evidence_confidence"], "A")

    def test_complete_packet_without_cohort_is_evidence_insufficient(self):
        payload = packet()
        payload["historical_metrics"] = calculate_stage_metrics([])
        result = assess_admission_outlook(payload)
        self.assertEqual(result["packet_readiness"], "complete")
        self.assertEqual(result["eligibility"], "pass")
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertEqual(result["evidence_confidence"], "D")
        self.assertIn("no_comparable_cohort", result["uncertainties"])

    def test_transcript_resume_critical_conflict_withholds_position(self):
        payload = packet()
        payload["material_audit"] = audit_materials(
            [{"document_id": DOC, "document_class": "transcript", "extraction_state": "reviewed"},
             {"document_id": "resume", "document_class": "resume", "extraction_state": "reviewed"}],
            [{"claim_id": "transcript-gpa", "field": "gpa", "value": 3.4,
              "state": "document_verified", "source_document_ids": [DOC]},
             {"claim_id": "resume-gpa", "field": "gpa", "value": 3.8,
              "state": "user_asserted", "source_document_ids": ["resume"]}], [])
        result = assess_admission_outlook(payload)
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertEqual(result["evidence_confidence"], "D")
        self.assertIn("critical_applicant_conflict:gpa", result["uncertainties"])
        conflicts = [c for c in result["band_change_conditions"] if c["kind"] == "applicant_conflict"]
        self.assertEqual(conflicts[0]["claim_ids"], ["transcript-gpa", "resume-gpa"])

    def test_low_tier_only_history_cannot_establish_comparable_cohort(self):
        result = assess_admission_outlook(packet(history_tier="T4"))
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertEqual(result["evidence_confidence"], "C")
        self.assertIn("historical_evidence_unusable", result["uncertainties"])
        self.assertEqual(result["historical_context"]["scopes"][0]["metrics"][0]["value"], 0.25)

    def test_current_policy_missing_stale_secondary_conflicted_or_wrong_year_blocks_position(self):
        for changes, confidence in (({"status": "missing"}, "D"),
                                    ({"status": "stale"}, "B"),
                                    ({"tier": "T3"}, "C"),
                                    ({"status": "conflicted"}, "D"),
                                    ({"applicable_admission_year": 2026}, "D")):
            with self.subTest(changes=changes):
                payload = packet()
                records = [copy.deepcopy(c["record"]) for c in payload["evidence_audit"]["claims"]]
                records[4].update(changes)
                payload["evidence_audit"] = audit_evidence(records, NOW)
                result = assess_admission_outlook(payload)
                self.assertEqual(result["competitive_position"], "evidence_insufficient")
                self.assertEqual(result["evidence_confidence"], confidence)
                self.assertIn("current_target_evidence_unusable:letter-policy", result["uncertainties"])

    def test_target_critical_evidence_absence_blocks_even_with_complete_material_policy(self):
        payload = packet()
        records = [c["record"] for c in payload["evidence_audit"]["claims"] if c["record"]["field"] != "eligibility"]
        payload["evidence_audit"] = audit_evidence(records, NOW)
        result = assess_admission_outlook(payload)
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertEqual(result["evidence_confidence"], "D")

    def test_competitive_dimension_has_transparent_ordinal_boundaries(self):
        for score, expected in ((0, "weak"), (39.9, "weak"), (40, "borderline"),
                                (59.9, "borderline"), (60, "competitive"),
                                (79.9, "competitive"), (80, "strong"), (100, "strong")):
            with self.subTest(score=score):
                self.assertEqual(assess_admission_outlook(packet(score))["competitive_position"], expected)

    def test_fit_weighted_score_and_rate_never_upgrade_competitive_dimension(self):
        payload = packet(20)
        payload["candidate_scoring"]["weighted_score"] = 99
        payload["historical_metrics"]["scopes"][0]["metrics"][0]["value"] = 0.99
        payload["fit_result"]["score"] = 100
        self.assertEqual(assess_admission_outlook(payload)["competitive_position"], "weak")

    def test_missing_competitive_dimension_is_not_zero(self):
        payload = packet()
        payload["candidate_scoring"]["grouping_inputs"].pop("competitive_position")
        result = assess_admission_outlook(payload)
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertIn("competitive_position_missing", result["uncertainties"])

    def test_scoped_history_does_not_borrow_other_program_or_round(self):
        for field, value in (("program_code", "085400"), ("admission_round", "pre_recommendation"),
                             ("admission_year", 2025), ("degree_type", "professional")):
            with self.subTest(field=field):
                payload = packet()
                payload["target_scope"][field] = value
                result = assess_admission_outlook(payload)
                self.assertEqual(result["competitive_position"], "evidence_insufficient")
                self.assertEqual(result["historical_context"]["scopes"], [])

    def test_history_claim_ids_must_resolve_to_matching_candidate_and_cycle(self):
        for changes in ({"candidate_id": "other"}, {"applicable_admission_year": 2025}):
            with self.subTest(changes=changes):
                payload = packet()
                records = [copy.deepcopy(c["record"]) for c in payload["evidence_audit"]["claims"]]
                records[5].update(changes)
                payload["evidence_audit"] = audit_evidence(records, NOW)
                self.assertEqual(assess_admission_outlook(payload)["competitive_position"], "evidence_insufficient")

    def test_missing_attendance_denominator_returns_specific_factual_gate(self):
        payload = packet()
        payload["historical_metrics"] = calculate_stage_metrics([
            {**SCOPE, "stage": "listed_shortlist", "count": 120, "claim_ids": ["shortlist"]},
            {**SCOPE, "stage": "final_admitted", "count": 20, "claim_ids": ["admitted"]}])
        result = assess_admission_outlook(payload)
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertEqual(result["band_change_conditions"][0]["field"], "confirmed_attended")

    def test_required_readiness_precedence_and_optional_isolation(self):
        payload = packet()
        base = payload["material_audit"]["items_by_target"][TARGET][0]
        for status, expected in (("repairable", "repairable"),
                                 ("materially_incomplete", "materially_incomplete"),
                                 ("unreadable", "unreadable")):
            with self.subTest(status=status):
                payload["material_audit"]["items_by_target"][TARGET] = [base, {**base, "status": status}]
                self.assertEqual(assess_admission_outlook(payload)["packet_readiness"], expected)
        payload["material_audit"]["items_by_target"][TARGET] = [
            base, {**base, "status": "unreadable", "necessity": "optional", "blocking": False}]
        self.assertEqual(assess_admission_outlook(payload)["packet_readiness"], "complete")
        payload["material_audit"]["items_by_target"]["other"] = [{**base, "status": "unreadable", "target_id": "other"}]
        self.assertEqual(assess_admission_outlook(payload)["packet_readiness"], "complete")

    def test_unsigned_required_recommendation_is_specific_unresolved_condition(self):
        result = assess_admission_outlook(packet(signature=False))
        self.assertEqual(result["packet_readiness"], "repairable")
        self.assertEqual(result["competitive_position"], "strong")
        self.assertEqual(result["band_change_conditions"], [
            {"kind": "material_condition", "field": "signature", "requirement_id": "letter",
             "claim_ids": ["letter-policy"]}])

    def test_recommendation_cannot_borrow_eligibility_policy_claim(self):
        payload = packet()
        manifest = [{"document_id": DOC, "document_class": "recommendation",
                     "extraction_state": "reviewed"}]
        claims = [{"claim_id": "signed", "field": "signature", "value": True,
                   "state": "document_verified", "source_document_ids": [DOC], "scope": "document"}]
        requirements = [{"requirement_id": "letter", "target_id": TARGET,
                         "item_type": "recommendation", "necessity": "required",
                         "conditions": {"signature": True}, "source_claim_ids": ["eligibility"]}]
        payload["material_audit"] = audit_materials(manifest, claims, requirements)
        result = assess_admission_outlook(payload)
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertIn("requirement_policy_unbound:letter", result["uncertainties"])
        policy_conditions = [c for c in result["band_change_conditions"]
                             if c["kind"] == "requirement_policy"]
        self.assertEqual(policy_conditions[0]["claim_ids"], ["eligibility"])

    def test_current_year_audited_gpa_conflict_withholds_position(self):
        payload = packet()
        records = [copy.deepcopy(c["record"]) for c in payload["evidence_audit"]["claims"]]
        records += [source("gpa-transcript", "gpa", 3.4, conflict_group="gpa-current"),
                    source("gpa-resume", "gpa", 3.8, conflict_group="gpa-current")]
        payload["evidence_audit"] = audit_evidence(records, NOW)
        result = assess_admission_outlook(payload)
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertIn("critical_applicant_conflict:gpa", result["uncertainties"])
        conflicts = [c for c in result["band_change_conditions"]
                     if c["kind"] == "applicant_conflict" and c["field"] == "gpa"]
        self.assertEqual(conflicts[0]["claim_ids"], ["gpa-transcript", "gpa-resume"])

    def test_unknown_eligibility_returns_gate_without_erasing_competitive_position(self):
        result = assess_admission_outlook(packet(gate="unknown"))
        self.assertEqual(result["eligibility"], "unknown")
        self.assertEqual(result["competitive_position"], "strong")
        self.assertEqual(result["evidence_confidence"], "D")
        self.assertIn({"kind": "eligibility_gate", "field": "language", "claim_ids": []},
                      result["band_change_conditions"])

    def test_low_candidate_confidence_cannot_be_upgraded_by_other_dimensions(self):
        payload = packet()
        payload["candidate_scoring"]["evidence_confidence"] = "C"
        result = assess_admission_outlook(payload)
        self.assertEqual(result["evidence_confidence"], "C")
        self.assertIn("candidate_scoring_confidence:C", result["uncertainties"])

    def test_missing_target_material_policy_cannot_support_a_position(self):
        payload = packet()
        payload["material_audit"] = audit_materials([], [], [])
        result = assess_admission_outlook(payload)
        self.assertEqual(result["packet_readiness"], "materially_incomplete")
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertEqual(result["evidence_confidence"], "D")

    def test_duplicate_audit_id_with_conflicting_records_cannot_confirm_policy(self):
        payload = packet()
        records = [copy.deepcopy(c["record"]) for c in payload["evidence_audit"]["claims"]]
        records.append({**records[4], "value": {"signature": False}})
        payload["evidence_audit"] = audit_evidence(records, NOW)
        result = assess_admission_outlook(payload)
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertEqual(result["evidence_confidence"], "D")

    def test_official_not_applicable_null_critical_value_remains_usable(self):
        payload = packet()
        records = [copy.deepcopy(c["record"]) for c in payload["evidence_audit"]["claims"]]
        records[1].update(status="not_applicable", value=None)
        payload["evidence_audit"] = audit_evidence(records, NOW)
        result = assess_admission_outlook(payload)
        self.assertEqual(result["competitive_position"], "strong")
        self.assertEqual(result["evidence_confidence"], "A")

    def test_historical_counts_cannot_relabel_an_unrelated_or_different_value_claim(self):
        for changes in ({"field": "deadline"}, {"value": 120},
                        {"value": {**SCOPE, "stage": "confirmed_attended", "count": 80,
                                   "program_code": "085400"}}):
            with self.subTest(changes=changes):
                payload = packet()
                records = [copy.deepcopy(c["record"]) for c in payload["evidence_audit"]["claims"]]
                records[5].update(changes)
                payload["evidence_audit"] = audit_evidence(records, NOW)
                result = assess_admission_outlook(payload)
                self.assertEqual(result["competitive_position"], "evidence_insufficient")
                self.assertIn("historical_evidence_payload_mismatch", result["uncertainties"])

    def test_historical_count_evidence_can_bind_the_full_scoped_aggregate(self):
        payload = packet()
        records = [copy.deepcopy(c["record"]) for c in payload["evidence_audit"]["claims"]]
        records[5]["value"] = {**SCOPE, "stage": "confirmed_attended", "count": 80}
        records[6]["value"] = {**SCOPE, "stage": "final_admitted", "count": 20}
        payload["evidence_audit"] = audit_evidence(records, NOW)
        self.assertEqual(assess_admission_outlook(payload)["competitive_position"], "strong")

    def test_no_probability_keys_or_private_extras_escape_and_inputs_are_immutable(self):
        payload = packet()
        payload["historical_metrics"]["scopes"][0]["personal_probability"] = 0.9
        payload["historical_metrics"]["scopes"][0]["counts"][0]["names"] = ["Private Name"]
        payload["fit_result"]["probability"] = 0.9
        before = copy.deepcopy(payload)
        result = assess_admission_outlook(payload)
        self.assertEqual(payload, before)

        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn("probability", key.lower())
                    keys(child)
            elif isinstance(value, list):
                for child in value:
                    keys(child)
        keys(result)
        self.assertNotIn("Private Name", str(result))
        result["program_fit"]["reasons"].append("changed")
        self.assertEqual(payload, before)

    def test_empty_payload_fails_conservatively_and_invalid_scores_rejected(self):
        result = assess_admission_outlook({})
        self.assertEqual(result["eligibility"], "unknown")
        self.assertEqual(result["packet_readiness"], "materially_incomplete")
        self.assertEqual(result["competitive_position"], "evidence_insufficient")
        self.assertEqual(result["evidence_confidence"], "D")
        for value in (True, -1, 101, math.nan, math.inf, "90"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                payload = packet()
                payload["candidate_scoring"]["grouping_inputs"]["competitive_position"] = value
                assess_admission_outlook(payload)


if __name__ == "__main__":
    unittest.main()
