# Admission evidence source policy

T1 is a primary official source: the institution, graduate admissions office,
department, or official admissions system publishing the applicable notice.
T2 is an attributable authoritative secondary official source, such as an official
department clarification or official cross-post of the primary notice. Verify its
scope against the primary notice. T3 is a credible third-party compilation or
report. T4 is a community post, anonymous account, or other unverified lead.
T3/T4 can discover opportunities but cannot override T1. Tier precedence is
T1 (4), T2 (3), T3 (2), T4 (1); all records remain in the audit.

## Freshness and confidence

Check the current admission year's notice, program, and round before using any
requirement. Recent retrieval does not prove that a notice applies to the current
year: the validator has no admission-year field on evidence, so an operator must
check applicability and mark outdated requirements stale or missing. The automated
date rule compares retrieval calendar dates with `now.date()`; age strictly greater
than `stale_after_days` (365 by default) is stale. Exactly 365 days remains fresh.
An explicit stale status remains stale even after recent retrieval. `not_applicable`
is exempt from staleness but must be justified by its source and tier.

Critical fields are eligibility, deadline, program_availability, and degree_type.
Apply confidence in this order:

1. D: any critical field is missing or conflicted, including an explicit missing
   or conflicted record. Invalid evidence associated with a candidate also gives D.
2. C: complete conflict-free critical coverage, but at least one critical field
   has only T3/T4 usable support.
3. B: complete conflict-free critical coverage, all critical fields have T1/T2
   support, but at least one field's strongest usable record is stale.
4. A: every critical field's strongest usable record is fresh, conflict-free
   T1/T2 evidence.

The strongest usable tier follows source precedence. A stale strongest T1 keeps
confidence B even alongside fresh T2 evidence. Missing/conflicted records are
unusable. A null critical value means unknown and supplies no usable coverage
unless its status explicitly justifies it as not_applicable. All such records
remain preserved. Stale and not_applicable records remain inspectable support with
their freshness exception/status exposed. These bands describe evidence quality,
not admission probability. Candidates absent from all input records cannot be
invented by this audit; the caller must supply their evidence or missing placeholders.

## Conflicts and traceability

Assign a shared conflict_group to competing assertions of the same requirement,
candidate, and cycle. Distinct values within that group are unresolved conflicts,
even when tiers differ. Preserve every value, source, tier, and record index;
do not delete lower-tier claims or silently choose a winner. An explicit conflicted
status also remains unresolved. A human can reconcile scope or obtain an official
clarification before updating records. Automatic comparison does not normalize
semantically equivalent strings; matching groups and values is the collector's job.

Claims contain complete deep-copied input records plus derived validity, age,
freshness, status, and conflict groups. Candidate summaries expose per-field source
indexes, strongest usable tier, fresh official indexes, and the causes of the band.
Malformed inputs are retained with validator errors and excluded from aggregation.

Store a short compliant excerpt sufficient to substantiate the claim; prefer a
brief paraphrase with a source link and avoid copying a full notice or article.
Follow source licensing and quotation limits. Source URLs and publisher labels
are provenance assertions, not verification that a page was fetched by this audit.

## Synthetic evidence record

```json
{
  "claim_id": "deadline-2027-official",
  "candidate_id": "school-unit-program-master-summer-2027",
  "field": "deadline",
  "value": "2027-06-15T17:00:00+08:00",
  "source_url": "https://example.edu.cn/notice",
  "source_title": "Synthetic current-cycle notice",
  "publisher": "Example University",
  "published_at": "2027-05-01",
  "retrieved_at": "2027-05-02T10:00:00+08:00",
  "tier": "T1",
  "status": "confirmed",
  "scope": "program",
  "short_evidence": "Synthetic fixture: applications close on June 15.",
  "conflict_group": "deadline-2027"
}
```
