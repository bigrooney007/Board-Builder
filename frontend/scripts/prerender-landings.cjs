const fs = require("node:fs");
const path = require("node:path");
const { pages, renderLandingHtml, robotsTxt, sitemapXml } = require("../src/seo/landingMetadata");
const build = path.resolve(__dirname, "../build");
const template = fs.readFileSync(path.join(build, "index.html"), "utf8");
for (const page of pages) {
  const target = path.join(build, page.path.slice(1), "index.html");
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, renderLandingHtml(template, page.path));
  if (!fs.existsSync(path.join(build, "social", page.image))) throw new Error(`Missing share image: ${page.image}`);
}
fs.writeFileSync(path.join(build, "robots.txt"), robotsTxt());
fs.writeFileSync(path.join(build, "sitemap.xml"), sitemapXml());
console.log(`Prepared crawler-visible HTML and share metadata for ${pages.length} landing pages.`);
