import React, { act } from "react";
import { createRoot } from "react-dom/client";
import GameHomePage from "./GameHomePage";
import GameDemonstrationPage from "./GameDemonstrationPage";
import { memberApi } from "@/member/api";

global.IS_REACT_ACT_ENVIRONMENT = true;
const mockContent = {
  headline: "Get Your Board Working With You To Raise Money",
  subheadline: "Build your fundraising strategy together.",
  hero_explanation: "Your board helps build the plan.",
  goal_label: "How much do you want to raise?", goal_placeholder: "500,000",
  cta_label: "START MY BOARD FUNDRAISING GAME", start_supporting: "Begin with your own thinking.",
  agent_intro: "Answer five questions", agent_questions: ["Who can fund the work?"], agent_followup: "Invite your board.",
  intro_heading: "Fundraising Is Not A One-Person Job", intro_paragraphs: ["Build it together."],
  stages_label: "PROCESS", stages_heading: "How it works", stages: [], stages_cta_label: "START",
  outcomes_label: "OUTCOMES", outcomes_heading: "What you get", outcomes: [],
  testimonials_heading: "Testimonials", faqs_label: "FAQ", faqs_heading: "Questions", faqs: [],
  closing_heading: "Ready?", closing_text: "Begin below.", closing_cta_label: "START",
};
jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
  useNavigate: () => jest.fn(), useSearchParams: () => [new URLSearchParams()],
}), { virtual: true });
jest.mock("@/member/MemberAuthContext", () => ({ useMemberAuth: () => ({ member: null, loading: false }) }), { virtual: true });
jest.mock("@/member/api", () => ({ memberApi: { get: jest.fn(), post: jest.fn(), put: jest.fn() }, clearMemberToken: jest.fn(), storeMemberToken: jest.fn() }), { virtual: true });
jest.mock("@/clean/platform", () => ({ useHomepageContent: (_key, content) => content, trackPlatformEvent: jest.fn() }), { virtual: true });
jest.mock("@/seo", () => ({ useLandingPageMeta: jest.fn() }), { virtual: true });
jest.mock("@/hooks/useFlowVideos", () => ({ useFlowVideo: () => null }), { virtual: true });
jest.mock("./gameShared", () => ({
  BfgShell: ({ children }) => <div>{children}</div>,
  useGameContent: () => mockContent,
  money: (value) => `$${Number(value).toLocaleString("en-US")}`,
  GameVideo: ({ video }) => <div data-testid="rendered-video">{video.youtube_id}</div>,
}));
jest.mock("@/components/TestimonialCarousel", () => ({ TestimonialCarousel: () => null }), { virtual: true });

async function renderPage(Page) {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<Page />));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}

test("fundraising sales page keeps its minimal hero and links to the separate opening form", async () => {
  const { node, cleanup } = await renderPage(GameHomePage);
  try {
    const hero = node.querySelector(".bfg-hero");
    expect([...hero.querySelector(".bfg-hero-inner").children].map((element) => element.tagName)).toEqual(["H1", "P", "A"]);
    expect(hero.querySelector("[data-testid='bfg-goal-box']")).toBeNull();
    expect(hero.querySelector("[data-testid='bfg-hero-cta']").getAttribute("href")).toBe("/board-fundraising/start");
    expect(node.querySelector("input, textarea, select, form")).toBeNull();
    expect([...node.querySelectorAll(".bfg-btn-primary")].every(link => link.getAttribute("href") === "/board-fundraising/start")).toBe(true);
  } finally { await cleanup(); }
});

test("demo shows the saved production video fallback and returns a new visitor to the free game", async () => {
  const { node, cleanup } = await renderPage(GameDemonstrationPage);
  try {
    expect(node.querySelector("[data-testid='rendered-video']").textContent).toBe("rsf_QZfEId8");
    expect(node.querySelector("[data-testid='bfg-demo-continue']").getAttribute("href"))
      .toBe("/board-fundraising/start");
    expect(node.textContent).not.toContain("CHOOSE HOW YOU WOULD LIKE TO MOVE FORWARD");
    expect(memberApi.post).not.toHaveBeenCalled();
  } finally { await cleanup(); }
});
