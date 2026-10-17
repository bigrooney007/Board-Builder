import React, { act } from "react";
import { createRoot } from "react-dom/client";
import BlogAdminSection from "./BlogAdminSection";
import { articles } from "@/content/fundraisingArticles";

global.IS_REACT_ACT_ENVIRONMENT = true;
const topics = [
  ["recruitment", "Board Recruitment", "Monday", "/recruit"],
  ["fundraising_activation", "Board Fundraising", "Tuesday", "/board-fundraising-game"],
  ["strategic_planning", "Strategic Planning", "Wednesday", "/strategic-planning"],
  ["reactivation", "Board Recommitment", "Thursday", "/board-recommitment"],
  ["board_applicant_network", "Joining Nonprofit Boards", "Friday", "/join-a-board"],
].map(([category_key, category, publish_day, cta_url]) => ({ category_key, category, publish_day, cta_url, audience: "The exact audience", scheduled_date: "2026-10-02", next_topic_id: "angle", topics: [{ topic_id: "angle", topic_title: "A specific article angle", pain_point: "A recognizable problem", limiting_belief: "The belief behind the problem", desired_outcome: "A useful outcome" }] }));
const draft = { blog_post_id: "draft1", title: "An article to review", category: "Joining Nonprofit Boards", publication_status: "Pending Review", scheduled_date: "2026-10-02", excerpt: "A useful share description.", body: "This is the article body.", graphic_headline: "Put Your Experience to Work", graphic_subtitle: "Find a board that values your contribution.", image_path: "/api/admin/blog/posts/draft1/image?v=1", image_alt: "Put your experience to work", cta_url: "/join-a-board", cta_label: "Ready to serve?", cta_button: "Join the Board Applicant Network", can_regenerate: true };

test("admin selects Friday, generates and reuses a draft, edits the cover and publishes", async () => {
  const client = {
    get: jest.fn(async (path) => ({ data: path === "/admin/blog/guides" ? { guides: articles } : path === "/admin/blog/topics" ? { schedule: topics, settings: { enabled: false, time: "08:00", timezone: "Europe/London" } } : { posts: [], has_more: false } })),
    post: jest.fn(async (path) => ({ data: { post: path.endsWith("/approve") ? { ...draft, publication_status: "Published", slug: "an-article", can_regenerate: false } : draft } })),
    patch: jest.fn(async (path, payload) => ({ data: { post: { ...draft, ...payload, image_path: "/api/admin/blog/posts/draft1/image?v=2" } } })),
    put: jest.fn(async (path, settings) => ({ data: { settings } })),
  };
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  const click = async (text) => { const button = [...node.querySelectorAll("button")].find((el) => el.textContent.includes(text)); expect(button).toBeDefined(); await act(async () => button.click()); };
  try {
    await act(async () => root.render(<BlogAdminSection client={client}/>));
    expect(node.querySelectorAll(".blog-weekdays button")).toHaveLength(5);
    await click("Friday");
    expect(node.textContent).toContain("The belief behind the problem");
    await click("Generate Blog Post + Graphic");
    expect(client.post).toHaveBeenCalledWith("/blog/generate", { category: "board_applicant_network", topic_id: "angle", scheduled_date: "2026-10-02" });
    expect(node.querySelector(".blog-cover").getAttribute("src")).toContain("/image?v=1");
    expect(node.querySelector(".blog-preview-cta a").getAttribute("href")).toBe("/join-a-board");
    await click("Edit Article and Graphic");
    expect([...node.querySelectorAll("button")].find((el) => el.textContent === "Publish Article").disabled).toBe(true);
    await act(async () => node.querySelector(".blog-edit-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(client.patch).toHaveBeenCalled();
    expect(node.querySelector(".blog-cover").getAttribute("src")).toContain("v=2");
    await click("Publish Article");
    expect(node.querySelector(".blog-share-link input").value).toBe("https://nonprofitboardbuilder.com/blog/an-article");
    expect([...node.querySelectorAll("button")].some((el) => el.textContent === "Regenerate Draft")).toBe(false);
    expect(client.post.mock.calls.filter(([url]) => url === "/blog/generate")).toHaveLength(1);
    expect(client.post.mock.calls.some(([url]) => url.endsWith("/linkedin-snippet"))).toBe(false);
  } finally { await act(async () => root.unmount()); node.remove(); }
});

test("existing dated articles open without a regeneration call and errors remain visible", async () => {
  const client = {
    get: jest.fn(async (path) => ({ data: path === "/admin/blog/guides" ? { guides: articles } : path.endsWith("topics") ? { schedule: topics, settings: null } : { posts: [draft] } })),
    post: jest.fn(async () => ({ data: { reused: true, post: draft } })),
  };
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  try {
    await act(async () => root.render(<BlogAdminSection client={client}/>));
    await act(async () => [...node.querySelectorAll("button")].find((el) => el.textContent === "Generate Blog Post + Graphic").click());
    expect(node.textContent).toContain("Opened the existing article");
    expect(client.post).toHaveBeenCalledTimes(1);
    client.post.mockRejectedValueOnce({ response: { data: { detail: "Generation is still running." } } });
    await act(async () => [...node.querySelectorAll("button")].find((el) => el.textContent === "Regenerate Draft").click());
    expect(node.querySelector('[role="alert"]').textContent).toBe("Generation is still running.");
  } finally { await act(async () => root.unmount()); node.remove(); }
});
