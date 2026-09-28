/* eslint-env node */
const { SITE_ORIGIN } = require("./landingMetadata");
const SITE_NAME = "Nonprofit Board Builder";
const escapeHtml = (value) => String(value || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
const blogUrl = (post) => `${SITE_ORIGIN}/blog${post ? "/" + encodeURIComponent(post.slug) : ""}`;
const description = "Practical insights on board recruitment, fundraising, strategic planning, recommitment and finding your opportunity to serve on a nonprofit board.";

function blogMetadata(post, status = 200) {
  const title = status === 404 ? "Article Not Found | Nonprofit Board Builder" : status !== 200 ? "Blog Temporarily Unavailable | Nonprofit Board Builder" : post ? `${post.title} | ${SITE_NAME}` : `Nonprofit Board Insights | ${SITE_NAME}`;
  const image = post?.image_url || `${SITE_ORIGIN}/social/nonprofit-board-builder-v1.png`;
  const alt = post?.image_alt || "Nonprofit Board Builder insights";
  const summary = post?.excerpt || description;
  const canonical = blogUrl(post);
  const tags = [
    ["name", "description", summary], ["name", "robots", status === 200 ? "index, follow, max-image-preview:large" : "noindex, follow"],
    ["property", "og:type", post ? "article" : "website"], ["property", "og:site_name", SITE_NAME],
    ["property", "og:locale", "en_US"], ["property", "og:title", title], ["property", "og:description", summary],
    ["property", "og:url", canonical], ["property", "og:image", image], ["property", "og:image:secure_url", image],
    ["property", "og:image:type", "image/png"], ["property", "og:image:width", "1200"], ["property", "og:image:height", "630"], ["property", "og:image:alt", alt],
    ["name", "twitter:card", "summary_large_image"], ["name", "twitter:title", title], ["name", "twitter:description", summary], ["name", "twitter:image", image], ["name", "twitter:image:alt", alt],
  ];
  if (post?.published_at) tags.push(["property", "article:published_time", post.published_at]);
  if (post?.edited_at) tags.push(["property", "article:modified_time", post.edited_at]);
  if (post) tags.push(["property", "article:author", SITE_ORIGIN + "/about-rooney"], ["property", "article:section", post.category]);
  const schema = status !== 200 ? null : post ? {
    "@context": "https://schema.org", "@type": "BlogPosting", "@id": canonical + "#article", mainEntityOfPage: canonical,
    headline: post.title, description: summary, image: { "@type": "ImageObject", url: image, width: 1200, height: 630 },
    author: { "@type": "Person", name: "Rooney Akpesiri", url: SITE_ORIGIN + "/about-rooney" },
    publisher: { "@type": "Organization", name: SITE_NAME, url: SITE_ORIGIN },
    datePublished: post.published_at, dateModified: post.edited_at || post.published_at, articleSection: post.category, inLanguage: "en-US",
  } : { "@context": "https://schema.org", "@type": "Blog", name: "Nonprofit Board Builder Insights", url: canonical, description };
  return { title, tags, canonical, schema };
}

function renderBlogHtml(template, post = null, posts = [], status = 200) {
  const metadata = blogMetadata(post, status);
  const tags = [`<title>${escapeHtml(metadata.title)}</title>`, ...metadata.tags.map(([attr, name, value]) => `<meta ${attr}="${name}" content="${escapeHtml(value)}" />`),
    ...(status === 200 ? [`<link rel="canonical" href="${metadata.canonical}" />`] : []),
    ...(metadata.schema ? [`<script id="blog-page-schema" type="application/ld+json">${JSON.stringify(metadata.schema).replace(/</g, "\\u003c")}</script>`] : [])].join("\n");
  let content;
  if (status !== 200) content = `<h1>${status === 404 ? "Article not found" : "The blog is temporarily unavailable"}</h1><p>${status === 404 ? "This article may not have been published yet." : "Please try again shortly."}</p><a href="/blog">Read our articles</a>`;
  else if (post) {
    const body = (post.body || "").split(/\n{2,}|\n(?=## )/).filter((block) => block.trim()).map((block) => block.trim().startsWith("## ") ? `<h2>${escapeHtml(block.trim().slice(3))}</h2>` : `<p>${escapeHtml(block.trim())}</p>`).join("");
    // The API supplies fixed service paths; never turn arbitrary content into executable links.
    const cta = /^\/(?!\/)[a-z0-9/-]*$/.test(post.cta_url || "") ? post.cta_url : "/";
    content = `<article><img src="${escapeHtml(post.image_url)}" alt="${escapeHtml(post.image_alt)}" width="1200" height="630" style="max-width:100%;height:auto" /><p>${escapeHtml(post.category)}</p><h1>${escapeHtml(post.title)}</h1><p>By Rooney Akpesiri</p><p>${escapeHtml(post.excerpt)}</p>${body}<aside><h2>${escapeHtml(post.cta_label)}</h2><a href="${cta}">${escapeHtml(post.cta_button)}</a></aside></article><p><a href="/blog">Read all articles</a></p>`;
  } else content = `<h1>Nonprofit Board Builder Insights</h1><p>${description}</p>${posts.map((item) => `<article><h2><a href="/blog/${encodeURIComponent(item.slug)}">${escapeHtml(item.title)}</a></h2><p>${escapeHtml(item.excerpt)}</p></article>`).join("") || "<p>New articles are coming soon.</p>"}`;
  const root = `<main id="blog-page-summary" style="max-width:850px;margin:48px auto;padding:24px;font-family:Arial,sans-serif;line-height:1.7;color:#10132d"><p><a href="/">${SITE_NAME}</a></p>${content}</main>`;
  return template.replace(/<title\b[^>]*>[\s\S]*?<\/title>/gi, "")
    .replace(/<meta\b[^>]*(?:name|property)=["'](?:description|robots|og:[^"']+|twitter:[^"']+|article:[^"']+)["'][^>]*>/gi, "")
    .replace(/<link\b[^>]*rel=["']canonical["'][^>]*>/gi, "")
    .replace(/<script\b[^>]*id=["'](?:landing|blog)-page-schema["'][^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<\/head>/i, () => `${tags}\n</head>`)
    .replace(/<noscript>You need to enable JavaScript to run this app\.<\/noscript>/i, "")
    .replace(/<div id=["']root["']>[\s\S]*?<\/div>/i, () => `<div id="root">${root}</div>`);
}

module.exports = { blogMetadata, renderBlogHtml, blogUrl };
