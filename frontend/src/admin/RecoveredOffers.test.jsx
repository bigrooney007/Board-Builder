import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import { HomepageTextSection } from "./HomepageTextSection";
import { useHomepageContent } from "@/clean/platform";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("axios", () => {
  const put = jest.fn();
  return { get: jest.fn(), create: () => ({ put }), put };
});
jest.mock("@/pages/MainHomePage", () => ({ MAIN_HOME_DEFAULTS: { headline: "Main" } }));
jest.mock("@/game/FacilitatedGamePage", () => ({ FACILITATED_GAME_HOME_DEFAULTS: { headline: "Facilitated" } }));
jest.mock("@/content/siteContent", () => ({ recruitmentHomeContent: { headline: "Recruit" } }));
jest.mock("@/funnels/GuidedProductPages", () => ({ GUIDED_PRODUCT_CONFIG: {
  "strategic-planning": { headline: "Planning", icon: () => null },
  "board-recommitment": { headline: "Recommitment", icon: () => null },
} }));

let root, node;
beforeEach(() => {
  jest.clearAllMocks();
  axios.put.mockResolvedValue({ data: { status: "saved" } });
  node = document.createElement("div"); document.body.appendChild(node);
  root = createRoot(node);
});
afterEach(async () => { await act(async () => root.unmount()); node.remove(); });
const saveButton = () => [...node.querySelectorAll("button")].find(b => b.textContent.includes("SAVE HOME PAGE TEXT"));
async function choose(value) {
  await act(async () => {
    const select = node.querySelector("select");
    select.value = value; select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

test("a late page load cannot replace another product's content or allow saving unloaded data", async () => {
  let resolveRecruit;
  axios.get.mockImplementation(url => url.endsWith("/offer-recruitment")
    ? new Promise(resolve => { resolveRecruit = resolve; })
    : Promise.resolve({ data: { content: {} } }));
  await act(async () => root.render(<HomepageTextSection />));
  await choose("offer-recruitment");
  expect(saveButton().disabled).toBe(true);
  await choose("offer-strategic-planning");
  expect(saveButton().disabled).toBe(false);
  await act(async () => resolveRecruit({ data: { content: { heading: "Wrong late recruitment text" } } }));
  expect(node.textContent).not.toContain("Wrong late recruitment text");
  await act(async () => saveButton().click());
  expect(axios.put).toHaveBeenCalledWith("/admin/platform/homepages/offer-strategic-planning", {
    content: expect.objectContaining({ heading: "Here's How Your Strategic Planning Process Moves Forward" }),
  });
});

test("a failed page load leaves save disabled instead of overwriting saved content", async () => {
  axios.get.mockRejectedValue(new Error("Synthetic connection failure"));
  await act(async () => root.render(<HomepageTextSection />));
  expect(saveButton().disabled).toBe(true);
  expect(node.textContent).toContain("Could not load this home page text.");
  expect(axios.put).not.toHaveBeenCalled();
});

test("saved fundraising text wins even when its content version is older", async () => {
  axios.get.mockResolvedValue({ data: { content: { headline: "The administrator's own words", content_version: 1 } } });
  function PublicText() {
    const copy = useHomepageContent("board-fundraising-game", { headline: "Default", content_version: 3 });
    return <h1>{copy.headline}</h1>;
  }
  await act(async () => root.render(<PublicText />));
  expect(node.querySelector("h1").textContent).toBe("The administrator's own words");
});
