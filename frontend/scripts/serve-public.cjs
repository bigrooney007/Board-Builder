// Optional production server for hosts that serve the compiled frontend directly.
// The existing reverse proxy continues routing /api to FastAPI.
const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");
const build = path.resolve(__dirname, "../build");
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf", ".txt": "text/plain", ".xml": "application/xml", ".mp4": "video/mp4" };
const blog = require("./blog-seo-handler.cjs")(() => fs.readFile(path.join(build, "index.html"), "utf8"));
http.createServer((req, res) => {
  blog(req, res, async (error) => {
    try {
      if (error) throw error;
      if (!["GET", "HEAD"].includes(req.method)) { res.writeHead(405); return res.end(); }
      const pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
      if (pathname.startsWith("/api/") || pathname.includes("\0")) { res.writeHead(404); return res.end(); }
      let file = path.resolve(build, "." + pathname);
      if (file !== build && !file.startsWith(build + path.sep)) { res.writeHead(404); return res.end(); }
      try { if ((await fs.stat(file)).isDirectory()) file = path.join(file, "index.html"); }
      catch {
        if (path.extname(file)) { res.writeHead(404); return res.end(); }
        file = path.join(build, "index.html");
      }
      const data = await fs.readFile(file);
      res.setHeader("Content-Type", types[path.extname(file)] || "application/octet-stream");
      res.setHeader("Cache-Control", pathname.startsWith("/static/") ? "public, max-age=31536000, immutable" : "no-cache");
      res.end(req.method === "HEAD" ? undefined : data);
    } catch { res.writeHead(500); res.end("Unable to load this page."); }
  });
}).listen(Number(process.env.PORT || 3000), "0.0.0.0", () => process.stdout.write("Public frontend server ready.\n"));
