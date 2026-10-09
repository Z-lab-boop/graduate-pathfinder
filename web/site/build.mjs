import { lstat, mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const source = dirname(fileURLToPath(import.meta.url));
const repository = resolve(source, "../..");
const output = resolve(repository, "dist/site");

function outputPath(path) {
  const destination = resolve(output, path);
  const difference = relative(output, destination);
  if (difference === ".." || difference.startsWith("../") || isAbsolute(difference)) {
    throw new Error(`Output path escapes dist/site: ${path}`);
  }
  return destination;
}

async function emit(path, contents) {
  const destination = outputPath(path);
  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, contents);
}

async function copyTree(from, to) {
  const info = await lstat(from);
  if (info.isSymbolicLink()) throw new Error(`Symbolic links are not permitted in site sources: ${from}`);
  if (info.isDirectory()) {
    for (const entry of await readdir(from)) await copyTree(resolve(from, entry), `${to}/${entry}`);
  } else if (info.isFile()) {
    await emit(to, await readFile(from));
  }
}

async function typeScriptSources(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Symbolic links are not permitted in site sources: ${path}`);
    if (entry.isDirectory()) files.push(...await typeScriptSources(path));
    else if (entry.name.endsWith(".ts") && !entry.name.endsWith(".d.ts")) {
      files.push(path);
    }
  }
  return files;
}

// This exact directory is the only removal target; sibling build outputs are preserved.
if (output !== resolve(repository, "dist", "site")) throw new Error("Unexpected site output directory");
const distInfo = await lstat(resolve(repository, "dist")).catch((error) => {
  if (error.code !== "ENOENT") throw error;
});
if (distInfo?.isSymbolicLink()) throw new Error("dist must not be a symbolic link");
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
for (const page of ["index.html", "explore.html", "docs.html"]) {
  await copyTree(resolve(source, page), page);
}
await copyTree(resolve(source, "src/site.css"), "assets/site.css");
for (const directory of ["data", "assets"]) {
  try {
    await copyTree(resolve(source, directory), directory);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}
const compilation = spawnSync(process.execPath, [
  resolve(source, "../node_modules/typescript/bin/tsc"),
  "--ignoreConfig", "--target", "ES2022", "--module", "ES2022", "--moduleResolution", "bundler",
  "--strict", "--skipLibCheck", "--rootDir", resolve(source, "src"), "--outDir", outputPath("assets"),
  ...await typeScriptSources(resolve(source, "src"))
], { stdio: "inherit" });
if (compilation.error) throw compilation.error;
if (compilation.status !== 0) throw new Error(`TypeScript compilation failed: ${compilation.status}`);
console.log("Built dist/site/ with relative static assets.");
