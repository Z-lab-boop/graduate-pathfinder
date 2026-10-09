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
  await expect(page.getByRole("navigation")).toContainText("首页");
  await expect(page).toHaveTitle("研途择校 | 每一项判断都有来源");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /本地优先/);
  await page.getByRole("link", { name: "文档", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN");
  await page.getByRole("button", { name: "Switch to English" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("browser locale never selects Chinese", async ({ browser }) => {
  const context = await browser.newContext({ locale: "zh-CN" });
  const page = await context.newPage();
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await context.close();
});

for (const value of ["zh", "fr", "<script>", "null"]) {
  test(`invalid stored language ${value} remains English`, async ({ page }) => {
    await page.addInitScript((stored) => localStorage.setItem("graduate-pathfinder-language", stored), value);
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("button", { name: "切换到中文" })).toBeVisible();
  });
}

test("unavailable storage keeps English usable and allows a local switch", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", { get() { throw new Error("Storage unavailable"); } });
  });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.getByRole("button", { name: "切换到中文" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN");
});

for (const [path, heading] of [["/", "Every application claim needs a source."], ["/docs.html", "Use the Skill locally."]] as const) {
  test(`${path} retains core English content without JavaScript`, async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
    await expect(page.getByRole("navigation")).toContainText("Explore");
    await expect(page.getByRole("contentinfo")).toContainText("Local-first. No uploads. No tracking.");
    await context.close();
  });
}

test("GitHub Pages subpath serves every page and relative asset", async ({ page, request }) => {
  for (const path of ["/graduate-pathfinder/", "/graduate-pathfinder/explore.html", "/graduate-pathfinder/docs.html"]) {
    const response = await page.goto(path);
    expect(response?.status()).toBe(200);
    await expect(page.locator("main")).toBeVisible();
    await page.getByRole("button", { name: "切换到中文" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN");
    await page.getByRole("button", { name: "Switch to English" }).click();
  }
  for (const [path, type] of [["site.css", "text/css"], ["site.js", "text/javascript"], ["i18n.js", "text/javascript"]]) {
    const response = await request.get(`/graduate-pathfinder/assets/${path}`);
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain(type);
  }
});

test("server rejects encoded traversal and mutation requests", async ({ request }) => {
  for (const path of ["/%2e%2e%2fREADME.md", "/graduate-pathfinder/%2e%2e%5cREADME.md", "/%252e%252e%252fREADME.md", "/%ZZ"]) {
    expect((await request.get(path)).status()).toBeGreaterThanOrEqual(400);
  }
  expect((await request.post("/")).status()).toBe(405);
  const head = await request.head("/");
  expect(head.status()).toBe(200);
  expect(await head.body()).toHaveLength(0);
});

for (const width of [360, 768, 1440]) {
  test(`${width}px has no horizontal overflow in either language`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    for (const path of ["/", "/explore.html", "/docs.html"]) {
      await page.goto(path);
      for (const language of ["en", "zh-CN"]) {
        if (language === "zh-CN") await page.getByRole("button", { name: "切换到中文" }).click();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      }
      await page.getByRole("button", { name: "Switch to English" }).click();
    }
  });
}

test("keyboard skip link and focus outlines work on light and dark surfaces", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  for (const selector of ["nav a", "footer a"]) {
    const link = page.locator(selector).first();
    await link.focus();
    const colors = await link.evaluate((element) => {
      const style = getComputedStyle(element);
      let surface: Element | null = element;
      let background = "rgba(0, 0, 0, 0)";
      while (surface && background === "rgba(0, 0, 0, 0)") {
        background = getComputedStyle(surface).backgroundColor;
        surface = surface.parentElement;
      }
      return { outline: style.outlineColor, background, width: parseFloat(style.outlineWidth), type: style.outlineStyle };
    });
    const luminance = (color: string) => {
      const values = color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map((channel) => {
        const value = channel / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      });
      return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
    };
    const values = [luminance(colors.outline), luminance(colors.background)].sort((a, b) => a - b);
    expect((values[1] + 0.05) / (values[0] + 0.05)).toBeGreaterThanOrEqual(3);
    expect(colors.width).toBeGreaterThanOrEqual(2);
    expect(colors.type).toBe("solid");
  }
});

test("reduced motion removes nonessential animation and transitions", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const motion = await page.getByRole("button").evaluate((element) => {
    const style = getComputedStyle(element);
    return { animation: style.animationDuration, transition: style.transitionDuration };
  });
  expect(motion).toEqual({ animation: "0s", transition: "0s" });
});

test("all runtime requests stay same-origin and read-only", async ({ page, context }) => {
  const requests: { url: string; method: string }[] = [];
  page.on("request", (request) => requests.push({ url: request.url(), method: request.method() }));
  for (const path of ["/", "/explore.html", "/docs.html"]) {
    await page.goto(path);
    await page.getByRole("button", { name: "切换到中文" }).click();
    await page.getByRole("button", { name: "Switch to English" }).click();
  }
  expect(requests.length).toBeGreaterThan(0);
  expect(requests.every((request) => new URL(request.url).origin === "http://127.0.0.1:4173" && request.method === "GET")).toBe(true);
  expect(await context.cookies()).toEqual([]);
});
