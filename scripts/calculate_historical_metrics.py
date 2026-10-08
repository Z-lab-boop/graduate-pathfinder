"""Reconstruct scoped historical timelines and descriptive aggregate stage ratios.

No public-list row identities are accepted or persisted. Historical ratios are
descriptive arithmetic, never an applicant's admission probability.
"""
from copy import deepcopy
from datetime import date, datetime, timezone


SCOPE_FIELDS = (
    "admission_year", "institution", "unit", "program_code",
    "degree_type", "research_track", "admission_round",
)
COUNT_STAGES = {
    "announced_quota", "reported_applicants", "listed_shortlist",
    "deduplicated_shortlist", "confirmed_attended", "excellent_campers",
    "pre_admit", "waitlist", "final_admitted",
}
PRIVATE_FIELDS = {"name", "names", "student_id", "student_ids", "student_number",
                  "student_numbers", "applicant_name", "applicant_names", "rows", "applicants"}
PROVENANCE_FIELDS = ("claim_ids", "source_url", "retrieval_date", "evidence_tier", "method_notes")


def scope_key(record: dict) -> tuple:
    """Return the complete exact scope; absent/empty fields never become wildcards."""
    year = record.get("admission_year")
    if type(year) is not int or year <= 0:
        raise ValueError("admission_year must be a positive integer")
    for field in SCOPE_FIELDS[1:]:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be an explicit nonempty string")
    return tuple(record[field] for field in SCOPE_FIELDS)


def _normalized(record: dict, fields: tuple) -> dict:
    scope_key(record)
    if PRIVATE_FIELDS.intersection(record):
        raise ValueError("normalized historical records must not contain row identities")
    claims = record.get("claim_ids")
    if (not isinstance(claims, list) or not claims or
            any(not isinstance(claim, str) or not claim.strip() for claim in claims)):
        raise ValueError("claim_ids must contain nonempty evidence references")
    for field in PROVENANCE_FIELDS[1:]:
        if field in record and (not isinstance(record[field], str) or not record[field].strip()):
            raise ValueError(f"{field} must be a nonempty string without row identities")
    return {field: deepcopy(record[field]) for field in
            SCOPE_FIELDS + PROVENANCE_FIELDS + fields if field in record}


def _parse_time(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("event dates must be ISO strings or null")
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        if "T" not in value:
            raise ValueError("timestamp requires T separator")
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("event dates must be ISO dates or timestamps") from error


def _time_sort(parsed):
    if parsed is None:
        return (1, "")
    if isinstance(parsed, datetime):
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return (0, parsed.isoformat())
    return (0, parsed.isoformat())


def reconstruct_timeline(events: list[dict]) -> list[dict]:
    """Group by scope in first-seen order; sort dated events, then unknowns.

    Original precision, offsets, timezone labels and both range boundaries remain
    unchanged. Unzoned/date-only values use calendar ordering, not invented UTC.
    """
    groups = {}
    for record in events:
        row = _normalized(record, ("event_type", "start", "end", "timezone", "date_text"))
        if not isinstance(row.get("event_type"), str) or not row["event_type"].strip():
            raise ValueError("event_type must be a nonempty string")
        if "date_text" in row and not isinstance(row["date_text"], str):
            raise ValueError("date_text must be an identity-free string")
        row.setdefault("start", None)
        row.setdefault("end", None)
        row.setdefault("timezone", None)
        if row["timezone"] is not None and (not isinstance(row["timezone"], str) or
                                             not row["timezone"].strip()):
            raise ValueError("timezone must be an explicit label or null")
        start, end = _parse_time(row["start"]), _parse_time(row["end"])
        if start is not None and end is not None:
            same_precision = type(start) is type(end)
            same_zone = (not isinstance(start, datetime) or
                         (start.tzinfo is None) == (end.tzinfo is None)) if same_precision else False
            if same_precision and same_zone and end < start:
                raise ValueError("event range ends before it starts")
        row["order_basis"] = ("unknown" if start is None else "utc_instant"
                              if isinstance(start, datetime) and start.tzinfo is not None
                              else "calendar_value")
        groups.setdefault(scope_key(row), []).append((start, row))
    return [row for group in groups.values()
            for _, row in sorted(group, key=lambda item: _time_sort(item[0]))]


def _claims(rows):
    return list(dict.fromkeys(claim for row in rows for claim in row["claim_ids"]))


def calculate_stage_metrics(counts: list[dict]) -> dict:
    """Retain aggregates and compute final_admitted / confirmed_attended only.

    Duplicate stage records are ambiguous even when counts agree: without an
    explicit reconciliation they are not summed or selected. Invalid counts are
    preserved with rejection reasons, never converted or used as denominators.
    """
    groups = {}
    for record in counts:
        row = _normalized(record, ("stage", "count"))
        if not isinstance(row.get("stage"), str) or row["stage"] not in COUNT_STAGES:
            raise ValueError("unknown count stage")
        if isinstance(row.get("count"), (dict, list, tuple, set)):
            raise ValueError("count must not contain structured row data")
        groups.setdefault(scope_key(row), []).append(row)
    result = {"scopes": [], "rejected": []}
    attendance_rows = [row for rows in groups.values() for row in rows
                       if row["stage"] == "confirmed_attended"]
    for key, rows in groups.items():
        scope = dict(zip(SCOPE_FIELDS, key))
        group = {"scope": scope, "scope_key": key, "counts": rows, "metrics": [], "rejected": []}
        result["scopes"].append(group)

        def reject(reason, relevant):
            entry = {"metric": "final_admitted_per_confirmed_attended", "scope": deepcopy(scope),
                     "reason": reason, "claim_ids": _claims(relevant)}
            group["rejected"].append(entry)
            result["rejected"].append(deepcopy(entry))

        stages = {}
        for row in rows:
            stages.setdefault(row["stage"], []).append(row)
            if type(row.get("count")) is not int or row["count"] < 0:
                reject("invalid_count", [row])
        for stage_rows in stages.values():
            if len(stage_rows) > 1:
                reject("ambiguous_stage_count", stage_rows)
        numerator = stages.get("final_admitted", [])
        denominator = stages.get("confirmed_attended", [])
        if not numerator:
            continue
        relevant = numerator + denominator
        if len(numerator) > 1 or len(denominator) > 1:
            continue
        elif not denominator:
            if attendance_rows:
                reject("scope_mismatch", numerator + attendance_rows)
            elif "listed_shortlist" in stages or "deduplicated_shortlist" in stages:
                reject("attendance_unconfirmed", numerator + stages.get("listed_shortlist", []) +
                       stages.get("deduplicated_shortlist", []))
            else:
                reject("missing_denominator", numerator)
        elif any(type(row.get("count")) is not int or row["count"] < 0 for row in relevant):
            continue
        elif denominator[0]["count"] == 0:
            reject("zero_denominator", relevant)
        else:
            group["metrics"].append({
                "metric": "final_admitted_per_confirmed_attended", "scope": deepcopy(scope),
                "numerator_stage": "final_admitted", "denominator_stage": "confirmed_attended",
                "numerator": numerator[0]["count"], "denominator": denominator[0]["count"],
                "value": numerator[0]["count"] / denominator[0]["count"],
                "claim_ids": _claims(relevant), "descriptive_only": True,
            })
    return result
