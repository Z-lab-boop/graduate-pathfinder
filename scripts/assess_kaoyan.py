"""Evidence-bound subject gates and scoped score comparisons, never probabilities."""
from copy import deepcopy
from datetime import datetime, timezone
import math
import unicodedata

from .validate_case import validate_evidence
from .rank_candidates import evaluate_gates
from .audit_evidence import CRITICAL_FIELDS

RISK_BANDS = {"reach", "match", "conservative", "monitor", "excluded"}

THRESHOLD_SCOPES = {
    "national", "institution", "unit", "program", "direction", "admitted_distribution",
}
IDENTITY_FIELDS = {
    "national": (), "institution": ("institution",),
    "unit": ("institution", "unit"),
    "program": ("institution", "unit", "program_code"),
    "direction": ("institution", "unit", "program_code", "research_track"),
    "admitted_distribution": ("institution", "unit", "program_code"),
}
APPLICABILITY_FIELDS = {
    "institution", "unit", "program_code", "research_track", "degree_type",
    "round", "area", "category", "study_mode", "special_plan",
}
THRESHOLD_PAYLOAD_FIELDS = {
    "year", "scope", "total", "population", "statistic", "subject_minimums", "subject_codes",
} | APPLICABILITY_FIELDS
THRESHOLD_METADATA_FIELDS = {"source_ref", "evidence", "notes"}


def _typed_equal(left, right):
    """JSON payload equality without bool/int or nested int/float coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_typed_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def _audit_binding(record, evidence_audit, prefix):
    """Resolve the consumed raw record against every audit entry with its ID."""
    claims = evidence_audit.get("claims", []) if isinstance(evidence_audit, dict) else []
    matches = [claim for claim in claims if isinstance(claim, dict)
               and isinstance(claim.get("record"), dict)
               and isinstance(record, dict) and _text(record.get("claim_id"))
               and claim["record"].get("claim_id") == record["claim_id"]] if isinstance(claims, list) else []
    if not matches:
        return [prefix + "_audit_claim_missing"]
    if any(not _typed_equal(claim["record"], record) for claim in matches):
        return [prefix + "_audit_payload_mismatch"]
    if any(claim.get("valid") is not True or claim.get("effective_status") != "confirmed"
           or claim.get("stale") is not False or claim.get("conflict_groups") != [] for claim in matches):
        return [prefix + "_audit_claim_unusable"]
    return []


def _unsupported_threshold_fields(record):
    return [k for k, v in record.items()
            if k not in THRESHOLD_PAYLOAD_FIELDS | THRESHOLD_METADATA_FIELDS and v is not None]


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _codes(value):
    if not isinstance(value, list) or not value or not all(_text(v) for v in value):
        return None
    return [unicodedata.normalize("NFKC", v).strip() for v in value]


def _now(profile):
    value = profile.get("audit_at")
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("audit_at must have a timezone")
    return parsed


def _official(record, year, now, candidate_id=None):
    """Current means confirmed T1/T2, applicable year, and age 0..365 days."""
    if not isinstance(record, dict) or validate_evidence(record):
        return False
    if record["tier"] not in {"T1", "T2"} or record["status"] != "confirmed":
        return False
    if record.get("effective_status", "confirmed") != "confirmed":
        return False
    if record.get("stale", False) or record.get("conflict_groups"):
        return False
    if type(record.get("applicable_admission_year")) is not int or record["applicable_admission_year"] != year:
        return False
    if candidate_id is not None and record["candidate_id"] != candidate_id:
        return False
    retrieved = datetime.fromisoformat(record["retrieved_at"].replace("Z", "+00:00"))
    age = (now.date() - retrieved.date()).days
    published = record.get("published_at")
    return 0 <= age <= 365 and (published is None or datetime.fromisoformat(published).date() <= now.date())


def _subject_support(owner, year, now, candidate_id=None, evidence_audit=None):
    combination = owner.get("subject_combination")
    if not isinstance(combination, dict):
        return None, [], "missing_subject_combination"
    codes = _codes(combination.get("codes"))
    records = combination.get("evidence")
    if codes is None or not isinstance(records, list) or not records:
        return codes, [], "missing_codes_or_evidence"
    usable = []
    refs = [r.get("claim_id") for r in records if isinstance(r, dict) and _text(r.get("claim_id"))]
    # Preserve disagreements instead of selecting one favorable record.
    for record in records:
        if evidence_audit is not None:
            reasons = _audit_binding(record, evidence_audit, "subject")
            if reasons:
                return codes, refs, reasons[0]
        if not _official(record, year, now, candidate_id) or _codes(record.get("value")) != codes:
            return codes, refs, "unconfirmed_stale_or_conflicting_subject_evidence"
        usable.append(record["claim_id"])
    return codes, usable, None


def validate_subject_match(profile: dict, candidate: dict, evidence_audit: dict | None = None) -> dict:
    """Bind a supplied full audit; omitted audit is legacy direct-call checking."""
    result = {"status": "unknown", "differences": [], "switch_required": False,
              "profile_codes": None, "candidate_codes": None, "source_refs": [], "reasons": [],
              "evidence_records": {name: deepcopy(owner["subject_combination"].get("evidence"))
                                   if isinstance(owner.get("subject_combination"), dict) else None
                                   for name, owner in (("profile", profile), ("candidate", candidate))}}
    if profile.get("pathway") != "kaoyan" or candidate.get("pathway") != "kaoyan":
        result["reasons"].append("kaoyan_pathway_required")
        return result
    year = profile.get("admission_year")
    if type(year) is not int or candidate.get("admission_year") != year:
        result["reasons"].append("admission_year_mismatch_or_missing")
        return result
    try:
        now = _now(profile)
    except (ValueError, TypeError, AttributeError):
        result["reasons"].append("invalid_audit_at")
        return result
    p_codes, p_refs, p_reason = _subject_support(profile, year, now, evidence_audit=evidence_audit)
    c_codes, c_refs, c_reason = _subject_support(candidate, year, now, candidate.get("candidate_id"), evidence_audit)
    result.update(profile_codes=p_codes, candidate_codes=c_codes, source_refs=p_refs + c_refs)
    if p_codes and c_codes:
        for index in range(max(len(p_codes), len(c_codes))):
            left = p_codes[index] if index < len(p_codes) else None
            right = c_codes[index] if index < len(c_codes) else None
            if left != right:
                result["differences"].append({"position": index + 1, "profile_code": left, "candidate_code": right})
    result["reasons"] = [r for r in (p_reason, c_reason) if r]
    if result["reasons"]:
        return result
    result["switch_required"] = bool(result["differences"])
    willingness = profile.get("preferences", {}).get("willing_to_switch_subjects") is True
    result["status"] = "pass" if not result["differences"] or willingness else "fail"
    result["reasons"] = ["exact_subject_match" if not result["differences"] else (
        "explicit_subject_switch_accepted" if willingness else "subject_switch_not_accepted")]
    return result


def classify_threshold(record: dict) -> dict:
    """Validate shape and preserve source data; classification is not verification."""
    if not isinstance(record, dict):
        raise ValueError("threshold must be an object")
    if type(record.get("year")) is not int or record["year"] <= 0:
        raise ValueError("threshold year must be a positive integer")
    if not _text(record.get("scope")) or record["scope"] not in THRESHOLD_SCOPES:
        raise ValueError("unknown threshold scope")
    if not _number(record.get("total")) or not _text(record.get("source_ref")):
        raise ValueError("threshold requires a finite nonnegative total and source_ref")
    if record["scope"] == "admitted_distribution" and not _text(record.get("statistic")):
        raise ValueError("admitted_distribution requires a named statistic")
    unsupported = _unsupported_threshold_fields(record)
    if unsupported:
        raise ValueError("unsupported_threshold_qualifiers:" + ",".join(sorted(unsupported)))
    if record.get("study_mode") is not None and record["study_mode"] not in ("full-time", "part-time"):
        raise ValueError("study_mode must be full-time or part-time")
    minimums = record.get("subject_minimums", {})
    if not isinstance(minimums, dict) or any(not _text(k) or not _number(v) for k, v in minimums.items()):
        raise ValueError("subject_minimums must map subject codes to finite nonnegative scores")
    normalized = [unicodedata.normalize("NFKC", k).strip() for k in minimums]
    if len(set(normalized)) != len(normalized):
        raise ValueError("subject_minimums contain duplicate normalized codes")
    result = deepcopy(record)
    result["is_program_specific"] = record["scope"] in {"program", "direction"}
    result["descriptive_only"] = record["scope"] == "admitted_distribution"
    return result


def _range(value):
    if not isinstance(value, list) or len(value) != 2 or not all(_number(v) for v in value):
        return None
    return value if value[0] <= value[1] else None


def _margin_status(margin):
    return "above" if margin[0] > 0 else ("below" if margin[1] < 0 else "overlaps")


def compare_score_scenario(profile: dict, candidate: dict, evidence_audit: dict | None = None) -> dict:
    """Bind supplied audit and compare only the explicit year/scope/population."""
    result = {"status": "insufficient_evidence", "comparisons": [], "excluded_thresholds": [], "reasons": []}
    if profile.get("pathway") != "kaoyan" or candidate.get("pathway") != "kaoyan":
        result["reasons"] = ["kaoyan_pathway_required"]
        return result
    if candidate.get("applicability") is not None:
        result["reasons"] = ["unsupported_candidate_applicability_qualifiers"]
        return result
    scenario = profile.get("score_scenario")
    if (not isinstance(scenario, dict) or type(scenario.get("year")) is not int
            or not _text(scenario.get("scope")) or scenario["scope"] not in THRESHOLD_SCOPES
            or _range(scenario.get("total")) is None):
        result["reasons"] = ["missing_or_invalid_score_scenario"]
        return result
    match = validate_subject_match(profile, candidate, evidence_audit)
    result["subject_match"] = match
    scenario_codes = _codes(scenario.get("subject_codes", match["profile_codes"]))
    if match["status"] != "pass" or scenario_codes != match["candidate_codes"]:
        result["reasons"] = ["confirmed_compatible_subject_scenario_required"]
        return result
    try:
        now = _now(profile)
    except (ValueError, TypeError, AttributeError):
        result["reasons"] = ["invalid_audit_at"]
        return result
    records = candidate.get("thresholds", [])
    if not isinstance(records, list) or not records:
        result["reasons"] = ["no_threshold_records"]
        return result
    binding_failed = False
    for raw in records:
        reasons = []
        try:
            threshold = classify_threshold(raw)
        except ValueError as exc:
            result["excluded_thresholds"].append({"threshold": deepcopy(raw), "reasons": [str(exc)]})
            continue
        for field in ("year", "scope", "population"):
            if threshold.get(field) != scenario.get(field):
                reasons.append(field + "_mismatch")
        if not _text(threshold.get("population")) or not _text(scenario.get("population")):
            reasons.append("population_definition_required")
        if threshold["descriptive_only"] and threshold.get("statistic") != scenario.get("statistic"):
            reasons.append("statistic_mismatch")
        if _codes(threshold.get("subject_codes")) != scenario_codes:
            reasons.append("source_backed_full_subject_applicability_required")
        if any(unicodedata.normalize("NFKC", code).strip() not in scenario_codes
               for code in threshold.get("subject_minimums", {})):
            reasons.append("threshold_subject_combination_mismatch")
        for field in IDENTITY_FIELDS[threshold["scope"]]:
            if not _text(threshold.get(field)) or threshold[field] != candidate.get(field):
                reasons.append(field + "_mismatch_or_missing")
        if threshold["scope"] == "national":
            for field in ("area", "category"):
                if not _text(threshold.get(field)) or not _text(candidate.get(field)):
                    reasons.append("national_" + field + "_applicability_required")
        for field in sorted(APPLICABILITY_FIELDS):
            if threshold.get(field) is not None and (
                    not _text(threshold[field]) or not _typed_equal(threshold[field], candidate.get(field))):
                reasons.append(field + "_mismatch")
        ev = threshold.get("evidence")
        if evidence_audit is not None:
            binding_reasons = _audit_binding(ev, evidence_audit, "threshold")
            reasons.extend(binding_reasons)
            if binding_reasons and threshold["year"] == scenario["year"] and threshold["scope"] == scenario["scope"]:
                binding_failed = True
        if (not _official(ev, threshold["year"], now, candidate.get("candidate_id"))
                or ev.get("claim_id") != threshold["source_ref"]):
            reasons.append("current_official_threshold_evidence_required")
        expected_value = {k: v for k, v in raw.items() if k in THRESHOLD_PAYLOAD_FIELDS}
        source_value = ev.get("value") if isinstance(ev, dict) else None
        source_payload = {k: v for k, v in source_value.items() if k in THRESHOLD_PAYLOAD_FIELDS} if isinstance(source_value, dict) else None
        if isinstance(source_value, dict) and _unsupported_threshold_fields(source_value):
            reasons.append("unsupported_source_threshold_qualifiers")
        if not _typed_equal(source_payload, expected_value):
            reasons.append("threshold_content_not_supported_by_source")
        if reasons:
            result["excluded_thresholds"].append({"threshold": threshold, "reasons": reasons})
            continue
        margins = [v - threshold["total"] for v in scenario["total"]]
        comparison = {"threshold": threshold, "total_margin": margins, "subject_margins": {},
                      "status": "insufficient_evidence", "descriptive_only": threshold["descriptive_only"], "reasons": []}
        subjects = scenario.get("subjects", {})
        statuses = [_margin_status(margins)]
        for code, minimum in threshold.get("subject_minimums", {}).items():
            values = _range(subjects.get(code)) if isinstance(subjects, dict) else None
            if values is None:
                comparison["reasons"].append("missing_or_invalid_subject_range:" + code)
            else:
                margin = [v - minimum for v in values]
                comparison["subject_margins"][code] = margin
                statuses.append(_margin_status(margin))
        if not comparison["reasons"]:
            comparison["status"] = "below" if "below" in statuses else ("overlaps" if "overlaps" in statuses else "above")
        result["comparisons"].append(comparison)
    statuses = [c["status"] for c in result["comparisons"]]
    if binding_failed:
        result["reasons"] = ["consumed_threshold_audit_binding_failed"]
    elif statuses and "insufficient_evidence" not in statuses:
        result["status"] = statuses[0] if len(set(statuses)) == 1 else "insufficient_evidence"
        result["reasons"] = ["compatible_scoped_comparison" if len(set(statuses)) == 1 else "conflicting_compatible_thresholds"]
    else:
        result["reasons"] = ["no_complete_compatible_threshold_comparison"]
    return result


def _audited_gates(profile, candidate, evidence_audit):
    """Keep declared gates, and downgrade labels when any basis is unusable."""
    raw_gates = candidate.get("gates", [])
    evaluate_gates(raw_gates)  # Retain the shared gate shape contract.
    gates = deepcopy(raw_gates)
    bindings = []
    for raw_gate, gate in zip(raw_gates, gates):
        records = gate.get("evidence", [])
        reasons = []
        refs = gate.get("source_refs", [])
        if not isinstance(refs, list) or any(not _text(ref) for ref in refs):
            reasons.append("gate_source_refs_invalid")
            refs = []
        refs = list(refs)
        bases = candidate.get("gate_bases", {})
        basis = bases.get(gate["gate_id"]) if isinstance(bases, dict) else None
        if basis is not None:
            if _text(basis):
                refs.append(basis)
            else:
                reasons.append("gate_basis_invalid")
        if not isinstance(records, list) or not records:
            reasons.append("gate_raw_evidence_missing")
            records = []
        refs.extend(record.get("claim_id") for record in records
                    if isinstance(record, dict) and _text(record.get("claim_id")))
        for record in records:
            reasons.extend(_audit_binding(record, evidence_audit, "gate"))
            try:
                official = _official(record, profile.get("admission_year"), _now(profile), candidate["candidate_id"])
            except (ValueError, TypeError, AttributeError):
                official = False
            if not official:
                reasons.append("current_official_gate_evidence_required")
        record_refs = {record.get("claim_id") for record in records if isinstance(record, dict)
                       and _text(record.get("claim_id"))}
        if not refs or any(ref not in record_refs for ref in refs):
            reasons.append("gate_referenced_claim_missing")
        if reasons:
            gate["status"] = "unknown"
            gate["evidence_status"] = "missing"
        bindings.append({"gate": deepcopy(raw_gate),
                         "source_refs": sorted(set(refs)), "reasons": sorted(set(reasons))})
    result = evaluate_gates(gates)
    result["audit_bindings"] = bindings
    return result


def assess_kaoyan_candidate(profile: dict, candidate: dict, evidence_audit: dict) -> dict:
    """Build decision bands, never admission probabilities or guarantees.

    Candidate extensions: current_catalog is a current official availability
    evidence record; historical_volatility/retest_risk are low/medium/high (an
    unknown value blocks banding); fit_score is a user decision score in 0..100.
    evidence_audit must be a full v0.1 audit report to resolve current critical
    claims; summary-only maps remain monitor with missing-provenance reasons.
    A conservative band requires total lower margin >=20, fit >=60, A/B
    confidence, low volatility, and non-high retest risk. These are explicit
    decision rules, not empirically calibrated admissions cutoffs.
    """
    candidate_id = candidate.get("candidate_id")
    if not _text(candidate_id):
        raise ValueError("candidate_id must be a non-empty string")
    # Passing even an empty audit is deliberate: legacy direct calls cannot
    # supply non-audited evidence to an assessment.
    if not isinstance(evidence_audit, dict):
        evidence_audit = {}
    subject_match = validate_subject_match(profile, candidate, evidence_audit)
    score_scenario = compare_score_scenario(profile, candidate, evidence_audit)
    summary_map = evidence_audit.get("candidate_summary", evidence_audit)
    summary = summary_map.get(candidate_id, {}) if isinstance(summary_map, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    confidence = summary.get("confidence")
    declared = candidate.get("evidence_confidence")
    if confidence in {"A", "B", "C", "D"} and declared in {"A", "B", "C", "D"}:
        confidence = max(confidence, declared)
    else:
        confidence = "D"
    result = {
        "candidate_id": candidate_id, "risk_band": "monitor",
        "subject_match": subject_match, "score_scenario": score_scenario,
        "historical_volatility": candidate.get("historical_volatility"),
        "retest_risk": candidate.get("retest_risk"), "fit_score": candidate.get("fit_score"),
        "evidence_confidence": confidence, "data_completeness": candidate.get("data_completeness"),
        "sensitivity": deepcopy(candidate.get("sensitivity")), "reasons": [], "source_refs": [],
    }
    refs = list(subject_match["source_refs"])
    for comparison in score_scenario["comparisons"]:
        refs.append(comparison["threshold"]["source_ref"])
    for excluded in score_scenario["excluded_thresholds"]:
        threshold = excluded["threshold"]
        if isinstance(threshold, dict):
            refs.append(threshold.get("source_ref"))
    catalog = candidate.get("current_catalog")
    if isinstance(catalog, dict):
        refs.append(catalog.get("claim_id"))
    gates = _audited_gates(profile, candidate, evidence_audit)
    result["gate_evaluation"] = gates
    refs.extend(ref for binding in gates["audit_bindings"] for ref in binding["source_refs"])
    for claim in evidence_audit.get("claims", []):
        record = claim.get("record", {}) if isinstance(claim, dict) else {}
        if isinstance(record, dict) and record.get("candidate_id") == candidate_id:
            refs.append(record.get("claim_id"))
    result["source_refs"] = sorted({ref for ref in refs if _text(ref)})
    if subject_match["status"] == "fail":
        result.update(risk_band="excluded", reasons=["confirmed_subject_mismatch"])
        return result
    if gates["eligibility"] == "fail":
        result.update(risk_band="excluded", reasons=["confirmed_gate_failure"])
        return result
    reasons = result["reasons"]
    if subject_match["status"] != "pass":
        reasons.append("current_subjects_unknown")
    try:
        catalog_known = (_official(catalog, profile.get("admission_year"), _now(profile), candidate_id)
                         and catalog.get("field") == "program_availability"
                         and catalog.get("value") is True)
    except (ValueError, TypeError, AttributeError):
        catalog_known = False
    if not catalog_known:
        reasons.append("current_catalog_unknown")
    claims = evidence_audit.get("claims", [])
    if isinstance(catalog, dict) and _text(catalog.get("claim_id")):
        reasons.extend(_audit_binding(catalog, evidence_audit, "current_catalog"))
    try:
        if any(isinstance(claim, dict) and isinstance(claim.get("record"), dict)
               and claim["record"].get("field") == "program_availability"
               and claim["record"].get("value") is False
               and _official(claim["record"], profile.get("admission_year"), _now(profile), candidate_id)
               for claim in claims):
            reasons.append("current_catalog_conflicting_official_availability")
    except (ValueError, TypeError, AttributeError):
        reasons.append("current_catalog_audit_claim_unusable")
    if gates["eligibility"] != "pass":
        reasons.append("critical_gates_unknown")
    if any(binding["reasons"] for binding in gates["audit_bindings"]):
        reasons.append("gate_audit_binding_failed")
    fields = summary.get("critical_fields", {})
    fields_known = isinstance(fields, dict) and all(
        isinstance(fields.get(field), dict) and fields[field].get("fresh_official_record_indexes")
        and fields[field].get("missing") is False and fields[field].get("conflicted") is False
        for field in CRITICAL_FIELDS)
    if "claims" not in evidence_audit:
        reasons.append("current_critical_source_provenance_missing")
        fields_known = False
    if "claims" in evidence_audit and fields_known:
        try:
            claims = evidence_audit["claims"]
            fields_known = all(any(
                isinstance(claim, dict) and isinstance(claim.get("record"), dict)
                and claim["record"].get("field") == field
                and claim["record"].get("value") is not None
                and claim.get("valid") is True
                and claim.get("effective_status") == "confirmed"
                and not claim.get("stale") and not claim.get("conflict_groups")
                and _official(claim["record"], profile.get("admission_year"), _now(profile), candidate_id)
                for claim in claims) for field in CRITICAL_FIELDS)
        except (ValueError, TypeError, AttributeError):
            fields_known = False
    if (not fields_known or any(summary.get(field) for field in
                           ("missing_critical_fields", "conflicted_critical_fields",
                            "invalid_record_indexes", "stale_official_fields", "secondary_only_fields"))):
        reasons.append("critical_current_fields_unknown")
    if confidence == "D":
        reasons.append("evidence_confidence_D")
    completeness = result["data_completeness"]
    if not _number(completeness) or not 0.70 <= completeness <= 1:
        reasons.append("data_completeness_below_0_70_or_unknown")
    fit = result["fit_score"]
    if not _number(fit) or not 60 <= fit <= 100:
        reasons.append("fit_below_60_or_unknown")
    for field in ("historical_volatility", "retest_risk"):
        if result[field] not in ("low", "medium", "high"):
            reasons.append(field + "_unknown")
    if (score_scenario["status"] not in {"above", "overlaps", "below"}
            or any(c["descriptive_only"] for c in score_scenario["comparisons"])):
        reasons.append("compatible_nondescriptive_score_comparison_required")
    if reasons:
        return result
    status = score_scenario["status"]
    high_risk = result["historical_volatility"] == "high" or result["retest_risk"] == "high"
    if status == "below" or high_risk:
        result.update(risk_band="reach", reasons=["score_below_scoped_threshold" if status == "below"
                                                  else "high_volatility_or_retest_risk"])
    elif (status == "above" and confidence in {"A", "B"}
          and result["historical_volatility"] == "low"
          and all(c["total_margin"][0] >= 20 for c in score_scenario["comparisons"])):
        result.update(risk_band="conservative", reasons=["strong_margin_adequate_fit_and_evidence"])
    else:
        result.update(risk_band="match", reasons=["compatible_score_with_moderate_conditions"])
    return result


def build_kaoyan_shortlist(results: dict[str, dict]) -> dict:
    """Select by fit after sensitivity checks, preserving unresolved choices.

    Input is candidate-ID keyed assessment output. All highest-fit match or
    conservative targets' sensitivity uses v0.1 stability/winner_set. Their
    winner sets are merged and intersected with eligible targets; missing checks
    require a user decision. A fit tie never uses ID order as a winner rule.
    """
    if not isinstance(results, dict):
        raise ValueError("results must be a candidate-ID mapping")
    for cid, item in results.items():
        if not _text(cid) or not isinstance(item, dict) or item.get("candidate_id") != cid:
            raise ValueError("result key must match candidate_id")
        if item.get("risk_band") not in RISK_BANDS:
            raise ValueError("unknown risk_band")
        if item["risk_band"] in {"match", "conservative", "reach"} and (
                not _number(item.get("fit_score")) or item["fit_score"] > 100):
            raise ValueError("eligible result requires a finite fit_score in 0..100")
    ordered = sorted(results, key=lambda cid: (
        -results[cid]["fit_score"] if _number(results[cid].get("fit_score")) else 0, cid))
    eligible = [cid for cid in ordered if results[cid]["risk_band"] in {"match", "conservative"}]
    shortlist = {"primary": None, "decision_set": [], "requires_user_decision": False,
                 "alternatives": [], "monitor": sorted(cid for cid in results if results[cid]["risk_band"] == "monitor"),
                 "excluded": sorted(cid for cid in results if results[cid]["risk_band"] == "excluded"),
                 "reasons": []}
    if eligible:
        top = eligible[0]
        tied = [cid for cid in eligible if results[cid]["fit_score"] == results[top]["fit_score"]]
        sensitivity = results[top].get("sensitivity")
        stability = sensitivity.get("stability") if isinstance(sensitivity, dict) else None
        tied_checks = [results[cid].get("sensitivity") for cid in tied]
        winners = set()
        for check in tied_checks:
            candidate_winners = check.get("winner_set", []) if isinstance(check, dict) else []
            if isinstance(candidate_winners, list) and all(_text(cid) for cid in candidate_winners):
                winners.update(candidate_winners)
        if any(isinstance(check, dict) and check.get("stability") == "fragile" for check in tied_checks):
            choices = [cid for cid in eligible if cid in tied or cid in winners]
            # An incomplete fragile set cannot justify a single apparent winner.
            if len(choices) < 2:
                choices = eligible
            shortlist.update(decision_set=choices, requires_user_decision=True, reasons=["fragile_top_choice"])
        elif len(tied) > 1:
            choices = [cid for cid in eligible if cid in tied or cid in winners]
            shortlist.update(decision_set=choices, requires_user_decision=True, reasons=["equal_fit_top_choices"])
        elif stability == "stable" and sensitivity.get("winner_set") == [top] and (
                "baseline_order" not in sensitivity or
                isinstance(sensitivity["baseline_order"], list) and sensitivity["baseline_order"][:1] == [top]):
            shortlist.update(primary=top, reasons=["stable_highest_fit_eligible_target"])
        else:
            shortlist.update(decision_set=eligible, requires_user_decision=True,
                             reasons=["sensitivity_missing_or_insufficient"])
    else:
        shortlist["reasons"] = ["no_eligible_match_or_conservative_target"]
    selected = set(shortlist["decision_set"] + ([shortlist["primary"]] if shortlist["primary"] else []))
    shortlist["alternatives"] = [cid for cid in ordered if results[cid]["risk_band"] in
                                 {"reach", "match", "conservative"} and cid not in selected]
    return shortlist
