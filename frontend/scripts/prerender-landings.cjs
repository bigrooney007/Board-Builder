const fs = require("node:fs");
const path = require("node:path");
const { pages, renderLandingHtml, robotsTxt, sitemapXml } = require("../src/seo/landingMetadata");
const { articles, articlePath } = require("../src/content/fundraisingArticles");
const renderFundraisingArticle = require("./fundraising-article-renderer.cjs");
const build = path.resolve(__dirname, "../build");
const template = fs.readFileSync(path.join(build, "index.html"), "utf8");
for (const page of pages) {
  const target = path.join(build, page.path.slice(1), "index.html");
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, renderLandingHtml(template, page.path));
  if (!fs.existsSync(path.join(build, "social", page.image))) throw new Error(`Missing share image: ${page.image}`);
}
for (const article of articles) {
  const target = path.join(build, articlePath(article).slice(1), "index.html");
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, renderFundraisingArticle(template, article));
  if (!fs.existsSync(path.join(build, "social", article.image))) throw new Error(`Missing article share image: ${article.image}`);
}
fs.writeFileSync(path.join(build, "robots.txt"), robotsTxt());
fs.writeFileSync(path.join(build, "sitemap.xml"), sitemapXml());
console.log(`Prepared crawler-visible HTML and share metadata for ${pages.length} landing pages and ${articles.length} fundraising guides.`);
