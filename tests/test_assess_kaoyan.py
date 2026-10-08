"""Synthetic contract tests; numbers do not describe actual admissions."""
from copy import deepcopy
import unittest

from scripts.assess_kaoyan import (
    classify_threshold, compare_score_scenario, validate_subject_match,
)
from scripts import assess_kaoyan
from scripts.audit_evidence import audit_evidence
from datetime import datetime


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
              "subject_codes": codes,
              }
    record["evidence"] = evidence(deepcopy(record), claim_id="line")
    candidate = {"candidate_id": "synthetic", "pathway": "kaoyan", "admission_year": 2026,
                 "institution": "Synthetic U", "unit": "Synthetic Unit",
                 "program_code": "085400", "subject_combination": combination(codes),
                 "thresholds": [record]}
    return profile, candidate


def assessment_inputs():
    profile, candidate = inputs()
    candidate.update(historical_volatility="low", retest_risk="low", fit_score=80,
                     data_completeness=0.9, evidence_confidence="A",
                     gates=[{"gate_id": "eligibility", "status": "pass",
                             "critical": True, "evidence_status": "confirmed"}],
                     sensitivity={"stability": "stable", "winner_set": ["synthetic"]})
    records = []
    for field, value in (("eligibility", True), ("deadline", "2026-10-20"),
                         ("program_availability", True), ("degree_type", "professional")):
        record = evidence(value, claim_id=field)
        record["field"] = field
        records.append(record)
    candidate["current_catalog"] = deepcopy(records[2])
    audit = audit_evidence(records, datetime.fromisoformat(profile["audit_at"]))
    return profile, candidate, audit


class KaoyanAssessmentTests(unittest.TestCase):
    def assess(self, p, c, audit):
        self.assertTrue(callable(getattr(assess_kaoyan, "assess_kaoyan_candidate", None)),
                        "assessment function is missing")
        return assess_kaoyan.assess_kaoyan_candidate(p, c, audit)

    def shortlist(self, results):
        self.assertTrue(callable(getattr(assess_kaoyan, "build_kaoyan_shortlist", None)),
                        "shortlist function is missing")
        return assess_kaoyan.build_kaoyan_shortlist(results)

    def test_confirmed_subject_mismatch_is_excluded_even_with_missing_data(self):
        p, c, a = assessment_inputs()
        c["subject_combination"] = combination(["101", "204", "301", "408"])
        c.pop("current_catalog")
        result = self.assess(p, c, a)
        self.assertEqual(result["risk_band"], "excluded")
        self.assertEqual(result["subject_match"], validate_subject_match(p, c))
        self.assertTrue(result["reasons"])
        self.assertIn("subjects", result["source_refs"])

    def test_current_catalog_must_be_current_official_and_known(self):
        for mutation in ("missing", "unknown", "stale", "secondary", "wrong_year", "wrong_candidate"):
            with self.subTest(mutation=mutation):
                p, c, a = assessment_inputs()
                if mutation == "missing":
                    c.pop("current_catalog")
                else:
                    key, value = {"unknown": ("value", None), "stale": ("status", "stale"),
                                  "secondary": ("tier", "T3"), "wrong_year": ("applicable_admission_year", 2025),
                                  "wrong_candidate": ("candidate_id", "other")}[mutation]
                    c["current_catalog"][key] = value
                self.assertEqual(self.assess(p, c, a)["risk_band"], "monitor")

    def test_strong_margin_low_volatility_and_adequate_fit_is_conservative(self):
        p, c, a = assessment_inputs()
        p["score_scenario"]["total"] = [320, 340]
        c["fit_score"] = 60
        c["retest_risk"] = "medium"
        result = self.assess(p, c, a)
        self.assertEqual(result["risk_band"], "conservative")
        self.assertEqual(result["score_scenario"], compare_score_scenario(p, c))
        self.assertTrue(result["reasons"])
        self.assertEqual(set(result["source_refs"]),
                         {"subjects", "line", "eligibility", "deadline", "program_availability", "degree_type"})

    def test_overlap_with_high_volatility_or_retest_risk_is_reach(self):
        for field in ("historical_volatility", "retest_risk"):
            p, c, a = assessment_inputs()
            p["score_scenario"]["total"] = [290, 310]
            c[field] = "high"
            self.assertEqual(self.assess(p, c, a)["risk_band"], "reach")

    def test_moderate_conditions_match_and_below_is_reach(self):
        for total, volatility, expected in (([310, 330], "low", "match"),
                                            ([320, 340], "medium", "match"),
                                            ([290, 310], "low", "match"),
                                            ([270, 290], "low", "reach")):
            p, c, a = assessment_inputs()
            p["score_scenario"]["total"] = total
            c["historical_volatility"] = volatility
            self.assertEqual(self.assess(p, c, a)["risk_band"], expected)

    def test_unknown_critical_inputs_and_confidence_d_force_monitor(self):
        for field, value in (("data_completeness", 0.6999), ("evidence_confidence", "D"),
                             ("fit_score", None), ("historical_volatility", "unknown"),
                             ("retest_risk", None), ("subject_combination", None)):
            p, c, a = assessment_inputs()
            c[field] = value
            self.assertEqual(self.assess(p, c, a)["risk_band"], "monitor")
        for field in ("missing_critical_fields", "conflicted_critical_fields", "invalid_record_indexes"):
            p, c, a = assessment_inputs()
            a["candidate_summary"]["synthetic"][field] = ["synthetic_unknown"]
            self.assertEqual(self.assess(p, c, a)["risk_band"], "monitor")

    def test_completeness_boundary_and_fit_boundary(self):
        for fit, expected in ((59.999, "monitor"), (60, "conservative")):
            p, c, a = assessment_inputs()
            c.update(fit_score=fit, data_completeness=0.70)
            p["score_scenario"]["total"] = [320, 340]
            self.assertEqual(self.assess(p, c, a)["risk_band"], expected)

    def test_insufficient_or_descriptive_score_comparison_is_monitor(self):
        for mutation in ("no_threshold", "missing_subject_range", "descriptive"):
            p, c, a = assessment_inputs()
            if mutation == "no_threshold":
                c["thresholds"] = []
            elif mutation == "missing_subject_range":
                p["score_scenario"]["subjects"] = {}
            else:
                p["score_scenario"].update(scope="admitted_distribution", statistic="median")
                line = c["thresholds"][0]
                line.update(scope="admitted_distribution", statistic="median")
                line["evidence"]["value"] = {k: deepcopy(v) for k, v in line.items() if k != "evidence"}
            result = self.assess(p, c, a)
            self.assertEqual(result["risk_band"], "monitor")
            self.assertEqual(result["score_scenario"], compare_score_scenario(p, c))

    def test_stable_shortlist_uses_fit_among_eligible_match_and_conservative(self):
        def result(cid, band, fit):
            return {"candidate_id": cid, "risk_band": band, "fit_score": fit,
                    "sensitivity": {"stability": "stable", "winner_set": ["target"]}}
        results = {cid: result(cid, band, fit) for cid, band, fit in
                   (("target", "match", 85), ("safe", "conservative", 75),
                    ("ambitious", "reach", 99), ("watch", "monitor", 100),
                    ("out", "excluded", 100))}
        shortlist = self.shortlist(results)
        self.assertEqual(shortlist["primary"], "target")
        self.assertEqual(shortlist["decision_set"], [])
        self.assertFalse(shortlist["requires_user_decision"])
        self.assertEqual(shortlist["alternatives"], ["ambitious", "safe"])
        self.assertEqual(shortlist["monitor"], ["watch"])
        self.assertEqual(shortlist["excluded"], ["out"])

    def test_fragile_or_equal_fit_top_returns_decision_set(self):
        for stability, other_fit in (("fragile", 79), ("stable", 80)):
            results = {cid: {"candidate_id": cid, "risk_band": "match", "fit_score": fit,
                             "sensitivity": {"stability": stability, "winner_set": ["a", "b", "watch"]}}
                       for cid, fit in (("a", 80), ("b", other_fit))}
            results["watch"] = {"candidate_id": "watch", "risk_band": "monitor", "fit_score": 100}
            shortlist = self.shortlist(results)
            self.assertIsNone(shortlist["primary"])
            self.assertEqual(shortlist["decision_set"], ["a", "b"])
            self.assertTrue(shortlist["requires_user_decision"])

    def test_missing_sensitivity_cannot_name_single_winner(self):
        results = {"a": {"candidate_id": "a", "risk_band": "match", "fit_score": 80}}
        shortlist = self.shortlist(results)
        self.assertIsNone(shortlist["primary"])
        self.assertEqual(shortlist["decision_set"], ["a"])
        self.assertTrue(shortlist["requires_user_decision"])

    def test_empty_shortlist_and_mismatched_result_key(self):
        result = self.shortlist({})
        self.assertIsNone(result["primary"])
        self.assertFalse(result["requires_user_decision"])
        with self.assertRaises(ValueError):
            self.shortlist({"wrong": {"candidate_id": "a", "risk_band": "match", "fit_score": 80}})

    def test_assessment_does_not_mutate_inputs(self):
        p, c, a = assessment_inputs()
        before = deepcopy((p, c, a))
        self.assess(p, c, a)
        self.assertEqual((p, c, a), before)

    def test_fresh_audit_does_not_make_wrong_year_critical_claim_current(self):
        p, c, a = assessment_inputs()
        a["claims"][0]["record"]["applicable_admission_year"] = 2025
        self.assertEqual(self.assess(p, c, a)["risk_band"], "monitor")

    def test_missing_critical_field_detail_cannot_be_assumed_known(self):
        p, c, a = assessment_inputs()
        a["candidate_summary"]["synthetic"]["critical_fields"].pop("deadline")
        self.assertEqual(self.assess(p, c, a)["risk_band"], "monitor")

    def test_stable_sensitivity_for_different_winner_cannot_promote_fit_top(self):
        results = {cid: {"candidate_id": cid, "risk_band": "match", "fit_score": fit,
                         "sensitivity": {"stability": "stable", "winner_set": ["b"]}}
                   for cid, fit in (("a", 80), ("b", 79))}
        result = self.shortlist(results)
        self.assertIsNone(result["primary"])
        self.assertEqual(result["decision_set"], ["a", "b"])
        self.assertTrue(result["requires_user_decision"])

    def test_fragile_equal_fit_set_also_keeps_other_sensitivity_winners(self):
        results = {cid: {"candidate_id": cid, "risk_band": "match", "fit_score": fit,
                         "sensitivity": {"stability": "fragile", "winner_set": ["a", "c"]}}
                   for cid, fit in (("a", 80), ("b", 80), ("c", 79))}
        self.assertEqual(self.shortlist(results)["decision_set"], ["a", "b", "c"])

    def test_margin_boundary_and_secondary_confidence_never_overstate_band(self):
        for margin, confidence, expected in ((19.999, "A", "match"), (20, "A", "conservative"),
                                              (20, "C", "match")):
            p, c, a = assessment_inputs()
            p["score_scenario"]["total"] = [300 + margin, 350]
            c["evidence_confidence"] = confidence
            self.assertEqual(self.assess(p, c, a)["risk_band"], expected)

    def test_confirmed_gate_failure_is_excluded_and_unknown_gate_monitored(self):
        for status, expected in (("fail", "excluded"), ("unknown", "monitor")):
            p, c, a = assessment_inputs()
            c["gates"][0]["status"] = status
            self.assertEqual(self.assess(p, c, a)["risk_band"], expected)

    def test_summary_only_audit_and_missing_candidate_are_monitored(self):
        p, c, a = assessment_inputs()
        result = self.assess(p, c, a["candidate_summary"])
        self.assertEqual(result["risk_band"], "monitor")
        self.assertIn("current_critical_source_provenance_missing", result["reasons"])
        self.assertIn("program_availability", result["source_refs"])
        self.assertEqual(self.assess(p, c, {})["risk_band"], "monitor")

    def test_invalid_risk_extensions_cannot_confirm_decision_band(self):
        for field, value in (("historical_volatility", []), ("retest_risk", {}),
                             ("fit_score", True), ("fit_score", float("nan")),
                             ("data_completeness", 10**400)):
            p, c, a = assessment_inputs()
            c[field] = value
            self.assertEqual(self.assess(p, c, a)["risk_band"], "monitor")

    def test_catalog_same_id_conflicting_audit_value_is_monitor(self):
        p, c, a = assessment_inputs()
        records = [deepcopy(claim["record"]) for claim in a["claims"]]
        records[2]["value"] = False
        a = audit_evidence(records, datetime.fromisoformat(p["audit_at"]))
        result = self.assess(p, c, a)
        self.assertEqual(result["risk_band"], "monitor")
        self.assertIn("current_catalog_audit_payload_mismatch", result["reasons"])
        self.assertIn("program_availability", result["source_refs"])

    def test_catalog_matching_id_requires_identical_audited_payload(self):
        for field, value in (("candidate_id", "other"), ("field", "degree_type"),
                             ("source_url", "https://example.invalid/different"),
                             ("applicable_admission_year", 2025), ("status", "secondary_only"),
                             ("value", 1), ("applicable_admission_year", 2026.0)):
            with self.subTest(field=field):
                p, c, a = assessment_inputs()
                a["claims"][2]["record"][field] = value
                result = self.assess(p, c, a)
                self.assertEqual(result["risk_band"], "monitor")
                self.assertIn("current_catalog_audit_payload_mismatch", result["reasons"])

    def test_other_current_official_catalog_false_blocks_positive_catalog(self):
        p, c, a = assessment_inputs()
        records = [deepcopy(claim["record"]) for claim in a["claims"]]
        negative = deepcopy(records[2])
        negative.update(claim_id="catalog-negative", value=False)
        records.append(negative)
        a = audit_evidence(records, datetime.fromisoformat(p["audit_at"]))
        result = self.assess(p, c, a)
        self.assertEqual(result["risk_band"], "monitor")
        self.assertIn("current_catalog_conflicting_official_availability", result["reasons"])
        self.assertIn("catalog-negative", result["source_refs"])

    def test_each_tied_top_sensitivity_contributes_to_complete_decision_set(self):
        for first_stability in ("stable", "fragile"):
            results = {cid: {"candidate_id": cid, "risk_band": "match", "fit_score": fit}
                       for cid, fit in (("a", 90), ("b", 90), ("c", 80))}
            results["a"]["sensitivity"] = {"stability": first_stability, "winner_set": ["a", "b"]}
            results["b"]["sensitivity"] = {"stability": "fragile", "winner_set": ["b", "c"]}
            shortlist = self.shortlist(results)
            self.assertIsNone(shortlist["primary"])
            self.assertTrue(shortlist["requires_user_decision"])
            self.assertEqual(shortlist["decision_set"], ["a", "b", "c"])
            self.assertNotIn("c", shortlist["alternatives"])


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
        c["thresholds"][0]["subject_codes"] = ["101", "204", "301", "408"]
        c["thresholds"][0]["evidence"]["value"]["subject_codes"] = ["101", "204", "301", "408"]
        p["score_scenario"]["subjects"]["204"] = [45, 55]
        self.assertEqual(compare_score_scenario(p, c)["status"], "above")

    def test_threshold_minimum_for_another_subject_combination_is_incompatible(self):
        p, c = inputs()
        c["thresholds"][0]["subject_minimums"] = {"204": 40}
        c["thresholds"][0]["evidence"]["value"]["subject_minimums"] = {"204": 40}
        p["score_scenario"]["subjects"]["204"] = [50, 60]
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_source_full_combination_cannot_be_filtered_from_total_only_line(self):
        for minimums in ({}, {"101": 40}):
            p, c = inputs()
            line = c["thresholds"][0]
            line["subject_minimums"] = minimums
            line["evidence"]["value"]["subject_minimums"] = minimums
            line["evidence"]["value"]["subject_codes"] = ["101", "204", "302", "408"]
            self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_missing_or_incompatible_threshold_full_combination_is_insufficient(self):
        for codes in (None, [], ["101", "204", "302", "408"]):
            p, c = inputs()
            line = c["thresholds"][0]
            line["subject_minimums"] = {}
            line["evidence"]["value"]["subject_minimums"] = {}
            if codes is None:
                del line["subject_codes"]
                del line["evidence"]["value"]["subject_codes"]
            else:
                line["subject_codes"] = codes
                line["evidence"]["value"]["subject_codes"] = codes
            self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_historical_threshold_requires_that_years_source_backed_combination(self):
        p, c = inputs()
        p["score_scenario"]["year"] = 2025
        line = c["thresholds"][0]
        line["year"] = line["evidence"]["applicable_admission_year"] = 2025
        line["evidence"]["value"]["year"] = 2025
        self.assertEqual(compare_score_scenario(p, c)["status"], "above")
        line["subject_codes"] = line["evidence"]["value"]["subject_codes"] = ["101", "204", "302", "408"]
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")
        line["subject_codes"] = line["evidence"]["value"]["subject_codes"] = ["101", "201", "301", "408"]
        line["evidence"]["applicable_admission_year"] = 2026
        self.assertEqual(compare_score_scenario(p, c)["status"], "insufficient_evidence")

    def test_optional_identity_restrictions_match_without_upgrading_scope(self):
        for scope, field in (("national", "institution"), ("national", "unit"),
                             ("institution", "unit"), ("institution", "program_code"),
                             ("unit", "program_code")):
            p, c = inputs()
            p["score_scenario"]["scope"] = scope
            line = c["thresholds"][0]
            line["scope"] = scope
            line["area"] = c["area"] = "A"
            line["category"] = c["category"] = "synthetic engineering"
            line["evidence"]["value"] = {k: deepcopy(v) for k, v in line.items() if k != "evidence"}
            self.assertEqual(compare_score_scenario(p, c)["status"], "above")
            line[field] = "different target"
            line["evidence"]["value"][field] = "different target"
            result = compare_score_scenario(p, c)
            self.assertEqual(result["status"], "insufficient_evidence")
            self.assertEqual(result["excluded_thresholds"][0]["threshold"]["scope"], scope)

    def test_national_area_and_category_must_be_known_and_match(self):
        for field in ("area", "category"):
            for mutation in ("missing_line", "missing_target", "mismatch"):
                p, c = inputs()
                p["score_scenario"]["scope"] = "national"
                line = c["thresholds"][0]
                line["scope"] = "national"
                line["area"] = c["area"] = "A"
                line["category"] = c["category"] = "synthetic engineering"
                if mutation == "missing_line":
                    del line[field]
                elif mutation == "missing_target":
                    del c[field]
                else:
                    c[field] = "different applicability"
                line["evidence"]["value"] = {k: deepcopy(v) for k, v in line.items() if k != "evidence"}
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
