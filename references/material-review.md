# Material review contract

`audit_materials(manifest, claims, requirements)` is a pure function over reviewed
records. It never opens source paths, copies documents, changes applicant claim
states, verifies authenticity, or writes files. Hashes establish content identity;
document visibility is not authenticity verification. Keep the private manifest
and applicant claims in the user-selected case directory outside the skill root.

## Extraction and provenance

Readers operate on selected originals read-only. Record the content-addressed
`document_id` from the manifest with every extracted fact and retain a page,
paragraph, sheet/cell or image-region locator in private review notes. A changed
source must be hashed again and its old facts reviewed; do not attach old facts
to new bytes. Extension-only `format_class` does not identify a transcript or
recommendation; set `document_class` only after content review.

- PDF: extract text with page locators; inspect tables, signatures and dates in a
  rendered page because text extraction can lose layout. Scanned pages require
  OCR and visual review.
- DOCX: read paragraphs and tables and inspect header/footer and embedded images.
  A typed name in a draft is not evidence of a completed signature.
- XLSX: retain sheet/cell references and distinguish stored values, formulas and
  cached results. Do not execute macros or infer an official transcript from a
  spreadsheet layout.
- Images: inspect the pixels and mark OCR candidates as `inferred`, preserving
  uncertainty. Do not convert OCR guesses into `document_verified` automatically.
- Plain text: preserve line references and user assertions as `user_asserted`;
  transcription alone does not certify the underlying fact.

Manifest extraction states accepted as readable are `complete`, `extracted`, and
`reviewed`, meaning extraction/content review has produced usable observations.
`unreadable` and `failed` force an unreadable result for selected matching
documents. `not_started`, `ocr_uncertain`, `partial`, unknown or absent states need
`extraction_review` and cannot satisfy conditions. A reader must retain uncertainty
until the relevant image/region is checked; setting `complete` must not hide OCR
uncertainty. These are input assumptions, not authenticity findings by the audit.

The six applicant states remain `document_verified`, `user_asserted`, `derived`,
`inferred`, `missing`, and `conflicted`. Only `document_verified` with nonempty IDs,
all bound to readable manifest rows, can satisfy a condition. Unknown references
or empty references cannot satisfy it even if the state label says verified.
A resume-only assertion cannot satisfy verified-fact conditions; corroborate it
with the appropriate independently reviewed transcript/certificate. Reading a
resume can establish that the resume exists (an empty conditions map), not the
truth of its GPA, ranking, awards or publications.

## Target requirements

Each record has globally unique `requirement_id`, `target_id`, `item_type`,
`necessity`, `conditions`, and nonempty `source_claim_ids`. Necessity is exactly
`required`, `optional`, `conditional`, or `not_applicable`. Source claim IDs refer
to official target-policy evidence, not applicant claims. Before creating the
record, resolve them through the source-policy workflow: check the admission
year, unit/program, round, official notice and attachments. An unresolved or
conflicting policy must be clarified before assigning an affirmative requirement;
the audit validates the record shape but cannot verify URLs from IDs alone.

`conditions` maps canonical applicant claim fields to typed expected values.
The reserved value `"present"` requires a nonempty value, allowing false and zero
to be present facts. Boolean true differs from numeric 1. Other expected values
use exact typed equality; there are no silent numeric/date conversions. A
`date: "present"` condition checks presence only; target-specific validity or date
windows must be represented by separately reviewed fields/conditions.

```json
{
  "requirement_id": "target-a-recommendation-1",
  "target_id": "target-a",
  "item_type": "recommendation",
  "necessity": "required",
  "conditions": {"signature": true, "date": "present"},
  "source_claim_ids": ["target-a-official-letter-policy"],
  "document_ids": ["sha256:<full digest of selected letter>"]
}
```

Optional `document_ids` explicitly binds the requirement to selected originals.
Without it, matching `document_class` rows are alternatives. Never infer completed
recommendation status from an unsigned draft: when signature/date are required,
include those fields and obtain verified observations for the same document.
All conditions must hold for one document; two incomplete letters cannot be
spliced together. Two required letters need two requirement records bound to
their distinct selected IDs, not two unbound records matching the same letter.
An unknown or differently classified selected ID yields `materially_incomplete`;
the evaluator does not fall back to another document.

A conditional record additionally uses `applies_when: {"field": "...", "value":
...}`. A verified, unconflicted applicant field equal to that value activates the
requirement; a verified unequal value makes it `not_applicable`. Missing,
unverified or conflicted applicability produces `materially_incomplete` with
`applicability` missing. This gate is an applicant-level fact, while each target's
conditions and selected documents are evaluated separately.

## Results and contradictions

The report has `items_by_id`, `items_by_target`, `contradictions`, and
`review_required`. Items expose IDs, target/type/necessity, policy provenance IDs,
selected content IDs, `status`, `missing_conditions`, `blocking`, and
`review_required`. Status is one of `complete`, `repairable`,
`materially_incomplete`, `unreadable`, or `not_applicable`. Required/activated
conditional deficiencies block that target; optional deficiencies stay visible
without blocking. Completeness means satisfaction of reviewed input conditions,
not submission, admission, document authenticity or verification of identity.

Contradictions group the same canonical applicant field and retain every claim's
ID, state, value and source document IDs, without a winning value. Missing-state
or empty values do not create a mismatch, but an explicit `conflicted` claim is
always preserved for review. The same GPA found in a resume and transcript with
different values remains a conflict even if only the transcript is verified.
Conflicts on a requirement condition prevent completion.

Physical observations such as letter signatures/dates must use applicant claim
`scope: "document"`; otherwise scope defaults to `applicant`. Document-scoped
claims group by each referenced document, including overlapping multi-document
references, so two letters can have different signature states without inventing
an applicant-level contradiction. Use canonical shared fields only for facts
that actually share a scale/context: distinguish GPA scales and ranking
denominators before comparing. The audit does not normalize or choose them.

Stop the completion workflow for an unreadable relevant page, missing signature,
missing required date, unresolved contradiction, or unclear conditional policy.
Ask for a legible/signed/dated replacement or a source-backed clarification as
appropriate; never fabricate missing evidence or select the most favorable value.

## Generated-text redaction

`redact_text(text)` accepts a generated string and returns `(redacted_text,
findings)`. It has no path API or file writes. Redact generated reports before
saving or sharing them, including rendered contradiction values. Never pass
original documents through it or rewrite sources; keep originals immutable.

Compiled patterns cover contiguous Chinese mobile numbers (optional country
prefix), email addresses, 18-character identity-number candidates, context-labelled
student numbers, and labelled signature lines. Stable tokens are
`[REDACTED_PHONE]`, `[REDACTED_EMAIL]`, `[REDACTED_IDENTITY]`,
`[REDACTED_STUDENT_NUMBER]`, and `[REDACTED_SIGNATURE]`. Findings contain only
`type`, `count`, `review_required`, and `possible_over_redaction`; never original
matches, surrounding snippets or offsets. Signature/student patterns preserve
the context label; signature redaction stops at the newline.

Every match carries review flags because broad patterns may redact public
institutional contacts or other identifier-like text. Review the generated output
for over-redaction and missed private information before sharing. This pattern
filter does not guarantee anonymization of names, addresses, split/formatted
numbers, arbitrary handwriting, images or identifying combinations. Findings
count replacement spans in pattern order; an entire signature line or labelled
student number can consume a nested email/number before that category is counted.
