# Graduate Pathfinder · 研途择校

A local-first Codex Skill for Chinese graduate admissions decisions. Review materials, compare targets, and keep official evidence, unknowns, conflicts and calculations separate.

[中文完整版](README.zh-CN.md)

![Graduate Pathfinder Home with evidence-first guidance and clearly labeled conceptual admissions artwork](docs/assets/site-home.png)

[Public site](https://z-lab-boop.github.io/graduate-pathfinder/) · [Explore the synthetic case](https://z-lab-boop.github.io/graduate-pathfinder/explore.html) · [Docs](https://z-lab-boop.github.io/graduate-pathfinder/docs.html) · [Installation](https://z-lab-boop.github.io/graduate-pathfinder/docs.html#install) · [Release status](https://z-lab-boop.github.io/graduate-pathfinder/docs.html#source)

The public site is a synthetic walkthrough with fictional applicants and institutions. It accepts no uploads, has no tracking, and offers no personal admission probability or guarantee. Concept artwork is labeled separately from synthetic product screenshots. No tagged binary release is published; install the complete source repository. Website assets and screenshots are documentation, not release binaries. These links identify the intended Pages routes; local verification does not establish live deployment.

## Product boundaries

This is decision support, not an official admissions system or a complete nationwide school database. Check current official evidence for the exact intake year and target identity. Missing, stale or conflicting evidence stays `unknown`, `conflicted` or `evidence_insufficient`.

The Skill does not:

- submit applications, log in to admissions systems, send messages, contact supervisors or accept offers;
- authenticate materials, edit originals, or silently promote resume statements to verified facts;
- promise admission or output personal admission probabilities without lawful, comparable, evaluated individual-level data and a usable model.

## Capabilities

| Version | Route | Capabilities |
| --- | --- | --- |
| v0.1 | Baoyan (recommendation route) | Opportunity screening, target comparison, application portfolios, deadlines and schedule conflicts |
| v0.2 | Kaoyan (exam route) | Subject gates, score scenarios, distinct threshold meanings, risk bands and shortlists |
| v0.3 | Materials and outlook | Local material inventories and review, scoped previous-cycle timelines/counts, comparable cohort ratios, ordinal competition and evidence confidence |

Baoyan and kaoyan gates, groupings and reporting contracts remain separate. For mixed requests, the Skill first establishes the route and intake year, then loads the relevant references.

## Install

1. Copy the HTTPS URL from this repository’s **Code** menu and clone into a local directory.
2. Link the complete directory into Codex’s skills directory. Inspect an existing destination before proceeding; do not overwrite it.

On macOS/Linux, run from the repository root:

```bash
set -eu
codex_root="${CODEX_HOME:-$HOME/.codex}"
skill_parent="$codex_root/skills"
skill_target="$skill_parent/graduate-pathfinder"
mkdir -p "$skill_parent"
if [ -e "$skill_target" ] || [ -L "$skill_target" ]; then
  printf '%s\n' "Refusing to overwrite existing skill target: $skill_target" >&2
  exit 1
else
  ln -s "$(pwd)" "$skill_target"
  python3 "$skill_parent/.system/skill-creator/scripts/quick_validate.py" "$skill_target"
fi
```

Alternatively, copy the complete repository to `$CODEX_HOME/skills/graduate-pathfinder` (default `$HOME/.codex/skills/graduate-pathfinder`). Include `SKILL.md`, `references/`, `scripts/` and `agents/`; do not copy just the entry file.

## Usage examples

Paste one of these original Chinese prompts into Codex and adapt the facts to your case.

```text
使用 $graduate-pathfinder，我是计算机专业前 5%，做一份 2027 保研投递组合。
```

```text
使用 $graduate-pathfinder，我估分 355，想考长三角的控制工程，先核对科目组合和官方口径，再给 shortlist。
```

```text
使用 $graduate-pathfinder，我会提供简历、成绩单和推荐信草稿。请复核这个保研目标的材料，整理上一可比年度的面试时间和各阶段人数，再给出序数竞争档位和不确定性。
```

Allow Codex to browse and prioritize official sources for current rules, deadlines, historical lists and counts. Without browsing, use user-provided official materials and local cases, retain evidence gaps, and stop judgments that depend on unavailable facts.

## Local cases and privacy

- Quick screening can stay in chat; create cases only when persistence or file delivery is requested.
- Keep cases outside the installed Skill, normally at `graduate-pathfinder-cases/<anonymous-label>/` in the working directory.
- Originals stay at user-selected local paths. A manifest records paths, hashes and extraction states without copying or rewriting the files.
- Keep identity/student numbers, phone numbers, private email addresses, signatures and home addresses out of public repositories, Issues and shareable reports. Manually review automated redaction before sharing.
- The public repository contains fictional test data, not real applicant cases or datasets copied from restricted sources.

## Deliverables

In-depth target selection can produce `profile.json`, `candidates.json`, `evidence.json`, `candidate-matrix.csv`, `report.md` and optional `deadlines.ics`. Refresh mode also produces `changes.md`.

v0.3 material review/outlook uses five public-safe deliverables:

- `material-audit.md`: target-specific completeness, condition gaps and conflicts;
- `applicant-claims.json`: normalized academic claims and their evidence states;
- `historical-cycle.json`: scoped timelines, stage counts, calculations and refusal reasons;
- `admission-outlook.md`: separate eligibility, material readiness, competition, fit and evidence confidence;
- `privacy-review.md`: redaction scope, possible over-redaction and human-review status.

`materials-manifest.json`, material requirements, full evidence audits and raw function results remain local inputs/intermediates, not default public deliverables. Public-safe outputs still require redaction and human privacy review before sharing.

## Historical ratios are not personal probabilities

Compute historical stage ratios such as `final_admitted / confirmed_attended` only with matching year, institution, unit, program code, degree type, track and round, and a verified denominator. These describe a past cohort, not the current applicant’s probability. Competition is a transparent ordinal judgment, separate from baoyan portfolio groups and kaoyan risk bands; no tier guarantees admission.

## Synthetic product views

These browser captures show fictional data and the local installation guide. Concept artwork is a visual metaphor, not applicant evidence or a real institution.

![Synthetic Explore material review showing fictional targets, evidence filters and open material gaps](docs/assets/site-explore.png)

![Graduate Pathfinder Docs showing version boundaries and navigation to complete-Skill installation and privacy guidance](docs/assets/site-docs.png)

## Verification

From the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 /path/to/skill-creator/scripts/quick_validate.py .
python3 -m compileall -q scripts tests
npm --prefix web ci
npm --prefix web run typecheck
npm --prefix web run test:site
npm --prefix web run capture:site
node scripts/check-site-assets.mjs
git diff --check
```

Install Playwright Chromium if your environment lacks it: `npm --prefix web exec playwright install chromium`. Captures use an owned dynamic localhost child server, English, a 1440×1000 viewport, device scale 1 and reduced motion. Each image is the top viewport, not a full-page record; Explore starts at Northlake / Materials with all evidence filters enabled. Compare SHA-256 hashes after two same-platform runs. See [capture policy and artwork audit](docs/assets/README.md).

These automated checks cover structure, decision logic and synthetic behavior. They neither authenticate real materials nor establish current nationwide admissions coverage. Live Pages and hosted CI acceptance require separate verification after deployment.

## Research basis and license

See [research basis](references/research-basis.md) for surveyed projects, distilled general mechanisms and reuse status. Their code and data are not copied by default; audit file-level licensing and attribution before introducing third-party material.

Released under the [MIT License](LICENSE).
