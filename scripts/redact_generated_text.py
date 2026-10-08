"""Conservatively redact generated strings only; no source-file API or I/O.

Findings expose counts and review flags, never matched text or its offsets.
Broad matches may include public contacts: review every redacted output.
"""
import re

PATTERNS = (
    ("signature", re.compile(
        r"(?im)^(?P<label>[ \t]*(?:(?:[-+*]|\d+[.)])[ \t]+)?"
        r"(?:\*\*|__|\*|_)?(?:(?:推荐人|申请人|导师)?签名|签字|signature|signed[ \t]+by)"
        r"(?:\*\*|__|\*|_)?[ \t]*[:：=](?:\*\*|__|\*|_)?[ \t]*)"
        r"(?![*_ \t]*\[REDACTED_)(?P<value>[^\r\n]+)")),
    ("student_number", re.compile(r"(?i)(?P<label>(?:学号|学生编号|student[ \t]*(?:id|number|no\.?))[ \t]*[:：=][ \t]*)(?!\[REDACTED_)(?P<value>[A-Z0-9][A-Z0-9_-]{3,31})(?![A-Z0-9_-])")),
    ("identity", re.compile(r"(?<![A-Za-z0-9])\d{17}[\dXx](?![A-Za-z0-9])")),
    ("phone", re.compile(r"(?<![A-Za-z0-9])(?:\+?86[ \t-]*)?1[3-9]\d{9}(?![A-Za-z0-9])")),
    ("email", re.compile(r"(?<![A-Za-z0-9_.+%-])[A-Za-z0-9_.+%-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}(?![A-Za-z0-9_-])")),
)


def redact_text(text: str) -> tuple[str, list[dict]]:
    """Return a redacted generated string and nonidentifying review findings.

    Tokens are stable by type. Findings contain only type/count and booleans;
    do not pass source documents here or persist a pre-redaction report copy.
    """
    if not isinstance(text, str):
        raise TypeError("generated text must be a string")
    findings = []
    for kind, pattern in PATTERNS:
        token = "[REDACTED_" + kind.upper() + "]"
        text, count = pattern.subn(lambda match: (match.groupdict().get("label") or "") + token, text)
        if count:
            findings.append({"type": kind, "count": count, "review_required": True,
                             "possible_over_redaction": True})
    return text, findings
