"""Synthetic contract tests; numbers do not describe actual admissions."""
from copy import deepcopy
import unittest

from scripts.assess_kaoyan import (
    classify_threshold, compare_score_scenario, validate_subject_match,
)


def evidence(value, year=2026, claim_id="subjects"):
    return {"claim_id": claim_id, "candidate_id": "synthetic", "field": "subjects",
            "value": value, "source_url": "https://example.invalid/official",
            "source_title": "Synthetic official record", "publisher": "Synthetic unit",
            "short_evidence": "Synthetic premise", "published_at": "2026-01-01",
            "retrieved_at": "2026-10-01T10:00:00+08:00", "tier": "T1",
            "status": "confirmed", "scope": "program", "conflict_group": None,
            "applicable_admission_year": year}


def combination(codes):
    return {"codes": codes, "evidence": [evidence(codes)]}


def inputs():
    codes = ["101", "201", "301", "408"]
    profile = {"pathway": "kaoyan", "admission_year": 2026,
               "audit_at": "2026-10-08T10:00:00+08:00", "preferences": {},
               "subject_combination": combination(codes),
               "score_scenario": {"year": 2026, "scope": "program",
                                  "population": "ordinary applicants", "total": [310, 330],
                                  "subjects": {"101": [50, 60], "201": [50, 60],
                                               "301": [100, 110], "408": [100, 110]}}}
    record = {"year": 2026, "scope": "program", "total": 300,
              "source_ref": "line", "population": "ordinary applicants",
              "program_code": "085400", "subject_minimums": {"101": 40, "201": 40},
              "institution": "Synthetic U", "unit": "Synthetic Unit",
              }
    record["evidence"] = evidence(deepcopy(record), claim_id="line")
    candidate = {"candidate_id": "synthetic", "pathway": "kaoyan", "admission_year": 2026,
                 "institution": "Synthetic U", "unit": "Synthetic Unit",
                 "program_code": "085400", "subject_combination": combination(codes),
                 "thresholds": [record]}
    return profile, candidate


class SubjectTests(unittest.TestCase):
    def test_exact_normalized_codes_match(self):
        p, c = inputs()
        p["subject_combination"] = combination([" 101 ", "２０１", "301", "408"])
        result = validate_subject_match(p, c)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["differences"], [])

    def test_confirmed_mismatch_without_switch_fails(self):
        p, c = inputs()
        c["subject_combination"] = combination(["101", "204", "301", "408"])
        result = validate_subject_match(p, c)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["differences"], [{"position": 2, "profile_code": "201", "candidate_code": "204"}])

    def test_explicit_switch_accepts_difference_without_hiding_it(self):
        p, c = inputs()
        c["subject_combination"] = combination(["101", "204", "301", "408"])
        p["preferences"]["willing_to_switch_subjects"] = True
        result = validate_subject_match(p, c)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["switch_required"])
        self.assertEqual(len(result["differences"]), 1)

    def test_display_names_or_reordering_are_not_exact_codes(self):
        for codes in (["201", "101", "301", "408"], ["101 politics", "201", "301", "408"]):
            p, c = inputs()
            c["subject_combination"] = combination(codes)
            self.assertEqual(validate_subject_match(p, c)["status"], "fail")

    def test_missing_empty_or_unverified_combinations_are_unknown(self):
        for side in ("profile", "candidate"):
            for change in (None, {"codes": [], "evidence": []}, {"codes": ["101"], "evidence": []}):
                p, c = inputs()
                (p if side == "profile" else c)["subject_combination"] = change
                self.assertEqual(validate_subject_match(p, c)["status"], "unknown")

    def test_stale_conflicted_secondary_wrong_year_and_wrong_value_are_unknown(self):
        for key, value in (("status", "stale"), ("status", "conflicted"), ("tier", "T3"),
                           ("applicable_admission_year", 2025), ("value", ["999"]),
                           ("retrieved_at", "2024-01-01T10:00:00+08:00"), ("source_url", "")):
            p, c = inputs()
            c["subject_combination"]["evidence"][0][key] = value
            p["preferences"]["willing_to_switch_subjects"] = True
            self.assertEqual(validate_subject_match(p, c)["status"], "unknown")


class ThresholdTests(unittest.TestCase):
    def test_national_line_is_not_program_line(self):
        result = classify_threshold({"year": 2026, "scope": "national", "total": 264,
                                     "program_code": "085400", "source_ref": "national-line"})
        self.assertFalse(result["is_program_specific"])
        self.assertEqual(result["scope"], "national")

    def test_all_scopes_and_year_population_statistic_are_preserved(self):
        for scope in ("national", "institution", "unit", "program", "direction", "admitted_distribution"):
            for year in (2025, 2026):
                record = {"year": year, "scope": scope, "total": 300, "source_ref": "synthetic",
                          "population": "ordinary", "subject_minimums": {"201": 40}}
                if scope == "admitted_distribution":
                    record["statistic"] = "median"
                result = classify_threshold(record)
                self.assertEqual(result["year"], year)
                self.assertEqual(result["population"], "ordinary")
                self.assertEqual(result["subject_minimums"], {"201": 40})
                self.assertEqual(result.get("statistic"), record.get("statistic"))
                result["subject_minimums"]["201"] = 99
                self.assertEqual(record["subject_minimums"]["201"], 40)

    def test_missing_required_fields_unknown_scopes_and_bad_numbers_rejected(self):
        base = {"year": 2026, "scope": "program", "total": 300, "source_ref": "line"}
        for key in base:
            record = dict(base)
            del record[key]
            with self.assertRaises(ValueError):
                classify_threshold(record)
        for key, value in (("scope", "school"), ("year", True), ("total", float("nan")),
                           ("total", -1), ("source_ref", " "), ("subject_minimums", {"201": True})):
            with self.assertRaises(ValueError):
                classify_threshold(dict(base, **{key: value}))

    def test_distribution_requires_named_statistic(self):
        for statistic in (None, "", " "):
            with self.assertRaises(ValueError):
                classify_threshold({"year": 2026, "scope": "admitted_distribution", "total": 300,
                                    "source_ref": "line", "statistic": statistic})


class ScenarioTests(unittest.TestCase):
    def test_total_and_subject_margins_above(self):
        p, c = inputs()
        result = compare_score_scenario(p, c)
        self.assertEqual(result["status"], "above")
        self.assertEqual(result["comparisons"][0]["total_margin"], [10, 30])
        self.assertEqual(result["comparisons"][0]["subject_margins"]["201"], [10, 20])
        self.assertEqual(result["comparisons"][0]["threshold"]["source_ref"], "line")
        self.assertNotIn("probability", result)

    def test_overlap_below_and_equality_are_conservative(self):
        for score, want in (([290, 310], "overlaps"), ([280, 299], "below"), ([300, 300], "overlaps")):
            p, c = inputs()
            p["score_scenario"]["total"] = score
            self.assertEqual(compare_score_scenario(p, c)["status"], want)

    def test_subject_below_beats_total_above(self):
        p, c = inputs()
        p["score_scenario"]["subjects"]["201"] = [20, 30]
        self.assertEqual(compare_score_scenario(p, c)["status"], "below")

    def test_missing_subject_range_is_insufficient_even_with_high_total(self):
        p, c = inputs()
        del p["score_scenario"]["subjects"]["201"]
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_scope_year_population_identity_and_unofficial_records_cannot_substitute(self):
        for key, value in (("scope", "national"), ("year", 2025), ("population", "special plan"),
                           ("program_code", "081200"), ("institution", "Other U"), ("evidence", None)):
            p, c = inputs()
            c["thresholds"][0][key] = value
            result = compare_score_scenario(p, c)
            self.assertEqual(result["status"], "insufficient_evidence")
            self.assertTrue(result["reasons"])

    def test_future_unpublished_line_is_not_inferred_from_history(self):
        p, c = inputs()
        p["score_scenario"]["year"] = 2027
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_multiple_years_survive_without_averaging(self):
        p, c = inputs()
        old = deepcopy(c["thresholds"][0])
        old["year"] = 2025
        old["total"] = 290
        c["thresholds"].append(old)
        result = compare_score_scenario(p, c)
        self.assertEqual(result["status"], "above")
        self.assertEqual(result["comparisons"][0]["threshold"]["year"], 2026)
        self.assertEqual(result["excluded_thresholds"][0]["threshold"]["year"], 2025)

    def test_distribution_is_descriptive_not_a_pass_line(self):
        p, c = inputs()
        p["score_scenario"]["scope"] = "admitted_distribution"
        p["score_scenario"]["statistic"] = "median"
        c["thresholds"][0].update(scope="admitted_distribution", statistic="median")
        c["thresholds"][0]["evidence"]["value"].update(scope="admitted_distribution", statistic="median")
        result = compare_score_scenario(p, c)
        self.assertEqual(result["status"], "above")
        self.assertTrue(result["comparisons"][0]["descriptive_only"])
        p["score_scenario"]["statistic"] = "minimum"
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_unrelated_source_value_does_not_certify_threshold(self):
        for change in ({"total": 200}, {"scope": "national"}, {"population": "special plan"},
                       {"subject_minimums": {}}, {"year": 2025}):
            p, c = inputs()
            c["thresholds"][0]["evidence"]["value"].update(change)
            self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_untranscribed_source_subject_minimum_cannot_be_dropped(self):
        p, c = inputs()
        del c["thresholds"][0]["subject_minimums"]
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_switch_requires_ranges_explicitly_for_target_codes(self):
        p, c = inputs()
        p["preferences"]["willing_to_switch_subjects"] = True
        c["subject_combination"] = combination(["101", "204", "301", "408"])
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")
        p["score_scenario"]["subject_codes"] = ["101", "204", "301", "408"]
        c["thresholds"][0]["subject_minimums"] = {"101": 40, "204": 40}
        c["thresholds"][0]["evidence"]["value"]["subject_minimums"] = {"101": 40, "204": 40}
        p["score_scenario"]["subjects"]["204"] = [45, 55]
        self.assertEqual(compare_score_scenario(p, c)["status"], "above")

    def test_threshold_minimum_for_another_subject_combination_is_incompatible(self):
        p, c = inputs()
        c["thresholds"][0]["subject_minimums"] = {"204": 40}
        c["thresholds"][0]["evidence"]["value"]["subject_minimums"] = {"204": 40}
        p["score_scenario"]["subjects"]["204"] = [50, 60]
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_malformed_threshold_extensions_are_rejected_cleanly(self):
        for change in ({"scope": []}, {"total": 10 ** 1000}):
            with self.assertRaises(ValueError):
                classify_threshold({"year": 2026, "scope": "national", "total": 264, "source_ref": "line", **change})

    def test_multiple_conflicting_current_thresholds_are_not_silently_selected(self):
        p, c = inputs()
        other = deepcopy(c["thresholds"][0])
        other["total"] = 350
        other["evidence"]["value"]["total"] = 350
        c["thresholds"].append(other)
        result = compare_score_scenario(p, c)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual([r["status"] for r in result["comparisons"]], ["above", "below"])

    def test_different_subject_codes_do_not_share_a_score_scenario(self):
        p, c = inputs()
        c["subject_combination"] = combination(["101", "204", "301", "408"])
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_normalized_minimum_code_collision_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_threshold({"year": 2026, "scope": "national", "total": 264,
                                "source_ref": "line", "subject_minimums": {"201": 40, "２０１": 50}})

    def test_invalid_ranges_and_non_kaoyan_inputs_do_not_pass(self):
        for value in ([330, 310], [True, 330], [310, float("inf")], None):
            p, c = inputs()
            p["score_scenario"]["total"] = value
            self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")
        p, c = inputs()
        p["pathway"] = "baoyan"
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
