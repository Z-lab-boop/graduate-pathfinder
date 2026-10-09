import { expect, test } from "@playwright/test";
import { contentCopy } from "../src/content.js";

// The browser-only compiler intentionally carries no Node ambient types.
declare function require(name: "node:fs"): { readFileSync(path: string, encoding: "utf8"): string };
const { readFileSync } = require("node:fs");

test("translation dictionaries have exact nonempty bilingual keys", () => {
  expect(Object.keys(contentCopy.en).sort()).toEqual(Object.keys(contentCopy["zh-CN"]).sort());
  for (const dictionary of Object.values(contentCopy)) expect(Object.values(dictionary).every(value => value.trim().length > 0)).toBe(true);
  expect(contentCopy.en["home.workflow.heading"]).toBe("From a profile to a considered outlook.");
});

test("translation covers every closed-corpus dynamic phrase and renderer label", () => {
  const demo = JSON.parse(readFileSync("site/data/demo.json", "utf8"));
  const fields: Record<string, string[]> = {
    materials: ["label", "extraction"], targets: ["institution", "unit", "program", "degree", "round"],
    requirements: ["label"], events: ["label"], scopes: ["institution", "unit", "program_code", "degree_type", "research_track", "admission_round"],
    metrics: ["label"], evidence: ["claim", "source"], outlooks: ["eligibility", "material_readiness", "competitive_tier", "fit", "confidence", "reasons"], fixes: ["guidance"]
  };
  const phrases: string[] = [];
  for (const [collection, keys] of Object.entries(fields)) {
    for (const record of demo[collection]) for (const key of keys) phrases.push(...[record[key]].flat());
  }
  const renderer = readFileSync("site/src/explore.ts", "utf8");
  phrases.push(...[...renderer.matchAll(/tr\("([^"]+)"\)/g)].map(match => match[1]));
  for (const phrase of phrases) {
    expect(Object.hasOwn(contentCopy.en, phrase), phrase).toBe(true);
    expect(Object.hasOwn(contentCopy["zh-CN"], phrase), phrase).toBe(true);
  }
});

test("Docs states the truthful release boundary and complete installation", async ({ page }) => {
  await page.goto("/graduate-pathfinder/docs.html");
  await expect(page.getByRole("heading", { name: "Install the complete Skill", exact: true })).toBeVisible();
  await expect(page.getByText("No tagged binary release is published.", { exact: true })).toBeVisible();
  await expect(page.getByText(/download binary/i)).toHaveCount(0);
  const readme = readFileSync("../README.md", "utf8");
  expect(await page.locator("#install-command").textContent()).toBe(readme.match(/```bash\n([\s\S]*?)\n```/)![1]);
  const examples = [...readme.matchAll(/```text\n([\s\S]*?)\n```/g)].map(match => match[1]);
  for (const [index, example] of examples.entries()) await expect(page.locator(`#usage-${index + 1}`)).toHaveText(example);
  for (const file of ["material-audit.md", "applicant-claims.json", "historical-cycle.json", "admission-outlook.md", "privacy-review.md"]) await expect(page.locator("#outputs")).toContainText(file);
});

for (const width of [360, 768, 1440]) {
  test(`translation ${width}px covers every static key, attribute, metadata and link`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/graduate-pathfinder/", "/graduate-pathfinder/explore.html", "/graduate-pathfinder/docs.html"]) {
      await page.goto(path);
      for (const language of ["en", "zh-CN"] as const) {
        if (language === "zh-CN") await page.getByRole("button", { name: "切换到中文" }).click();
        const records = await page.locator("[data-i18n], [data-i18n-label], [data-i18n-alt]").evaluateAll(elements => elements.flatMap(element => [
          ...["data-i18n", "data-i18n-label", "data-i18n-alt"].filter(attr => element.hasAttribute(attr)).map(attr => ({ key: element.getAttribute(attr)!, value: attr === "data-i18n" ? element.textContent : element.getAttribute(attr === "data-i18n-label" ? "aria-label" : "alt") }))
        ]));
        for (const record of records) {
          expect(Object.hasOwn(contentCopy[language], record.key), record.key).toBe(true);
          expect(record.value).toBe(contentCopy[language][record.key as keyof typeof contentCopy.en]);
        }
        const section = await page.locator("body").getAttribute("data-page");
        await expect(page).toHaveTitle(contentCopy[language][`${section}.title` as keyof typeof contentCopy.en]);
        await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", contentCopy[language][`${section}.description` as keyof typeof contentCopy.en]);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        expect(await page.locator("body").innerText()).not.toMatch(/undefined|\[object Object\]/);
        for (const href of await page.locator('a[href]').evaluateAll(links => links.map(link => link.getAttribute("href")!))) {
          expect(href.startsWith("/")).toBe(false);
          if (href.startsWith("./")) expect(new URL(href, page.url()).pathname).toMatch(/^\/graduate-pathfinder\//);
        }
      }
      await page.getByRole("button", { name: "Switch to English" }).click();
    }
  });
}

test("Docs copies exact commands and keeps translated feedback", async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, "clipboard", { value: { writeText: async (text: string) => { (window as any).copiedText = text; } } }));
  await page.goto("/docs.html");
  for (const id of ["install-command", "usage-1", "usage-2", "usage-3", "test-command"]) {
    await page.locator(`[data-copy="${id}"]`).click();
    expect(await page.evaluate(() => (window as any).copiedText)).toBe(await page.locator(`#${id}`).textContent());
  }
  await expect(page.locator("[data-copy-status]")).toHaveText("Copied to clipboard.");
  await page.getByRole("button", { name: "切换到中文" }).click();
  await expect(page.locator("[data-copy-status]")).toHaveText("已复制到剪贴板。");
});

test("Docs clipboard refusal selects the command for manual copying", async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, "clipboard", { value: { writeText: async () => { throw new Error("Unavailable"); } } }));
  await page.goto("/docs.html");
  await page.locator('[data-copy="install-command"]').click();
  await expect(page.locator("[data-copy-status]")).toHaveText("Command selected. Copy it with your keyboard.");
  expect(await page.evaluate(() => window.getSelection()?.toString())).toBe(await page.locator("#install-command").textContent());
});

test("JavaScript fallback Home preserves English story and three artwork captions", async ({ page }, testInfo) => {
  expect(testInfo.project.use.javaScriptEnabled).toBe(false);
  await page.goto("/graduate-pathfinder/");
  await expect(page.getByRole("heading", { level: 1, name: "Every application claim needs a source." })).toBeVisible();
  await expect(page.getByRole("navigation")).toContainText("Docs");
  await expect(page.locator("figcaption")).toHaveCount(3);
  for (const caption of await page.locator("figcaption").all()) await expect(caption).toContainText(/Generated/);
  await expect(page.getByText("Concept artwork", { exact: true })).toHaveCount(3);
  await expect(page.getByRole("contentinfo")).toContainText("Local-first. No uploads. No tracking.");
  await expect(page.getByText("No tagged binary release is published.", { exact: true })).toBeVisible();
});

test("JavaScript fallback Docs preserves install, examples, privacy and release boundary", async ({ page }) => {
  await page.goto("/graduate-pathfinder/docs.html");
  await expect(page.getByRole("heading", { level: 1, name: "Use the Skill locally." })).toBeVisible();
  await expect(page.getByRole("navigation")).toContainText("Explore");
  await expect(page.locator("#install-command")).toContainText('ln -s "$(pwd)" "$skill_target"');
  await expect(page.locator("#usage-3")).toBeVisible();
  await expect(page.getByRole("contentinfo")).toContainText("Local-first. No uploads. No tracking.");
  await expect(page.getByText("No tagged binary release is published.", { exact: true })).toBeVisible();
});

test("JavaScript fallback Explore explains the interaction requirement", async ({ page }) => {
  await page.goto("/graduate-pathfinder/explore.html");
  await expect(page.getByRole("navigation")).toContainText("Docs");
  await expect(page.getByText("The interactive case needs JavaScript. Read the local workflow above for the evidence and privacy boundaries.", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Read the local workflow" })).toBeVisible();
  await expect(page.getByText("Loading fictional evidence…", { exact: true })).toHaveCount(0);
});
