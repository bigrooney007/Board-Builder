/* eslint-env node */
// Shared by the initial HTML renderer and React navigation. No browser or server-only dependencies.
const pages = require("../content/landingSeo.json");
const SITE_ORIGIN = "https://nonprofitboardbuilder.com";
const SITE_NAME = "Nonprofit Board Builder";
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
const pageForPath = (pathname) => pages.find((page) => page.path === (pathname.replace(/\/+$/, "") || "/"));
const canonicalUrl = (page) => SITE_ORIGIN + page.path;
const imageUrl = (page) => `${SITE_ORIGIN}/social/${page.image}`;

function metaTags(page) {
  return [
    ["name", "description", page.description],
    ["name", "robots", "index, follow, max-image-preview:large"],
    ["property", "og:type", "website"],
    ["property", "og:site_name", SITE_NAME],
    ["property", "og:locale", "en_US"],
    ["property", "og:title", page.title],
    ["property", "og:description", page.description],
    ["property", "og:url", canonicalUrl(page)],
    ["property", "og:image", imageUrl(page)],
    ["property", "og:image:secure_url", imageUrl(page)],
    ["property", "og:image:type", "image/png"],
    ["property", "og:image:width", "1200"],
    ["property", "og:image:height", "630"],
    ["property", "og:image:alt", `${page.imageLines.join(" ")} ${SITE_NAME}.`],
    ["name", "twitter:card", "summary_large_image"],
    ["name", "twitter:title", page.title],
    ["name", "twitter:description", page.description],
    ["name", "twitter:image", imageUrl(page)],
    ["name", "twitter:image:alt", `${page.imageLines.join(" ")} ${SITE_NAME}.`],
  ];
}

function structuredData(page) {
  const organizationId = SITE_ORIGIN + "/#organization";
  const websiteId = SITE_ORIGIN + "/#website";
  const url = canonicalUrl(page);
  const graph = [
    { "@type": "Organization", "@id": organizationId, name: SITE_NAME, url: SITE_ORIGIN + "/", founder: { "@type": "Person", name: "Rooney Akpesiri" } },
    { "@type": "WebSite", "@id": websiteId, name: SITE_NAME, url: SITE_ORIGIN + "/", publisher: { "@id": organizationId } },
    { "@type": page.path === "/" ? "CollectionPage" : "WebPage", "@id": url + "#webpage", url, name: page.title, description: page.description, inLanguage: "en", isPartOf: { "@id": websiteId }, publisher: { "@id": organizationId }, primaryImageOfPage: { "@type": "ImageObject", url: imageUrl(page), width: 1200, height: 630 } },
  ];
  if (page.path !== "/") {
    graph[2].mainEntity = { "@id": url + "#service" };
    graph.push({ "@type": "Service", "@id": url + "#service", name: page.name, serviceType: page.name, url, description: page.description, provider: { "@id": organizationId }, image: imageUrl(page) });
    graph.push({ "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: SITE_NAME, item: SITE_ORIGIN + "/" }, { "@type": "ListItem", position: 2, name: page.name, item: url }] });
  }
  return { "@context": "https://schema.org", "@graph": graph };
}

function fallbackContent(page) {
  // A useful public page remains available before React loads and when JavaScript is unavailable.
  const paragraphs = page.paragraphs.map((text) => `<p>${escapeHtml(text)}</p>`).join("");
  const steps = page.steps.length ? `<h2>How it works</h2><ol>${page.steps.map((text) => `<li>${escapeHtml(text)}</li>`).join("")}</ol>` : "";
  const links = pages.filter((item) => item.path !== page.path).map((item) => {
    const name = page.path === "/board-fundraising-game" && item.path === "/organize-board-fundraising-game"
      ? "Facilitated Board Fundraising Meeting" : item.name;
    return `<li><a href="${item.path}">${escapeHtml(name)}</a></li>`;
  }).join("");
  return `<main id="landing-page-summary" style="max-width:900px;margin:56px auto;padding:24px;font-family:Inter,Arial,sans-serif;line-height:1.7;color:#0f172a"><p style="color:#4f46e5;font-weight:700">${SITE_NAME}</p><h1>${escapeHtml(page.headline)}</h1>${paragraphs}${steps}<nav aria-label="Explore Nonprofit Board Builder"><h2>Explore our pathways</h2><ul>${links}</ul></nav><noscript><p>Enable JavaScript to use the interactive forms and dashboard.</p></noscript></main>`;
}

function renderLandingHtml(template, pathname) {
  const page = pageForPath(pathname);
  if (!page) return template;
  const tags = [`<title>${escapeHtml(page.title)}</title>`, ...metaTags(page).map(([attr, key, value]) => `<meta ${attr}="${key}" content="${escapeHtml(value)}" />`), `<link rel="canonical" href="${canonicalUrl(page)}" />`, `<script id="landing-page-schema" type="application/ld+json">${JSON.stringify(structuredData(page)).replace(/</g, "\\u003c")}</script>`].join("\n");
  return template
    .replace(/<title\b[^>]*>[\s\S]*?<\/title>/gi, "")
    .replace(/<meta\b[^>]*(?:name|property)=["'](?:description|robots|og:[^"']+|twitter:[^"']+)["'][^>]*>/gi, "")
    .replace(/<link\b[^>]*rel=["']canonical["'][^>]*>/gi, "")
    .replace(/<script\b[^>]*id=["']landing-page-schema["'][^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<\/head>/i, `${tags}\n</head>`)
    .replace(/<noscript>You need to enable JavaScript to run this app\.<\/noscript>/i, "")
    .replace(/<div id=["']root["']><\/div>/i, `<div id="root">${fallbackContent(page)}</div>`);
}

function robotsTxt() {
  const privatePaths = ["/api/", "/admin", "/app/", "/login", "/forgot-password", "/reset-password/", "/purchase/", "/apply/", "/sign/", "/shared/", "/board-profile/", "/reference-form/", "/referee-form/", "/onboarding-session/", "/game/", "/play/", "/group-game/", "/strategic-planning/dashboard", "/strategic-planning/intake", "/board-recommitment/dashboard", "/board-recommitment/intake"];
  // The wildcard rules allow Googlebot and OAI-SearchBot to crawl every public landing page.
  return ["User-agent: *", "Allow: /", ...privatePaths.map((path) => `Disallow: ${path}`), "Allow: /api/blog/images/", "Allow: /api/blog/sitemap.xml", "", `Sitemap: ${SITE_ORIGIN}/sitemap.xml`, `Sitemap: ${SITE_ORIGIN}/api/blog/sitemap.xml`, ""].join("\n");
}

function sitemapXml() {
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${pages.map((page) => `  <url><loc>${canonicalUrl(page)}</loc></url>`).join("\n")}\n</urlset>\n`;
}

module.exports = { pages, SITE_ORIGIN, pageForPath, canonicalUrl, imageUrl, metaTags, structuredData, renderLandingHtml, robotsTxt, sitemapXml };
