"""Preserve admission evidence and expose deterministic confidence causes."""
from copy import deepcopy
from datetime import datetime

if __package__:
    from .validate_case import validate_evidence
else:
    from validate_case import validate_evidence

TIER_WEIGHT = {"T1": 4, "T2": 3, "T3": 2, "T4": 1}
CRITICAL_FIELDS = {"eligibility", "deadline", "program_availability", "degree_type"}


def audit_evidence(records: list[dict], now: datetime, stale_after_days: int = 365) -> dict:
    """Audit validated records; invalid inputs remain visible and cannot confirm a claim.

    Retrieval dates are compared as calendar dates, without timezone conversion.
    B denotes stale official support; C denotes secondary-only support; D takes
    precedence for missing/conflicted critical evidence or invalid candidate evidence.
    """
    if not isinstance(now, datetime):
        raise TypeError("now must be a datetime")
    if type(stale_after_days) is not int or stale_after_days < 0:
        raise ValueError("stale_after_days must be a non-negative integer")
    report = {"claims": [], "candidate_summary": {}, "conflicts": {}, "errors": []}
    grouped = {}
    candidates = {}
    for index, source in enumerate(records):
        record = deepcopy(source)
        errors = validate_evidence(record)
        claim = {"record_index": index, "record": record, "valid": not errors,
                 "stale": False, "effective_status": "invalid", "conflict_groups": []}
        report["claims"].append(claim)
        if isinstance(record, dict) and isinstance(record.get("candidate_id"), str):
            candidates.setdefault(record["candidate_id"], []).append(claim)
        if errors:
            report["errors"].append({"record_index": index, "errors": errors})
            continue
        age = (now.date() - datetime.fromisoformat(record["retrieved_at"].replace("Z", "+00:00")).date()).days
        claim["age_days"] = age
        claim["stale"] = record["status"] != "not_applicable" and (
            age > stale_after_days or record["status"] == "stale")
        status = record["status"]
        if status not in {"missing", "conflicted", "not_applicable"}:
            if claim["stale"]:
                status = "stale"
            elif record["tier"] in {"T3", "T4"}:
                status = "secondary_only"
        claim["effective_status"] = status
        if record["conflict_group"] is not None:
            grouped.setdefault(record["conflict_group"], []).append(claim)

    for group, claims in sorted(grouped.items()):
        values = []
        for claim in claims:
            value = claim["record"]["value"]
            if not any(type(value) is type(previous) and value == previous for previous in values):
                values.append(deepcopy(value))
        if len(values) > 1 or any(c["effective_status"] == "conflicted" for c in claims):
            report["conflicts"][group] = {
                "values": values, "record_indexes": [c["record_index"] for c in claims],
                "claim_ids": [c["record"]["claim_id"] for c in claims],
            }
            for claim in claims:
                claim["conflict_groups"].append(group)
                claim["effective_status"] = "conflicted"

    for candidate_id, claims in sorted(candidates.items()):
        fields = {}
        missing, conflicted, stale_official, secondary = [], [], [], []
        invalid = [c["record_index"] for c in claims if not c["valid"]]
        for field in sorted(CRITICAL_FIELDS):
            supporting = [c for c in claims if c["valid"] and c["record"]["field"] == field]
            usable = [c for c in supporting
                      if c["effective_status"] not in {"missing", "conflicted"}
                      and (c["record"]["value"] is not None
                           or c["effective_status"] == "not_applicable")]
            # Official precedence remains inspectable; no source records are discarded.
            strongest = max(usable, key=lambda c: (TIER_WEIGHT[c["record"]["tier"]],
                                                    not c["stale"]), default=None)
            official = [c for c in usable if c["record"]["tier"] in {"T1", "T2"}]
            fresh_official = [c for c in official if not c["stale"]]
            is_missing = not usable or any(c["effective_status"] == "missing" for c in supporting)
            is_conflicted = any(c["effective_status"] == "conflicted" for c in supporting)
            if is_missing:
                missing.append(field)
            if is_conflicted:
                conflicted.append(field)
            if usable and not official:
                secondary.append(field)
            if official and strongest["stale"]:
                stale_official.append(field)
            fields[field] = {
                "record_indexes": [c["record_index"] for c in supporting],
                "usable_record_indexes": [c["record_index"] for c in usable],
                "strongest_usable_tier": strongest["record"]["tier"] if strongest else None,
                "strongest_record_index": strongest["record_index"] if strongest else None,
                "fresh_official_record_indexes": [c["record_index"] for c in fresh_official],
                "missing": is_missing, "conflicted": is_conflicted,
            }
        confidence = "D" if missing or conflicted or invalid else (
            "C" if secondary else ("B" if stale_official else "A"))
        report["candidate_summary"][candidate_id] = {
            "confidence": confidence, "critical_fields": fields,
            "missing_critical_fields": missing, "conflicted_critical_fields": conflicted,
            "stale_official_fields": stale_official, "secondary_only_fields": secondary,
            "invalid_record_indexes": invalid, "stale_after_days": stale_after_days,
            "evaluated_at": now.isoformat(),
        }
    return report
