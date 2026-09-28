// Validate the production build, or a running deployment: node scripts/verify-landing-seo.cjs https://nonprofitboardbuilder.com
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");
const { pages, SITE_ORIGIN } = require("../src/seo/landingMetadata");
const build = path.resolve(__dirname, "../build");
const baseUrl = process.argv[2]?.replace(/\/$/, "");

async function read(route) {
  if (!baseUrl) return fs.readFileSync(path.join(build, route));
  const response = await fetch(baseUrl + route, { headers: { "User-Agent": "OAI-SearchBot" } });
  assert.equal(response.status, 200, `HTTP status for ${route}`);
  return Buffer.from(await response.arrayBuffer());
}

(async () => {
  for (const page of pages) {
    const html = await read(baseUrl ? page.path : path.posix.join(page.path, "index.html"));
    const doc = new JSDOM(html.toString()).window.document;
    assert.equal(doc.title, page.title, page.path);
    for (const selector of ['meta[name="description"]', 'meta[property="og:title"]', 'meta[property="og:description"]', 'meta[property="og:image"]', 'meta[name="twitter:image"]', 'link[rel="canonical"]']) assert.equal(doc.querySelectorAll(selector).length, 1, `${page.path} ${selector}`);
    assert.equal(doc.querySelector('meta[name="description"]').content, page.description);
    assert.equal(doc.querySelector('meta[property="og:image"]').content, `${SITE_ORIGIN}/social/${page.image}`);
    assert.equal(doc.querySelector('link[rel="canonical"]').getAttribute("href"), SITE_ORIGIN + page.path);
    assert.equal(doc.querySelector("#root h1").textContent, page.headline);
    JSON.parse(doc.querySelector("#landing-page-schema").textContent);
    const png = await read(`/social/${page.image}`);
    assert.equal(png.subarray(1, 4).toString(), "PNG");
    assert.equal(png.readUInt32BE(16), 1200);
    assert.equal(png.readUInt32BE(20), 630);
    console.log(`PASS ${page.path}: initial HTML, metadata, structured data and 1200x630 image`);
  }
  const sitemap = (await read("/sitemap.xml")).toString();
  for (const page of pages) assert(sitemap.includes(`<loc>${SITE_ORIGIN}${page.path}</loc>`));
  assert((await read("/robots.txt")).toString().includes(`Sitemap: ${SITE_ORIGIN}/sitemap.xml`));
  console.log("PASS sitemap and robots.txt");
})().catch((error) => { console.error(error); process.exitCode = 1; });
