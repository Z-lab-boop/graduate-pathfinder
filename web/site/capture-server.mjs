import { createServer } from "node:http";
import { readFile, realpath, stat } from "node:fs/promises";
import { extname, isAbsolute, relative, resolve } from "node:path";

// Readiness exists only on the private parent/child channel, never stdout/HTTP.
let server;
try {
  if (!process.send || !process.argv[2]) throw new Error("Capture server requires private IPC and a root");
  const root = await realpath(process.argv[2]);
  if (!(await stat(root)).isDirectory() || !(await stat(resolve(root, "index.html"))).isFile()) throw new Error("Invalid capture root");
  const contained = path => { const part = relative(root, path); return part !== ".." && !part.startsWith("../") && !isAbsolute(part); };
  const mime = { ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json", ".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml" };
  server = createServer(async (request, response) => {
    response.setHeader("Cache-Control", "no-store");
    response.setHeader("X-Content-Type-Options", "nosniff");
    if (!["GET", "HEAD"].includes(request.method)) { response.writeHead(405).end(); return; }
    try {
      let path = decodeURIComponent((request.url ?? "/").split("?")[0]);
      if (!path.startsWith("/") || /[\\\0%]/.test(path) || path.split("/").includes("..")) { response.writeHead(400).end(); return; }
      if (path === "/graduate-pathfinder") path = "/";
      else if (path.startsWith("/graduate-pathfinder/")) path = path.slice("/graduate-pathfinder".length);
      const file = await realpath(resolve(root, `.${path}`, path.endsWith("/") ? "index.html" : ""));
      if (!contained(file)) { response.writeHead(403).end(); return; }
      if (!(await stat(file)).isFile()) { response.writeHead(404).end(); return; }
      const bytes = await readFile(file);
      response.writeHead(200, { "Content-Type": mime[extname(file)] ?? "application/octet-stream", "Content-Length": bytes.length });
      response.end(request.method === "HEAD" ? undefined : bytes);
    } catch (error) { response.writeHead(["ENOENT", "ENOTDIR"].includes(error.code) ? 404 : 500).end(); }
  });
  server.once("error", error => { console.error(error.message); process.exit(1); });
  server.listen(0, "127.0.0.1", () => process.send({ pid: process.pid, host: "127.0.0.1", port: server.address().port, root }));
  const stop = () => {
    server.close(() => { if (process.connected) process.disconnect(); });
    server.closeAllConnections();
  };
  process.on("disconnect", stop);
  process.on("SIGTERM", stop);
} catch (error) { console.error(error.message); process.exit(1); }
