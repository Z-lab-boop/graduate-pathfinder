"""Deterministic UTF-8 RFC 5545 calendar text for resolved schedule records.

Optional summary, description, and location are escaped TEXT properties.
UID hashes candidate ID, event type, and normalized UTC start. DTSTAMP equals
DTSTART as a reproducible serialization choice, not a claim of creation time.
Callers writing files must preserve UTF-8 and the returned CRLF bytes.
"""
import hashlib
import json

from .detect_schedule_conflicts import parse_event


def _escape_text(value):
    if not isinstance(value, str):
        raise ValueError("calendar text must be a string")
    if any((ord(char) < 32 and char not in "\t\r\n") or ord(char) == 127 for char in value):
        raise ValueError("calendar text contains unsupported control characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("calendar text must be valid UTF-8") from error
    return (value.replace("\r\n", "\n").replace("\r", "\n")
            .replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\n", "\\n"))


def _fold_line(line):
    """Fold at 75 octets including continuation space, preserving codepoints."""
    parts, current, octets = [], "", 0
    for char in line:
        size = len(char.encode("utf-8"))
        if octets + size > 75:
            parts.append(current)
            current, octets = " ", 1
        current += char
        octets += size
    parts.append(current)
    return "\r\n".join(parts)


def _utc_text(value):
    return (f"{value.year:04d}{value.month:02d}{value.day:02d}T"
            f"{value.hour:02d}{value.minute:02d}{value.second:02d}Z")


def render_ics(events: list[dict], calendar_name: str) -> str:
    """Serialize resolved events in canonical order; reject duplicate identity."""
    name = _escape_text(calendar_name)
    parsed = [parse_event(record) for record in events]
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//graduate-pathfinder//EN",
             "X-WR-CALNAME:" + name]
    seen = set()
    for record in sorted(parsed, key=lambda item:
                         (item["start_utc"], item["candidate_id"], item["event_type"])):
        identity = [record["candidate_id"], record["event_type"], _utc_text(record["start_utc"])]
        uid = hashlib.sha256(json.dumps(identity, ensure_ascii=True,
                                       separators=(",", ":")).encode("utf-8")).hexdigest()
        if uid in seen:
            raise ValueError("duplicate calendar event identity")
        seen.add(uid)
        start = _utc_text(record["start_utc"])
        lines.extend(["BEGIN:VEVENT", "UID:" + uid + "@graduate-pathfinder",
                      "DTSTAMP:" + start, "DTSTART:" + start,
                      "DTEND:" + _utc_text(record["end_utc"]),
                      "SUMMARY:" + _escape_text(record.get("summary",
                                            record["candidate_id"] + " " + record["event_type"]))])
        for field in ("description", "location"):
            if field in record:
                lines.append(field.upper() + ":" + _escape_text(record[field]))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold_line(line) for line in lines) + "\r\n"
