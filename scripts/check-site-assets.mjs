import { createHash } from "node:crypto";
import { readFile, readdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const images = ["site-home.png", "site-explore.png", "site-docs.png"];
const base = "https://z-lab-boop.github.io/graduate-pathfinder/";
const brand = {
  source: ["docs/assets/graduate-pathfinder-mark-source.png", 1254, 1254, "3609a18dffff700fd34e04960a134f5342327bfacb16cb418f85e9c22390ce62"],
  delivery: ["web/site/assets/generated/graduate-pathfinder-mark.png", 512, 512, "8d51a1811f6a5a7cf59e7720cfab396c2846402480f6158a089dd91cb165d216"]
};
const readmeCards = {
  "docs/assets/admissions-atlas-card.webp": [29_260, "ba453e971a9829d5f3e069104c845d132cd15ffc80f80cab693d2f57939e7b24"],
  "docs/assets/materials-review-card.webp": [34_414, "0274eabd8d0fcbd8a3e3763619ae4ca8e0bd9389ced13eb7e214d2f33e582f32"],
  "docs/assets/campus-route-card.webp": [41_042, "e9b264741aed2cf4fc12836e5f5a8a74d876ae08a2d2453b4d4da30293ab998c"]
};
const artwork = {
  "admissions-atlas-hero.png": [1536, 1024, "e626a33f3bc1f3ab7b48e57ace625aab27ffa3af781226a82ab863f49f2a658d"],
  "materials-review.png": [1448, 1086, "bd8c3fd171d3e72b8f330ebe872f5682bef52b78a2a8a1a9e20d779d95c1809b"],
  "campus-route.png": [1672, 941, "f8677b7dcf871792029a48305320a48e5b5546e09b1f0beb412503ddfd2fa831"]
};
const derivatives = {
  "admissions-atlas-hero.webp": "ca4a0e034a6c24d9e8f4040b7c9c046b3ef332f9a8ee8630eca794f23c9d22d7",
  "materials-review.webp": "0b0afc6e1a2393a2bbc118b8400de013f557fc9b8f4bf0ba6c880752dc33bd6c",
  "campus-route.webp": "f2cf4809d6b830383f64c741bf68bd7393778d323f09be77a4cf4c2e53a6e5cb"
};
async function files(root, directory = "") {
  const result = [];
  for (const entry of await readdir(resolve(root, directory), { withFileTypes: true })) {
    if ([".git", ".worktrees", ".superpowers", ".zerotoken", "node_modules", "dist", "test-results", "playwright-report", "__pycache__"].includes(entry.name)) continue;
    const name = directory ? `${directory}/${entry.name}` : entry.name;
    if (entry.isDirectory()) result.push(...await files(root, name));
    else if (entry.isFile()) result.push(name);
  }
  return result;
}
export async function checkSiteAssets(root) {
  const errors = [];
  const read = async file => { try { return await readFile(resolve(root, file)); } catch { errors.push(`missing ${file}`); return null; } };
  const png = (bytes, file, width, height, limited = false) => {
    if (!bytes) return;
    if (limited && (bytes.length <= 20_000 || bytes.length >= 900_000)) errors.push(`size outside documentation policy: ${file}`);
    if (bytes.length < 24 || bytes.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") { errors.push(`invalid PNG signature: ${file}`); return; }
    if (bytes.readUInt32BE(16) !== width || bytes.readUInt32BE(20) !== height) errors.push(`wrong dimensions: ${file}`);
  };
  for (const name of images) png(await read(`docs/assets/${name}`), name, 1440, 1000, true);
  for (const [name, width, height, hash] of Object.values(brand)) {
    const bytes = await read(name);
    png(bytes, name, width, height);
    if (bytes && createHash("sha256").update(bytes).digest("hex") !== hash) errors.push(`brand provenance mismatch: ${name}`);
  }
  for (const [name, [size, hash]] of Object.entries(readmeCards)) {
    const bytes = await read(name);
    if (bytes && (bytes.length !== size || bytes.toString("ascii", 0, 4) !== "RIFF" || bytes.toString("ascii", 8, 12) !== "WEBP" || createHash("sha256").update(bytes).digest("hex") !== hash)) errors.push(`README card provenance mismatch: ${name}`);
  }
  for (const name of ["README.md", "README.zh-CN.md"]) {
    const text = (await read(name))?.toString() ?? "";
    const counterpart = name === "README.md" ? "README.zh-CN.md" : "README.md";
    const hasLink = target => text.includes(`](${target})`) || text.includes(`href="${target}"`);
    if (!hasLink(counterpart)) errors.push(`missing language counterpart: ${name}`);
    for (const image of images) {
      const reference = [...text.matchAll(/!\[([^\]]*)\]\(([^)]+)\)/g)].find(match => match[2] === `docs/assets/${image}`);
      if (!reference) errors.push(`missing README image reference: ${name}/${image}`);
      else if (reference[1].trim().length < 12) errors.push(`missing meaningful alt text: ${name}/${image}`);
    }
    for (const path of [brand.delivery[0], ...Object.keys(readmeCards)]) {
      const tag = [...text.matchAll(/<img\s+[^>]*>/g)].find(match => match[0].includes(`src="${path}"`));
      if (!tag) errors.push(`missing branded README visual: ${name}/${path}`);
      else if (!/\balt="[^"]{12,}"/.test(tag[0])) errors.push(`missing meaningful branded visual alt text: ${name}/${path}`);
    }
    for (const suffix of ["", "explore.html", "docs.html", "docs.html#install", "docs.html#source"]) {
      if (!hasLink(base + suffix)) errors.push(`missing exact Pages link: ${name}/${suffix}`);
    }
    const urls = text.match(/https?:\/\/[^\s)<>"']+/g) ?? [];
    for (const url of urls) if (url.includes("github.io") && !["", "explore.html", "docs.html", "docs.html#install", "docs.html#source"].some(suffix => url === base + suffix)) errors.push(`stale Pages URL: ${name}`);
    if (/!\[[^\]]*\]\(\s*(?:https?:)?\/\//i.test(text) || /<img[^>]+src\s*=\s*["'](?:https?:)?\/\//i.test(text)) errors.push(`external image hotlink: ${name}`);
  }
  const provenance = (await read("web/site/assets/generated/README.md"))?.toString() ?? "";
  if (!provenance.includes("Concept artwork") || !provenance.includes("image_gen.imagegen")) errors.push("missing generated-art provenance semantics");
  for (const [, , , hash] of Object.values(brand)) if (!provenance.includes(hash)) errors.push(`missing brand provenance hash: ${hash}`);
  for (const [, hash] of Object.values(readmeCards)) if (!provenance.includes(hash)) errors.push(`missing README card provenance hash: ${hash}`);
  for (const [name, [width, height, hash]] of Object.entries(artwork)) {
    const bytes = await read(`web/site/assets/generated/${name}`);
    png(bytes, name, width, height);
    if (bytes && (createHash("sha256").update(bytes).digest("hex") !== hash || !provenance.includes(hash))) errors.push(`generated-art provenance mismatch: ${name}`);
  }
  for (const [name, hash] of Object.entries(derivatives)) {
    const bytes = await read(`web/site/assets/generated/${name}`);
    if (bytes && (bytes.toString("ascii", 0, 4) !== "RIFF" || bytes.toString("ascii", 8, 12) !== "WEBP" || createHash("sha256").update(bytes).digest("hex") !== hash || !provenance.includes(hash))) errors.push(`lossless derivative provenance mismatch: ${name}`);
  }
  for (const file of await files(root)) {
    if (/\.(html|css)$/.test(file) && file.startsWith("web/site/")) {
      const text = (await read(file))?.toString() ?? "";
      if (/(?:src|srcset)\s*=\s*["']\s*(?:https?:)?\/\//i.test(text) || /url\(\s*["']?(?:https?:)?\/\//i.test(text)) errors.push(`external image/runtime hotlink: ${file}`);
    }
    if (!/\.(json|ya?ml|toml|txt|sh|mjs|py)$/.test(file) || file === "scripts/check-site-assets.mjs" || file.includes("/tests/") || file.startsWith("tests/")) continue;
    const text = (await read(file))?.toString() ?? "";
    const releaseConfig = /(?:release|archive|allowlist)/i.test(file) || /(?:releaseAssets|release_files|binary_allowlist|softprops\/action-gh-release)/i.test(text) || (file.endsWith("package.json") && /"files"\s*:/.test(text));
    if (!releaseConfig) continue;
    // Examine path/glob strings in release configs, including broad docs/** or **/*.
    const tokens = text.match(/[\w.*?\/-]+/g) ?? [];
    for (const token of tokens) {
      const normalized = token.replace(/^\.\//, "").replace(/\/$/, "/**");
      if (!["docs", "docs/assets", "web/site/assets"].includes(normalized) && !normalized.includes("/") && !normalized.includes("*")) continue;
      const expression = new RegExp(`^${normalized.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*\*/g, "\u0000").replace(/\*/g, "[^/]*").replace(/\?/g, ".").replace(/\u0000/g, ".*")}(?:/.*)?$`);
      const documentationAssets = [
        ...images.map(name => `docs/assets/${name}`), brand.source[0], brand.delivery[0],
        ...Object.keys(readmeCards),
        ...Object.keys(artwork).map(name => `web/site/assets/generated/${name}`),
        ...Object.keys(derivatives).map(name => `web/site/assets/generated/${name}`)
      ];
      if (documentationAssets.some(asset => expression.test(asset))) { errors.push(`documentation assets included in binary release allowlist: ${file}`); break; }
    }
  }
  return errors;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const errors = await checkSiteAssets(resolve(dirname(fileURLToPath(import.meta.url)), ".."));
  if (errors.length) { console.error(errors.join("\n")); process.exitCode = 1; }
  else console.log("Site asset policy passed: screenshots, bilingual READMEs, Pages links, artwork provenance and release exclusion.");
}
