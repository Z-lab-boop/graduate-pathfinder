"""Compose an ordinal, evidence-bound outlook from independently computed results.

Payload: candidate_id, admission_year (current cycle), target_scope (the explicitly
selected historical cohort's complete SCOPE_FIELDS), eligibility_result from
evaluate_gates, material_audit from audit_materials, candidate_scoring from
score_candidate, historical_metrics from calculate_stage_metrics, fit_result
{score: 0..100, reasons: [str]}, and the full audit_evidence report.
critical_applicant_fields optionally adds decision-critical canonical fields.

Bands use only grouping_inputs.competitive_position: >=80 strong, >=60
competitive, >=40 borderline, otherwise weak. These are transparent ordinal
decision rules, not calibrated admission cutoffs. Historical ratios never enter
the band. Required material readiness uses worst-state precedence; optional and
not-applicable deficiencies do not block. Conditions are unresolved factual
checks, with no asserted direction or guaranteed effect on an admission outcome.
No files are opened, no applicant facts are chosen from conflicts, and inputs
are never changed. Generated text still needs the separate redaction workflow.
"""
from copy import deepcopy
import math

from .audit_evidence import CRITICAL_FIELDS
from .calculate_historical_metrics import SCOPE_FIELDS, PROVENANCE_FIELDS, calculate_stage_metrics, scope_key


READINESS = {"complete", "repairable", "materially_incomplete", "unreadable"}
COMPETITIVE_BANDS = {"strong", "competitive", "borderline", "weak", "evidence_insufficient"}
CONFIDENCE = {"A", "B", "C", "D"}
CRITICAL_APPLICANT_FIELDS = {"gpa", "ranking", "rank", "rank_percentile", "ranking_denominator",
                             "language_score", "language_threshold", "eligibility",
                             "degree_type", "graduation_year"}
READINESS_ORDER = {"complete": 0, "repairable": 1, "materially_incomplete": 2, "unreadable": 3}


def _score(value, name):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite number between 0 and 100")
    return float(value)


def _typed_equal(left, right):
    """Compare JSON-like values without Python's bool/int equivalence."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def assess_admission_outlook(payload: dict) -> dict:
    """Return the exact eight-field contract; missing evidence is conservative.

Explicit eligibility failures take precedence over scoring's gate result. Fit,
readiness and eligibility never change the competitive dimension. No comparable
officially evidenced cohort, critical applicant conflict, or unusable current
target evidence overrides that dimension to evidence_insufficient. Confidence
is the weakest decision-critical source/comparability/coverage assessment.
"""
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    candidate_id, year = payload.get("candidate_id"), payload.get("admission_year")
    scoring = payload.get("candidate_scoring", {})
    material = payload.get("material_audit", {})
    audit = payload.get("evidence_audit", {})
    historical = payload.get("historical_metrics", {})
    eligibility_result = payload.get("eligibility_result", {})
    fit = payload.get("fit_result", {})
    if not all(isinstance(value, dict) for value in (scoring, material, audit, historical, eligibility_result, fit)):
        raise ValueError("upstream results must be objects")
    if scoring.get("candidate_id", candidate_id) != candidate_id:
        raise ValueError("candidate_scoring candidate_id must match candidate_id")
    extra_critical = payload.get("critical_applicant_fields", [])
    if not isinstance(extra_critical, list) or not all(isinstance(v, str) and v.strip() for v in extra_critical):
        raise ValueError("critical_applicant_fields must be an array of field names")
    critical = CRITICAL_APPLICANT_FIELDS | set(extra_critical)
    uncertainties, conditions, confidence_levels = [], [], ["A"]
    insufficient = False

    def concern(reason, confidence="D", blocks=False):
        nonlocal insufficient
        if reason not in uncertainties:
            uncertainties.append(reason)
        confidence_levels.append(confidence)
        insufficient |= blocks

    def condition(kind, field, claim_ids=(), **details):
        entry = {"kind": kind, "field": field, **details, "claim_ids": list(dict.fromkeys(claim_ids))}
        if entry not in conditions:
            conditions.append(entry)

    def evidence_support(refs, cycle):
        """Every ID must resolve; duplicate unusable audit entries stay blocking."""
        if not refs:
            return False, "D"
        levels, usable = ["A"], True
        for ref in refs:
            claims = [c for c in audit.get("claims", []) if isinstance(c, dict)
                      and isinstance(c.get("record"), dict) and c["record"].get("claim_id") == ref]
            if len(claims) != 1:
                levels.append("D")
                usable = False
            for claim in claims:
                record = claim["record"]
                status = claim.get("effective_status")
                if (claim.get("valid") is not True or record.get("candidate_id") != candidate_id
                        or type(cycle) is not int or type(record.get("applicable_admission_year")) is not int
                        or record["applicable_admission_year"] != cycle
                        or status in {"missing", "conflicted", "invalid"}
                        or claim.get("conflict_groups")
                        or (record.get("value") is None and status != "not_applicable")
                        or claim.get("age_days", 0) < 0):
                    usable = False
                    levels.append("D")
                elif record.get("tier") in {"T3", "T4"}:
                    usable = False
                    levels.append("C")
                elif claim.get("stale") is not False or status == "stale":
                    usable = False
                    levels.append("B")
                elif record.get("tier") not in {"T1", "T2"} or status not in {"confirmed", "not_applicable"}:
                    usable = False
                    levels.append("D")
        return usable, max(levels)

    explicit = eligibility_result.get("eligibility", "unknown")
    scored = scoring.get("eligibility", "unknown")
    if explicit not in {"pass", "fail", "unknown"} or scored not in {"pass", "fail", "unknown"}:
        raise ValueError("eligibility must be pass, fail, or unknown")
    eligibility = "fail" if "fail" in {explicit, scored} else explicit
    if eligibility == "unknown":
        concern("eligibility_unresolved")
    elif explicit != scored and scoring:
        concern("eligibility_results_disagree")
    for gate in eligibility_result.get("unknown_critical_gates", []):
        condition("eligibility_gate", gate)

    items_by_target = material.get("items_by_target", {})
    if not isinstance(items_by_target, dict):
        raise ValueError("material_audit items_by_target must be an object")
    items = items_by_target.get(candidate_id, [])
    readiness = "complete" if candidate_id in items_by_target else "materially_incomplete"
    if candidate_id not in items_by_target:
        concern("target_material_requirements_missing", blocks=True)
        condition("current_target_evidence", "material_requirements")
    for item in items:
        if item.get("target_id") != candidate_id:
            raise ValueError("material item target_id must match selected target")
        status = item.get("status")
        if status not in READINESS | {"not_applicable"}:
            raise ValueError("invalid material item status")
        if item.get("necessity") not in {"required", "conditional"} or status == "not_applicable":
            continue
        readiness = max((readiness, status), key=READINESS_ORDER.get)
        if status != "complete":
            uncertainties.append("material_unresolved:" + item["requirement_id"])
            for field in item.get("missing_conditions", []):
                condition("material_condition", field, item.get("source_claim_ids", []),
                          requirement_id=item["requirement_id"])
    for conflict in material.get("contradictions", []):
        field = conflict.get("field")
        if conflict.get("scope", "applicant") == "applicant" and field in critical:
            concern("critical_applicant_conflict:" + field, blocks=True)
            condition("applicant_conflict", field, [c["claim_id"] for c in conflict.get("claims", [])])

    audited_claims = [c for c in audit.get("claims", []) if isinstance(c, dict)
                      and isinstance(c.get("record"), dict)
                      and c["record"].get("candidate_id") == candidate_id
                      and c["record"].get("applicable_admission_year") == year]
    for field in sorted(critical):
        field_claims = [c for c in audited_claims if c["record"].get("field") == field]
        conflicted = [c for c in field_claims
                      if c.get("effective_status") == "conflicted" or c.get("conflict_groups")]
        if conflicted:
            group_ids = {group for c in conflicted for group in c.get("conflict_groups", [])}
            related = [c for c in field_claims if c in conflicted or group_ids.intersection(c.get("conflict_groups", []))]
            claim_ids = list(dict.fromkeys(c["record"].get("claim_id") for c in related
                                           if isinstance(c["record"].get("claim_id"), str)))
            concern("critical_applicant_conflict:" + field, "D", blocks=True)
            condition("applicant_conflict", field, claim_ids)

    summary = audit.get("candidate_summary", {}).get(candidate_id, {})
    for name, confidence in (("target_evidence_confidence", summary.get("confidence", "D")),
                             ("candidate_scoring_confidence", scoring.get("evidence_confidence", "D"))):
        if confidence not in CONFIDENCE:
            raise ValueError("upstream confidence must be A, B, C, or D")
        confidence_levels.append(confidence)
        if confidence != "A":
            concern(name + ":" + confidence, confidence)
    for field in sorted(CRITICAL_FIELDS):
        current = [c["record"]["claim_id"] for c in audit.get("claims", [])
                   if isinstance(c, dict) and isinstance(c.get("record"), dict)
                   and c["record"].get("candidate_id") == candidate_id and c["record"].get("field") == field
                   and c["record"].get("applicable_admission_year") == year]
        usable, confidence = evidence_support(current, year)
        if not usable:
            concern("current_target_evidence_unusable:" + field, confidence, blocks=True)
            condition("current_target_evidence", field, current)
    for item in items:
        refs = item.get("source_claim_ids", [])
        refs_valid = isinstance(refs, list) and all(isinstance(ref, str) and ref for ref in refs)
        if not refs_valid:
            refs = []
        binding = item.get("policy_binding")
        expected_binding = {key: deepcopy(item[key]) for key in
                            ("requirement_id", "target_id", "item_type", "necessity") if key in item}
        if isinstance(item.get("conditions"), dict):
            expected_binding["conditions"] = deepcopy(item["conditions"])
        if "applies_when" in item:
            expected_binding["applies_when"] = deepcopy(item["applies_when"])
        semantic_binding_valid = (isinstance(binding, dict) and _typed_equal(binding, expected_binding)
                                  and item.get("target_id") == candidate_id and refs_valid and bool(refs))
        for ref in refs:
            usable, confidence = evidence_support([ref], year)
            claims = [c for c in audit.get("claims", []) if isinstance(c, dict)
                      and isinstance(c.get("record"), dict)
                      and c["record"].get("claim_id") == ref]
            if not usable:
                concern("current_target_evidence_unusable:" + ref, confidence, blocks=True)
                condition("current_target_evidence", ref, [ref])
            if (len(claims) != 1 or
                    claims[0]["record"].get("field") != "material_requirement_policy" or
                    not _typed_equal(claims[0]["record"].get("value"), expected_binding)):
                semantic_binding_valid = False
        if not semantic_binding_valid:
            requirement_id = item.get("requirement_id", "unknown")
            concern("requirement_policy_unbound:" + requirement_id, "D", blocks=True)
            condition("requirement_policy", requirement_id, refs)

    selected_scope = payload.get("target_scope", {})
    try:
        selected_key = scope_key(selected_scope)
    except (ValueError, AttributeError):
        selected_key = None
    scopes = []
    for group in historical.get("scopes", []):
        if selected_key is None or scope_key(group.get("scope", {})) != selected_key:
            continue
        # Reconstruct only allowlisted aggregates; extra keys/row identities and
        # a tampered descriptive ratio cannot be forwarded into the report.
        rows = [{k: deepcopy(v) for k, v in row.items()
                 if k in set(SCOPE_FIELDS) | set(PROVENANCE_FIELDS) | {"stage", "count"}}
                for row in group.get("counts", [])]
        reconstructed = calculate_stage_metrics(rows)
        if any(scope_key(g["scope"]) != selected_key for g in reconstructed["scopes"]):
            raise ValueError("historical group counts must match their scope")
        scopes.extend(reconstructed["scopes"])
    comparable = False
    for group in scopes:
        expected_counts = {}
        for row in group["counts"]:
            for ref in row.get("claim_ids", []):
                expected_counts.setdefault(ref, []).append(row)
        for metric in group["metrics"]:
            usable, confidence = evidence_support(metric["claim_ids"], group["scope"]["admission_year"])
            for ref in metric["claim_ids"]:
                claims = [c for c in audit.get("claims", []) if isinstance(c, dict)
                          and isinstance(c.get("record"), dict)
                          and c["record"].get("claim_id") == ref]
                expected_rows = expected_counts.get(ref, [])
                if (len(claims) != 1 or len(expected_rows) != 1
                        or claims[0]["record"].get("field") != "historical_count"
                        or claims[0]["record"].get("value") != {
                            **group["scope"], "stage": expected_rows[0]["stage"],
                            "count": expected_rows[0]["count"]}):
                    usable, confidence = False, "D"
                    concern("historical_evidence_payload_mismatch", "D")
            comparable |= usable
            if not usable:
                concern("historical_evidence_unusable", confidence)
                condition("historical_evidence", "scoped_stage_counts", metric["claim_ids"])
        for rejected in group["rejected"]:
            if rejected["reason"] in {"missing_denominator", "attendance_unconfirmed", "zero_denominator"}:
                condition("historical_denominator", "confirmed_attended", rejected["claim_ids"])
    if not comparable:
        insufficient = True
        if not any(group["metrics"] for group in scopes):
            concern("no_comparable_cohort", blocks=True)
            if not any(entry["kind"] == "historical_denominator" for entry in conditions):
                condition("historical_cohort", "exact_scope_stage_counts")

    inputs = scoring.get("grouping_inputs", {})
    position = inputs.get("competitive_position")
    if position is None:
        concern("competitive_position_missing", blocks=True)
        condition("competitive_evidence", "competitive_position")
        band = "evidence_insufficient"
    else:
        position = _score(position, "competitive_position")
        band = "strong" if position >= 80 else "competitive" if position >= 60 else "borderline" if position >= 40 else "weak"
    if insufficient:
        band = "evidence_insufficient"
    if "score" not in fit:
        concern("program_fit_missing")
    reasons = fit.get("reasons", [])
    if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
        raise ValueError("fit reasons must be an array of strings")
    return {"eligibility": eligibility, "packet_readiness": readiness,
            "competitive_position": band,
            "program_fit": {"score": _score(fit.get("score", 0.0), "program_fit"), "reasons": deepcopy(reasons)},
            "evidence_confidence": max(confidence_levels),
            "historical_context": {"scopes": scopes,
                                   "rejected": [deepcopy(r) for group in scopes for r in group["rejected"]],
                                   "descriptive_only": True},
            "uncertainties": list(dict.fromkeys(uncertainties)), "band_change_conditions": conditions}
