import { expect, test } from "@playwright/test";

const reviewCanaries = [
  ["formatted phone", "Phone: 138-1234-5678"], ["international phone", "+86 138 1234 5678"],
  ["real institution", "ETH Zurich"], ["real school domain", "ethz.ch"],
  ["Google credential", "AIza" + "A".repeat(35)], ["Slack credential", "xoxb-" + "a".repeat(24)],
  ["AWS credential", "AKIA" + "A".repeat(16)], ["npm credential", "npm_" + "A".repeat(36)],
  ["UNC path", "\\\\private-server\\applicant\\transcript"], ["Windows path", "C:\\private\\transcript"],
  ["POSIX path", "/private/applicant/transcript"], ["home path", "~applicant/private"],
  ["embedded home path", "Transcript ($HOME/private)"], ["unknown display copy", "Unreviewed fictional text"]
];

test("Explore stays synthetic and keeps five outlook dimensions separate", async ({ page }) => {
  await page.goto("/explore.html");
  await expect(page.getByText("Synthetic walkthrough", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Northlake Institute · Data Systems", exact: true }).click();
  await page.getByRole("tab", { name: "Outlook", exact: true }).click();
  const outlook = page.getByRole("region", { name: "Admission outlook", exact: true });
  for (const name of ["Eligibility", "Material readiness", "Competitive tier", "Fit", "Evidence confidence"]) await expect(outlook).toContainText(name);
  await expect(outlook).not.toContainText(/\d+% chance/i);
});

test("historical counts explain scope and refused calculations", async ({ page }) => {
  await page.goto("/explore.html");
  await page.getByRole("tab", { name: "Previous cycle" }).click();
  await expect(page.getByText("Past cohort description · not personal probability", { exact: true })).toBeVisible();
  await expect(page.getByText("Refused: stage scopes do not match", { exact: true })).toBeVisible();
  await expect(page.getByText("12 / 24 = 50%", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Confirmed attended · 24", exact: true }).click();
  await expect(page.getByRole("complementary", { name: "Evidence inspector" })).toContainText("Fictional cycle register");
  await expect(page.getByRole("heading", { name: "Final admitted among confirmed attendees", exact: true })).toBeVisible();
  await expect(page.locator(".history-metric").first()).toContainText("synthetic-data-methods");
});

test("Explore competitive tier uses v0.3 evidence states rather than portfolio groups", async ({ page }) => {
  await page.goto("/explore.html");
  await page.getByRole("button", { name: "Meridian Technical College · Intelligent Systems", exact: true }).click();
  await page.getByRole("tab", { name: "Outlook", exact: true }).click();
  const row = page.locator(".outlook-axes > div").filter({ hasText: "Competitive tier" });
  await expect(row).toContainText("evidence_insufficient");
  await expect(page.getByRole("region", { name: "Admission outlook" })).toContainText("Comparable history and current competitive evidence are missing.");
  await expect(page.getByRole("region", { name: "Admission outlook" })).not.toContainText(/\b(?:reach|core|safety)\b/);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "test-results/explore-meridian-outlook-en.png", fullPage: true });
  await page.getByRole("button", { name: "切换到中文" }).click();
  await expect(page.locator(".outlook-axes > div").filter({ hasText: "竞争序数档位" })).toContainText("证据不足");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "test-results/explore-meridian-outlook-zh-CN.png", fullPage: true });
});

test("demo schema review probes reject formatted phones, institution names, credentials and UNC paths", async ({ page }) => {
  await page.goto("/explore.html");
  const accepted = await page.evaluate(async () => {
    const path = "./assets/demo-schema.js";
    const { parseDemo } = await import(path);
    const original = await (await fetch("./data/demo.json")).json();
    const findings: string[] = [];
    for (const value of ["Phone: 138-1234-5678", "ETH Zurich", "AIza" + "A".repeat(35), "\\\\private-server\\applicant\\transcript"]) {
      const data = structuredClone(original); data.evidence[0].claim = value;
      try { parseDemo(data); findings.push(value); } catch {}
    }
    return findings;
  });
  expect(accepted).toEqual([]);
});

test("demo schema rejects v0.1 portfolio groups and unsupported historical ratio stages", async ({ page }) => {
  await page.goto("/explore.html");
  const accepted = await page.evaluate(async () => {
    const path = "./assets/demo-schema.js";
    const { parseDemo } = await import(path);
    const original = await (await fetch("./data/demo.json")).json();
    const findings: string[] = [];
    for (const value of ["reach", "core", "safety", "insufficient"]) {
      const data = structuredClone(original); data.outlooks[0].competitive_tier = value;
      try { parseDemo(data); findings.push(value); } catch {}
    }
    const data = structuredClone(original);
    const metric = data.metrics.find((item: any) => item.state === "matched");
    data.counts.find((item: any) => item.id === metric.numerator_id).stage = "admitted";
    data.counts.find((item: any) => item.id === metric.denominator_id).stage = "interviewed";
    try { parseDemo(data); findings.push("admitted / interviewed"); } catch {}
    return findings;
  });
  expect(accepted).toEqual([]);
});

test("demo schema fixed corpus rejects review canaries in every display field", async ({ page }) => {
  await page.goto("/explore.html");
  const accepted = await page.evaluate(async (canaries) => {
    const path = "./assets/demo-schema.js";
    const { parseDemo } = await import(path);
    const original = await (await fetch("./data/demo.json")).json();
    const findings: string[] = [];
    const hidden = new Set(["id", "target_id", "material_id", "evidence_id", "numerator_id", "denominator_id", "requirement_id"]);
    for (const [collection, records] of Object.entries(original)) if (Array.isArray(records)) {
      for (const [field, current] of Object.entries(records[0])) {
        if (hidden.has(field) || typeof current !== "string" && !Array.isArray(current)) continue;
        for (const [label, value] of canaries) {
          const data = structuredClone(original);
          data[collection][0][field] = Array.isArray(current) ? [value] : value;
          try { parseDemo(data); findings.push(`${collection}.${field}: ${label}`); } catch {}
        }
      }
    }
    return findings;
  }, reviewCanaries);
  expect(accepted).toEqual([]);
});

test("demo schema requires exact complete seven-field historical scopes", async ({ page }) => {
  await page.goto("/explore.html");
  const result = await page.evaluate(async () => {
    const path = "./assets/demo-schema.js";
    const { parseDemo } = await import(path);
    const original = await (await fetch("./data/demo.json")).json();
    const keys = ["admission_year", "institution", "unit", "program_code", "degree_type", "research_track", "admission_round"];
    if (!Array.isArray(original.scopes)) return { complete: false, accepted: [] };
    const accepted: string[] = [];
    const mismatches: Record<string, unknown> = { admission_year: 2026, institution: "Meridian Technical College", unit: "Intelligent Systems", program_code: "Data Methods", degree_type: "professional", research_track: "Design Computing", admission_round: "september" };
    for (const field of keys) {
      const missing = structuredClone(original); delete missing.scopes[0][field];
      try { parseDemo(missing); accepted.push(`missing ${field}`); } catch {}
      const mismatch = structuredClone(original);
      mismatch.scopes[0][field] = mismatches[field];
      try { parseDemo(mismatch); accepted.push(`mismatched ${field}`); } catch {}
    }
    const foreignTarget = structuredClone(original);
    foreignTarget.counts.forEach((count: any) => count.target_id = "target-meridian");
    try { parseDemo(foreignTarget); accepted.push("history borrowed by another target"); } catch {}
    const wrongRound = structuredClone(original);
    wrongRound.targets.find((target: any) => target.id === "target-northlake").round = "september";
    try { parseDemo(wrongRound); accepted.push("matched metric borrowed by another round"); } catch {}
    return { complete: original.scopes.every((scope: any) => keys.every(key => Object.hasOwn(scope, key))), accepted };
  });
  expect(result.complete).toBe(true);
  expect(result.accepted).toEqual([]);
});

for (const [label, value] of reviewCanaries) test(`Explore privacy rejection for ${label} clears every partial record`, async ({ page }) => {
  await page.route("**/data/demo.json", async route => {
    const response = await route.fetch(); const data = await response.json(); data.evidence[0].claim = value;
    return route.fulfill({ contentType: "application/json", body: JSON.stringify(data) });
  });
  await page.goto("/explore.html");
  await expect(page.getByRole("heading", { name: "Walkthrough unavailable", exact: true })).toBeVisible();
  await expect(page.locator("[data-record], [role=tab], [data-target]")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(value);
});

test("Explore keyboard, filters, inspector and bilingual state remain coordinated", async ({ page }) => {
  await page.goto("/explore.html");
  const first = page.getByRole("button", { name: "Northlake Institute · Data Systems", exact: true });
  await first.focus();
  await page.keyboard.press("ArrowDown");
  const second = page.getByRole("button", { name: "Meridian Technical College · Intelligent Systems", exact: true });
  await expect(second).toBeFocused();
  await expect(second).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("tab", { name: "Materials", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Targets", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.getByRole("tab", { name: "Materials", exact: true }).click();
  await page.getByRole("checkbox", { name: "Confirmed", exact: true }).uncheck();
  await page.getByRole("checkbox", { name: "Missing", exact: true }).uncheck();
  await page.getByRole("checkbox", { name: "Conflicted", exact: true }).uncheck();
  await page.getByRole("checkbox", { name: "Review required", exact: true }).uncheck();
  await expect(page.getByText("No records match these evidence filters.", { exact: true })).toBeVisible();
  await page.getByRole("checkbox", { name: "Missing", exact: true }).check();
  await expect(page.locator("[data-record]")).toHaveCount(1);
  await page.getByRole("button", { name: "Preview guidance", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("Guidance only");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Preview guidance", exact: true })).toBeFocused();
  await page.getByRole("button", { name: "切换到中文" }).click();
  await expect(page.getByRole("button", { name: "虚构·子午技术学院 · 智能系统", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("checkbox", { name: "缺失", exact: true })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "已确认", exact: true })).not.toBeChecked();
  await page.getByRole("button", { name: "预览指导", exact: true }).click();
  await page.getByRole("button", { name: "Switch to English" }).evaluate((button: HTMLButtonElement) => button.click());
  await expect(page.getByRole("dialog")).toContainText("Guidance only");
});

test("demo schema rejects privacy canaries, fields, enums and invalid references defensively", async ({ page }) => {
  await page.goto("/explore.html");
  const result = await page.evaluate(async () => {
    const path = "./assets/demo-schema.js";
    const { parseDemo } = await import(path);
    const original = await (await fetch("./data/demo.json")).json();
    const rejected: string[] = [];
    const accepted: string[] = [];
    const reject = (label: string, mutate: (data: any) => void) => {
      const data = structuredClone(original); mutate(data);
      try { parseDemo(data); accepted.push(label); } catch { rejected.push(label); }
    };
    for (const collection of ["materials", "targets", "requirements", "events", "scopes", "counts", "metrics", "evidence", "outlooks", "fixes"]) {
      reject(`${collection} foreign`, data => data[collection][0].foreign = "extra");
      reject(`${collection} duplicate`, data => data[collection].push(structuredClone(data[collection][0])));
    }
    reject("top foreign", data => data.foreign = true);
    reject("credential JSON key", data => data.evidence[0].api_key = "private");
    for (const [label, value] of [["null root", null], ["array root", []], ["empty root", {}]]) {
      try { parseDemo(value); accepted.push(label as string); } catch { rejected.push(label as string); }
    }
    for (const [collection, field] of [["materials", "kind"], ["materials", "extraction"], ["materials", "evidence"], ["targets", "degree"], ["targets", "round"], ["counts", "stage"], ["evidence", "status"], ["evidence", "tier"], ["metrics", "state"], ["outlooks", "eligibility"], ["outlooks", "material_readiness"], ["outlooks", "competitive_tier"], ["outlooks", "fit"], ["outlooks", "confidence"]]) reject(`${collection}.${field}`, data => data[collection][0][field] = "unknown");
    for (const [collection, field] of [["requirements", "target_id"], ["requirements", "material_id"], ["requirements", "evidence_id"], ["events", "target_id"], ["events", "evidence_id"], ["counts", "target_id"], ["counts", "scope_id"], ["counts", "evidence_id"], ["metrics", "numerator_id"], ["metrics", "denominator_id"], ["outlooks", "target_id"], ["fixes", "requirement_id"]]) reject(`${collection}.${field}`, data => data[collection][0][field] = "absent");
    for (const value of [-1, 1.5, "12"]) reject(`count ${value}`, data => data.counts[0].value = value);
    reject("false synthetic", data => data.synthetic = false);
    reject("matched scope mismatch", data => data.counts.find((item: any) => item.id === "count-confirmed-attended").scope_id = "northlake-data-alternate-2025");
    reject("unconfirmed ratio evidence", data => data.evidence.find((item: any) => item.id === "evidence-cycle").status = "missing");
    reject("zero denominator", data => data.counts.find((item: any) => item.id === "count-confirmed-attended").value = 0);
    reject("ratio beyond denominator", data => data.counts.find((item: any) => item.id === "count-final-admitted").value = 25);
    reject("wrong dimension enum", data => data.outlooks[0].fit = "eligible");
    reject("mutation guidance", data => data.fixes[0].guidance = "Submit this material");
    reject("invalid calendar date", data => data.events[0].date = "2025-02-31");
    const canaries = ["<img src=x>", "&lt;script&gt;", "/Users/person/file", "/home/person/file", "~/secret", "C:\\Users\\person", "https://example.org", "javascript:alert(1)", "file:///tmp/private", "data:text/plain,private", "person@example.org", "13812345678", "110101199901011234", "student_id: 2024001234", "学号：2024001234", "sk-abcdefghijklmnop", "Bearer abcdefghijklmnop", "ghp_abcdefghijklmnopqrstuvwx", "github_pat_abcdefghijklmnop", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwZXJzb24ifQ.signature", "access_token=secret", '"api_key": "secret"', '"session": "private"', "session: secret", "清华大学", "Peking University", "mit.edu", "Stanford", "Massachusetts Institute of Technology", "真实院校", "Northlake Institute (real)"];
    const display = [["materials", "label"], ["targets", "institution"], ["targets", "unit"], ["targets", "program"], ["requirements", "label"], ["events", "label"], ["events", "date"], ["scopes", "institution"], ["scopes", "unit"], ["scopes", "program_code"], ["scopes", "research_track"], ["scopes", "degree_type"], ["scopes", "admission_round"], ["counts", "scope_id"], ["evidence", "claim"], ["evidence", "source"], ["metrics", "label"], ["fixes", "guidance"]];
    for (const [collection, field] of display) for (const value of canaries) reject(`${collection}.${field}:${value}`, data => data[collection][0][field] = value);
    for (const value of canaries) reject(`reason:${value}`, data => data.outlooks[0].reasons[0] = value);
    const parsed = parseDemo(original);
    const allowed = [["materials", "kind", ["resume", "transcript", "recommendation", "certificate"]], ["materials", "extraction", ["reviewed", "partial", "unreadable"]], ["materials", "evidence", ["confirmed", "missing", "conflicted", "review_required"]], ["targets", "degree", ["academic", "professional"]], ["targets", "round", ["summer-camp", "pre-recommendation", "september"]], ["evidence", "tier", ["synthetic_primary", "synthetic_note"]], ["outlooks", "eligibility", ["eligible", "blocked", "insufficient"]], ["outlooks", "material_readiness", ["ready", "repairable", "blocked", "insufficient"]], ["outlooks", "competitive_tier", ["strong", "competitive", "borderline", "weak", "evidence_insufficient"]], ["outlooks", "fit", ["high", "medium", "low", "insufficient"]], ["outlooks", "confidence", ["high", "medium", "low", "insufficient"]]] as [string, string, string[]][];
    const validErrors: string[] = [];
    for (const [collection, field, values] of allowed) for (const value of values) {
      const candidate = structuredClone(original);
      const record = collection === "targets" ? candidate.targets.find((target: any) => target.id === "target-meridian") : candidate[collection][0];
      record[field] = value;
      try { parseDemo(candidate); } catch { validErrors.push(`${collection}.${field}:${value}`); }
    }
    const reversed = structuredClone(original);
    for (const value of Object.values(reversed)) if (Array.isArray(value)) value.reverse();
    const deterministic = JSON.stringify(parsed) === JSON.stringify(parseDemo(reversed));
    parsed.materials[0].label = "Changed locally";
    const defensive = original.materials.every((material: any) => material.label !== "Changed locally");
    return { accepted, rejected: rejected.length, deterministic, defensive, validErrors };
  });
  expect(result.accepted).toEqual([]);
  expect(result.rejected).toBeGreaterThan(300);
  expect(result.deterministic).toBe(true);
  expect(result.defensive).toBe(true);
  expect(result.validErrors).toEqual([]);
});

for (const failure of ["network", "status", "json", "schema", "privacy"]) test(`Explore ${failure} failure removes all partial records`, async ({ page }) => {
  await page.route("**/data/demo.json", async route => {
    if (failure === "network") return route.abort();
    let body = failure === "json" ? "{" : "{}";
    if (failure === "privacy") { const response = await route.fetch(); const data = await response.json(); data.materials[5].label = '"session": "session_canary"'; body = JSON.stringify(data); }
    return route.fulfill({ status: failure === "status" ? 503 : 200, contentType: "application/json", body });
  });
  await page.goto("/explore.html");
  await expect(page.getByRole("heading", { name: "Walkthrough unavailable", exact: true })).toBeVisible();
  await expect(page.locator("[data-record], [role=tab], [data-target]")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Read the expected behavior", exact: true })).toHaveAttribute("href", "https://github.com/Z-lab-boop/graduate-pathfinder/blob/main/tests/fixtures/baoyan_case/expected-behavior.md");
  await page.getByRole("button", { name: "切换到中文" }).click();
  await expect(page.getByRole("heading", { name: "演示暂不可用", exact: true })).toBeVisible();
});

test("Explore privacy permits same-origin GET only and renders no private records", async ({ page, context }) => {
  const requests: { url: string; method: string }[] = [];
  page.on("request", request => requests.push({ url: request.url(), method: request.method() }));
  await page.goto("/graduate-pathfinder/explore.html");
  for (const name of ["Materials", "Targets", "Previous cycle", "Outlook"]) {
    await page.getByRole("tab", { name, exact: true }).click();
    await expect(page.locator("body")).not.toContainText(/\/Users\/|\/home\/|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b1[3-9]\d{9}\b|\b\d{10,18}\b|sk-|access_token|session_canary/i);
  }
  expect(requests.every(request => request.method === "GET" && new URL(request.url).origin === "http://127.0.0.1:4173")).toBe(true);
  expect(requests.some(request => request.url.endsWith("/graduate-pathfinder/data/demo.json"))).toBe(true);
  expect(await context.cookies()).toEqual([]);
  await expect(page.locator("body")).not.toContainText(/\/Users\/|\/home\/|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b1[3-9]\d{9}\b|\b\d{10,18}\b|sk-|access_token|session_canary/i);
});

for (const width of [360, 768, 1440]) test(`Explore ${width}px bilingual dialog and reduced motion`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/explore.html");
  for (const language of ["en", "zh-CN"]) {
    if (language === "zh-CN") await page.getByRole("button", { name: "切换到中文" }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `test-results/explore-materials-${width}-${language}.png`, fullPage: true });
    await page.getByRole("button", { name: language === "en" ? "Preview guidance" : "预览指导", exact: true }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await page.getByRole("dialog").evaluate(dialog => dialog.scrollWidth <= dialog.clientWidth)).toBe(true);
    await page.screenshot({ path: `test-results/explore-${width}-${language}.png`, fullPage: true });
    await page.keyboard.press("Escape");
    for (const [en, zh] of [["Targets", "目标"], ["Previous cycle", "上年度"], ["Outlook", "展望"]]) {
      await page.getByRole("tab", { name: language === "en" ? en : zh, exact: true }).click();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: `test-results/explore-${en.replace(" ", "-")}-${width}-${language}.png`, fullPage: true });
    }
    await page.getByRole("tab", { name: language === "en" ? "Materials" : "材料", exact: true }).click();
  }
});

test("Explore inspected evidence is brought into view on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 700 });
  await page.goto("/explore.html");
  await page.getByRole("button", { name: "Inspect evidence", exact: true }).first().click();
  await expect(page.getByRole("complementary", { name: "Evidence inspector" })).toBeInViewport();
  await expect(page.getByRole("complementary", { name: "Evidence inspector" })).toContainText("Fictional conflict register");
});
