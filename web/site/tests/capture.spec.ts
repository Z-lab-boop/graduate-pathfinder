import { expect, test } from "@playwright/test";

// Node utilities stay outside the browser-only source compiler.
declare const require: (name: string) => any;
const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");
const http = require("node:http");
const { fork } = require("node:child_process");
const load = (file: string) => import(path.resolve(file));
const images = ["site-home.png", "site-explore.png", "site-docs.png"];

test("capture lossless artwork delivery preserves approved pixels and local fallback", async ({ page }) => {
  await page.goto("/graduate-pathfinder/");
  for (const name of ["admissions-atlas-hero", "materials-review", "campus-route"]) {
    const bytes = await fs.readFile(`site/assets/generated/${name}.webp`);
    expect(bytes.length).toBeLessThan((await fs.stat(`site/assets/generated/${name}.png`)).size);
    const pixels = await page.evaluate(async name => {
      const digest = async (extension: string) => {
        const image = new Image(); image.src = `./assets/generated/${name}.${extension}`; await image.decode();
        const canvas = document.createElement("canvas"); canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
        const context = canvas.getContext("2d")!; context.drawImage(image, 0, 0);
        const hash = await crypto.subtle.digest("SHA-256", context.getImageData(0, 0, canvas.width, canvas.height).data);
        return { width: canvas.width, height: canvas.height, hash: [...new Uint8Array(hash)].join(",") };
      };
      return [await digest("png"), await digest("webp")];
    }, name);
    expect(pixels[0]).toEqual(pixels[1]);
    const image = page.locator(`img[src$="${name}.png"]`);
    await expect(image).toHaveCount(1);
    expect(await image.evaluate((element: HTMLImageElement) => element.currentSrc)).toMatch(/\.webp$/);
  }
});

for (const name of images) {
  test(`capture ${name} satisfies the public documentation policy`, async () => {
    const bytes = await fs.readFile(`../docs/assets/${name}`);
    expect(bytes.length).toBeGreaterThan(20_000);
    expect(bytes.length).toBeLessThan(900_000);
    expect(bytes.readUInt32BE(16)).toBe(1440);
    expect(bytes.readUInt32BE(20)).toBe(1000);
  });
}

test("README documentation policy validates the repository", async () => {
  const { checkSiteAssets } = await load("../scripts/check-site-assets.mjs");
  expect(await checkSiteAssets(path.resolve(".."))).toEqual([]);
});

test("repository landing README is Chinese-first with a complete English counterpart", async () => {
  const chinese = await fs.readFile(path.resolve("../README.md"), "utf8");
  expect(chinese).toContain('<h1 align="center">研途择校 · Graduate Pathfinder</h1>');
  expect(chinese).toContain("循证据，辨路径，让不确定性保持可见。");
  expect(chinese).toContain('href="README.en.md">English</a>');
  const english = await fs.readFile(path.resolve("../README.en.md"), "utf8");
  expect(english).toContain('<h1 align="center">Graduate Pathfinder · 研途择校</h1>');
  expect(english).toContain("Trace evidence. Compare paths. Keep uncertainty visible.");
  expect(english).toContain('href="README.md">中文</a>');
});

test("README and every site shell expose the project-owned visual identity", async ({ page }) => {
  const mark = "web/site/assets/generated/graduate-pathfinder-mark.png";
  const cards = ["admissions-atlas-card.webp", "materials-review-card.webp", "campus-route-card.webp"];
  for (const readme of ["README.md", "README.en.md", "README.zh-CN.md"]) {
    const text = await fs.readFile(path.resolve("..", readme), "utf8");
    expect(text).toContain(`<img src="${mark}"`);
    for (const card of cards) expect(text).toContain(`docs/assets/${card}`);
  }
  for (const route of ["/graduate-pathfinder/", "/graduate-pathfinder/explore.html", "/graduate-pathfinder/docs.html"]) {
    await page.goto(route);
    const favicon = page.locator('link[rel="icon"]');
    await expect(favicon).toHaveAttribute("href", "./assets/generated/graduate-pathfinder-mark.png");
    expect(await page.evaluate(async () => (await fetch((document.querySelector('link[rel="icon"]') as HTMLLinkElement).href)).status)).toBe(200);
    const logo = page.locator("a.brand img.brand-mark");
    await expect(logo).toBeVisible();
    await expect(logo).toHaveAttribute("src", "./assets/generated/graduate-pathfinder-mark.png");
    expect(await logo.evaluate((image: HTMLImageElement) => [image.complete, image.naturalWidth, image.naturalHeight])).toEqual([true, 512, 512]);
    expect(await logo.evaluate((image: HTMLImageElement) => {
      const canvas = document.createElement("canvas"); canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
      const context = canvas.getContext("2d")!; context.drawImage(image, 0, 0);
      const alpha = context.getImageData(0, 0, canvas.width, canvas.height).data.filter((_value, index) => index % 4 === 3);
      return { transparent: alpha.some(value => value < 255), visible: alpha.some(value => value > 0) };
    })).toEqual({ transparent: true, visible: true });
  }
});

test("README documentation policy rejects broken asset, link, provenance and release fixtures", async () => {
  const { checkSiteAssets } = await load("../scripts/check-site-assets.mjs");
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "gp-assets-"));
  try {
    await fs.mkdir(path.join(root, "docs/assets"), { recursive: true });
    await fs.mkdir(path.join(root, "web/site/assets/generated"), { recursive: true });
    const png = require("node:buffer").Buffer.alloc(30_000);
    require("node:buffer").Buffer.from("89504e470d0a1a0a", "hex").copy(png);
    png.writeUInt32BE(1440, 16); png.writeUInt32BE(1000, 20);
    for (const name of images) await fs.writeFile(path.join(root, "docs/assets", name), png);
    const baseline = "[English](README.en.md) [中文](README.md) [中文兼容](README.zh-CN.md)\n" +
      '<img src="web/site/assets/generated/graduate-pathfinder-mark.png" alt="Graduate Pathfinder project-owned compass and evidence-card mark">\n' +
      ["admissions-atlas-card", "materials-review-card", "campus-route-card"].map(name => `<img src="docs/assets/${name}.webp" alt="Original conceptual admissions artwork ${name}">`).join("\n") + "\n" +
      images.map(name => `![Synthetic product walkthrough ${name}](docs/assets/${name})`).join("\n") +
      "\n[Home](https://z-lab-boop.github.io/graduate-pathfinder/) [Explore](https://z-lab-boop.github.io/graduate-pathfinder/explore.html) [Docs](https://z-lab-boop.github.io/graduate-pathfinder/docs.html) [Install](https://z-lab-boop.github.io/graduate-pathfinder/docs.html#install) [Release](https://z-lab-boop.github.io/graduate-pathfinder/docs.html#source)";
    // The policy also checks actual artwork hashes; copy the approved provenance corpus.
    await fs.cp(path.resolve("site/assets/generated"), path.join(root, "web/site/assets/generated"), { recursive: true });
    await fs.copyFile(path.resolve("../docs/assets/graduate-pathfinder-mark-source.png"), path.join(root, "docs/assets/graduate-pathfinder-mark-source.png"));
    for (const card of ["admissions-atlas-card.webp", "materials-review-card.webp", "campus-route-card.webp"]) {
      await fs.copyFile(path.resolve("../docs/assets", card), path.join(root, "docs/assets", card));
    }
    for (const name of ["README.md", "README.en.md", "README.zh-CN.md"]) await fs.writeFile(path.join(root, name), baseline);
    expect(await checkSiteAssets(root)).toEqual([]);
    const home = path.join(root, "docs/assets/site-home.png");
    await fs.unlink(home);
    expect((await checkSiteAssets(root)).join("\n")).toContain("missing");
    await fs.writeFile(home, require("node:buffer").Buffer.alloc(900_000));
    expect((await checkSiteAssets(root)).join("\n")).toContain("size");
    await fs.writeFile(home, png);
    const wrong = require("node:buffer").Buffer.from(png); wrong.writeUInt32BE(100, 16);
    await fs.writeFile(home, wrong);
    expect((await checkSiteAssets(root)).join("\n")).toContain("dimensions");
    await fs.writeFile(home, png);
    for (const [mutation, expected] of [
      [baseline.replace("Synthetic product walkthrough site-home.png", ""), "alt text"],
      [baseline.replaceAll("z-lab-boop.github.io/graduate-pathfinder/", "z-lab-boop.github.io/old/"), "Pages"],
      [baseline + "\n![Remote image](https://example.invalid/image.png)", "hotlink"]
    ]) {
      await fs.writeFile(path.join(root, "README.md"), mutation);
      expect((await checkSiteAssets(root)).join("\n")).toContain(expected);
    }
    await fs.writeFile(path.join(root, "README.md"), baseline);
    const mark = path.join(root, "web/site/assets/generated/graduate-pathfinder-mark.png");
    const approvedMark = await fs.readFile(mark);
    await fs.unlink(mark);
    expect((await checkSiteAssets(root)).join("\n")).toContain("missing");
    await fs.writeFile(mark, require("node:buffer").Buffer.concat([approvedMark, require("node:buffer").Buffer.from("changed")]));
    expect((await checkSiteAssets(root)).join("\n")).toContain("brand provenance");
    await fs.writeFile(mark, approvedMark);
    await fs.writeFile(path.join(root, "README.md"), baseline.replace("Graduate Pathfinder project-owned compass and evidence-card mark", ""));
    expect((await checkSiteAssets(root)).join("\n")).toContain("branded visual alt text");
    await fs.writeFile(path.join(root, "README.md"), baseline);
    await fs.writeFile(path.join(root, "release-allowlist.json"), JSON.stringify(["docs/assets/**"]));
    expect((await checkSiteAssets(root)).join("\n")).toContain("release");
    await fs.unlink(path.join(root, "release-allowlist.json"));
    await fs.appendFile(path.join(root, "web/site/assets/generated/admissions-atlas-hero.png"), "changed");
    expect((await checkSiteAssets(root)).join("\n")).toContain("provenance");
  } finally { await fs.rm(root, { recursive: true, force: true }); }
});

test("capture uses only its owned dynamic child despite a foreign HTTP 200 listener", async () => {
  const { startOwnedServer } = await load("site/capture.mjs");
  let foreignRequests = 0;
  const foreign = http.createServer((_request: any, response: any) => { foreignRequests++; response.end("foreign"); });
  await new Promise<void>(resolve => foreign.listen(0, "127.0.0.1", resolve));
  let owned: any;
  try {
    owned = await startOwnedServer(path.resolve("../dist/site"));
    expect(owned.ready.port).not.toBe(foreign.address().port);
    expect(owned.ready.pid).toBe(owned.child.pid);
    expect(await (await fetch(`http://127.0.0.1:${owned.ready.port}/`)).text()).toContain("Every application claim needs a source.");
    await expect(startOwnedServer(path.resolve("../dist/absent-capture-root"))).rejects.toThrow();
    const empty = await fs.mkdtemp(path.join(os.tmpdir(), "gp-empty-root-"));
    try { await expect(startOwnedServer(empty)).rejects.toThrow(/Capture child exited/); }
    finally { await fs.rm(empty, { recursive: true, force: true }); }
    expect(foreignRequests).toBe(0);
  } finally {
    await owned?.stop();
    await new Promise<void>(resolve => foreign.close(resolve));
  }
  expect(owned.child.exitCode).toBe(0);
});

test("capture rejects invalid IPC readiness, early exit and timeout before browsing", async () => {
  const { waitForReady } = await load("site/capture.mjs");
  const root = path.resolve("../dist/site");
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), "gp-ipc-"));
  try {
    for (const expression of [
      "process.exit(1)", "setInterval(() => {}, 1000)",
      `process.send({ pid: process.pid + 1, host: '127.0.0.1', port: 1234, root: ${JSON.stringify(root)} })`,
      `process.send({ pid: process.pid, host: 'localhost', port: 1234, root: ${JSON.stringify(root)} })`,
      "process.send({ pid: process.pid, host: '127.0.0.1', port: 1234, root: '/wrong' })",
      `process.send({ pid: process.pid, host: '127.0.0.1', port: 0, root: ${JSON.stringify(root)} })`
    ]) {
      const file = path.join(temp, "child.mjs");
      await fs.writeFile(file, expression);
      const child = fork(file, [], { stdio: ["ignore", "ignore", "ignore", "ipc"] });
      try { await expect(waitForReady(child, root, 300)).rejects.toThrow(); }
      finally { child.kill(); }
    }
  } finally { await fs.rm(temp, { recursive: true, force: true }); }
});

test("capture failed page leaves approved images intact and terminates the child", async () => {
  const { captureSite } = await load("site/capture.mjs");
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), "gp-capture-"));
  try {
    await fs.cp(path.resolve("../dist/site"), path.join(temp, "site"), { recursive: true });
    await fs.unlink(path.join(temp, "site/explore.html"));
    await fs.mkdir(path.join(temp, "output"));
    for (const name of images) await fs.writeFile(path.join(temp, "output", name), "approved-image");
    await expect(captureSite({ root: path.join(temp, "site"), outputDirectory: path.join(temp, "output") })).rejects.toThrow();
    for (const name of images) expect(await fs.readFile(path.join(temp, "output", name), "utf8")).toBe("approved-image");
    expect((await fs.readdir(path.join(temp, "output"))).sort()).toEqual([...images].sort());
  } finally { await fs.rm(temp, { recursive: true, force: true }); }
});
