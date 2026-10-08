import copy
import math
import unittest

from scripts.rank_candidates import (
    assign_portfolio_group, evaluate_gates, rank_candidates, score_candidate,
)


def candidate(candidate_id="target-a", **changes):
    record = {
        "candidate_id": candidate_id,
        "gates": [{"gate_id": "eligibility", "status": "pass", "critical": True,
                   "evidence_status": "confirmed"}],
        "dimensions": {"competitive_position": 65, "research_fit": 80},
        "evidence_confidence": "A", "data_completeness": 0.9,
    }
    record.update(changes)
    return record


class CandidateRankingTests(unittest.TestCase):
    def setUp(self):
        self.weights = {"competitive_position": 3, "research_fit": 2}

    def test_confirmed_failed_gate_excludes_even_with_other_unknown_gate(self):
        record = candidate()
        record["gates"][0]["status"] = "fail"
        record["gates"].append({"gate_id": "quota", "status": "unknown", "critical": True,
                                "evidence_status": "missing"})
        result = score_candidate(record, self.weights)
        self.assertEqual(result["eligibility"], "fail")
        self.assertEqual(result["portfolio_group"], "excluded")
        self.assertEqual(result["gate_evaluation"]["failed_gates"], ["eligibility"])

    def test_unknown_gate_cannot_enter_core_group(self):
        record = candidate()
        record["gates"][0].update(status="unknown", evidence_status="missing")
        result = score_candidate(record, self.weights)
        self.assertEqual(result["portfolio_group"], "monitor")
        self.assertEqual(result["eligibility"], "unknown")

    def test_unconfirmed_pass_or_fail_is_unknown(self):
        for status in ("pass", "fail"):
            record = candidate()
            record["gates"][0].update(status=status, evidence_status="secondary_only")
            self.assertEqual(score_candidate(record, self.weights)["eligibility"], "unknown")

    def test_noncritical_unknown_does_not_block_but_confirmed_failure_does(self):
        gates = candidate()["gates"] + [{"gate_id": "optional", "status": "unknown",
                                        "critical": False, "evidence_status": "missing"}]
        self.assertEqual(evaluate_gates(gates)["eligibility"], "pass")
        gates[-1].update(status="fail", evidence_status="confirmed")
        self.assertEqual(evaluate_gates(gates)["eligibility"], "fail")

    def test_empty_or_only_noncritical_gates_cannot_confirm_eligibility(self):
        for gates in ([], [{"gate_id": "optional", "status": "pass", "critical": False,
                           "evidence_status": "confirmed"}]):
            self.assertEqual(evaluate_gates(gates)["eligibility"], "unknown")

    def test_missing_dimension_is_not_zero(self):
        result = score_candidate(candidate(dimensions={"competitive_position": 65}), self.weights)
        self.assertNotIn("research_fit", result["dimension_contributions"])
        self.assertAlmostEqual(result["weight_coverage"], 0.6)
        self.assertAlmostEqual(result["weighted_score"], 65)
        self.assertEqual(result["portfolio_group"], "monitor")

    def test_normalization_and_inspectable_contributions(self):
        result = score_candidate(candidate(), self.weights)
        self.assertAlmostEqual(result["normalized_weights"]["competitive_position"], 0.6)
        self.assertAlmostEqual(result["normalized_weights"]["research_fit"], 0.4)
        self.assertAlmostEqual(result["dimension_contributions"]["competitive_position"], 39)
        self.assertAlmostEqual(result["dimension_contributions"]["research_fit"], 32)
        self.assertAlmostEqual(result["weighted_score"], 71)
        self.assertAlmostEqual(result["weight_coverage"], 1)
        self.assertEqual(result["data_completeness"], 0.9)

    def test_no_present_positive_weight_returns_no_score(self):
        result = score_candidate(candidate(dimensions={}), self.weights)
        self.assertIsNone(result["weighted_score"])
        self.assertEqual(result["dimension_contributions"], {})
        self.assertEqual(result["weight_coverage"], 0)
        self.assertEqual(result["portfolio_group"], "monitor")

    def test_zero_weight_dimension_does_not_supply_coverage(self):
        result = score_candidate(candidate(dimensions={"research_fit": 80}),
                                 {"competitive_position": 1, "research_fit": 0})
        self.assertIsNone(result["weighted_score"])
        self.assertEqual(result["weight_coverage"], 0)

    def test_invalid_weights_are_rejected(self):
        for weights in ({}, {"research_fit": 0}, {"research_fit": -1},
                        {"research_fit": True}, {"research_fit": math.nan},
                        {"research_fit": math.inf}, {"unknown_dimension": 1}):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                score_candidate(candidate(), weights)

    def test_unrepresentable_number_is_rejected_without_overflow(self):
        for record, weights in ((candidate(dimensions={"research_fit": 10 ** 1000}), self.weights),
                                (candidate(), {"research_fit": 10 ** 1000}),
                                (candidate(data_completeness=10 ** 1000), self.weights)):
            with self.assertRaises(ValueError):
                score_candidate(record, weights)

    def test_dimensions_only_accept_finite_numbers_in_range(self):
        for value in (-1, 101, math.nan, math.inf, True, None, "80"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                score_candidate(candidate(dimensions={"research_fit": value}), self.weights)
        for value in (0, 100):
            self.assertEqual(score_candidate(candidate(dimensions={"research_fit": value}),
                                              {"research_fit": 1})["weighted_score"], value)

    def test_unknown_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            score_candidate(candidate(dimensions={"prestige": 100}), self.weights)

    def test_confidence_d_forces_monitor(self):
        self.assertEqual(score_candidate(candidate(evidence_confidence="D"), self.weights)
                         ["portfolio_group"], "monitor")

    def test_coverage_boundary(self):
        record = candidate()
        for present_weight, group in ((0.6999, "monitor"), (0.7, "core")):
            result = score_candidate(record, {"competitive_position": present_weight / 2,
                                             "research_fit": present_weight / 2,
                                             "career_fit": 1 - present_weight})
            self.assertEqual(result["portfolio_group"], group)

    def test_grouping_thresholds_use_explicit_position_and_fit(self):
        for position, fit, group in ((49.99, 60, "reach"), (50, 60, "core"),
                                     (79.99, 60, "core"), (80, 60, "safety"),
                                     (80, 59.99, "monitor")):
            with self.subTest(position=position, fit=fit):
                result = score_candidate(candidate(dimensions={"competitive_position": position,
                                                               "research_fit": fit}), self.weights)
                self.assertEqual(result["portfolio_group"], group)
                self.assertEqual(assign_portfolio_group(result), group)

    def test_missing_grouping_dimension_forces_monitor_even_with_full_coverage(self):
        result = score_candidate(candidate(dimensions={"career_fit": 90}), {"career_fit": 1})
        self.assertEqual(result["weight_coverage"], 1)
        self.assertEqual(result["portfolio_group"], "monitor")

    def test_rank_is_id_keyed_deterministic_and_nonrankable_is_null(self):
        items = [candidate("b"), candidate("a"),
                 candidate("high", dimensions={"competitive_position": 90, "research_fit": 90}),
                 candidate("watch", evidence_confidence="D"),
                 candidate("out", gates=[{"gate_id": "eligibility", "status": "fail",
                                            "critical": True, "evidence_status": "confirmed"}])]
        results = rank_candidates(items, self.weights)
        self.assertEqual(results["high"]["rank"], 1)
        self.assertEqual(results["a"]["rank"], 2)
        self.assertEqual(results["b"]["rank"], 3)
        self.assertIsNone(results["watch"]["rank"])
        self.assertIsNone(results["out"]["rank"])
        self.assertEqual(results, rank_candidates(list(reversed(items)), self.weights))

    def test_duplicate_or_empty_candidate_ids_are_rejected(self):
        for items in ([candidate(), candidate()], [candidate("")]):
            with self.assertRaises(ValueError):
                rank_candidates(items, self.weights)

    def test_invalid_gate_shapes_and_confidence_are_rejected(self):
        for gate in ({}, {"gate_id": "x", "status": "yes", "critical": True,
                          "evidence_status": "confirmed"},
                     {"gate_id": "x", "status": "pass", "critical": "true",
                      "evidence_status": "confirmed"}):
            with self.assertRaises(ValueError):
                evaluate_gates([gate])
        with self.assertRaises(ValueError):
            score_candidate(candidate(evidence_confidence="E"), self.weights)

    def test_inputs_are_preserved_and_no_personal_probability_key(self):
        items = [candidate()]
        before = copy.deepcopy(items)
        weights_before = copy.deepcopy(self.weights)
        results = rank_candidates(items, self.weights)
        self.assertEqual(items, before)
        self.assertEqual(self.weights, weights_before)

        def inspect(value):
            if isinstance(value, dict):
                self.assertNotIn("admission_probability", value)
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
        inspect(results)


if __name__ == "__main__":
    unittest.main()
