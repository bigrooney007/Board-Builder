// Run against the existing deployment after publishing an article in the admin.
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");
const base = (process.argv[2] || "").replace(/\/$/, "");
if (!/^https?:\/\//.test(base)) throw new Error("Usage: node scripts/verify-blog-seo.cjs https://nonprofitboardbuilder.com");
const read = (path) => fetch(base + path, { headers: { "User-Agent": "facebookexternalhit/1.1" }, signal: AbortSignal.timeout(15000) });
async function main() {
  const index = await read("/blog"); assert.equal(index.status, 200, "Blog index HTTP status");
  const doc = new JSDOM(await index.text()).window.document;
  assert.match(doc.title, /Board.*Insights/); assert.ok(doc.querySelector('meta[property="og:image"]'));
  const response = await read("/api/blog/posts?limit=100"); assert.equal(response.status, 200);
  const { posts } = await response.json();
  const paths = { recruitment: "/recruit", fundraising_activation: "/board-fundraising-game", strategic_planning: "/strategic-planning", reactivation: "/board-recommitment", board_applicant_network: "/join-a-board" };
  // One live article per current category is enough to exercise each destination.
  const selected = [...new Map(posts.filter((post) => paths[post.category_key]).map((post) => [post.category_key, post])).values()];
  for (const post of selected) {
    const html = await read(`/blog/${encodeURIComponent(post.slug)}`); assert.equal(html.status, 200, post.slug);
    const page = new JSDOM(await html.text()).window.document;
    assert.equal(page.querySelector('meta[property="og:image"]').content, post.image_url);
    assert.equal(page.querySelector('meta[name="description"]').content, post.excerpt);
    assert.equal(page.querySelector('meta[property="og:type"]').content, "article");
    assert.equal(page.querySelector('meta[name="twitter:card"]').content, "summary_large_image");
    assert.equal(page.querySelector("#root h1").textContent, post.title);
    assert.equal(page.querySelector("#root aside a").getAttribute("href"), paths[post.category_key]);
    const schema = JSON.parse(page.querySelector("#blog-page-schema").textContent);
    assert.equal(schema["@type"], "BlogPosting"); assert.equal(schema.image.url, post.image_url);
    const url = new URL(post.image_url);
    const png = await read(url.pathname + url.search); assert.equal(png.status, 200);
    assert.match(png.headers.get("content-type"), /image\/png/);
    const bytes = Buffer.from(await png.arrayBuffer()); assert.equal(bytes.subarray(1, 4).toString(), "PNG");
    assert.equal(bytes.readUInt32BE(16), 1200); assert.equal(bytes.readUInt32BE(20), 630);
    console.log(`PASS /blog/${post.slug}: article HTML, CTA, schema and cover image`);
  }
  const robots = await (await read("/robots.txt")).text(); assert.ok(robots.includes("Allow: /api/blog/images/"));
  const sitemap = await read("/api/blog/sitemap.xml"); assert.equal(sitemap.status, 200);
  const xml = await sitemap.text(); for (const post of selected) assert.ok(xml.includes(`/blog/${post.slug}`));
  console.log(`PASS blog index, crawler rules and sitemap. Checked ${selected.length} published topic(s).`);
  if (!selected.length) console.log("No current-topic articles are published yet. Publish a draft and rerun to verify its share card.");
}
main().catch((error) => { console.error(error.message); process.exitCode = 1; });
