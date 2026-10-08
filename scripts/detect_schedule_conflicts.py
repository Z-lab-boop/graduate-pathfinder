"""Validate explicit-offset schedules and compare half-open UTC intervals.

Records require candidate_id, event_type, start, and end. Timestamps may have
minute or second precision. Supplied precision/date_precision/deadline_precision
must be 'exact'; absent precision means the explicit timestamps are exact.
Original timestamps are retained; start_utc/end_utc are derived datetime values.
"""
from datetime import datetime, timezone
from itertools import combinations
import re


_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?"
    r"(?P<offset>Z|[+-]\d{2}:\d{2})"
)


def _parse_timestamp(value, field):
    match = _TIMESTAMP.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ValueError(f"{field} must be an explicit-offset ISO timestamp without fractions")
    offset = match["offset"]
    if offset != "Z":
        if offset == "-00:00" or int(offset[1:3]) > 23 or int(offset[4:6]) > 59:
            raise ValueError(f"{field} has an invalid or unresolved offset")
    try:
        local = datetime.fromisoformat(value)
        if local.tzinfo is None or local.utcoffset() is None:
            raise ValueError("missing timezone")
        return local.astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{field} is not a resolved timestamp representable in UTC") from error


def parse_event(record: dict) -> dict:
    """Copy and normalize a resolved event; never infer dates or timezones."""
    if not isinstance(record, dict):
        raise ValueError("event must be an object")
    for field in ("candidate_id", "event_type"):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
    for field in ("precision", "date_precision", "deadline_precision"):
        if field in record and record[field] != "exact":
            raise ValueError(f"{field} must be exact before scheduling")
    start = _parse_timestamp(record.get("start"), "start")
    end = _parse_timestamp(record.get("end"), "end")
    if end <= start:
        raise ValueError("end must be later than start")
    return {**record, "start_utc": start, "end_utc": end}


def detect_conflicts(events: list[dict]) -> list[dict]:
    """Report every overlapping pair in input order, using [start, end)."""
    parsed = [parse_event(record) for record in events]
    conflicts = []
    for first, second in combinations(parsed, 2):
        start = max(first["start_utc"], second["start_utc"])
        end = min(first["end_utc"], second["end_utc"])
        if start < end:
            conflicts.append({
                "candidate_ids": [first["candidate_id"], second["candidate_id"]],
                "event_types": [first["event_type"], second["event_type"]],
                "overlap_minutes": (end - start).total_seconds() / 60,
                "local_timestamps": [{"start": item["start"], "end": item["end"]}
                                     for item in (first, second)],
            })
    return conflicts
