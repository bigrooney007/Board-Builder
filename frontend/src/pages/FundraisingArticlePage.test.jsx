import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import { BlogPostPage } from "./BlogPages";
import { articles, articlePost, START_PATH } from "@/content/fundraisingArticles";

global.IS_REACT_ACT_ENVIRONMENT = true;
let mockSlug = "";
jest.mock("react-router-dom", () => ({
  useParams: () => ({ slug: mockSlug }),
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}), { virtual: true });
jest.mock("axios", () => ({ get: jest.fn() }));
jest.mock("@/funnels/FunnelLayout", () => ({ FunnelLayout: ({ children }) => <div>{children}</div> }));

beforeEach(() => { jest.clearAllMocks(); axios.get.mockRejectedValue(new Error("Content API offline")); window.scrollTo = jest.fn(); document.getElementById("fundraising-guide-data")?.remove(); });

test.each(articles)("$topic guide is immediately readable through the blog route and leads directly to the first form", async article => {
  mockSlug = article.slug;
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  try {
    await act(async () => root.render(<BlogPostPage />));
    expect(axios.get).toHaveBeenCalledWith(`/api/blog/guides/${article.slug}`);
    expect(node.querySelector("form, input, textarea, select")).toBeNull();
    expect(node.textContent).toContain(article.intro[0]);
    expect(node.textContent).toContain("No email required.");
    const starts = [...node.querySelectorAll("[data-article-start]")];
    expect(starts.length).toBeGreaterThan(0);
    expect(starts.every(link => link.getAttribute("href") === START_PATH)).toBe(true);
    for (const step of article.steps) expect(node.textContent).toContain(step.paragraphs[0]);
    expect(node.textContent).toContain("The five questions are free.");
    expect(document.querySelector('link[rel="canonical"]').href).toBe(`https://nonprofitboardbuilder.com/blog/${article.slug}`);
    expect(document.querySelector('meta[property="og:image"]').content).toBe(articlePost(article).image_url);
  } finally { await act(async () => root.unmount()); node.remove(); }
});

test("saved guide wording updates the page and share metadata while keeping the form destination", async () => {
  const article = articles[0]; mockSlug = article.slug;
  const saved = { ...article, title: "My revised board fundraising article", headline: "My own heading", intro: ["This is the introduction I wrote in Admin."], excerpt: "My updated description for readers and LinkedIn.", ctaButton: "Start with my five questions", edited_at: "2026-10-06T12:00:00Z" };
  axios.get.mockResolvedValue({ data: { ...saved, steps: saved.steps.map(step => ({ ...step, questions: [] })) } });
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  try {
    await act(async () => root.render(<BlogPostPage />));
    expect(node.textContent).toContain(saved.intro[0]);
    expect(node.querySelector("h1").textContent).toContain(saved.headline);
    expect(node.querySelectorAll(".fa-questions")).toHaveLength(0);
    expect(document.title).toContain(saved.title);
    expect(document.querySelector('meta[property="og:description"]').content).toBe(saved.excerpt);
    expect(document.querySelector('meta[property="article:modified_time"]').content).toBe(saved.edited_at);
    expect([...node.querySelectorAll("[data-article-start]")].every(link => link.getAttribute("href") === START_PATH)).toBe(true);
    expect(document.querySelector('link[type="application/rss+xml"]').href).toBe("https://nonprofitboardbuilder.com/api/blog/feed.xml");
  } finally { await act(async () => root.unmount()); node.remove(); }
});

test("the newest server-rendered wording stays visible when the content API is unavailable", async () => {
  const article = articles[1]; mockSlug = article.slug;
  const bootstrap = document.createElement("script"); bootstrap.id = "fundraising-guide-data"; bootstrap.type = "application/json";
  bootstrap.textContent = JSON.stringify({ ...article, intro: ["The server already loaded my saved wording."] }); document.head.appendChild(bootstrap);
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  try {
    await act(async () => root.render(<BlogPostPage />));
    expect(node.textContent).toContain("The server already loaded my saved wording.");
  } finally { await act(async () => root.unmount()); node.remove(); bootstrap.remove(); }
});
