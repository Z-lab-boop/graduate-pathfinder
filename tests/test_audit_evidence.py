import copy
from datetime import datetime
import unittest

from scripts.audit_evidence import audit_evidence
from tests.test_validate_case import evidence


class EvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.fromisoformat("2027-05-03T10:00:00+08:00")
        self.candidate = evidence()["candidate_id"]
        self.records = []
        for field, value in (("eligibility", "pass"), ("deadline", "2027-06-15"),
                             ("program_availability", True), ("degree_type", "academic-master")):
            item = evidence()
            item.update(claim_id=field, field=field, value=value)
            self.records.append(item)

    def summary(self, records=None, **kwargs):
        return audit_evidence(self.records if records is None else records,
                              self.now, **kwargs)["candidate_summary"][self.candidate]

    def test_fresh_t1_and_t2_critical_coverage_confirms_a(self):
        self.records[0]["tier"] = "T2"
        report = audit_evidence(self.records, self.now)
        self.assertEqual(report["candidate_summary"][self.candidate]["confidence"], "A")
        self.assertEqual(report["claims"][0]["effective_status"], "confirmed")
        self.assertEqual(report["errors"], [])

    def test_secondary_only_support_downgrades_to_c(self):
        for item in self.records:
            item.update(tier="T3", status="secondary_only")
        summary = self.summary()
        self.assertEqual(summary["confidence"], "C")
        self.assertEqual(summary["critical_fields"]["deadline"]["strongest_usable_tier"], "T3")

    def test_stale_official_support_downgrades_to_b(self):
        self.records[1]["retrieved_at"] = "2026-05-02T10:00:00+08:00"
        report = audit_evidence(self.records, self.now)
        self.assertEqual(report["claims"][1]["effective_status"], "stale")
        self.assertEqual(report["candidate_summary"][self.candidate]["confidence"], "B")

    def test_conflicted_critical_claim_forces_confidence_d(self):
        self.records[1]["conflict_group"] = "deadline-2027"
        other = copy.deepcopy(self.records[1])
        other.update(claim_id="deadline-other", value="2027-06-20", tier="T3")
        report = audit_evidence(self.records + [other], self.now)
        self.assertEqual(report["candidate_summary"][self.candidate]["confidence"], "D")
        self.assertIn("deadline-2027", report["conflicts"])
        self.assertEqual(report["conflicts"]["deadline-2027"]["values"],
                         ["2027-06-15", "2027-06-20"])
        self.assertEqual(len(report["claims"]), 5)

    def test_absent_critical_claim_forces_d_with_cause(self):
        summary = self.summary(self.records[1:])
        self.assertEqual(summary["confidence"], "D")
        self.assertEqual(summary["missing_critical_fields"], ["eligibility"])

    def test_explicit_missing_or_conflicted_critical_claim_forces_d(self):
        for status in ("missing", "conflicted"):
            with self.subTest(status=status):
                records = copy.deepcopy(self.records)
                records[0]["status"] = status
                self.assertEqual(self.summary(records)["confidence"], "D")

    def test_preserves_records_without_mutating_inputs_and_prefers_official(self):
        secondary = copy.deepcopy(self.records[1])
        secondary.update(claim_id="secondary", tier="T4", status="secondary_only")
        records = self.records + [secondary]
        before = copy.deepcopy(records)
        report = audit_evidence(records, self.now)
        self.assertEqual(records, before)
        self.assertEqual([claim["record"] for claim in report["claims"]], records)
        self.assertEqual(report["candidate_summary"][self.candidate]["critical_fields"]["deadline"]
                         ["strongest_usable_tier"], "T1")
        report["claims"][0]["record"]["value"] = "changed"
        self.assertEqual(records, before)

    def test_freshness_boundary_and_not_applicable_exception(self):
        self.records[0]["retrieved_at"] = "2026-05-03T23:59:59+08:00"
        self.assertEqual(self.summary()["confidence"], "A")
        self.records[0]["status"] = "not_applicable"
        self.records[0]["retrieved_at"] = "2020-01-01T00:00:00Z"
        report = audit_evidence(self.records, self.now, stale_after_days=1)
        self.assertEqual(report["claims"][0]["effective_status"], "not_applicable")
        self.assertFalse(report["claims"][0]["stale"])

    def test_unrelated_candidates_and_noncritical_conflicts_are_isolated(self):
        extra = copy.deepcopy(self.records[0])
        extra.update(candidate_id="other", claim_id="other", field="notes", status="conflicted")
        report = audit_evidence(self.records + [extra], self.now)
        self.assertEqual(report["candidate_summary"][self.candidate]["confidence"], "A")
        self.assertEqual(report["candidate_summary"]["other"]["confidence"], "D")

    def test_invalid_record_returns_validator_errors_and_preserves_record(self):
        bad = evidence()
        bad["tier"] = "T9"
        report = audit_evidence(self.records + [bad], self.now)
        self.assertEqual(report["errors"][0]["record_index"], 4)
        self.assertIn("tier must be one of T1, T2, T3, T4", report["errors"][0]["errors"])
        self.assertEqual(report["claims"][4]["record"], bad)
        self.assertEqual(report["candidate_summary"][self.candidate]["confidence"], "D")

    def test_empty_records_returns_empty_report(self):
        self.assertEqual(audit_evidence([], self.now),
                         {"claims": [], "candidate_summary": {}, "conflicts": {}, "errors": []})

    def test_stale_strongest_t1_stays_b_despite_fresh_t2(self):
        self.records[1]["retrieved_at"] = "2020-01-01T00:00:00Z"
        fresh = copy.deepcopy(self.records[1])
        fresh.update(claim_id="fresh-copy", tier="T2", retrieved_at="2027-05-02T10:00:00+08:00")
        summary = self.summary(self.records + [fresh])
        self.assertEqual(summary["confidence"], "B")
        self.assertEqual(summary["critical_fields"]["deadline"]["strongest_usable_tier"], "T1")
        self.assertEqual(summary["critical_fields"]["deadline"]["fresh_official_record_indexes"], [4])

    def test_null_critical_value_is_missing_without_not_applicable(self):
        self.records[1]["value"] = None
        report = audit_evidence(self.records, self.now)
        summary = report["candidate_summary"][self.candidate]
        self.assertEqual(summary["confidence"], "D")
        self.assertTrue(summary["critical_fields"]["deadline"]["missing"])
        self.assertEqual(summary["critical_fields"]["deadline"]["usable_record_indexes"], [])
        self.assertIsNone(report["claims"][1]["record"]["value"])

    def test_null_not_applicable_value_keeps_justified_coverage(self):
        self.records[1].update(value=None, status="not_applicable")
        self.assertEqual(self.summary()["confidence"], "A")

    def test_secondary_band_takes_precedence_over_stale_official_band(self):
        self.records[0]["tier"] = "T4"
        self.records[1]["status"] = "stale"
        summary = self.summary()
        self.assertEqual(summary["confidence"], "C")
        self.assertEqual(summary["stale_official_fields"], ["deadline"])
        self.assertEqual(summary["secondary_only_fields"], ["eligibility"])

    def test_identical_values_do_not_create_a_conflict(self):
        self.records[1]["conflict_group"] = "deadline-2027"
        duplicate = copy.deepcopy(self.records[1])
        duplicate["claim_id"] = "duplicate"
        report = audit_evidence(self.records + [duplicate], self.now)
        self.assertEqual(report["conflicts"], {})
        self.assertEqual(report["candidate_summary"][self.candidate]["confidence"], "A")

    def test_explicit_stale_status_does_not_reset_after_recent_retrieval(self):
        self.records[0]["status"] = "stale"
        self.assertEqual(self.summary()["confidence"], "B")

    def test_invalid_freshness_parameter_is_rejected(self):
        for value in (-1, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    audit_evidence(self.records, self.now, stale_after_days=value)


if __name__ == "__main__":
    unittest.main()
