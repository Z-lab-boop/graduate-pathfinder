# Graduate Pathfinder Public Site Design

Date: 2026-10-09  
Status: approved in chat; awaiting written-spec review  
Repository: `Z-lab-boop/graduate-pathfinder`

## 1. Objective

Create a distinctive public website for Graduate Pathfinder that makes the repository immediately understandable and visually memorable while preserving the Skill's evidence-first boundaries.

The site must present Graduate Pathfinder as a local-first Codex Skill for Chinese graduate admissions decisions. It must highlight baoyan material review, target-school comparison, scoped previous-cycle interview timelines and counts, and ordinal admission outlook without implying an official database, a personal admission probability, or an automated submission service.

The default experience is English, with an explicit Chinese switch. The site will be deployed from this repository to GitHub Pages.

## 2. Product boundary

The website is a public explanation and synthetic walkthrough, not a hosted admissions evaluator.

It will:

- explain the v0.1–v0.3 capabilities and evidence model;
- demonstrate the workflow with committed fictional data;
- show how materials, requirements, historical counts, conflicts, and outlook remain separate;
- link to installation and local Skill usage;
- make privacy and uncertainty visible instead of hiding them.

It will not:

- accept document uploads or store applicant data;
- call a backend, analytics service, external font service, CDN, or third-party runtime API;
- claim live nationwide school coverage;
- display invented facts under real university names;
- output a personal admission probability or guarantee;
- submit materials, log in to admissions systems, contact supervisors, or accept offers.

## 3. Audience and success criteria

Primary audiences:

1. Chinese undergraduates evaluating baoyan or graduate-school options.
2. Codex users deciding whether to install the Skill.
3. Open-source reviewers checking whether the project is trustworthy and usable.

Success means:

- a first-time visitor understands the product in under one minute;
- the visual identity is clearly connected to admissions evidence, files, and timelines rather than generic AI software;
- English and Chinese visitors receive complete, equivalent explanations;
- the interactive demo is useful without being mistaken for real applicant or university data;
- the site works at the `/graduate-pathfinder/` GitHub Pages subpath, on mobile, without JavaScript for core explanations, and without external runtime requests;
- repository screenshots and site assets are reproducible and verified.

## 4. Information architecture

The public site has three static pages.

### 4.1 Home

Home introduces the product through a split editorial composition:

- left: a concise statement, installation path, and evidence-first promises;
- right: an original photographic composition of an admissions dossier, annotated timeline, and campus archive;
- below: a five-stage journey — Profile, Materials, Targets, History, Outlook;
- proof panel: a real screenshot produced from the synthetic browser walkthrough;
- boundary strip: local-first, no upload, no guaranteed admission, no hidden probability.

Primary headline:

> Every application claim needs a source.

Chinese equivalent:

> 每一项申请判断，都应有证据来源。

Primary actions:

- Explore the synthetic case
- Install the Skill

### 4.2 Explore

Explore is a client-only walkthrough using a fictional applicant and fictional institutions. It demonstrates four coordinated views:

1. **Materials** — resume, transcript, recommendation draft, signatures, dates, extraction state, and target-specific gaps.
2. **Targets** — three fictional candidates with eligibility, fit, readiness, and evidence confidence kept separate.
3. **Previous cycle** — a scoped timeline and stage counts with explicit numerator, denominator, scope, and refusal-to-calculate states.
4. **Outlook** — five independent dimensions: eligibility, material readiness, ordinal competitive tier, fit, and evidence confidence.

Interaction requirements:

- select a fictional target and update every linked panel;
- filter evidence by confirmed, missing, conflicted, or review-required;
- inspect the exact source claim behind a requirement or historical count;
- open a safe-fix preview for a material gap, labeled as guidance only;
- switch English/Chinese without losing selection;
- navigate all tabs, filters, records, and dialogs with a keyboard;
- show a clear unavailable state if the committed demo file fails validation.

The page must continuously display `Synthetic walkthrough / 合成演示`. No real school name, person, email, identifier, URL, credential, home path, or plausible private record may be included.

### 4.3 Docs / Install

Docs explains:

- what Graduate Pathfinder is and is not;
- v0.1 baoyan portfolio, v0.2 kaoyan gates, and v0.3 material/outlook capabilities;
- safe installation of the complete Skill directory;
- three copyable usage examples;
- local case files and five v0.3 public-safe deliverables;
- privacy, evidence tiers, historical-ratio semantics, and refusal conditions;
- source build/test commands and the current release boundary.

Docs must not claim a binary release unless a tagged release with assets is verified. The static HTML must retain authoritative English text when JavaScript is disabled.

## 5. Visual direction: Admissions Evidence Atlas

The selected C2 direction becomes an admissions archive rather than a software observatory.

### 5.1 Mood

- scholarly editorial archive;
- field notes, registration marks, stamped evidence states, and measured timelines;
- quiet confidence rather than futuristic AI spectacle;
- asymmetric split layouts and layered documents rather than a conventional SaaS card grid.

### 5.2 Palette

- archive paper: warm bone and pale flax;
- ink: deep navy-black;
- verified: mineral teal;
- attention: cinnabar red;
- unknown: muted brass;
- conflict: dark plum;

All foreground, control, focus, and state combinations must meet WCAG AA contrast requirements. Focus indicators must reach at least 3:1 against adjacent surfaces.

### 5.3 Typography

Use a bundled or system-safe editorial serif for display and a restrained sans/monospace stack for evidence labels. No runtime font downloads are allowed. The design must not rely on generic purple gradients, glassmorphism, or common AI landing-page motifs.

### 5.4 Original image set

Generate three original raster images and store them in the repository:

1. `admissions-atlas-hero`: overhead archival desk with abstract application folders, translucent timeline strips, brass measurement tools, and a distant campus silhouette; no readable text, logo, person, or real institution.
2. `materials-review`: close crop of anonymous paper layers, seal impressions, checklist geometry, and soft window light; no readable content or identifying marks.
3. `campus-route`: cinematic architectural corridor with map-like light paths and no recognizable university branding or people.

Every image receives a provenance note and a visible caption describing it as conceptual artwork. Product screenshots must be generated from the synthetic site, labeled separately, and never presented as real applicant evidence.

## 6. Technical architecture

Keep the existing Python Skill and tests unchanged except for repository integration checks.

New website source lives under `web/site/`:

- three static HTML entry files;
- focused TypeScript modules for language, demo schema, state, and page rendering;
- one CSS system with page-specific sections;
- committed synthetic JSON under `web/site/data/`;
- local generated images under `web/site/assets/generated/`;
- Playwright tests under `web/site/tests/`.

A small Node build script compiles TypeScript/CSS and copies static assets to `dist/site/`. All output URLs remain relative so the same build works at localhost and `/graduate-pathfinder/`.

The language system uses English static HTML as the no-JavaScript baseline. JavaScript applies complete English or Chinese dictionaries only after an explicit user choice. The choice is stored only in `localStorage`; no cookies, browser-locale auto-switch, or remote persistence.

The synthetic demo parser must reject:

- unknown fields and enum values;
- duplicate IDs and broken references;
- absolute paths, home shorthand, URLs, emails, identifiers, and credential-shaped values;
- real-school domains or non-fictional institution markers;
- unsafe markup or values intended for HTML interpretation.

Rendering uses created elements, `textContent`, and attribute setters. Demo values are never inserted through `innerHTML`.

## 7. Synthetic data model

The demo contains:

- one fictional applicant profile with no identifying fields;
- three fictional targets with invented institution/unit/program names;
- six fictional documents with extraction/readiness states;
- target-specific material requirements;
- evidence claims with source tier and status;
- a previous-cycle timeline and counts for one precisely defined fictional scope;
- at least one valid historical metric and one intentionally refused metric;
- an outlook object with five independent dimensions and explicit missing/conflict reasons.

Historical stage ratios must always display their scope and the warning that they describe a past cohort, not the current applicant's probability.

## 8. Accessibility and responsive behavior

- semantic landmarks and a skip link on every page;
- keyboard-operable language switch, tabs, filters, target list, evidence inspector, and preview dialog;
- visible focus indicators on light and dark surfaces;
- meaningful alt text for product screenshots and empty alt text for purely decorative layers;
- no information encoded only by color;
- reduced-motion mode removes nonessential transitions and parallax;
- no horizontal page overflow at 360, 768, or 1440 CSS pixels in either language;
- core Home and Docs content remains useful without JavaScript.

## 9. Privacy, security, and truthfulness

- no upload, form submission, mutation request, analytics, telemetry, service worker, or external runtime request;
- all demo requests are same-origin GETs for committed files;
- no real admissions data or copied restricted dataset;
- no claim that visible material is authentic;
- no personal probability language;
- no claim that historical counts are current or universally comparable;
- no release/download claim without a verified release asset;
- generated images are conceptual; screenshots are synthetic product evidence.

## 10. Repository presentation

Refresh `README.md` as the English-first repository entry and provide `README.zh-CN.md` as the full Chinese equivalent. Both openings include:

- a concise product statement;
- a link to the language counterpart;
- the approved Home screenshot;
- links to the public site, Explore, Docs, installation, and release status;
- explicit synthetic/privacy/probability boundaries.

Add deterministic capture tooling for Home, Explore, and Docs. Asset checks verify existence, dimensions, size, README references, alt text, and inclusion policy. Site captures are repository documentation, not release binaries.

## 11. Deployment

Add a least-privilege GitHub Pages workflow:

- trigger only from `main` and guarded manual dispatch;
- build and test the site before upload;
- upload only `dist/site/`;
- use ref-scoped concurrency so a rejected non-main run cannot cancel a main deployment;
- do not overwrite an existing Pages source or custom domain without an explicit check.

Before enabling Pages, inspect current repository settings. A 404 means no site exists; another source or custom domain requires stopping for review.

## 12. Verification

Required automated checks:

- existing `python3 -m unittest discover -s tests -v` remains green;
- Skill structural validation and compileall remain green;
- TypeScript typecheck and static build;
- Playwright behavior, bilingual, no-JavaScript, keyboard, privacy, failure, subpath, and responsive tests;
- deterministic screenshot capture and asset policy checks;
- repository safety check for private-data canaries and unintended artifacts;
- workflow YAML and shell-block validation;
- `git diff --check`.

Required human checks:

- inspect all generated images for accidental text, logos, people, or institutional identity;
- inspect Home/Explore/Docs at desktop and mobile widths in both languages;
- confirm generated-image captions and synthetic labels are visually obvious;
- after merge, verify hosted CI and the live GitHub Pages URL.

## 13. Out of scope

- real document upload or in-browser parsing;
- user accounts, cloud storage, databases, or a hosted assessment API;
- a nationwide university/program dataset;
- automated scraping from the public site;
- payment, subscriptions, notifications, or application submission;
- binary release publication.

