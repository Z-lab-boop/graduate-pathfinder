import copy
import math
import unittest

from scripts.sensitivity_analysis import analyze_sensitivity
from tests.test_rank_candidates import candidate


def options():
    return [candidate("z", dimensions={"competitive_position": 65,
                                      "research_fit": 90, "location_fit": 40}),
            candidate("a", dimensions={"competitive_position": 65,
                                      "research_fit": 70, "location_fit": 90})]


class SensitivityTests(unittest.TestCase):
    def test_location_increase_changes_winner_and_finds_smallest_threshold(self):
        result = analyze_sensitivity(options(), {"research_fit": .75, "location_fit": .25})
        self.assertEqual(result["baseline_order"], ["z", "a"])
        self.assertEqual(result["stability"], "fragile")
        self.assertEqual(result["winner_set"], ["a", "z"])
        raised = next(s for s in result["scenarios"]
                      if s["criterion"] == "location_fit" and s["direction"] == "increase")
        self.assertEqual(raised["winner"], "a")
        self.assertAlmostEqual(raised["weights"]["location_fit"], .35 / 1.1)
        threshold = result["counterfactual_threshold"]
        self.assertEqual(threshold["criterion"], "location_fit")
        self.assertAlmostEqual(threshold["weight"], .29)
        self.assertAlmostEqual(threshold["change"], .04)
        self.assertEqual(threshold["winner"], "a")
        self.assertEqual(threshold["effect"], "decision_weight")

    def test_dominating_candidate_is_stable_without_counterfactual(self):
        items = [candidate("a", dimensions={"competitive_position": 65,
                                           "research_fit": 70, "location_fit": 40}),
                 candidate("z", dimensions={"competitive_position": 80,
                                           "research_fit": 90, "location_fit": 90})]
        result = analyze_sensitivity(items, {"research_fit": 3, "location_fit": 1})
        self.assertEqual(result["baseline_order"], ["z", "a"])
        self.assertEqual(result["stability"], "stable")
        self.assertEqual(result["winner_set"], ["z"])
        self.assertEqual(len(result["scenarios"]), 4)
        self.assertIsNone(result["counterfactual_threshold"])

    def test_inputs_and_dictionary_order_do_not_affect_results(self):
        items, weights = options(), {"research_fit": .75, "location_fit": .25}
        before = copy.deepcopy((items, weights))
        result = analyze_sensitivity(items, weights)
        self.assertEqual((items, weights), before)
        self.assertEqual(result, analyze_sensitivity(items[::-1], dict(reversed(list(weights.items())))))

    def test_nonrankable_candidates_never_win(self):
        items = options() + [candidate("watch", evidence_confidence="D"),
                             candidate("out", gates=[{"gate_id": "x", "status": "fail",
                                                      "critical": True, "evidence_status": "confirmed"}])]
        result = analyze_sensitivity(items, {"research_fit": .75, "location_fit": .25})
        self.assertEqual(result["baseline_order"], ["z", "a"])
        self.assertEqual(result["winner_set"], ["a", "z"])

    def test_fewer_than_two_rankable_candidates_is_insufficient(self):
        for items in ([], [candidate("z")], [candidate("watch", evidence_confidence="D")]):
            result = analyze_sensitivity(items, {"research_fit": 1})
            self.assertEqual(result["stability"], "insufficient_candidates")
            self.assertIsNone(result["counterfactual_threshold"])

    def test_clamps_and_marks_zero_sum_scenario_invalid(self):
        result = analyze_sensitivity(options(), {"research_fit": 1}, delta=1)
        lowered = next(s for s in result["scenarios"] if s["direction"] == "decrease")
        self.assertFalse(lowered["valid"])
        self.assertIsNone(lowered["winner"])
        self.assertEqual(result["stability"], "stable")
        self.assertIsNone(result["counterfactual_threshold"])
        result = analyze_sensitivity(options(), {"research_fit": .95, "location_fit": .05})
        lowered = next(s for s in result["scenarios"]
                      if s["criterion"] == "location_fit" and s["direction"] == "decrease")
        self.assertEqual(lowered["weights"]["location_fit"], 0)

    def test_zero_delta_and_invalid_delta(self):
        self.assertEqual(analyze_sensitivity(options(), {"research_fit": .75,
                                                       "location_fit": .25}, 0)["stability"], "stable")
        for delta in (-.1, True, math.nan, math.inf, "0.1"):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                analyze_sensitivity(options(), {"research_fit": 1}, delta)

    def test_zero_other_weights_preserve_proportional_search(self):
        result = analyze_sensitivity(options(), {"research_fit": 1, "location_fit": 0})
        threshold = result["counterfactual_threshold"]
        self.assertEqual(threshold["criterion"], "location_fit")
        self.assertAlmostEqual(threshold["weight"], .29)
        self.assertEqual(threshold["winner"], "a")


if __name__ == "__main__":
    unittest.main()
