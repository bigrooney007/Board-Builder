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

beforeEach(() => { jest.clearAllMocks(); window.scrollTo = jest.fn(); });

test.each(articles)("$topic guide is immediately readable through the blog route and leads directly to the first form", async article => {
  mockSlug = article.slug;
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  try {
    await act(async () => root.render(<BlogPostPage />));
    expect(axios.get).not.toHaveBeenCalled();
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
