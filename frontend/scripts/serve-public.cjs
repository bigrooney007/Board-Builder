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
      const isV2 = pathname === "/v2" || pathname.startsWith("/v2/");
      if (isV2) {
        res.setHeader("X-Robots-Tag", "noindex, nofollow, noarchive");
        res.setHeader("Referrer-Policy", "no-referrer");
      }
      if (pathname.startsWith("/api/") || pathname.includes("\0")) { res.writeHead(404); return res.end(); }
      let file = path.resolve(build, "." + pathname);
      if (file !== build && !file.startsWith(build + path.sep)) { res.writeHead(404); return res.end(); }
      try { if ((await fs.stat(file)).isDirectory()) file = path.join(file, "index.html"); }
      catch {
        if (path.extname(file)) { res.writeHead(404); return res.end(); }
        file = path.join(build, "index.html");
      }
      let data = await fs.readFile(file);
      if (isV2 && path.extname(file) === ".html") {
        data = Buffer.from(data.toString("utf8")
          .replace(/<meta\s+name=["']robots["'][^>]*>/gi, "")
          .replace(/<link\s+rel=["']canonical["'][^>]*>/gi, "")
          .replace(/<script\s+[^>]*id=["']landing-page-schema["'][\s\S]*?<\/script>/gi, "")
          .replace("</head>", '<meta name="robots" content="noindex,nofollow,noarchive"></head>'));
      }
      res.setHeader("Content-Type", types[path.extname(file)] || "application/octet-stream");
      res.setHeader("Cache-Control", isV2 ? "private, no-store" : pathname.startsWith("/static/") ? "public, max-age=31536000, immutable" : "no-cache");
      res.end(req.method === "HEAD" ? undefined : data);
    } catch { res.writeHead(500); res.end("Unable to load this page."); }
  });
}).listen(Number(process.env.PORT || 3000), "0.0.0.0", () => process.stdout.write("Public frontend server ready.\n"));
