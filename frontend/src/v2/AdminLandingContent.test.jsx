import React, { act } from "react";
import { createRoot } from "react-dom/client";
import AdminLandingContent from "./AdminLandingContent";
import { defaultLandingContent } from "./LandingContent";
import { v2Api } from "./api";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("react-router-dom", () => ({ Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a> }));
jest.mock("@/components/TestimonialCarousel", () => ({ TestimonialCarousel: () => <div data-testid="genuine-carousel" /> }));
jest.mock("./api", () => ({ v2Api: { get: jest.fn(), put: jest.fn(), post: jest.fn() }, errorMessage: (error, fallback) => error?.response?.data?.detail || fallback }));
const clone = (value) => JSON.parse(JSON.stringify(value));
let pages;
let saves;
let publications;

beforeEach(() => {
  pages = {}; saves = []; publications = [];
  for (const product of ["recruit", "board-fundraising-game", "strategic-planning", "board-recommitment"]) {
    pages[product] = { product, revision: 0, draft: defaultLandingContent(product), published: defaultLandingContent(product), saved_at: null, published_at: null };
  }
  v2Api.get.mockReset(); v2Api.put.mockReset(); v2Api.post.mockReset();
  v2Api.get.mockImplementation(async (path) => ({ data: clone(pages[path.split("/").pop()]) }));
  v2Api.put.mockImplementation(async (path, payload) => {
    const product = path.split("/").pop(); saves.push(clone(payload));
    pages[product] = { ...pages[product], revision: pages[product].revision + 1, saved_at: "2026-10-14T12:00:00Z", draft: clone(payload.content) };
    return { data: clone(pages[product]) };
  });
  v2Api.post.mockImplementation(async (path, payload) => {
    const product = path.split("/").slice(-2)[0]; publications.push(clone(payload));
    pages[product] = { ...pages[product], revision: pages[product].revision + 1, published_at: "2026-10-14T12:01:00Z", published: clone(pages[product].draft) };
    return { data: clone(pages[product]) };
  });
});

async function mount() {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<AdminLandingContent />));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}
const button = (node, label) => [...node.querySelectorAll("button")].find((item) => item.textContent === label);
const field = (node, label) => [...node.querySelectorAll("label")].find((item) => [...item.childNodes].filter((child) => child.nodeType === Node.TEXT_NODE).map((child) => child.textContent).join("") === label)?.querySelector("input,textarea");
async function type(node, label, value) {
  await act(async () => {
    const input = field(node, label);
    const prototype = input.tagName === "INPUT" ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, "value").set.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function click(node, label) { await act(async () => button(node, label).click()); }
async function save(node) { await act(async () => node.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }))); }

test("all four offer pages load independently and drafts survive switching pages", async () => {
  const { node, cleanup } = await mount();
  try {
    for (const name of ["Board Recruitment", "Board Fundraising Activation", "Strategic Planning", "Board Recommitment"]) {
      await click(node, name);
      await type(node, "Main heading", "My words for " + name);
      await save(node);
      expect(publications).toHaveLength(0);
      expect(node.textContent).toContain("Visitors continue to see the published version");
    }
    await click(node, "Board Recruitment");
    expect(field(node, "Main heading").value).toBe("My words for Board Recruitment");
    expect(saves).toHaveLength(4);
  } finally { await cleanup(); }
});

test("preview renders paragraphs safely and publication saves the exact current draft first", async () => {
  const { node, cleanup } = await mount();
  try {
    await type(node, "Main heading", "This sounds like me");
    await type(node, "Opening explanation", "First full paragraph.\n\n<script>unsafe()</script>");
    await click(node, "Preview my changes");
    const preview = node.querySelector(".v2-editor-preview");
    expect(preview.querySelector("h1").textContent).toBe("This sounds like me");
    expect(preview.querySelector("script")).toBeNull();
    expect(preview.textContent).toContain("<script>unsafe()</script>");
    expect([...preview.querySelectorAll("p")].some((p) => p.textContent === "First full paragraph.")).toBe(true);
    expect(v2Api.put).not.toHaveBeenCalled();
    await click(node, "Publish changes");
    expect(saves[0].content.headline).toBe("This sounds like me");
    expect(publications).toEqual([{ revision: 1 }]);
    expect(pages.recruit.published.headline).toBe("This sounds like me");
    expect(node.textContent).toContain("No deployment is needed");
    expect(button(node, "Publish changes").disabled).toBe(true);
  } finally { await cleanup(); }
});

test("a failed save keeps the administrator's writing for a retry", async () => {
  const { node, cleanup } = await mount();
  try {
    await type(node, "Main heading", "Writing I must not lose");
    v2Api.put.mockRejectedValueOnce({ response: { data: { detail: "Synthetic save failure" } } });
    await save(node);
    expect(field(node, "Main heading").value).toBe("Writing I must not lose");
    expect(node.textContent).toContain("Synthetic save failure");
    expect(v2Api.post).not.toHaveBeenCalled();
    await save(node);
    expect(pages.recruit.draft.headline).toBe("Writing I must not lose");
  } finally { await cleanup(); }
});

test("adding a step requires its complete text and reordering preserves its explanation", async () => {
  const { node, cleanup } = await mount();
  try {
    await click(node, "Add a teaching step");
    expect(button(node, "Publish changes").disabled).toBe(true);
    await type(node, "Step 5 heading", "My additional teaching step");
    await type(node, "Step 5 explanation", "My practical guidance for this step.");
    const lastStep = node.querySelectorAll(".v2-editor-step")[4];
    await act(async () => button(lastStep, "Move up").click());
    await save(node);
    expect(pages.recruit.draft.teaching[3]).toEqual(["My additional teaching step", "My practical guidance for this step."]);
    expect(pages.recruit.draft.teaching).toHaveLength(5);
  } finally { await cleanup(); }
});

test("switching offers warns before losing unsaved writing", async () => {
  const { node, cleanup } = await mount();
  const confirm = jest.spyOn(window, "confirm").mockReturnValue(false);
  try {
    await type(node, "Main heading", "Unsaved writing");
    await click(node, "Strategic Planning");
    expect(confirm).toHaveBeenCalled();
    expect(field(node, "Main heading").value).toBe("Unsaved writing");
    expect(v2Api.get).toHaveBeenCalledTimes(1);
  } finally { confirm.mockRestore(); await cleanup(); }
});
