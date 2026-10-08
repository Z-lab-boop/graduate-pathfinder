"""Sensitivity of decision rankings; thresholds do not predict admission outcomes."""
import math

from scripts.rank_candidates import _normalize_weights, _number, rank_candidates


def _order(results):
    """Use explicit ranks, independent of candidate IDs or mapping iteration order."""
    return [item["candidate_id"] for item in sorted(
        (item for item in results.values()
         if item["portfolio_group"] in {"reach", "core", "safety"}
         and item["rank"] is not None), key=lambda item: item["rank"])]


def _counterfactual(candidates, weights, baseline_winner):
    changes = []
    for criterion, original in weights.items():
        other_total = math.fsum(value for name, value in weights.items() if name != criterion)
        for step in range(101):
            target = step / 100
            if target == original or (other_total == 0 and target != 1):
                continue
            adjusted = {name: (target if name == criterion else
                               (1 - target) * value / other_total)
                        for name, value in weights.items()}
            order = _order(rank_candidates(candidates, adjusted))
            if order and order[0] != baseline_winner:
                changes.append({"criterion": criterion, "weight": target,
                                "baseline_weight": original, "change": abs(target - original),
                                "winner": order[0], "weights": adjusted,
                                "effect": "decision_weight"})
    if not changes:
        return None
    # Round only the comparison key to make mathematically equal changes deterministic.
    return min(changes, key=lambda item: (round(item["change"], 12),
                                         item["criterion"], item["weight"], item["winner"]))


def analyze_sensitivity(candidates: list[dict], weights: dict[str, float],
                        delta: float = 0.10) -> dict:
    """Perturb normalized weights one at a time and search a 0.01 weight grid.

    A scenario with all weights zero is invalid and cannot select a winner.
    When other weights total zero, proportional counterfactual scaling is only
    defined at weight 1; no arbitrary redistribution is introduced.
    """
    _number(delta, "delta", 0, math.inf)
    normalized = _normalize_weights(weights)
    baseline = _order(rank_candidates(candidates, normalized))
    baseline_winner = baseline[0] if baseline else None
    scenarios, winners = [], set(baseline[:1])
    fragile = False
    for criterion, original in normalized.items():
        for direction, shift in (("decrease", -delta), ("increase", delta)):
            adjusted = dict(normalized)
            adjusted[criterion] = max(0, original + shift)
            valid = any(adjusted.values())
            scenario_weights = _normalize_weights(adjusted) if valid else adjusted
            order = _order(rank_candidates(candidates, scenario_weights)) if valid else []
            winner = order[0] if order else None
            scenarios.append({"criterion": criterion, "direction": direction,
                              "weights": scenario_weights, "valid": valid,
                              "order": order, "winner": winner})
            if winner is not None:
                winners.add(winner)
            if valid and winner != baseline_winner:
                fragile = True
    sufficient = len(baseline) >= 2
    return {"baseline_order": baseline, "baseline_weights": normalized,
            "scenarios": scenarios, "winner_set": sorted(winners),
            "stability": ("insufficient_candidates" if not sufficient else
                          "fragile" if fragile else "stable"),
            "counterfactual_threshold": (_counterfactual(candidates, normalized, baseline_winner)
                                         if sufficient else None)}
