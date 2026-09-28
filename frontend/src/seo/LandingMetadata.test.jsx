import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { useLandingPageMeta } from "../seo";
import { pages, SITE_ORIGIN, renderLandingHtml, robotsTxt, sitemapXml } from "./landingMetadata";

const template = '<html><head><title>Old homepage</title><meta name="description" content="Old description"><meta property="og:title" content="Old"><meta name="twitter:card" content="summary"><meta name="viewport" content="width=device-width"><script defer src="/static/js/app.js"></script></head><body><div id="root"></div></body></html>';

test.each(pages)("$path has complete metadata and useful content before JavaScript", (page) => {
  const html = renderLandingHtml(template, page.path);
  const doc = new DOMParser().parseFromString(html, "text/html");
  expect(doc.title).toBe(page.title);
  expect(doc.querySelectorAll('meta[name="description"]').length).toBe(1);
  expect(doc.querySelector('meta[name="description"]').content).toBe(page.description);
  expect(doc.querySelectorAll('link[rel="canonical"]').length).toBe(1);
  expect(doc.querySelector('link[rel="canonical"]').getAttribute("href")).toBe(SITE_ORIGIN + page.path);
  for (const key of ["og:title", "og:description", "og:url", "og:image", "og:image:alt"]) {
    expect(doc.querySelectorAll(`meta[property="${key}"]`).length).toBe(1);
    expect(doc.querySelector(`meta[property="${key}"]`).content).not.toBe("");
  }
  expect(doc.querySelector('meta[property="og:image"]').content).toBe(`${SITE_ORIGIN}/social/${page.image}`);
  expect(doc.querySelector('meta[property="og:image:width"]').content).toBe("1200");
  expect(doc.querySelector('meta[property="og:image:height"]').content).toBe("630");
  expect(doc.querySelector('meta[name="twitter:card"]').content).toBe("summary_large_image");
  expect(doc.querySelector('meta[name="twitter:image"]').content).toContain(page.image);
  expect(doc.querySelector('meta[name="robots"]').content).toContain("max-image-preview:large");
  expect(doc.querySelector('meta[name="viewport"]')).not.toBeNull();
  expect(doc.querySelector('script[src="/static/js/app.js"]')).not.toBeNull();
  expect(doc.querySelector("#root h1").textContent).toBe(page.headline);
  const data = JSON.parse(doc.querySelector("#landing-page-schema").textContent);
  expect(data["@graph"].find((item) => item["@id"] === SITE_ORIGIN + page.path + "#webpage").description).toBe(page.description);
  expect(renderLandingHtml(template, page.path + (page.path === "/" ? "" : "/"))).toBe(html);
});

test("page titles and images are unique and public routes remain crawlable", () => {
  expect(new Set(pages.map((page) => page.title)).size).toBe(7);
  expect(new Set(pages.map((page) => page.image)).size).toBe(7);
  const disallowed = robotsTxt().split("\n").filter((line) => line.startsWith("Disallow: ")).map((line) => line.slice(10));
  for (const page of pages) {
    expect(disallowed.some((path) => page.path.startsWith(path))).toBe(false);
    expect(sitemapXml()).toContain(`<loc>${SITE_ORIGIN}${page.path}</loc>`);
  }
  expect(robotsTxt()).toContain("User-agent: *\nAllow: /");
  expect(robotsTxt()).toContain("Disallow: /api/");
  expect(renderLandingHtml(template, "/app/board-recruitment")).toBe(template);
});

test("client navigation updates all metadata without retaining another page's image", async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  const Page = ({ path }) => { useLandingPageMeta(path); return <p>Page</p>; };
  try {
    for (const page of pages) {
      await act(async () => root.render(<Page path={page.path} />));
      expect(document.title).toBe(page.title);
      expect(document.querySelectorAll('meta[property="og:image"]').length).toBe(1);
      expect(document.querySelector('meta[property="og:image"]').content).toContain(page.image);
      expect(document.querySelectorAll('link[rel="canonical"]').length).toBe(1);
      expect(document.querySelectorAll("#landing-page-schema").length).toBe(1);
    }
  } finally {
    await act(async () => root.unmount()); node.remove();
  }
  expect(document.querySelector('meta[property="og:image"]')).toBeNull();
});
