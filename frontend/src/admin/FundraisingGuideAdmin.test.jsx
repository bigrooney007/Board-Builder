import React, { act } from "react";
import { createRoot } from "react-dom/client";
import FundraisingGuideAdmin from "./FundraisingGuideAdmin";
import { articles, START_PATH } from "@/content/fundraisingArticles";
import { BLOG_FEED_URL } from "@/seo/blogMetadata";

global.IS_REACT_ACT_ENVIRONMENT = true;

test("admin edits paragraphs, previews and saves a guide; a failed save preserves their wording", async () => {
  const client = {
    get: jest.fn(async () => ({ data: { guides: articles } })),
    put: jest.fn(async (path, guide) => ({ data: { guide } })),
  };
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  try {
    await act(async () => root.render(<FundraisingGuideAdmin client={client} />));
    expect(node.querySelector('input[readonly]').value).toBe(BLOG_FEED_URL);
    await act(async () => node.querySelector(".blog-guide-card button").click());
    const label = [...node.querySelectorAll("label")].find(label => label.textContent === "Introduction");
    const input = document.getElementById(label.htmlFor);
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(input, "My first paragraph.\n\nMy second paragraph.");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(node.querySelector("iframe").getAttribute("srcdoc")).toContain("My second paragraph.");
    expect(node.querySelector("iframe").getAttribute("srcdoc")).toContain(`href="${START_PATH}"`);
    client.put.mockRejectedValueOnce({ response: { data: { detail: "Please try this save again." } } });
    await act(async () => node.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(node.querySelector('[role="alert"]').textContent).toContain("Please try this save again.");
    expect(input.value).toContain("My second paragraph.");
    await act(async () => node.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(client.put).toHaveBeenLastCalledWith(`/admin/blog/guides/${articles[0].slug}`, expect.objectContaining({ intro: ["My first paragraph.", "My second paragraph."] }));
    expect(node.querySelector("form")).toBeNull();
    expect(node.textContent).toContain("Saved and published.");
  } finally { await act(async () => root.unmount()); node.remove(); }
});
