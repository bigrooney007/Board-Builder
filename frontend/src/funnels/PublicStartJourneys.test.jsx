import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import GameHomePage from "@/game/GameHomePage";
import GameStartPage from "@/game/GameStartPage";
import RecruitFreePage from "./RecruitFreePage";
import RecruitmentHomePage from "./RecruitmentHomePage";
import { GuidedLandingPage, GuidedStartPage } from "./GuidedProductPages";
import { memberApi, storeMemberToken } from "@/member/api";

global.IS_REACT_ACT_ENVIRONMENT = true;
const mockNavigate = jest.fn();
const mockSetMember = jest.fn();
let mockMember = null;
let mockSearch = "";
const mockContent = {
  headline: "Get Your Board Members Raising Money From Your Next Board Meeting",
  subheadline: "Activate and equip your Board.", hero_explanation: "Create your strategy together.",
  goal_label: "How much do you want to raise?", goal_placeholder: "500,000",
  cta_label: "ANSWER THE 5 FUNDRAISING QUESTIONS AND GET MY BOARD FUNDRAISING",
  start_supporting: "Begin with your fundraising goal.",
  intro_heading: "Build the strategy together", intro_paragraphs: [],
  stages_label: "PROCESS", stages_heading: "Three meeting steps", stages: [], stages_cta_label: "START",
  outcomes_label: "OUTCOMES", outcomes_heading: "What you get", outcomes: [],
  faqs_label: "FAQ", faqs_heading: "Questions", faqs: [],
  closing_heading: "Get your Board fundraising", closing_text: "Start with your own ideas.", closing_cta_label: "START",
};
jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
  Navigate: ({ to }) => <div data-testid="redirect">{to}</div>,
  useNavigate: () => mockNavigate, useLocation: () => ({ search: mockSearch }),
}), { virtual: true });
jest.mock("axios", () => ({ post: jest.fn() }));
jest.mock("@/member/api", () => ({
  memberApi: { post: jest.fn(), put: jest.fn() },
  clearMemberToken: jest.fn(), storeMemberToken: jest.fn(),
}), { virtual: true });
jest.mock("@/member/MemberAuthContext", () => ({
  useMemberAuth: () => ({ member: mockMember, loading: false, setMember: mockSetMember }),
}), { virtual: true });
jest.mock("@/clean/platform", () => ({
  useHomepageContent: (_key, defaults) => defaults, trackPlatformEvent: jest.fn(), usePlatformVideo: () => null,
}), { virtual: true });
jest.mock("@/seo", () => ({ useLandingPageMeta: jest.fn(), usePageMeta: jest.fn() }), { virtual: true });
jest.mock("@/game/gameShared", () => ({
  BfgShell: ({ children }) => <div>{children}</div>, useGameContent: () => mockContent,
  money: (value) => `$${Number(value).toLocaleString("en-US")}`,
}));
jest.mock("@/components/TestimonialCarousel", () => ({ TestimonialCarousel: () => null }), { virtual: true });
jest.mock("@/member/BoardRecommitmentDashboard", () => () => null);
jest.mock("./StrategicPlanningDashboard", () => () => null);
jest.mock("./GuidedPrepaymentQuestionsPage", () => ({
  __esModule: true, default: ({ product }) => <div data-testid="saved-questions">{product}</div>,
}));

async function mount(element) {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(element));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}
async function type(node, selector, value) {
  await act(async () => {
    const input = node.querySelector(selector);
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function submit(node) {
  await act(async () => node.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
}
beforeEach(() => {
  jest.clearAllMocks(); localStorage.clear(); sessionStorage.clear();
  mockMember = null; mockSearch = ""; window.scrollTo = jest.fn();
  memberApi.post.mockReset(); memberApi.put.mockReset(); axios.post.mockReset();
});

test.each([
  ["fundraising", <GameHomePage />, "/board-fundraising/start"],
  ["recruitment", <RecruitmentHomePage />, "/recruit/start"],
  ["strategic planning", <GuidedLandingPage product="strategic-planning" />, "/strategic-planning/start"],
  ["recommitment", <GuidedLandingPage product="board-recommitment" />, "/board-recommitment/start"],
])("%s sales page has no form fields and every primary CTA opens its first form", async (_name, element, path) => {
  const { node, cleanup } = await mount(element);
  try {
    expect(node.querySelector("form, input, textarea, select")).toBeNull();
    const links = [...node.querySelectorAll(".bfg-btn-primary")];
    expect(links.length).toBeGreaterThanOrEqual(2);
    expect(links.every(link => link.getAttribute("href") === path)).toBe(true);
    expect(memberApi.post).not.toHaveBeenCalled(); expect(axios.post).not.toHaveBeenCalled();
  } finally { await cleanup(); }
});

test("direct fundraising form saves an anonymous visitor and continues to the five questions", async () => {
  memberApi.post.mockResolvedValueOnce({ data: {} }).mockResolvedValueOnce({ data: { token: "fundraising-token", member: { email: "alex@example.org" } } });
  const { node, cleanup } = await mount(<GameStartPage />);
  try {
    await act(async () => node.querySelector('[data-testid="bfg-goal-preset-250000"]').click());
    expect(memberApi.post).not.toHaveBeenCalled();
    await type(node, "#bfg-lead-name", "Alex Founder"); await type(node, "#bfg-lead-email", "alex@example.org"); await type(node, "#bfg-lead-org", "BrightPath");
    await submit(node);
    expect(memberApi.post).toHaveBeenCalledWith("/members/game-free-start", { name: "Alex Founder", email: "alex@example.org", organization: "BrightPath", goal_amount: 250000 });
    expect(storeMemberToken).toHaveBeenCalledWith("fundraising-token");
    expect(mockSetMember).toHaveBeenCalledWith({ email: "alex@example.org" });
    expect(mockNavigate).toHaveBeenCalledWith("/game/questions");
  } finally { await cleanup(); }
});

test("fundraising form preserves the signed-in member and saves their goal before the questions", async () => {
  mockMember = { email: "alex@example.org" }; memberApi.put.mockResolvedValue({ data: {} });
  const { node, cleanup } = await mount(<GameStartPage />);
  try {
    await type(node, "#bfg-goal", "500000"); await type(node, "#bfg-lead-name", "Alex Founder");
    await type(node, "#bfg-lead-email", "alex@example.org"); await type(node, "#bfg-lead-org", "BrightPath");
    await submit(node);
    expect(memberApi.put).toHaveBeenCalledWith("/game/profile", expect.objectContaining({ goal: { amount: 500000, purpose: "Reach our fundraising goal" }, organization: { name: "BrightPath" } }));
    expect(memberApi.post).not.toHaveBeenCalled(); expect(mockNavigate).toHaveBeenCalledWith("/game/questions");
  } finally { await cleanup(); }
});

test("direct recruitment form saves a not-sure choice and carries its assessment token forward", async () => {
  axios.post.mockResolvedValue({ data: { token: "recruit-token" } });
  const { node, cleanup } = await mount(<RecruitFreePage />);
  try {
    await type(node, "#recruit-lead-name", "Alex Founder"); await type(node, "#recruit-lead-email", "alex@example.org"); await type(node, "#recruit-lead-org", "BrightPath");
    await act(async () => node.querySelector('[data-testid="recruit-free-not-sure"]').click());
    await submit(node);
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining("/recruit/free/start"), { name: "Alex Founder", email: "alex@example.org", organization: "BrightPath", desired_count: "not_sure" });
    expect(localStorage.getItem("recruitFreeToken")).toBe("recruit-token");
    expect(mockNavigate).toHaveBeenCalledWith("/recruit/questions?token=recruit-token");
  } finally { await cleanup(); }
});

test.each(["strategic-planning", "board-recommitment"])("direct %s form creates the correct lead and opens their saved questions", async product => {
  memberApi.post.mockResolvedValue({ data: { token: "member-token" } }); axios.post.mockResolvedValue({ data: { token: "private-lead-token" } });
  localStorage.setItem(`guidedLead:${product}`, "older-lead-token");
  const { node, cleanup } = await mount(<GuidedStartPage product={product} />);
  try {
    await type(node, 'input[autoComplete="name"]', "Alex Founder"); await type(node, 'input[type="email"]', "alex@example.org");
    await type(node, 'input[autoComplete="organization"]', "BrightPath"); await type(node, 'input[type="number"]', "5");
    await submit(node);
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining("/guided/lead"), { product, name: "Alex Founder", email: "alex@example.org", organization: "BrightPath", board_count: 5, origin_url: window.location.origin });
    expect(localStorage.getItem(`guidedLead:${product}`)).toBe("private-lead-token");
    expect(storeMemberToken).toHaveBeenCalledWith("member-token");
    expect(mockNavigate).toHaveBeenCalledWith(`/${product}/start?token=private-lead-token`);
  } finally { await cleanup(); }
});

test.each(["strategic-planning", "board-recommitment"])("existing %s token links resume questions without repeating the contact form", async product => {
  mockSearch = "?token=saved-lead-token";
  const { node, cleanup } = await mount(<GuidedStartPage product={product} />);
  try {
    expect(node.querySelector("form")).toBeNull();
    expect(node.querySelector('[data-testid="saved-questions"]').textContent).toBe(product);
    expect(memberApi.post).not.toHaveBeenCalled(); expect(axios.post).not.toHaveBeenCalled();
  } finally { await cleanup(); }
});
