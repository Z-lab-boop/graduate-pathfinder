import { createServer } from "node:http";
import { readFile, realpath, stat } from "node:fs/promises";
import { dirname, extname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = await realpath(resolve(dirname(fileURLToPath(import.meta.url)), "../../dist/site"));
const port = Number(process.argv[2] ?? 4173);
if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error("Port must be an integer from 0 through 65535");
const mimeTypes = {
  ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml"
};

function contained(path) {
  const difference = relative(root, path);
  return difference !== ".." && !difference.startsWith("../") && !isAbsolute(difference);
}

const server = createServer(async (request, response) => {
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("Cache-Control", "no-store");
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { Allow: "GET, HEAD" }).end();
    return;
  }
  let path;
  try {
    path = decodeURIComponent((request.url ?? "/").split("?")[0]);
    if (!path.startsWith("/") || /[\\\0%]/.test(path) || path.split("/").includes("..")) throw new Error("Unsafe path");
  } catch {
    response.writeHead(400).end();
    return;
  }
  if (path === "/graduate-pathfinder") path = "/";
  else if (path.startsWith("/graduate-pathfinder/")) path = path.slice("/graduate-pathfinder".length);
  const destination = resolve(root, `.${path}`, path.endsWith("/") ? "index.html" : "");
  if (!contained(destination)) {
    response.writeHead(403).end();
    return;
  }
  try {
    const canonical = await realpath(destination);
    if (!contained(canonical)) {
      response.writeHead(403).end();
      return;
    }
    const info = await stat(canonical);
    if (!info.isFile()) {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, { "Content-Type": mimeTypes[extname(canonical)] ?? "application/octet-stream", "Content-Length": info.size });
    response.end(request.method === "HEAD" ? undefined : await readFile(canonical));
  } catch (error) {
    response.writeHead(error.code === "ENOENT" || error.code === "ENOTDIR" ? 404 : 500).end();
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(JSON.stringify({ pid: process.pid, host: "127.0.0.1", port: server.address().port }));
});
