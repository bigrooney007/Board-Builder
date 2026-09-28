import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { blogMetadata, renderBlogHtml } from "./blogMetadata";
import { useBlogMeta, useLandingPageMeta } from "../seo";

const template = '<html><head><title>Home</title><meta name="description" content="Old"><meta property="og:image" content="old.png"><script id="landing-page-schema" type="application/ld+json">{}</script><script defer src="/static/app.js"></script></head><body><div id="root"><main>Old homepage</main></div></body></html>';
const paths = ["/recruit", "/board-fundraising-game", "/strategic-planning", "/board-recommitment", "/join-a-board"];
const article = (cta) => ({ title: "A specific reader's next step", slug: "the-next-step", body: "The original thought stays here.\n\n## A useful perspective\n\nThe next paragraph develops it.", excerpt: "Move from one specific problem to the contribution you want to make.", image_url: "https://nonprofitboardbuilder.com/api/blog/images/the-next-step.png?v=123", image_alt: "A specific graphic headline", cta_label: "Ready for your next step?", cta_button: "Get Started", cta_url: cta, category: "Board Recruitment", published_at: "2026-09-28T09:00:00-04:00" });

test.each(paths)("article HTML includes the cover, text, schema and correct %s CTA before JavaScript", (cta) => {
  const post = article(cta); const doc = new DOMParser().parseFromString(renderBlogHtml(template, post), "text/html");
  expect(doc.querySelectorAll('meta[property="og:image"]')).toHaveLength(1);
  expect(doc.querySelector('meta[property="og:image"]').content).toBe(post.image_url);
  expect(doc.querySelector('meta[name="description"]').content).toBe(post.excerpt);
  expect(doc.querySelector('meta[property="og:type"]').content).toBe("article");
  expect(doc.querySelector('meta[name="twitter:card"]').content).toBe("summary_large_image");
  expect(doc.querySelector("#root img").src).toBe(post.image_url);
  expect(doc.querySelector("#root h1").textContent).toBe(post.title);
  expect(doc.querySelector("#root aside a").getAttribute("href")).toBe(cta);
  expect(doc.querySelector("#root").textContent).toContain("The original thought stays here.");
  expect(doc.querySelector("#root").textContent).not.toContain("Old homepage");
  expect(doc.querySelector("#landing-page-schema")).toBeNull();
  expect(doc.querySelector('script[src="/static/app.js"]')).not.toBeNull();
  const schema = JSON.parse(doc.querySelector("#blog-page-schema").textContent);
  expect(schema["@type"]).toBe("BlogPosting"); expect(schema.author.name).toBe("Rooney Akpesiri");
  expect(schema.image.url).toBe(post.image_url);
});

test("unpublished pages are noindex and editor text cannot inject HTML or scripts", () => {
  for (const status of [404, 503]) {
    const doc = new DOMParser().parseFromString(renderBlogHtml(template, null, [], status), "text/html");
    expect(doc.querySelector('meta[name="robots"]').content).toContain("noindex");
    expect(doc.querySelector("#blog-page-schema")).toBeNull();
  }
  const post = { ...article("javascript:alert(1)"), title: '</script><script>alert(1)</script>', body: '<img onerror="alert(1)" src="x">' };
  const doc = new DOMParser().parseFromString(renderBlogHtml(template, post), "text/html");
  expect(doc.querySelectorAll("[onerror]")).toHaveLength(0);
  expect(doc.querySelector("#root aside a").getAttribute("href")).toBe("/");
  expect(JSON.parse(doc.querySelector("#blog-page-schema").textContent).headline).toBe(post.title);
});

test("navigation between an article and landing page replaces the share image", async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  const Blog = () => { useBlogMeta(article("/join-a-board")); return null; };
  const Landing = () => { useLandingPageMeta("/recruit"); return null; };
  try {
    await act(async () => root.render(<Blog/>));
    expect(document.querySelector('meta[property="og:image"]').content).toContain("/api/blog/images/");
    await act(async () => root.render(<Landing/>));
    expect(document.querySelector('meta[property="og:image"]').content).toContain("board-recruitment-v1.png");
    expect(document.querySelector("#blog-page-schema")).toBeNull();
    expect(document.querySelector('meta[property="article:published_time"]')).toBeNull();
    expect(blogMetadata(null).canonical).toBe("https://nonprofitboardbuilder.com/blog");
  } finally { await act(async () => root.unmount()); node.remove(); }
});
