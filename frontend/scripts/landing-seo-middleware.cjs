const path = require("node:path");
const { pageForPath, renderLandingHtml, robotsTxt, sitemapXml } = require("../src/seo/landingMetadata");

// Emergent previews and deployments using the development server receive the same
// initial metadata as the production HTML files. Every user agent sees identical HTML.
module.exports = function landingSeoMiddleware(server) {
  const readTemplate = () => new Promise((resolve, reject) => {
    server.middleware.waitUntilValid(() => {
      server.compiler.outputFileSystem.readFile(path.join(server.compiler.outputPath, "index.html"), (error, html) => error ? reject(error) : resolve(html.toString()));
    });
  });
  const blogHandler = require("./blog-seo-handler.cjs")(readTemplate);
  return { name: "landing-page-seo", middleware(req, res, next) {
    if (!["GET", "HEAD"].includes(req.method)) return next();
    const pathname = new URL(req.url, "http://localhost").pathname;
    if (pathname === "/robots.txt") return res.type("text/plain").send(robotsTxt());
    if (pathname === "/sitemap.xml") return res.type("application/xml").send(sitemapXml());
    if (!pageForPath(pathname)) return blogHandler(req, res, next);
    server.middleware.waitUntilValid(() => {
      server.compiler.outputFileSystem.readFile(path.join(server.compiler.outputPath, "index.html"), (error, html) => {
        if (error) return next(error);
        res.setHeader("Cache-Control", "no-cache");
        res.type("html").send(renderLandingHtml(html.toString(), pathname));
      });
    });
  } };
};
