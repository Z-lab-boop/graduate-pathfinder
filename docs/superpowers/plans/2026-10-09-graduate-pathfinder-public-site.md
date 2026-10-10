# Graduate Pathfinder Public Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publicly deploy an English-first, Chinese-switchable Graduate Pathfinder website with an original admissions-archive visual identity, a privacy-safe synthetic admissions walkthrough, truthful installation documentation, and reproducible GitHub presentation assets.

**Architecture:** Add an isolated static-site subsystem under `web/site/` without changing the existing Skill runtime or Python decision logic. A small TypeScript/Node build produces relative-path static files in `dist/site/`; committed fictional JSON drives a client-only Explore page, while Home and Docs retain authoritative English content without JavaScript. Playwright, repository policy checks, and a least-privilege Pages workflow verify the public artifact.

**Tech Stack:** Static HTML, CSS, TypeScript, Node.js build scripts, Playwright, existing Python `unittest`, GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-09-graduate-pathfinder-public-site-design.md`

## Global Constraints

- Work only in `Z-lab-boop/graduate-pathfinder`; never modify or publish `Z-lab-boop/HarnessScope`.
- Preserve the existing Skill behavior, Python scripts, references, test fixtures, and `v0.3.0` release semantics.
- English is the static and default language; Chinese is enabled only by an explicit switch and persisted only in `localStorage`.
- The site makes no external runtime request: no analytics, telemetry, CDN, remote font, backend, upload, service worker, or third-party API.
- Explore uses only committed fictional data and labels itself `Synthetic walkthrough / 合成演示` continuously.
- Never claim live nationwide coverage, material authenticity, personal admission probability, guaranteed admission, automatic submission, or a binary release that has not been verified.
- Historical ratios describe one precisely scoped fictional past cohort and never the fictional applicant's probability.
- Generated images are conceptual art; product screenshots come only from the synthetic site and receive different captions.
- All URLs must work at `/graduate-pathfinder/`; all asset and navigation URLs are relative.
- Keyboard focus indicators must provide at least 3:1 contrast against adjacent light and dark surfaces; no information is color-only.
- Home and Docs remain useful without JavaScript; reduced motion and 360/768/1440 px layouts are tested in both languages.
- `dist/`, Playwright results, local cases, generated scratch files, and private applicant material never enter the repository or release archives.

---

### Task 1: Static Build, Page Shell, and Explicit Bilingual Runtime

**Files:**
- Create: `web/package.json`
- Create: `web/package-lock.json`
- Create: `web/tsconfig.json`
- Create: `web/site/build.mjs`
- Create: `web/site/test-server.mjs`
- Create: `web/site/playwright.config.ts`
- Create: `web/site/index.html`
- Create: `web/site/explore.html`
- Create: `web/site/docs.html`
- Create: `web/site/src/i18n.ts`
- Create: `web/site/src/site.ts`
- Create: `web/site/src/site.css`
- Create: `web/site/tests/shell.spec.ts`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: no earlier task output.
- Produces: `Language = "en" | "zh-CN"`, `copy: Record<Language, Record<string,string>>`, `applyLanguage(language: Language): void`, `initSite(): void`, `npm --prefix web run build:site`, `npm --prefix web run test:site`, and `dist/site/`.

- [ ] **Step 1: Add the package scripts and failing shell test**

Install and lock the development dependencies:

```bash
npm --prefix web install --save-dev @playwright/test typescript
```

Set these scripts in `web/package.json`:

```json
{
  "private": true,
  "scripts": {
    "build:site": "node site/build.mjs",
    "typecheck": "tsc --noEmit -p tsconfig.json",
    "test:site": "npm run build:site && playwright test --config site/playwright.config.ts"
  }
}
```

Start `shell.spec.ts` with exact requirements:

```ts
import { expect, test } from "@playwright/test";

for (const path of ["/", "/explore.html", "/docs.html"]) {
  test(`${path} has an English-first accessible shell`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeVisible();
    await expect(page.getByRole("button", { name: "切换到中文" })).toBeVisible();
    await expect(page.locator("main")).toBeVisible();
  });
}

test("language choice is explicit, local and persistent", async ({ page, context }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "切换到中文" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN");
  expect(await context.cookies()).toEqual([]);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN");
});
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run:

```bash
npm --prefix web run test:site -- --grep "English-first|language choice"
```

Expected: FAIL because the build, pages, and language runtime do not exist.

- [ ] **Step 3: Implement the build and contained test server**

`build.mjs` must:

- remove only `dist/site/` resolved from the repository root;
- copy the three HTML entries, CSS, data, and assets;
- transpile TypeScript with the installed compiler into ESM JavaScript;
- reject output paths outside `dist/site/`;
- preserve relative URLs and never inject a production origin.

`test-server.mjs` must:

- bind only `127.0.0.1`;
- serve both `/` and `/graduate-pathfinder/` prefixes;
- normalize percent-encoding and reject traversal;
- support GET and HEAD only;
- set correct HTML, CSS, JS, JSON, PNG, and SVG MIME types;
- accept an optional port argument and emit one JSON readiness line with PID, host, and actual port.

- [ ] **Step 4: Implement the English static shells and bilingual runtime**

Each HTML file contains a complete English header, navigation, main heading, privacy/footer text, skip link, and language button before JavaScript runs. Use only relative references such as `./assets/site.css` and `./assets/site.js`.

`i18n.ts` defines strict key parity:

```ts
export type Language = "en" | "zh-CN";
export const LANGUAGE_KEY = "graduate-pathfinder-language";
export const copy: Record<Language, Record<string, string>> = {
  en: { "nav.home": "Home", "nav.explore": "Explore", "nav.docs": "Docs" },
  "zh-CN": { "nav.home": "首页", "nav.explore": "演示", "nav.docs": "文档" }
};
```

`site.ts` ignores browser locale, accepts only the two allowlisted stored values, updates `[data-i18n]` with `textContent`, updates `lang`, button accessible name, title, and metadata, and catches storage errors without breaking English fallback.

CSS establishes the archive-paper/ink/cinnabar tokens, semantic shell, skip link, dark and light focus variables, responsive navigation, and reduced-motion baseline.

- [ ] **Step 5: Verify the shell contract**

Add tests for:

- invalid stored values remain English;
- no-JavaScript Home and Docs keep headings/navigation/privacy text;
- `/graduate-pathfinder/` serves every page and asset;
- encoded traversal is rejected;
- 360 px has no page overflow;
- computed focus outline contrast reaches 3:1 on light and dark surfaces.

Run:

```bash
npm --prefix web run typecheck
npm --prefix web run test:site
git diff --check
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .gitignore web/package.json web/package-lock.json web/tsconfig.json web/site
git commit -m "feat: add bilingual graduate pathfinder site shell"
```

---

### Task 2: Original Admissions-Archive Artwork and Home Story

**Files:**
- Create: `web/site/assets/generated/admissions-atlas-hero.png`
- Create: `web/site/assets/generated/materials-review.png`
- Create: `web/site/assets/generated/campus-route.png`
- Create: `web/site/assets/generated/README.md`
- Create: `web/site/src/home.ts`
- Create: `web/site/tests/home.spec.ts`
- Modify: `web/site/index.html`
- Modify: `web/site/src/site.ts`
- Modify: `web/site/src/site.css`

**Interfaces:**
- Consumes: `initSite()`, `applyLanguage()`, Task 1 tokens/build.
- Produces: `homeCopy: Record<Language, Record<string,string>>`, `initHome(): void`, three reviewed local concept images, the five-stage journey, and truthful product/concept captions.

- [ ] **Step 1: Write failing Home behavior tests**

```ts
test("Home tells the evidence-first story with truthful image roles", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Every application claim needs a source." })).toBeVisible();
  await expect(page.getByText("Concept artwork", { exact: true })).toHaveCount(3);
  await expect(page.getByText("Synthetic product walkthrough", { exact: true })).toBeVisible();
  await expect(page.getByText("No uploads · no admission guarantees", { exact: true })).toBeVisible();
});

test("journey navigation preserves the selected stage", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Materials" }).click();
  await page.waitForTimeout(250);
  await expect(page.getByRole("link", { name: "Materials" })).toHaveAttribute("aria-current", "step");
});
```

- [ ] **Step 2: Run and confirm failure**

Run `npm --prefix web run test:site -- --grep "Home|journey"`.

Expected: FAIL because the Home story and art do not exist.

- [ ] **Step 3: Generate and inspect the three original images**

Use the built-in image generation tool with these exact creative briefs:

```text
admissions-atlas-hero.png — 3:2 editorial photograph, overhead archival admissions desk, anonymous layered application folders with no readable text, translucent timeline strips, brass measuring tools, cinnabar registration marks, distant abstract campus silhouette reflected in dark glass, warm bone paper against deep navy, museum catalog lighting, tactile grain, no people, no logo, no watermark, no institution identity.
```

```text
materials-review.png — 4:3 macro editorial photograph of anonymous document layers, blank recommendation envelope, embossed seal impressions without letters, checklist geometry without readable text, mineral teal and cinnabar evidence tabs, soft side-window light, scholarly archive atmosphere, no people, no logo, no watermark, no identity data.
```

```text
campus-route.png — 16:9 cinematic architectural corridor of a fictional campus, map-like bands of light tracing several possible routes, archive-paper and deep-ink palette with restrained brass highlights, atmospheric but realistic, no people, no sign, no logo, no recognizable university architecture, no readable text.
```

Visually inspect original pixels. Regenerate any image containing apparent letters, logos, people, or recognizable institutional markers. Record prompt, generation date, tool, final dimensions, and SHA-256 in `assets/generated/README.md`.

- [ ] **Step 4: Implement the split Admissions Evidence Atlas Home**

Build:

- asymmetric hero with concise copy and archive artwork;
- five-stage Profile → Materials → Targets → History → Outlook journey;
- evidence-state legend with text and shape, not color only;
- an HTML evidence-flow preview explicitly labeled as synthetic product UI; Task 5 later adds deterministic page screenshots to the repository README;
- local/privacy boundary strip;
- concept captions under all three generated images.

`initHome()` must synchronize click, keyboard focus, URL fragment, `aria-current="step"`, and visible stage. When multiple stages have equal intersection ratios, keep the current stage rather than reverting to the first stage.

- [ ] **Step 5: Verify visuals, behavior, translation, and responsive layout**

Test:

- all images load under `/graduate-pathfinder/`;
- image alternatives and captions are truthful;
- 360/768/1440 px layouts have no overflow in English and Chinese;
- keyboard journey works after observer delivery;
- reduced motion removes nonessential reveal/parallax;
- static English journey remains understandable without JavaScript.

Run:

```bash
npm --prefix web run test:site -- --grep "Home|journey|home"
npm --prefix web run typecheck
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add web/site/assets/generated web/site/index.html web/site/src/home.ts web/site/src/site.ts web/site/src/site.css web/site/tests/home.spec.ts
git commit -m "feat: create admissions evidence atlas home"
```

---

### Task 3: Validated Synthetic Admissions Walkthrough

**Files:**
- Create: `web/site/data/demo.json`
- Create: `web/site/src/demo-schema.ts`
- Create: `web/site/src/explore.ts`
- Create: `web/site/tests/explore.spec.ts`
- Modify: `web/site/explore.html`
- Modify: `web/site/src/site.ts`
- Modify: `web/site/src/site.css`

**Interfaces:**
- Consumes: Task 1 language runtime and Task 2 tokens.
- Produces: `parseDemo(input: unknown): Demo`, `initExplore(): Promise<void>`, target selection, evidence filters, materials/targets/history/outlook views, evidence inspector, and guidance-only fix preview.

- [ ] **Step 1: Write failing Explore interaction tests**

```ts
test("Explore stays synthetic and keeps five outlook dimensions separate", async ({ page }) => {
  await page.goto("/explore.html");
  await expect(page.getByText("Synthetic walkthrough", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Northlake Institute · Data Systems" }).click();
  await expect(page.getByRole("region", { name: "Admission outlook" })).toContainText("Eligibility");
  await expect(page.getByRole("region", { name: "Admission outlook" })).toContainText("Material readiness");
  await expect(page.getByRole("region", { name: "Admission outlook" })).not.toContainText(/\d+% chance/i);
});

test("historical counts explain scope and refused calculations", async ({ page }) => {
  await page.goto("/explore.html");
  await page.getByRole("tab", { name: "Previous cycle" }).click();
  await expect(page.getByText("Past cohort description · not personal probability", { exact: true })).toBeVisible();
  await expect(page.getByText("Refused: stage scopes do not match", { exact: true })).toBeVisible();
});
```

- [ ] **Step 2: Run and confirm failure**

Run `npm --prefix web run test:site -- --grep "Explore|historical"`.

Expected: FAIL because the schema, data, and interactive views do not exist.

- [ ] **Step 3: Define the strict demo schema**

Define exact discriminated interfaces in `demo-schema.ts`:

```ts
export type EvidenceStatus = "confirmed" | "missing" | "conflicted" | "review_required";
export type OutlookState = "eligible" | "blocked" | "ready" | "repairable" | "reach" | "core" | "safety" | "insufficient" | "high" | "medium" | "low";
export interface DemoMaterial { id:string; label:string; kind:"resume"|"transcript"|"recommendation"|"certificate"; extraction:"reviewed"|"partial"|"unreadable"; evidence:EvidenceStatus; }
export interface DemoTarget { id:string; institution:string; unit:string; program:string; degree:"academic"|"professional"; round:"summer-camp"|"pre-recommendation"|"september"; }
export interface DemoCount { id:string; target_id:string; stage:"applied"|"interviewed"|"attended"|"admitted"; value:number; scope_id:string; evidence_id:string; }
export interface DemoOutlook { target_id:string; eligibility:OutlookState; material_readiness:OutlookState; competitive_tier:OutlookState; fit:OutlookState; confidence:OutlookState; reasons:string[]; }
```

Add explicit requirement, event, metric, evidence, and fix-preview interfaces. `parseDemo` must reject unknown fields, duplicate IDs, broken references, negative/non-integer counts, non-allowlisted enums, unsafe markup, absolute/home paths, URLs, emails, student/identity/phone patterns, credential keys including quoted JSON keys, credential values, and non-fictional institution markers. It returns a defensive copy with deterministic ordering.

- [ ] **Step 4: Create the fictional dataset**

Use only clearly invented names such as:

- Northlake Institute · Data Systems
- Meridian Technical College · Intelligent Systems
- Harborline Academy · Human-Centered Computing

Include:

- six anonymous materials;
- target-specific requirements and at least one unsigned/draft gap;
- confirmed, missing, conflicted, and review-required evidence;
- one precisely matched historical metric;
- one refused metric caused by mismatched scope;
- five independent outlook dimensions per target;
- guidance-only fixes that never say Apply or Submit.

- [ ] **Step 5: Implement safe DOM/SVG views**

Build a semantic target rail, tablist, materials matrix, timeline, stage-count diagram, five-axis outlook, evidence inspector, and preview dialog. SVG elements have adjacent semantic button/list equivalents. Selecting any representation updates the same state and inspector. All demo values are rendered with `textContent`/created elements; only fixed trusted templates may exist in source HTML.

Every fetch is same-origin GET. On network, status, JSON, or schema failure, remove partial results and show `Walkthrough unavailable` with a stable link to `https://github.com/Z-lab-boop/graduate-pathfinder/blob/main/tests/fixtures/baoyan_case/expected-behavior.md`.

- [ ] **Step 6: Add schema, privacy, keyboard, and failure tests**

Cover:

- every enum and foreign-field rejection;
- quoted/unquoted credential assignments in every display field;
- real-school domains/names canaries;
- deterministic defensive copy;
- target and tab keyboard navigation;
- filter composition and empty state;
- English/Chinese dynamic copy without state loss;
- no PUT/POST/PATCH/DELETE, cookies, or cross-origin request;
- failure modes render zero partial records;
- 360/768/1440 px with dialogs open;
- no `/Users/`, `/home/`, email, phone, student number, identity number, `sk-`, token, or session canary in rendered text.

Run:

```bash
npm --prefix web run test:site -- --grep "Explore|demo schema|privacy|historical"
npm --prefix web run typecheck
git diff --check
```

- [ ] **Step 7: Commit**

```bash
git add web/site/data/demo.json web/site/explore.html web/site/src/demo-schema.ts web/site/src/explore.ts web/site/src/site.ts web/site/src/site.css web/site/tests/explore.spec.ts
git commit -m "feat: add synthetic admissions walkthrough"
```

---

### Task 4: Complete Docs, Install, and Bilingual Content

**Files:**
- Create: `web/site/src/content.ts`
- Create: `web/site/tests/content.spec.ts`
- Modify: `web/site/docs.html`
- Modify: `web/site/index.html`
- Modify: `web/site/explore.html`
- Modify: `web/site/src/i18n.ts`
- Modify: `web/site/src/site.ts`
- Modify: `web/site/src/site.css`
- Modify: `web/site/playwright.config.ts`

**Interfaces:**
- Consumes: every user-visible key from Tasks 1–3.
- Produces: exhaustive `contentCopy: Record<Language, ContentCopy>`, authoritative English static Docs/Home, complete Chinese runtime content, and dedicated no-JavaScript projects.

- [ ] **Step 1: Write content-contract tests**

```ts
test("translation dictionaries have exact nonempty bilingual keys", async () => {
  expect(Object.keys(contentCopy.en).sort()).toEqual(Object.keys(contentCopy["zh-CN"]).sort());
  expect(Object.values(contentCopy.en).every(Boolean)).toBe(true);
  expect(Object.values(contentCopy["zh-CN"]).every(Boolean)).toBe(true);
});

test("Docs states the truthful release boundary", async ({ page }) => {
  await page.goto("/docs.html");
  await expect(page.getByRole("heading", { name: "Install the complete Skill" })).toBeVisible();
  await expect(page.getByText("No tagged binary release is published.", { exact: true })).toBeVisible();
  await expect(page.getByText(/download binary/i)).toHaveCount(0);
});
```

- [ ] **Step 2: Run and confirm failure**

Run `npm --prefix web run test:site -- --grep "translation|release boundary|Docs"`.

Expected: FAIL because complete content and Docs do not exist.

- [ ] **Step 3: Implement complete English and Chinese content**

Cover every visible label, heading, paragraph, badge, accessible name, metadata field, error message, dynamic evidence state, target view, timeline label, preview message, and footer. Enforce exact key parity at type/test time.

Docs must include the safe symlink installation command from the existing README, explain that the whole repository directory is required, and provide the three existing usage examples for baoyan, kaoyan, and v0.3 material/outlook review.

Truthful copy must state:

- the Skill is local-first and public source/tests are available;
- no tagged binary release is published;
- site demo data are fictional;
- material review does not authenticate documents;
- historical ratios are not personal probabilities;
- current requirements/dates/counts require official evidence for the exact year and target identity.

- [ ] **Step 4: Add a real JavaScript-disabled Playwright project**

Configure two projects:

```ts
projects: [
  { name: "chromium", grepInvert: /^JavaScript fallback/, use: { browserName: "chromium" } },
  { name: "no-javascript", grep: /^JavaScript fallback/, use: { browserName: "chromium", javaScriptEnabled: false } }
]
```

No-JavaScript tests assert Home and Docs retain the main heading, page navigation, three image-role captions, installation command, privacy statement, and release boundary. Explore shows a precise interaction-required message while retaining navigation and documentation links.

- [ ] **Step 5: Verify content and responsive behavior**

Test every `[data-i18n]` key in both languages, title/description metadata, links, copyable commands, 360/768/1440 px layout, and no missing/undefined text. Cross-check public claims against `README.md`, `SKILL.md`, `references/baoyan-mode.md`, and `references/material-review.md`.

Run:

```bash
npm --prefix web run test:site -- --grep "translation|Docs|JavaScript fallback|release boundary"
npm --prefix web run test:site
npm --prefix web run typecheck
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add web/site/docs.html web/site/index.html web/site/explore.html web/site/src/content.ts web/site/src/i18n.ts web/site/src/site.ts web/site/src/site.css web/site/playwright.config.ts web/site/tests/content.spec.ts
git commit -m "feat: complete bilingual graduate pathfinder content"
```

---

### Task 5: Reproducible Captures and Repository Home

**Files:**
- Create: `web/site/capture.mjs`
- Create: `web/site/capture-server.mjs`
- Create: `web/site/tests/capture.spec.ts`
- Create: `scripts/check-site-assets.mjs`
- Create: `docs/assets/site-home.png`
- Create: `docs/assets/site-explore.png`
- Create: `docs/assets/site-docs.png`
- Create: `README.zh-CN.md`
- Modify: `README.md`
- Modify: `web/package.json`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: final Tasks 1–4 pages and build.
- Produces: `npm --prefix web run capture:site`, three deterministic PNGs, `node scripts/check-site-assets.mjs`, English-first README, and full Chinese README.

- [ ] **Step 1: Add failing capture and README policy tests**

```ts
for (const name of ["site-home.png", "site-explore.png", "site-docs.png"]) {
  test(`${name} satisfies the public documentation policy`, async () => {
    const bytes = await readFile(new URL(`../../../docs/assets/${name}`, import.meta.url));
    expect(bytes.byteLength).toBeGreaterThan(20_000);
    expect(bytes.byteLength).toBeLessThan(900_000);
  });
}
```

Add checker fixtures that prove missing images, oversized images, wrong dimensions, absent alt text, stale Pages links, and accidental release-archive inclusion all fail.

- [ ] **Step 2: Run and confirm failure**

Run `npm --prefix web run test:site -- --grep "capture|README|documentation policy"`.

Expected: FAIL because capture tooling/assets/policy do not exist.

- [ ] **Step 3: Implement child-owned dynamic capture serving**

`capture-server.mjs` binds port `0` on `127.0.0.1`, then sends `{ pid, host, port, root }` over a private Node IPC channel only after listening. It exits nonzero on bind/root errors.

`capture.mjs` must:

- spawn that exact child with IPC;
- reject timeouts, invalid PID/host/root, early exit, and bind errors before launching Chromium;
- never accept readiness from a fixed or foreign HTTP port;
- force English, 1440×1000 viewport, reduced motion, deterministic dataset state, and loaded local fonts/images;
- capture Home, Explore, and Docs with exact clip/viewport rules;
- use temporary files and atomic rename so failure never corrupts an approved PNG;
- always terminate the owned child.

Add a regression with a foreign HTTP 200 listener proving it is never accepted.

- [ ] **Step 4: Capture and visually inspect all three screenshots**

Run twice:

```bash
npm --prefix web run capture:site
shasum -a 256 docs/assets/site-home.png docs/assets/site-explore.png docs/assets/site-docs.png
```

Hashes must match between same-platform runs. Inspect original dimensions for clipped copy, missing images, synthetic labels, focus leftovers, and accidental private text.

- [ ] **Step 5: Refresh the bilingual repository presentation**

`README.md` is English-first and `README.zh-CN.md` is a full Chinese equivalent. Both include:

- language counterpart link;
- `site-home.png` with meaningful alt text;
- public site/Explore/Docs links under `https://z-lab-boop.github.io/graduate-pathfinder/`;
- v0.1–v0.3 capability table;
- safe installation and usage examples;
- synthetic/no-upload/no-probability/no-binary-release boundaries;
- secondary Explore and Docs screenshots.

- [ ] **Step 6: Implement and run repository asset policy**

`check-site-assets.mjs` validates PNG signature/dimensions/size, required README references and alt text, exact Pages URLs, no external image hotlinks, generated-art provenance, and that site documentation assets are not included in any binary release allowlist.

Run:

```bash
node scripts/check-site-assets.mjs
npm --prefix web run test:site -- --grep "capture|README|documentation policy"
npm --prefix web run test:site
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
git diff --check
```

- [ ] **Step 7: Commit**

```bash
git add .gitignore README.md README.zh-CN.md docs/assets scripts/check-site-assets.mjs web/package.json web/site/capture.mjs web/site/capture-server.mjs web/site/tests/capture.spec.ts
git commit -m "docs: publish graduate pathfinder visual identity"
```

---

### Task 6: CI, GitHub Pages, Full Verification, and Public Acceptance

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/pages.yml`
- Create: `docs/public-site-release-gates.md`
- Create: `scripts/check_skill_structure.py`
- Create: `scripts/check_workflows.py`
- Create: `tests/test_skill_structure_check.py`
- Create: `tests/test_workflow_contract.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `npm --prefix web run build:site`, `test:site`, `capture:site`, `dist/site/`, `scripts/check-site-assets.mjs`, existing Python verification.
- Produces: required CI checks, exact Pages artifact, guarded public deployment, and documented release gates.

- [ ] **Step 1: Add workflow contract tests/check script**

Implement `scripts/check_workflows.py` with Python standard-library text and indentation checks. It accepts the repository root, requires both workflow files, verifies the exact workflow/job/step keys listed below, extracts every literal `run: |` shell block, and validates each extracted block with `bash -n`. It is a focused repository contract checker, not a general YAML parser; GitHub remains the authoritative hosted YAML parser.

The checker asserts:

- ordinary CI runs Python unit tests, the repository-owned Skill structure check, compileall, site typecheck/tests, and site asset checks;
- Pages triggers only on `main` push plus guarded manual dispatch;
- permissions are `contents: read`, with `pages: write` and `id-token: write` only on the deployment workflow;
- concurrency group is `pages-${{ github.ref }}` with cancellation enabled;
- deployment depends on the build job;
- the final pre-upload step rebuilds the site after tests;
- upload path is exactly `dist/site`;
- no CNAME or custom-domain mutation exists.

`tests/test_workflow_contract.py` creates valid minimal workflow fixtures plus mutations for missing permissions, wrong branch, static concurrency group, absent main guard, wrong upload path, missing rebuild, and invalid shell. Each mutation must fail with the relevant invariant name.

Run `python3 -m unittest tests.test_workflow_contract -v` first and expect failure because the checker and workflows do not exist.

- [ ] **Step 2: Implement ordinary CI**

`ci.yml` uses Ubuntu and macOS where appropriate, installs Python/Node dependencies from committed files, then runs:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
python3 scripts/check_skill_structure.py .
npm --prefix web ci
npx --prefix web playwright install chromium
npm --prefix web run typecheck
npm --prefix web run test:site
node scripts/check-site-assets.mjs
git diff --check
```

Implement `scripts/check_skill_structure.py` with only Python standard-library dependencies. It must parse the `SKILL.md` frontmatter conservatively, require nonempty `name` and `description`, require `name: graduate-pathfinder`, require the existing `references/`, `scripts/`, `tests/`, and `agents/openai.yaml` paths, reject broken symlinks and symlinks escaping the repository, and exit nonzero with a specific message for each failed invariant. `tests/test_skill_structure_check.py` exercises the valid repository plus missing frontmatter, wrong name, missing path, broken symlink, and escaping symlink fixtures. Hosted CI runs this repository-owned check; local release verification additionally runs the installed `quick_validate.py`.

- [ ] **Step 3: Implement guarded Pages deployment**

`pages.yml`:

- triggers on push to `main` and `workflow_dispatch`;
- applies `if: github.ref == 'refs/heads/main'` to the build job;
- uses ref-scoped concurrency;
- installs from lockfiles;
- runs existing Python gates, site typecheck/tests, asset checker, and final clean site build;
- runs `actions/configure-pages`, uploads exactly `dist/site`, and deploys through `actions/deploy-pages`;
- never enables Pages implicitly and never writes a CNAME.

- [ ] **Step 4: Document local, hosted, and public gates**

`docs/public-site-release-gates.md` distinguishes:

- local automated pass;
- hosted Actions pass;
- generated-image human review;
- live Pages acceptance;
- current release/download status.

No local pass may be described as hosted or live.

- [ ] **Step 5: Run fresh full local verification**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
python3 scripts/check_skill_structure.py .
npm --prefix web ci
npx --prefix web playwright install chromium
npm --prefix web run typecheck
npm --prefix web run test:site
npm --prefix web run build:site
node scripts/check-site-assets.mjs
python3 scripts/check_workflows.py
git diff --check
```

Run the installed local validator:

```bash
python3 /Users/zzz/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Inspect `dist/site/` and assert it contains only intended static pages, scripts, styles, JSON, and images with no test fixtures, source maps, local paths, credentials, or CNAME.

- [ ] **Step 6: Inspect existing Pages state before any mutation**

Run read-only:

```bash
gh auth status
gh api repos/Z-lab-boop/graduate-pathfinder/pages
```

If a Pages site exists with a non-workflow source or custom domain, stop and request direction. If the endpoint returns 404, record that Pages is absent. Do not enable Pages until the reviewed branch is integrated into `main`.

- [ ] **Step 7: Commit local deployment configuration**

```bash
git add .github/workflows/ci.yml .github/workflows/pages.yml docs/public-site-release-gates.md scripts/check_skill_structure.py scripts/check_workflows.py tests/test_skill_structure_check.py tests/test_workflow_contract.py .gitignore
git commit -m "ci: publish graduate pathfinder site with pages"
```

- [ ] **Step 8: Final review, integration, and live acceptance**

After per-task review and one whole-branch review:

1. integrate through the user-selected branch completion path;
2. verify hosted CI passes;
3. if Pages was absent, enable workflow build only after confirming repository ownership and no custom domain;
4. wait for the Pages workflow;
5. verify `https://z-lab-boop.github.io/graduate-pathfinder/`, `/explore.html`, and `/docs.html` return the intended site;
6. verify CSS, JavaScript, JSON, and all local images load under the project subpath;
7. record live acceptance without claiming a binary release.
