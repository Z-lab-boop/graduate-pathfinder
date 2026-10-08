import copy
import json
import unittest

from scripts.audit_materials import audit_materials
from scripts.redact_generated_text import redact_text


def document(kind="recommendation", state="complete", document_id="sha256:" + "a" * 64):
    return {"document_id": document_id, "document_class": kind,
            "extraction_state": state, "source_path": "/synthetic/source.pdf"}


def claim(field, value, state="document_verified", claim_id=None, refs=None, **extra):
    return {"claim_id": claim_id or field, "field": field, "value": value,
            "state": state, "source_document_ids": refs if refs is not None else ["sha256:" + "a" * 64],
            "notes": "synthetic", **extra}


def requirement(identifier="recommendation-1", target="target-a", **extra):
    return {"requirement_id": identifier, "target_id": target,
            "item_type": "recommendation", "necessity": "required",
            "conditions": {"signature": True, "date": "present"},
            "source_claim_ids": ["target-a-policy"], **extra}


class MaterialAuditTests(unittest.TestCase):
    def setUp(self):
        self.manifest = [document()]
        self.claims = [claim("signature", True, scope="document"),
                       claim("date", "2026-10-08", scope="document")]
        self.requirements = [requirement()]

    def item(self, **kwargs):
        return audit_materials(kwargs.get("manifest", self.manifest),
                               kwargs.get("claims", self.claims),
                               kwargs.get("requirements", self.requirements))["items_by_id"]["recommendation-1"]

    def test_signed_dated_document_satisfies_requirement_without_input_changes(self):
        before = copy.deepcopy((self.manifest, self.claims, self.requirements))
        item = self.item()
        self.assertEqual(item["status"], "complete")
        self.assertEqual(item["missing_conditions"], [])
        self.assertFalse(item["blocking"])
        self.assertEqual((self.manifest, self.claims, self.requirements), before)

    def test_unsigned_recommendation_is_not_complete(self):
        self.claims[0]["value"] = False
        item = self.item()
        self.assertEqual(item["status"], "repairable")
        self.assertIn("signature", item["missing_conditions"])
        self.assertTrue(item["blocking"])

    def test_missing_date_is_repairable(self):
        item = self.item(claims=self.claims[:1])
        self.assertEqual(item["status"], "repairable")
        self.assertIn("date", item["missing_conditions"])

    def test_optional_missing_item_is_visible_but_not_blocking(self):
        item = self.item(manifest=[], requirements=[requirement(necessity="optional")], claims=[])
        self.assertEqual(item["status"], "materially_incomplete")
        self.assertFalse(item["blocking"])

    def test_required_missing_item_is_blocking(self):
        self.assertTrue(self.item(manifest=[], claims=[])["blocking"])

    def test_explicit_not_applicable_item(self):
        item = self.item(manifest=[], claims=[], requirements=[requirement(necessity="not_applicable")])
        self.assertEqual(item["status"], "not_applicable")
        self.assertFalse(item["blocking"])

    def test_conditional_applicability_requires_verified_claim(self):
        req = requirement(necessity="conditional", applies_when={"field": "needs_letter", "value": True})
        for value, state, expected in ((False, "document_verified", "not_applicable"),
                                      (True, "document_verified", "complete"),
                                      (False, "user_asserted", "materially_incomplete")):
            with self.subTest(value=value, state=state):
                item = self.item(claims=self.claims + [claim("needs_letter", value, state)], requirements=[req])
                self.assertEqual(item["status"], expected)
        item = self.item(requirements=[req])
        self.assertIn("applicability", item["missing_conditions"])

    def test_conditional_applicability_does_not_choose_a_document_scoped_value(self):
        req = requirement(necessity="conditional", applies_when={"field": "needs_letter", "value": True})
        item = self.item(claims=self.claims + [claim("needs_letter", False, scope="document")], requirements=[req])
        self.assertEqual(item["status"], "materially_incomplete")
        self.assertIn("applicability", item["missing_conditions"])

    def test_targets_apply_their_own_conditions(self):
        self.claims = self.claims[:1]
        report = audit_materials(self.manifest, self.claims,
                                [requirement(), requirement("letter-b", "target-b", conditions={"signature": True})])
        self.assertEqual(report["items_by_target"]["target-a"][0]["status"], "repairable")
        self.assertEqual(report["items_by_target"]["target-b"][0]["status"], "complete")

    def test_unreadable_selected_document_forces_unreadable(self):
        item = self.item(manifest=[document(state="unreadable")])
        self.assertEqual(item["status"], "unreadable")
        self.assertTrue(item["review_required"])

    def test_ocr_and_not_started_extraction_cannot_satisfy_conditions(self):
        for state in ("not_started", "ocr_uncertain", "partial", "unknown"):
            with self.subTest(state=state):
                item = self.item(manifest=[document(state=state)])
                self.assertEqual(item["status"], "repairable")
                self.assertTrue(item["review_required"])

    def test_nonverified_claim_states_cannot_satisfy_requirement(self):
        for state in ("user_asserted", "derived", "inferred", "missing", "conflicted"):
            with self.subTest(state=state):
                item = self.item(claims=[claim("signature", True, state), self.claims[1]])
                self.assertEqual(item["status"], "repairable")
                self.assertIn("signature", item["missing_conditions"])

    def test_unbound_and_other_document_claims_cannot_complete_selected_item(self):
        for refs in ([], ["sha256:" + "b" * 64]):
            with self.subTest(refs=refs):
                item = self.item(claims=[claim("signature", True, refs=refs), self.claims[1]])
                self.assertEqual(item["status"], "repairable")
                self.assertIn("signature", item["missing_conditions"])

    def test_conditions_cannot_mix_two_incomplete_letters(self):
        other = document(document_id="sha256:" + "b" * 64)
        item = self.item(manifest=self.manifest + [other], claims=[self.claims[0], claim("date", "2026-10-08", refs=[other["document_id"]])])
        self.assertEqual(item["status"], "repairable")

    def test_explicit_document_selection_does_not_fall_back_to_another_letter(self):
        item = self.item(requirements=[requirement(document_ids=["sha256:" + "b" * 64])])
        self.assertEqual(item["status"], "materially_incomplete")

    def test_resume_transcript_conflict_preserves_both_values_and_states(self):
        resume = document("resume", document_id="sha256:" + "b" * 64)
        claims = [claim("gpa", 3.8, "user_asserted", "resume-gpa", [resume["document_id"]]),
                  claim("gpa", 3.4, claim_id="transcript-gpa")]
        report = audit_materials([document("transcript"), resume], claims,
                                [requirement(item_type="transcript", conditions={"gpa": "present"})])
        conflict = report["contradictions"][0]
        self.assertEqual(conflict["field"], "gpa")
        self.assertEqual([c["value"] for c in conflict["claims"]], [3.8, 3.4])
        self.assertEqual([c["state"] for c in conflict["claims"]], ["user_asserted", "document_verified"])
        self.assertEqual([c["claim_id"] for c in conflict["claims"]], ["resume-gpa", "transcript-gpa"])
        self.assertNotIn("winner", conflict)
        self.assertEqual(report["items_by_id"]["recommendation-1"]["status"], "repairable")
        self.assertNotIn("/synthetic/source.pdf", json.dumps(report))

    def test_document_scoped_signature_values_on_distinct_letters_do_not_conflict(self):
        other = document(document_id="sha256:" + "b" * 64)
        report = audit_materials(self.manifest + [other], self.claims + [claim("signature", False, claim_id="other-signature", refs=[other["document_id"]], scope="document")], self.requirements)
        self.assertEqual(report["contradictions"], [])
        self.assertEqual(report["items_by_id"]["recommendation-1"]["status"], "complete")

    def test_unknown_requirement_shape_and_duplicate_ids_fail_closed(self):
        for req in (requirement(necessity="sometimes"), requirement(conditions=[]),
                    requirement(source_claim_ids=[])):
            with self.subTest(req=req), self.assertRaises(ValueError):
                audit_materials(self.manifest, self.claims, [req])
        with self.assertRaises(ValueError):
            audit_materials(self.manifest, self.claims, self.requirements * 2)

    def test_boolean_conditions_do_not_accept_numeric_one(self):
        self.claims[0]["value"] = 1
        self.assertEqual(self.item()["status"], "repairable")

    def test_nested_typed_conditions_do_not_accept_boolean_number_equivalence(self):
        self.claims[0]["value"] = {"signed": 1}
        item = self.item(requirements=[requirement(conditions={"signature": {"signed": True}})])
        self.assertEqual(item["status"], "repairable")

    def test_resume_assertion_is_not_promoted_by_a_document_verified_label(self):
        report = audit_materials([document("resume")], [claim("gpa", 3.8)],
                                [requirement(item_type="resume", conditions={"gpa": "present"})])
        self.assertEqual(report["items_by_id"]["recommendation-1"]["status"], "repairable")
        self.assertIn("gpa", report["items_by_id"]["recommendation-1"]["missing_conditions"])

    def test_overlapping_document_references_preserve_conflicting_claims(self):
        other = document(document_id="sha256:" + "b" * 64)
        claims = self.claims + [claim("signature", False, claim_id="overlap", scope="document",
                                      refs=[self.manifest[0]["document_id"], other["document_id"]])]
        report = audit_materials(self.manifest + [other], claims, self.requirements)
        self.assertEqual(len(report["contradictions"]), 1)
        self.assertEqual({c["claim_id"] for c in report["contradictions"][0]["claims"]}, {"signature", "overlap"})

    def test_unbound_reference_in_a_claim_cannot_be_ignored(self):
        self.claims[0]["source_document_ids"].append("sha256:" + "b" * 64)
        self.assertIn("signature", self.item()["missing_conditions"])

    def test_empty_date_and_conflicted_single_claim_remain_reviewable(self):
        self.claims[1]["value"] = ""
        self.claims[0]["state"] = "conflicted"
        report = audit_materials(self.manifest, self.claims, self.requirements)
        self.assertEqual(len(report["contradictions"]), 1)
        self.assertEqual(report["items_by_id"]["recommendation-1"]["missing_conditions"], ["signature", "date"])

    def test_duplicate_claim_ids_and_invalid_states_are_rejected(self):
        for claims in (self.claims * 2, [claim("signature", True, "confirmed")]):
            with self.subTest(claims=claims), self.assertRaises(ValueError):
                audit_materials(self.manifest, claims, self.requirements)


class GeneratedTextRedactionTests(unittest.TestCase):
    def test_synthetic_identifiers_are_redacted_and_findings_do_not_echo_matches(self):
        original = "手机：13800000000 邮箱：synthetic.person@example.invalid 身份证：11010119900101001X 学号：SYN20260001"
        text, findings = redact_text(original)
        for kind in ("PHONE", "EMAIL", "IDENTITY", "STUDENT_NUMBER"):
            self.assertIn("[REDACTED_" + kind + "]", text)
        for secret in ("13800000000", "synthetic.person@example.invalid", "11010119900101001X", "SYN20260001"):
            self.assertNotIn(secret, text)
            self.assertNotIn(secret, json.dumps(findings))
        self.assertEqual({f["type"]: f["count"] for f in findings},
                         {"phone": 1, "email": 1, "identity": 1, "student_number": 1})
        self.assertTrue(all(f["review_required"] and f["possible_over_redaction"] for f in findings))

    def test_repeated_matches_are_counted_and_stable(self):
        text, findings = redact_text("13800000000 / +86 13900000000")
        self.assertEqual(text.count("[REDACTED_PHONE]"), 2)
        self.assertEqual(findings[0]["count"], 2)
        self.assertEqual(redact_text(text), (text, []))

    def test_student_numbers_require_context_labels(self):
        text, findings = redact_text("订单 SYN20260001\nStudent ID: SYN20260002\n学号=20260003")
        self.assertIn("订单 SYN20260001", text)
        self.assertEqual(text.count("[REDACTED_STUDENT_NUMBER]"), 2)
        self.assertEqual(findings[0]["count"], 2)

    def test_signature_lines_hide_names_without_erasing_following_body(self):
        text, findings = redact_text("正文\n推荐人签名：合成姓名\n日期：2026-10-08\n后续正文\nSignature: Synthetic Name")
        self.assertNotIn("合成姓名", text)
        self.assertNotIn("Synthetic Name", text)
        self.assertIn("日期：2026-10-08\n后续正文", text)
        self.assertEqual(text.count("[REDACTED_SIGNATURE]"), 2)
        self.assertEqual(findings[0]["type"], "signature")

    def test_plain_text_and_unlabelled_short_numbers_remain_unchanged(self):
        text = "GPA 3.5; 2026-10-08; sample 20260001; ordinary text"
        self.assertEqual(redact_text(text), (text, []))

    def test_findings_have_only_nonidentifying_metadata(self):
        _, findings = redact_text("someone@example.invalid\n签名：合成姓名")
        for finding in findings:
            self.assertEqual(set(finding), {"type", "count", "review_required", "possible_over_redaction"})

    def test_redaction_rejects_paths_or_non_text_objects(self):
        with self.assertRaises(TypeError):
            redact_text({"source_path": "/synthetic/source.pdf"})

    def test_signature_redaction_is_idempotent_with_spaces_in_label(self):
        text, _ = redact_text("Signature:   Synthetic Name\n签名：  合成姓名")
        self.assertEqual(redact_text(text), (text, []))


if __name__ == "__main__":
    unittest.main()
