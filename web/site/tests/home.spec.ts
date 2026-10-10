import { expect, test } from "@playwright/test";

test("Home tells the evidence-first story with truthful image roles", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Every application claim needs a source." })).toBeVisible();
  await expect(page.getByText("Concept artwork", { exact: true })).toHaveCount(3);
  await expect(page.getByText("Synthetic product walkthrough", { exact: true })).toBeVisible();
  await expect(page.getByText("No uploads · no admission guarantees", { exact: true })).toBeVisible();
  const images = page.locator("main img");
  await expect(images).toHaveCount(3);
  for (const image of await images.all()) await expect(image).toHaveAttribute("alt", /Concept artwork/);
});

test("journey navigation preserves the selected stage", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Materials", exact: true }).click();
  await page.waitForTimeout(250);
  await expect(page.getByRole("link", { name: "Materials", exact: true })).toHaveAttribute("aria-current", "step");
  await expect(page).toHaveURL(/#materials$/);
  await expect(page.locator("#materials")).toHaveAttribute("data-active", "true");
});

test("home journey follows scrolling after a link was focused", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Materials", exact: true }).click();
  await page.locator("#history").evaluate((element) => element.scrollIntoView({ block: "start" }));
  await expect(page.getByRole("link", { name: "History", exact: true })).toHaveAttribute("aria-current", "step");
  await expect(page).toHaveURL(/#history$/);
});

test("home journey follows scrolling after viewport height changes", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.setViewportSize({ width: 768, height: 320 });
  await page.locator("#history").evaluate((element) => element.scrollIntoView({ block: "start" }));
  await expect(page.getByRole("link", { name: "History", exact: true })).toHaveAttribute("aria-current", "step");
});

test("home journey keyboard and equal observer ratios retain the current stage", async ({ page }) => {
  await page.addInitScript(() => {
    (window as any).atlasObservers = [];
    window.IntersectionObserver = class {
      callback: IntersectionObserverCallback;
      constructor(callback: IntersectionObserverCallback) { this.callback = callback; (window as any).atlasObservers.push(this); }
      observe() {} unobserve() {} disconnect() {} takeRecords() { return []; }
      root = null; rootMargin = ""; scrollMargin = ""; thresholds = [];
    };
  });
  await page.goto("/");
  const materials = page.getByRole("link", { name: "Materials", exact: true });
  await materials.focus();
  await page.keyboard.press("Enter");
  await page.evaluate(() => {
    (document.activeElement as HTMLElement).blur();
    const observer = (window as any).atlasObservers[0];
    observer.callback(["profile", "materials", "targets"].map((id) => ({ target: document.getElementById(id), intersectionRatio: 0.5, isIntersecting: true })), observer);
  });
  await expect(materials).toHaveAttribute("aria-current", "step");
  await expect(page).toHaveURL(/#materials$/);
  await materials.focus();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Targets", exact: true })).toHaveAttribute("aria-current", "step");
  await expect(page.locator("#targets")).toBeInViewport();
  await page.getByRole("button", { name: "切换到中文" }).click();
  await expect(page.getByRole("link", { name: "目标", exact: true })).toHaveAttribute("aria-current", "step");
  await expect(page.getByText("概念艺术图", { exact: true })).toHaveCount(3);
  await expect(page.getByText("合成产品流程演示", { exact: true })).toBeVisible();
});

test("home journey follows fragments and browser history", async ({ page }) => {
  await page.goto("/#history");
  await expect(page.getByRole("link", { name: "History", exact: true })).toHaveAttribute("aria-current", "step");
  await page.getByRole("link", { name: "Outlook", exact: true }).click();
  await expect(page).toHaveURL(/#outlook$/);
  await page.goBack();
  await expect(page.getByRole("link", { name: "History", exact: true })).toHaveAttribute("aria-current", "step");
});

test("browser history ignores stale visibility until the fragment stage settles", async ({ page }) => {
  await page.addInitScript(() => {
    (window as any).atlasObservers = [];
    window.IntersectionObserver = class {
      callback: IntersectionObserverCallback;
      constructor(callback: IntersectionObserverCallback) { this.callback = callback; (window as any).atlasObservers.push(this); }
      observe() {} unobserve() {} disconnect() {} takeRecords() { return []; }
      root = null; rootMargin = ""; scrollMargin = ""; thresholds = [];
    };
  });
  await page.goto("/#history");
  await page.getByRole("link", { name: "Outlook", exact: true }).click();
  await page.goBack();
  await expect(page).toHaveURL(/#history$/);
  await page.evaluate(() => {
    const observer = (window as any).atlasObservers[0];
    observer.callback([{ target: document.getElementById("outlook"), intersectionRatio: 1, isIntersecting: true }], observer);
  });
  await expect(page.getByRole("link", { name: "History", exact: true })).toHaveAttribute("aria-current", "step");
  await page.evaluate(() => {
    const observer = (window as any).atlasObservers[0];
    observer.callback([{ target: document.getElementById("history"), intersectionRatio: 1, isIntersecting: true }], observer);
    observer.callback([
      { target: document.getElementById("history"), intersectionRatio: 0, isIntersecting: false },
      { target: document.getElementById("outlook"), intersectionRatio: 1, isIntersecting: true }
    ], observer);
  });
  await expect(page.getByRole("link", { name: "Outlook", exact: true })).toHaveAttribute("aria-current", "step");
});

test("Home images load at the repository subpath", async ({ page }) => {
  await page.goto("/graduate-pathfinder/");
  await expect(page.locator("main img")).toHaveCount(3);
  for (const image of await page.locator("main img").all()) {
    await image.scrollIntoViewIfNeeded();
    await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.complete && element.naturalWidth > 0)).toBe(true);
    expect(await image.getAttribute("src")).toMatch(/^\.\/assets\/generated\//);
  }
});

test("home English journey remains understandable without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/");
  for (const name of ["Profile", "Materials", "Targets", "History", "Outlook"]) {
    await expect(page.getByRole("link", { name, exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  }
  await expect(page.getByText("Synthetic product walkthrough", { exact: true })).toBeVisible();
  await context.close();
});

for (const width of [360, 768, 1440]) {
  test(`home ${width}px bilingual layout and reduced motion`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    for (const language of ["en", "zh-CN"]) {
      if (language === "zh-CN") await page.getByRole("button", { name: "切换到中文" }).click();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(await page.locator(".atlas-hero").evaluate((element) => getComputedStyle(element).animationDuration)).toBe("0s");
      await expect(page.locator(".evidence-legend")).toContainText(language === "en" ? "Review required" : "需复核");
    }
  });
}
