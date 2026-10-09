import { fork } from "node:child_process";
import { mkdir, mkdtemp, realpath, rename, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const directory = dirname(fileURLToPath(import.meta.url));
const repository = resolve(directory, "../..");
export function waitForReady(child, root, timeout = 10_000) {
  return new Promise((resolveReady, reject) => {
    const finish = (error, value) => {
      clearTimeout(timer); child.off("message", message); child.off("exit", exited); child.off("error", failed);
      if (error) reject(error); else resolveReady(value);
    };
    const failed = error => finish(error);
    const exited = () => finish(new Error("Capture child exited before readiness"));
    const message = value => {
      if (!value || value.pid !== child.pid || value.host !== "127.0.0.1" || value.root !== root || !Number.isInteger(value.port) || value.port < 1 || value.port > 65535) {
        finish(new Error("Invalid capture child IPC readiness"));
      } else finish(null, value);
    };
    const timer = setTimeout(() => finish(new Error("Capture child readiness timeout")), timeout);
    child.on("message", message); child.once("exit", exited); child.once("error", failed);
    if (child.exitCode !== null || child.signalCode !== null) exited();
  });
}

export async function startOwnedServer(root) {
  root = await realpath(root);
  const child = fork(resolve(directory, "capture-server.mjs"), [root], { stdio: ["ignore", "ignore", "pipe", "ipc"] });
  let diagnostic = "";
  child.stderr.on("data", bytes => { diagnostic = (diagnostic + bytes).slice(-2000); });
  const stop = async () => {
    if (child.exitCode !== null || child.signalCode !== null) return;
    await new Promise(resolveExit => {
      const timer = setTimeout(() => child.kill("SIGKILL"), 2000);
      child.once("exit", () => { clearTimeout(timer); resolveExit(); });
      child.kill("SIGTERM");
    });
  };
  try { return { child, ready: await waitForReady(child, root), stop }; }
  catch (error) { await stop(); throw new Error(`${error.message}${diagnostic ? `: ${diagnostic.trim()}` : ""}`); }
}

// All three use the initial page, viewport top-left, 1440×1000 CSS pixels,
// device scale 1. No full-page truncation or variable-length document clip.
export async function captureSite({ root = resolve(repository, "dist/site"), outputDirectory = resolve(repository, "docs/assets") } = {}) {
  let owned, browser, temporary;
  try {
    owned = await startOwnedServer(root); // No browser launch before validated IPC.
    await mkdir(outputDirectory, { recursive: true });
    temporary = await mkdtemp(resolve(outputDirectory, ".capture-"));
    browser = await chromium.launch();
    const context = await browser.newContext({ locale: "en-US", viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, reducedMotion: "reduce", colorScheme: "light", timezoneId: "UTC" });
    await context.addInitScript(() => localStorage.clear());
    const origin = `http://${owned.ready.host}:${owned.ready.port}`;
    const external = [];
    await context.route("**/*", route => {
      if (new URL(route.request().url()).origin !== origin) { external.push(route.request().url()); return route.abort(); }
      return route.continue();
    });
    const names = ["home", "explore", "docs"];
    for (const name of names) {
      if (owned.child.exitCode !== null || owned.child.signalCode !== null) throw new Error("Capture child exited before capture");
      const page = await context.newPage();
      const response = await page.goto(`${origin}/graduate-pathfinder/${name === "home" ? "" : `${name}.html`}`, { waitUntil: "networkidle" });
      if (!response?.ok()) throw new Error(`Capture page failed: ${name}`);
      if (name === "explore") {
        await page.locator('[role="tab"][aria-selected="true"]').waitFor();
        if (await page.locator('[role="tab"][aria-selected="true"]').textContent() !== "Materials") throw new Error("Unexpected synthetic dataset state");
        await page.locator('[data-target="target-northlake"][aria-pressed="true"]').waitFor();
      }
      await page.evaluate(async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].map(async image => {
          image.loading = "eager";
          await image.decode();
          if (!image.naturalWidth) throw new Error("Image failed to load");
        }));
        if (document.documentElement.lang !== "en") throw new Error("Capture language is not English");
        if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
        window.scrollTo(0, 0);
      });
      await page.screenshot({ path: resolve(temporary, `site-${name}.png`), clip: { x: 0, y: 0, width: 1440, height: 1000 }, animations: "disabled", caret: "hide" });
      await page.close();
    }
    if (external.length) throw new Error("External capture resource requested");
    // Only completed captures replace approved files; rename is atomic on this filesystem.
    for (const name of names) await rename(resolve(temporary, `site-${name}.png`), resolve(outputDirectory, `site-${name}.png`));
  } finally {
    try { await browser?.close(); }
    finally { try { await owned?.stop(); } finally { if (temporary) await rm(temporary, { recursive: true, force: true }); } }
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await captureSite();
  console.log("Captured Home, Explore and Docs: 1440×1000, English, synthetic data, owned dynamic server.");
}
