const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");
const { articles, articlePath, articleWordCount, START_PATH } = require("../src/content/fundraisingArticles");
const blogHandler = require("./blog-seo-handler.cjs");
const renderArticle = require("./fundraising-article-renderer.cjs");
const { sitemapXml } = require("../src/seo/landingMetadata");
const build = path.resolve(__dirname, "../build");
const template = '<html><head><meta name="viewport" content="width=device-width"><title>Old</title><script defer src="/static/app.js"></script></head><body><div id="root"><main>Old</main></div><script src="/body-script.js"></script></body></html>';

async function main() {
  for (const article of articles) {
    const pathname = articlePath(article);
    const html = fs.readFileSync(path.join(build, pathname.slice(1), "index.html"), "utf8");
    const doc = new JSDOM(html).window.document;
    assert.equal(doc.querySelectorAll('meta[property="og:image"]').length, 1);
    assert.equal(doc.querySelector('meta[property="og:type"]').content, "article");
    assert.equal(doc.querySelector('link[rel="canonical"]').href, `https://nonprofitboardbuilder.com${pathname}`);
    assert.ok(doc.querySelector('link[href="/styles/fundraising-articles.css"]'));
    assert.equal(doc.querySelector('meta[name="twitter:card"]').content, "summary_large_image");
    assert.ok(!doc.querySelector('meta[name="robots"]').content.includes("noindex"));
    assert.equal(doc.querySelectorAll("form, input, textarea, select").length, 0);
    assert.ok(doc.querySelector("main").textContent.includes(article.intro[0]));
    assert.ok(doc.querySelector("main").textContent.includes(article.offerNote));
    for (const link of doc.querySelectorAll("[data-article-start]")) assert.equal(link.getAttribute("href"), START_PATH);
    assert.ok(sitemapXml().includes(`https://nonprofitboardbuilder.com${pathname}`));
    const image = fs.readFileSync(path.join(build, "social", article.image));
    assert.equal(image.subarray(1, 4).toString(), "PNG");
    assert.equal(image.readUInt32BE(16), 1200); assert.equal(image.readUInt32BE(20), 630);
    const rendered = new JSDOM(renderArticle(template, article)).window.document;
    assert.ok(rendered.querySelector('script[src="/body-script.js"]'));
    let apiCalls = 0;
    const handler = blogHandler(async () => template, { fetch: async () => { apiCalls++; throw new Error("Blog API offline"); } });
    for (const method of ["GET", "HEAD"]) {
      const response = { headers: {}, setHeader(key, value) { this.headers[key] = value; }, end(value) { this.body = value; } };
      await handler({ method, url: pathname + "/?utm_source=linkedin" }, response, error => { throw error || new Error("Guide was not handled"); });
      assert.equal(response.statusCode, 200);
      assert.equal(response.headers["X-Robots-Tag"], undefined);
      if (method === "GET") assert.ok(response.body.includes(article.intro[0]));
      else assert.equal(response.body, undefined);
    }
    assert.equal(apiCalls, 2, "GET and HEAD should attempt saved content and retain the complete fallback when offline");
    const edited = { ...article, title: "The professor's revised article", intro: ["Saved text with <script>characters</script> is displayed safely."], excerpt: "An edited description for the published page.", edited_at: "2026-10-06T12:00:00Z" };
    const editedHandler = blogHandler(async () => template, { fetch: async () => ({ ok: true, json: async () => edited }) });
    const updated = { setHeader() {}, end(value) { this.body = value; } };
    await editedHandler({ method: "GET", url: pathname }, updated, error => { throw error || new Error("Guide was not handled"); });
    const editedDoc = new JSDOM(updated.body).window.document;
    assert.ok(editedDoc.querySelector("main").textContent.includes(edited.intro[0]));
    assert.equal(editedDoc.querySelector('meta[property="og:description"]').content, edited.excerpt);
    assert.equal(JSON.parse(editedDoc.getElementById("fundraising-guide-data").textContent).title, edited.title);
    assert.ok(editedDoc.querySelector('link[type="application/rss+xml"]'));
    assert.equal(editedDoc.querySelectorAll("main script").length, 0);
    assert.ok(articleWordCount(article) <= 650, "Keep the article concise");
    console.log(`PASS ${pathname}: public HTML, direct form CTA, share image, sitemap and offline GET/HEAD`);
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
