import { expect, test } from "@playwright/test";
import { spawnSync } from "node:child_process";
import { cp, mkdtemp, mkdir, readdir, rm, stat, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repository = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

test("build rejects an escaping TypeScript import without emitting outside dist/site", async () => {
  const fixture = await mkdtemp(join(tmpdir(), "graduate-pathfinder-containment-"));
  try {
    const site = join(fixture, "web/site");
    await mkdir(join(site, "src"), { recursive: true });
    await cp(join(repository, "web/site/build.mjs"), join(site, "build.mjs"));
    await symlink(join(repository, "web/node_modules"), join(fixture, "web/node_modules"), "dir");
    for (const entry of ["index.html", "explore.html", "docs.html"]) {
      await writeFile(join(site, entry), "<!doctype html><html lang=\"en\"><title>Fixture</title></html>");
    }
    await writeFile(join(site, "src/site.css"), "body { color: black; }");
    await writeFile(join(site, "src/site.ts"), 'import { escaped } from "../../outside.js";\nconsole.log(escaped);\n');
    await writeFile(join(fixture, "web/outside.ts"), 'export const escaped = "outside rootDir";\n');
    const before = new Set(await readdir(fixture, { recursive: true }));

    const result = spawnSync(process.execPath, [join(site, "build.mjs")], { cwd: fixture, encoding: "utf8" });
    expect(result.error).toBeUndefined();
    expect(result.status).not.toBe(0);
    expect(result.stdout + result.stderr).toContain("TS6059");
    const emittedOutside = (await readdir(fixture, { recursive: true })).filter((path) =>
      !before.has(path) && path !== "dist" && path !== join("dist", "site") &&
      !path.startsWith(join("dist", "site") + "/")
    );
    expect(emittedOutside).toEqual([]);
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
});

test("build emits only public static artifact types", async () => {
  const sharedOutput = join(repository, "dist/site");
  const sharedBefore = await stat(sharedOutput);
  const fixture = await mkdtemp(join(tmpdir(), "graduate-pathfinder-artifact-"));
  try {
    // Keep real sources/build behavior while each worker owns its output directory.
    await cp(join(repository, "web/site"), join(fixture, "web/site"), { recursive: true });
    await symlink(join(repository, "web/node_modules"), join(fixture, "web/node_modules"), "dir");
    const result = spawnSync(process.execPath, [join(fixture, "web/site/build.mjs")], {
      cwd: fixture,
      encoding: "utf8"
    });
    expect(result.error).toBeUndefined();
    expect(result.status, result.stdout + result.stderr).toBe(0);
    const entries = await readdir(join(fixture, "dist/site"), { recursive: true, withFileTypes: true });
    const files = entries.filter(entry => entry.isFile()).map(entry => join(entry.parentPath, entry.name));
    expect(files.length).toBeGreaterThan(0);
    expect(entries.some(entry => entry.isSymbolicLink())).toBe(false);
    expect(files.some(file => file.endsWith("assets/generated/README.md"))).toBe(false);
    expect(files.filter(file => !/\.(?:html|css|js|json|png|webp|svg)$/.test(file))).toEqual([]);
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
  const sharedAfter = await stat(sharedOutput);
  expect([sharedAfter.ino, sharedAfter.birthtimeMs, sharedAfter.mtimeMs]).toEqual(
    [sharedBefore.ino, sharedBefore.birthtimeMs, sharedBefore.mtimeMs]
  );
});
