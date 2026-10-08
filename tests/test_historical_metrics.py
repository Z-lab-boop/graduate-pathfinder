import copy
import json
import unittest

from scripts.calculate_historical_metrics import (
    calculate_stage_metrics, reconstruct_timeline, scope_key,
)


SCOPE = dict(admission_year=2026, institution="Synthetic University", unit="Engineering",
             program_code="081200", degree_type="academic", research_track="AI",
             admission_round="summer_camp")


def record(**updates):
    return {**SCOPE, "claim_ids": ["synthetic-claim"], **updates}


class HistoricalMetricsTests(unittest.TestCase):
    def test_scope_is_exact_and_requires_complete_identity(self):
        self.assertEqual(scope_key(record()), (2026, "Synthetic University", "Engineering",
                                              "081200", "academic", "AI", "summer_camp"))
        for field in SCOPE:
            row = record()
            row.pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                scope_key(row)

    def test_timeline_orders_chronologically_preserves_range_timezone_and_unknown(self):
        rows = [record(event_type="unknown", start=None, end=None, timezone=None),
                record(event_type="camp", start="2025-07-02T09:00:00+08:00",
                       end="2025-07-04T17:00:00+08:00", timezone="Asia/Shanghai"),
                record(event_type="apply", start="2025-06-01", end=None, timezone=None)]
        before = copy.deepcopy(rows)
        result = reconstruct_timeline(rows)
        self.assertEqual([row["event_type"] for row in result], ["apply", "camp", "unknown"])
        self.assertEqual(result[1]["end"], "2025-07-04T17:00:00+08:00")
        self.assertEqual(result[1]["timezone"], "Asia/Shanghai")
        self.assertIsNone(result[2]["start"])
        self.assertEqual(rows, before)

    def test_timeline_keeps_rounds_separate_and_compares_aware_instants(self):
        rows = [record(event_type="later", start="2025-07-01T09:00:00+08:00"),
                record(event_type="other", start="2025-01-01", admission_round="pre_recommendation"),
                record(event_type="earlier", start="2025-07-01T00:30:00Z")]
        result = reconstruct_timeline(rows)
        self.assertEqual([row["event_type"] for row in result], ["earlier", "later", "other"])
        # Scope groups follow first appearance; actual instants order within each group.
        self.assertEqual(result[0]["event_type"], "earlier")

    def test_timeline_rejects_offset_component_overflow_in_either_boundary(self):
        for offset in ("+08:99", "-08:60", "+24:00", "+08:30:60", "+0899", "-0860",
                       "+2400", "+083060", "+08:99:00.5"):
            for boundary in ("start", "end"):
                with self.subTest(offset=offset, boundary=boundary), self.assertRaises(ValueError):
                    reconstruct_timeline([record(event_type="camp", **{
                        boundary: "2025-07-01T09:00:00" + offset})])

    def test_timeline_preserves_supported_iso_precision_offsets_and_ordering(self):
        timestamps = ["2025-07-01T09:00:00+08:00", "2025-07-01T09:00+08",
                      "2025-07-01T090000+0800", "2025-07-01T09:00:00+08:00:30.5",
                      "2025-07-01T090000+080030.5", "2025-07-01T09:00:00.5",
                      "2025-07-01T00:00:00Z", "2025-07-01"]
        result = reconstruct_timeline([record(event_type=str(index), start=value)
                                       for index, value in enumerate(timestamps)])
        self.assertEqual([row["event_type"] for row in result], ["7", "6", "3", "4", "0", "1", "2", "5"])
        self.assertEqual({row["start"] for row in result}, set(timestamps))

    def test_same_scope_ratio_preserves_evidence_and_aggregate_counts(self):
        result = calculate_stage_metrics([
            record(stage="confirmed_attended", count=80, claim_ids=["attendance"]),
            record(stage="final_admitted", count=20, claim_ids=["admit"])])
        group = result["scopes"][0]
        metric = group["metrics"][0]
        self.assertEqual(metric["value"], 0.25)
        self.assertEqual(metric["claim_ids"], ["admit", "attendance"])
        self.assertEqual(metric["scope"], SCOPE)
        self.assertEqual(group["counts"][0]["count"], 80)
        self.assertEqual(result["rejected"], [])

    def test_every_scope_difference_blocks_ratio(self):
        for field, value in dict(admission_year=2025, institution="Other", unit="Other",
                                program_code="085400", degree_type="professional",
                                research_track="systems", admission_round="pre_recommendation").items():
            with self.subTest(field=field):
                result = calculate_stage_metrics([
                    record(stage="final_admitted", count=20),
                    record(stage="confirmed_attended", count=80, **{field: value})])
                self.assertFalse(any(group["metrics"] for group in result["scopes"]))
                self.assertIn("scope_mismatch", [r["reason"] for r in result["rejected"]])

    def test_listed_names_do_not_become_attendance(self):
        result = calculate_stage_metrics([record(stage="listed_shortlist", count=120),
                                          record(stage="final_admitted", count=20)])
        group = result["scopes"][0]
        self.assertEqual(group["counts"][0]["stage"], "listed_shortlist")
        self.assertEqual(group["counts"][0]["count"], 120)
        self.assertEqual(group["metrics"], [])
        self.assertEqual(group["rejected"][0]["reason"], "attendance_unconfirmed")

    def test_invalid_zero_missing_and_duplicate_counts_are_rejected(self):
        for value, expected in [(-1, "invalid_count"), (True, "invalid_count"),
                                (2.5, "invalid_count"), ("80", "invalid_count"),
                                (0, "zero_denominator")]:
            with self.subTest(value=value):
                result = calculate_stage_metrics([record(stage="confirmed_attended", count=value),
                                                  record(stage="final_admitted", count=20)])
                self.assertEqual(result["scopes"][0]["metrics"], [])
                self.assertIn(expected, [r["reason"] for r in result["rejected"]])
        result = calculate_stage_metrics([record(stage="final_admitted", count=20)])
        self.assertEqual(result["rejected"][0]["reason"], "missing_denominator")
        result = calculate_stage_metrics([record(stage="confirmed_attended", count=80),
                                          record(stage="confirmed_attended", count=90),
                                          record(stage="final_admitted", count=20)])
        self.assertEqual(result["scopes"][0]["metrics"], [])
        self.assertEqual(result["rejected"][0]["reason"], "ambiguous_stage_count")

    def test_missing_evidence_unknown_stages_and_private_fields_are_rejected(self):
        for changes in ({"claim_ids": []}, {"stage": "attendees"},
                        {"names": ["Synthetic Name"]}, {"student_id": "synthetic"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                calculate_stage_metrics([record(**{"stage": "confirmed_attended", "count": 80, **changes})])
        with self.assertRaises(ValueError):
            reconstruct_timeline([record(event_type="camp", names=["Synthetic Name"])])

    def test_output_does_not_echo_extra_input_fields(self):
        result = calculate_stage_metrics([record(stage="announced_quota", count=20,
                                                unrelated_payload={"names": ["private"]})])
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(calculate_stage_metrics([]), {"scopes": [], "rejected": []})
        self.assertEqual(reconstruct_timeline([]), [])

    def test_malformed_dates_reversed_ranges_and_private_metadata_fail_closed(self):
        for changes in ({"start": "July"}, {"start": "2025-02-30"},
                        {"start": "2025-07-03", "end": "2025-07-01"},
                        {"method_notes": {"names": ["private"]}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                reconstruct_timeline([record(event_type="camp", **changes)])

    def test_conflicting_non_ratio_stage_counts_are_preserved_and_rejected(self):
        result = calculate_stage_metrics([record(stage="announced_quota", count=20, claim_ids=["q1"]),
                                          record(stage="announced_quota", count=30, claim_ids=["q2"])])
        self.assertEqual([row["count"] for row in result["scopes"][0]["counts"]], [20, 30])
        self.assertEqual(result["rejected"][0]["reason"], "ambiguous_stage_count")
        self.assertEqual(result["rejected"][0]["claim_ids"], ["q1", "q2"])

    def test_private_structured_values_cannot_escape_allowlisted_fields(self):
        for changes in ({"count": {"names": ["private"]}}, {"stage": ["private"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                calculate_stage_metrics([record(**{"stage": "announced_quota", "count": 2, **changes})])
        with self.assertRaises(ValueError):
            reconstruct_timeline([record(event_type="camp", date_text={"student_id": "private"})])

    def test_scope_mismatch_rejection_cites_both_scopes(self):
        result = calculate_stage_metrics([
            record(stage="final_admitted", count=20, claim_ids=["admit"]),
            record(stage="confirmed_attended", count=80, admission_year=2025, claim_ids=["other-year"])])
        self.assertEqual(result["rejected"][0]["claim_ids"], ["admit", "other-year"])


if __name__ == "__main__":
    unittest.main()
