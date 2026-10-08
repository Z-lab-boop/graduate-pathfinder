"""Transparent decision scores and portfolio groups, without outcome prediction."""
import math

ALLOWED_DIMENSIONS = {
    "competitive_position", "research_fit", "academic_match", "career_fit",
    "location_fit", "cost_fit", "application_readiness",
}
EVIDENCE_STATES = {"confirmed", "secondary_only", "conflicted", "stale", "missing", "not_applicable"}


def _number(value, name, low, high):
    valid = type(value) in (int, float) and low <= value <= high
    if valid:
        try:
            valid = math.isfinite(value)
        except OverflowError:
            valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite number between {low} and {high}")
    return value


def _normalize_weights(weights):
    if not isinstance(weights, dict) or not weights:
        raise ValueError("weights must be a non-empty dimension mapping")
    for name, value in weights.items():
        if name not in ALLOWED_DIMENSIONS:
            raise ValueError(f"unknown weighted dimension: {name}")
        _number(value, f"weight {name}", 0, math.inf)
    maximum = max(weights.values())
    if maximum == 0:
        raise ValueError("weights must sum to a positive value")
    # Scaling avoids overflow when otherwise valid finite weights have a huge sum.
    scaled = {name: value / maximum for name, value in weights.items()}
    total = math.fsum(scaled.values())
    return {name: value / total for name, value in sorted(scaled.items())}


def evaluate_gates(gates: list[dict]) -> dict:
    """Only confirmed pass/fail evidence resolves a gate; failures take precedence."""
    if not isinstance(gates, list):
        raise ValueError("gates must be an array")
    details, failed, unknown = [], [], []
    seen = set()
    critical_count = 0
    for gate in gates:
        if not isinstance(gate, dict):
            raise ValueError("each gate must be an object")
        gate_id = gate.get("gate_id")
        if not isinstance(gate_id, str) or not gate_id.strip() or gate_id in seen:
            raise ValueError("gate_id must be a unique non-empty string")
        seen.add(gate_id)
        status = gate.get("status")
        evidence_status = gate.get("evidence_status")
        critical = gate.get("critical")
        if status not in {"pass", "fail", "unknown"}:
            raise ValueError("gate status must be pass, fail, or unknown")
        if evidence_status not in EVIDENCE_STATES:
            raise ValueError("gate evidence_status is invalid")
        if type(critical) is not bool:
            raise ValueError("gate critical must be a boolean")
        effective = status if evidence_status == "confirmed" else "unknown"
        details.append({"gate_id": gate_id, "status": status, "critical": critical,
                        "evidence_status": evidence_status, "effective_status": effective})
        critical_count += critical
        if effective == "fail":
            failed.append(gate_id)
        elif effective == "unknown" and critical:
            unknown.append(gate_id)
    eligibility = "fail" if failed else ("unknown" if unknown or not critical_count else "pass")
    return {"eligibility": eligibility, "failed_gates": failed,
            "unknown_critical_gates": unknown, "gates": details}


def assign_portfolio_group(result: dict) -> str:
    """Apply documented conservative overrides before position/fit thresholds."""
    if result["eligibility"] == "fail":
        return "excluded"
    if (result["eligibility"] != "pass" or result["evidence_confidence"] == "D"
            or result["weight_coverage"] < 0.70):
        return "monitor"
    inputs = result["grouping_inputs"]
    position, fit = inputs.get("competitive_position"), inputs.get("research_fit")
    if position is None or fit is None or fit < 60:
        return "monitor"
    if position < 50:
        return "reach"
    if position < 80:
        return "core"
    return "safety"


def score_candidate(candidate: dict, weights: dict[str, float]) -> dict:
    """Score only present dimensions; preserve evidence and coverage separately."""
    normalized = _normalize_weights(weights)
    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ValueError("candidate_id must be a non-empty string")
    confidence = candidate.get("evidence_confidence")
    if confidence not in {"A", "B", "C", "D"}:
        raise ValueError("evidence_confidence must be A, B, C, or D")
    completeness = _number(candidate.get("data_completeness"), "data_completeness", 0, 1)
    dimensions = candidate.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("dimensions must be a mapping")
    for name, value in dimensions.items():
        if name not in ALLOWED_DIMENSIONS:
            raise ValueError(f"unknown dimension: {name}")
        _number(value, f"dimension {name}", 0, 100)
    gates = evaluate_gates(candidate.get("gates"))
    present = {name: dimensions[name] for name in normalized if name in dimensions}
    coverage = math.fsum(normalized[name] for name in present)
    contributions = {name: value * normalized[name] for name, value in present.items()}
    result = {
        "candidate_id": candidate_id, "eligibility": gates["eligibility"],
        "gate_evaluation": gates, "evidence_confidence": confidence,
        "data_completeness": completeness, "normalized_weights": normalized,
        "dimension_contributions": contributions, "weight_coverage": coverage,
        "weighted_score": math.fsum(contributions.values()) / coverage if coverage else None,
        "grouping_inputs": {name: dimensions[name] for name in
                            ("competitive_position", "research_fit") if name in dimensions},
        "rank": None,
    }
    result["portfolio_group"] = assign_portfolio_group(result)
    return result


def rank_candidates(candidates: list[dict], weights: dict[str, float]) -> dict[str, dict]:
    """Return ID-keyed results; rank viable groups by score then ID, starting at 1."""
    _normalize_weights(weights)
    results = {}
    for candidate in candidates:
        result = score_candidate(candidate, weights)
        candidate_id = result["candidate_id"]
        if candidate_id in results:
            raise ValueError(f"duplicate candidate_id: {candidate_id}")
        results[candidate_id] = result
    rankable = [result for result in results.values()
                if result["portfolio_group"] in {"reach", "core", "safety"}]
    for rank, result in enumerate(sorted(rankable, key=lambda item:
                                        (-item["weighted_score"], item["candidate_id"])), 1):
        result["rank"] = rank
    return dict(sorted(results.items()))
