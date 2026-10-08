"""Evidence-bound subject gates and scoped score comparisons, never probabilities."""
from copy import deepcopy
from datetime import datetime, timezone
import math
import unicodedata

from .validate_case import validate_evidence

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


def _subject_support(owner, year, now, candidate_id=None):
    combination = owner.get("subject_combination")
    if not isinstance(combination, dict):
        return None, [], "missing_subject_combination"
    codes = _codes(combination.get("codes"))
    records = combination.get("evidence")
    if codes is None or not isinstance(records, list) or not records:
        return codes, [], "missing_codes_or_evidence"
    usable = []
    # Preserve disagreements instead of selecting one favorable record.
    for record in records:
        if not _official(record, year, now, candidate_id) or _codes(record.get("value")) != codes:
            return codes, [], "unconfirmed_stale_or_conflicting_subject_evidence"
        usable.append(record["claim_id"])
    return codes, usable, None


def validate_subject_match(profile: dict, candidate: dict) -> dict:
    """A willingness gate may accept a switch, but never repairs absent evidence."""
    result = {"status": "unknown", "differences": [], "switch_required": False,
              "profile_codes": None, "candidate_codes": None, "source_refs": [], "reasons": []}
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
    p_codes, p_refs, p_reason = _subject_support(profile, year, now)
    c_codes, c_refs, c_reason = _subject_support(candidate, year, now, candidate.get("candidate_id"))
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


def compare_score_scenario(profile: dict, candidate: dict) -> dict:
    """Compare an explicitly selected year/scope/population without future inference."""
    result = {"status": "insufficient_evidence", "comparisons": [], "excluded_thresholds": [], "reasons": []}
    if profile.get("pathway") != "kaoyan" or candidate.get("pathway") != "kaoyan":
        result["reasons"] = ["kaoyan_pathway_required"]
        return result
    scenario = profile.get("score_scenario")
    if (not isinstance(scenario, dict) or type(scenario.get("year")) is not int
            or not _text(scenario.get("scope")) or scenario["scope"] not in THRESHOLD_SCOPES
            or _range(scenario.get("total")) is None):
        result["reasons"] = ["missing_or_invalid_score_scenario"]
        return result
    match = validate_subject_match(profile, candidate)
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
        if any(unicodedata.normalize("NFKC", code).strip() not in scenario_codes
               for code in threshold.get("subject_minimums", {})):
            reasons.append("threshold_subject_combination_mismatch")
        for field in IDENTITY_FIELDS[threshold["scope"]]:
            if not _text(threshold.get(field)) or threshold[field] != candidate.get(field):
                reasons.append(field + "_mismatch_or_missing")
        for field in ("research_track", "degree_type", "round", "area", "category"):
            if field in threshold and threshold[field] != candidate.get(field):
                reasons.append(field + "_mismatch")
        ev = threshold.get("evidence")
        if (not _official(ev, threshold["year"], now, candidate.get("candidate_id"))
                or ev.get("claim_id") != threshold["source_ref"]):
            reasons.append("current_official_threshold_evidence_required")
        payload_fields = {"year", "scope", "total", "population", "statistic", "subject_minimums",
                          "institution", "unit", "program_code", "research_track", "degree_type",
                          "round", "area", "category"}
        expected_value = {k: v for k, v in raw.items() if k in payload_fields}
        source_value = ev.get("value") if isinstance(ev, dict) else None
        source_payload = {k: v for k, v in source_value.items() if k in payload_fields} if isinstance(source_value, dict) else None
        if source_payload != expected_value:
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
    if statuses and "insufficient_evidence" not in statuses:
        result["status"] = statuses[0] if len(set(statuses)) == 1 else "insufficient_evidence"
        result["reasons"] = ["compatible_scoped_comparison" if len(set(statuses)) == 1 else "conflicting_compatible_thresholds"]
    else:
        result["reasons"] = ["no_complete_compatible_threshold_comparison"]
    return result
