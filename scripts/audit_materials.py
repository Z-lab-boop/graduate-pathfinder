"""Pure target-specific packet audit; visibility never certifies authenticity.

Inputs are normalized review records, not source files. See material-review.md
for requirement, extraction and document-scoped condition contracts.
"""
from copy import deepcopy

if __package__:
    from .validate_case import APPLICANT_CLAIM_STATES
else:
    from validate_case import APPLICANT_CLAIM_STATES

READABLE_STATES = {"complete", "extracted", "reviewed"}
UNREADABLE_STATES = {"unreadable", "failed"}
NECESSITIES = {"required", "optional", "conditional", "not_applicable"}


def _strings(value):
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def _same(left, right):
    # JSON values retain their types: True must not equal numeric 1.
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _present(value):
    return value is not None and value != "" and value != [] and value != {}


def _validate(manifest, claims, requirements):
    if not all(isinstance(records, list) for records in (manifest, claims, requirements)):
        raise ValueError("manifest, claims and requirements must be arrays")
    for row in manifest:
        if not isinstance(row, dict) or not isinstance(row.get("document_id"), str) or not row["document_id"].strip():
            raise ValueError("manifest document_id must be a non-empty string")
    seen = set()
    for row in claims:
        if (not isinstance(row, dict) or not isinstance(row.get("claim_id"), str)
                or not row["claim_id"].strip() or not isinstance(row.get("field"), str)
                or not row["field"].strip() or "value" not in row
                or not isinstance(row.get("state"), str) or row["state"] not in APPLICANT_CLAIM_STATES
                or not _strings(row.get("source_document_ids"))):
            raise ValueError("invalid applicant claim shape")
        if row["claim_id"] in seen:
            raise ValueError("duplicate applicant claim_id")
        if row.get("scope", "applicant") not in {"applicant", "document"}:
            raise ValueError("claim scope must be applicant or document")
        seen.add(row["claim_id"])
    seen = set()
    for row in requirements:
        if (not isinstance(row, dict) or any(not isinstance(row.get(key), str) or not row[key].strip()
                for key in ("requirement_id", "target_id", "item_type"))
                or not isinstance(row.get("necessity"), str) or row["necessity"] not in NECESSITIES
                or not isinstance(row.get("conditions"), dict)
                or any(not isinstance(key, str) or not key.strip() for key in row["conditions"])
                or not _strings(row.get("source_claim_ids")) or not row["source_claim_ids"]
                or ("document_ids" in row and not _strings(row["document_ids"]))):
            raise ValueError("invalid target requirement shape")
        if row["requirement_id"] in seen:
            raise ValueError("requirement_id must be unique across targets")
        if row["necessity"] == "conditional":
            gate = row.get("applies_when")
            if not isinstance(gate, dict) or not isinstance(gate.get("field"), str) or not gate["field"].strip() or "value" not in gate:
                raise ValueError("conditional requirement needs applies_when field and value")
        seen.add(row["requirement_id"])


def _contradictions(claims):
    groups = {}
    for row in claims:
        scope = row.get("scope", "applicant")
        # A multi-document claim participates in each document's group so an
        # overlapping single-document claim cannot disappear from conflicts.
        references = sorted(set(row["source_document_ids"])) if scope == "document" else [None]
        for ref in references or [None]:
            refs = (ref,) if ref is not None else ()
            groups.setdefault((row["field"], scope, refs), []).append(row)
    result = []
    for (field, scope, refs), rows in groups.items():
        values = [row["value"] for row in rows if row["state"] != "missing" and _present(row["value"])]
        if (any(row["state"] == "conflicted" for row in rows)
                or any(not _same(values[0], value) for value in values[1:])):
            result.append({"field": field, "scope": scope, "source_document_ids": list(refs),
                           "claims": [{key: deepcopy(row[key]) for key in
                                       ("claim_id", "state", "value", "source_document_ids")} for row in rows],
                           "review_required": True})
    return result


def audit_materials(manifest: list[dict], claims: list[dict], requirements: list[dict]) -> dict:
    """Evaluate each target's material requirements without opening/writing files.

    source_claim_ids are target-policy provenance IDs, not applicant claim IDs.
    conditions map applicant claim fields to typed expectations; 'present' tests
    nonempty values. Conditional applies_when compares a verified applicant fact.
    """
    _validate(manifest, claims, requirements)
    documents = {}
    for row in manifest:
        documents.setdefault(row["document_id"], []).append(row)
    contradictions = _contradictions(claims)

    def verified(row):
        refs = row["source_document_ids"]
        return (row["state"] == "document_verified" and bool(refs)
                and all(ref in documents and all(doc.get("extraction_state") in READABLE_STATES
                                                 for doc in documents[ref]) for ref in refs)
                # Reading a resume verifies what it says, not its assertions.
                and any(doc.get("document_class") not in {"resume", "unknown", None}
                        for ref in refs for doc in documents.get(ref, [])))

    def conflicting(field, document_ids=None):
        return any(c["field"] == field and (c["scope"] == "applicant" or document_ids is None
                   or bool(set(c["source_document_ids"]) & set(document_ids))) for c in contradictions)

    report = {"items_by_id": {}, "items_by_target": {}, "contradictions": contradictions,
              "review_required": bool(contradictions)}
    for req in requirements:
        selected_ids = req.get("document_ids")
        selected = [row for row in manifest if row.get("document_class") == req["item_type"]
                    and (selected_ids is None or row["document_id"] in selected_ids)]
        ids = list(dict.fromkeys(row["document_id"] for row in selected))
        item = {key: deepcopy(req[key]) for key in
                ("requirement_id", "target_id", "item_type", "necessity", "source_claim_ids")}
        item.update(document_ids=ids, status="materially_incomplete", missing_conditions=[],
                    review_required=False, blocking=False)
        applies = True
        if req["necessity"] == "not_applicable":
            applies = False
        elif req["necessity"] == "conditional":
            gate = req["applies_when"]
            rows = [row for row in claims if row["field"] == gate["field"]
                    and row.get("scope", "applicant") == "applicant" and verified(row)]
            if not rows or conflicting(gate["field"]):
                applies = None
                item["missing_conditions"].append("applicability")
                item["review_required"] = True
            else:
                applies = _same(rows[0]["value"], gate["value"])
        if applies is False:
            item["status"] = "not_applicable"
        elif applies is None:
            pass
        elif not selected or (selected_ids is not None and set(selected_ids) - set(ids)):
            item["missing_conditions"].append("document")
        elif any(row.get("extraction_state") in UNREADABLE_STATES for row in selected):
            item["status"] = "unreadable"
            item["missing_conditions"].append("readability")
            item["review_required"] = True
        else:
            missing_sets = []
            for doc_id in ids:
                missing = []
                if not all(row.get("extraction_state") in READABLE_STATES for row in documents[doc_id]):
                    missing.append("extraction_review")
                for field, expected in req["conditions"].items():
                    rows = [row for row in claims if row["field"] == field
                            and doc_id in row["source_document_ids"] and verified(row)]
                    if (conflicting(field, [doc_id]) or not rows
                            or not all(_present(row["value"]) if expected == "present"
                                       else _same(row["value"], expected) for row in rows)):
                        missing.append(field)
                missing_sets.append(missing)
            # Conditions must all hold for one document; never splice two drafts.
            if any(not missing for missing in missing_sets):
                item["status"] = "complete"
            else:
                item["status"] = "repairable"
                item["missing_conditions"] = list(dict.fromkeys(key for missing in missing_sets for key in missing))
                item["review_required"] = True
        item["blocking"] = req["necessity"] in {"required", "conditional"} and item["status"] not in {"complete", "not_applicable"}
        report["items_by_id"][req["requirement_id"]] = item
        report["items_by_target"].setdefault(req["target_id"], []).append(item)
        report["review_required"] |= item["review_required"]
    return report
