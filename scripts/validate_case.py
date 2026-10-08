"""Validate normalized admission cases without interpreting missing evidence."""
import argparse
from datetime import date, datetime, timezone
import math
import re
from pathlib import Path

if __package__:
    from .case_io import load_json
else:
    from case_io import load_json

PATHWAYS = {"baoyan", "kaoyan"}
EVIDENCE_TIERS = {"T1", "T2", "T3", "T4"}
EVIDENCE_STATES = {
    "confirmed", "secondary_only", "conflicted",
    "stale", "missing", "not_applicable",
}
ELIGIBILITY_STATES = {"pass", "fail", "unknown"}
APPLICANT_CLAIM_STATES = {
    "document_verified", "user_asserted", "derived",
    "inferred", "missing", "conflicted",
}
SKILL_ROOT = Path(__file__).resolve().parents[1]


def _strings(record, fields, errors, nullable=()):
    for field in fields:
        value = record.get(field)
        if field in nullable and field in record and value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string" + (" or null" if field in nullable else ""))


def _enum(record, field, allowed, errors):
    value = record.get(field)
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{field} must be one of {', '.join(sorted(allowed))}")


def _year(record, errors):
    if type(record.get("admission_year")) is not int:
        errors.append("admission_year must be an integer")


def _timestamp(value):
    match = re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?P<offset>Z|[+-]\d{2}:\d{2})",
        value) if isinstance(value, str) else None
    if match is None:
        return False
    offset = match["offset"]
    if offset != "Z" and (offset == "-00:00" or int(offset[1:3]) > 23 or int(offset[4:6]) > 59):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            return False
        parsed.astimezone(timezone.utc)
        return True
    except (ValueError, OverflowError):
        return False


def validate_profile(profile: dict) -> list[str]:
    if not isinstance(profile, dict):
        return ["record must be an object"]
    errors = []
    _strings(profile, ("case_label",), errors)
    _enum(profile, "pathway", PATHWAYS, errors)
    _year(profile, errors)
    if not isinstance(profile.get("preferences"), dict):
        errors.append("preferences must be an object")
    return errors


def validate_candidate(candidate: dict) -> list[str]:
    if not isinstance(candidate, dict):
        return ["record must be an object"]
    errors = []
    _strings(candidate, ("candidate_id", "institution", "unit", "program_code", "program_name",
                         "research_track", "status"), errors, ("program_code", "research_track"))
    _enum(candidate, "pathway", PATHWAYS, errors)
    _enum(candidate, "degree_type", {"academic-master", "professional-master", "direct-phd"}, errors)
    _enum(candidate, "round", {"summer-camp", "pre-recommendation", "september", "regular-exam"}, errors)
    _enum(candidate, "eligibility", ELIGIBILITY_STATES, errors)
    _enum(candidate, "evidence_confidence", {"A", "B", "C", "D"}, errors)
    _enum(candidate, "status", {"discovered", "verified", "preparing", "submitted", "screened",
          "assessment", "offer", "waitlist", "rejected", "withdrawn", "pending-official-system", "accepted"}, errors)
    _year(candidate, errors)
    if "deadline" not in candidate or (candidate["deadline"] is not None and not _timestamp(candidate["deadline"])):
        errors.append("deadline must be a timezone-aware RFC3339 timestamp or null")
    completeness = candidate.get("data_completeness")
    if type(completeness) not in (int, float) or not 0 <= completeness <= 1 or not math.isfinite(completeness):
        errors.append("data_completeness must be a finite number between 0 and 1")
    if not isinstance(candidate.get("sources"), list):
        errors.append("sources must be an array")
    return errors


def validate_evidence(record: dict) -> list[str]:
    if not isinstance(record, dict):
        return ["record must be an object"]
    errors = []
    _strings(record, ("claim_id", "candidate_id", "field", "source_url", "source_title", "publisher",
                      "short_evidence", "conflict_group"), errors, ("conflict_group",))
    if "value" not in record:
        errors.append("value is required")
    _enum(record, "tier", EVIDENCE_TIERS, errors)
    _enum(record, "status", EVIDENCE_STATES, errors)
    _enum(record, "scope", {"school", "program", "round"}, errors)
    if not _timestamp(record.get("retrieved_at")):
        errors.append("retrieved_at must be a timezone-aware RFC3339 timestamp")
    published = record.get("published_at")
    try:
        if "published_at" not in record or (published is not None and
                (not isinstance(published, str) or date.fromisoformat(published).isoformat() != published)):
            errors.append("published_at must be YYYY-MM-DD or null")
    except ValueError:
        errors.append("published_at must be YYYY-MM-DD or null")
    return errors


def validate_applicant_claim(claim: dict) -> list[str]:
    """Validate claim provenance shape, without certifying document authenticity."""
    if not isinstance(claim, dict):
        return ["record must be an object"]
    errors = []
    _strings(claim, ("claim_id", "field"), errors)
    if "value" not in claim:
        errors.append("value is required")
    _enum(claim, "state", APPLICANT_CLAIM_STATES, errors)
    refs = claim.get("source_document_ids")
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        errors.append("source_document_ids must be an array of non-empty strings")
    elif claim.get("state") == "document_verified" and not refs:
        errors.append("source_document_ids must reference at least one manifest document for document_verified")
    if not isinstance(claim.get("notes"), str):
        errors.append("notes must be a string")
    return errors


def _validate_applicant_claims(directory: Path) -> list[str]:
    path = directory / "applicant-claims.json"
    if not path.exists():
        return []
    try:
        claims = load_json(path)
    except (OSError, ValueError) as error:
        return [f"applicant-claims.json: {error}"]
    if not isinstance(claims, list):
        return ["applicant-claims.json: must be an array"]
    errors = []
    references = []
    for index, claim in enumerate(claims):
        errors.extend(f"applicant-claims.json[{index}]: {error}" for error in validate_applicant_claim(claim))
        if isinstance(claim, dict) and isinstance(claim.get("source_document_ids"), list):
            references.extend((index, ref) for ref in claim["source_document_ids"]
                              if isinstance(ref, str) and ref.strip())
    if references:
        try:
            manifest = load_json(directory / "materials-manifest.json")
        except (OSError, ValueError) as error:
            errors.append(f"materials-manifest.json: {error}")
            return errors
        if not isinstance(manifest, list):
            errors.append("materials-manifest.json: must be an array")
            return errors
        document_ids = set()
        for index, document in enumerate(manifest):
            if (not isinstance(document, dict) or not isinstance(document.get("document_id"), str)
                    or not document["document_id"].strip()):
                errors.append(f"materials-manifest.json[{index}]: document_id must be a non-empty string")
            else:
                document_ids.add(document["document_id"])
        for index, reference in references:
            if reference not in document_ids:
                errors.append(f"applicant-claims.json[{index}]: unknown manifest document ID {reference}")
    return errors


def validate_case(case_dir: Path, *, skill_root: Path = SKILL_ROOT) -> list[str]:
    directory = Path(case_dir).resolve()
    if directory.is_relative_to(Path(skill_root).resolve()):
        return ["case directory must be outside the skill root"]
    errors = []
    for filename, validator, array in (("profile.json", validate_profile, False),
                                       ("candidates.json", validate_candidate, True),
                                       ("evidence.json", validate_evidence, True)):
        try:
            payload = load_json(directory / filename)
        except (OSError, ValueError) as error:
            errors.append(f"{filename}: {error}")
            continue
        if array:
            if not isinstance(payload, list):
                errors.append(f"{filename}: must be an array")
                continue
            for index, record in enumerate(payload):
                errors.extend(f"{filename}[{index}]: {error}" for error in validator(record))
        else:
            errors.extend(f"{filename}: {error}" for error in validator(payload))
    errors.extend(_validate_applicant_claims(directory))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--skill-root", type=Path, default=SKILL_ROOT)
    args = parser.parse_args()
    errors = validate_case(args.case_dir, skill_root=args.skill_root)
    if errors:
        print("\n".join(errors))
        return 1
    print("Case is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
