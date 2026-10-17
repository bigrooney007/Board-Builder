import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import GuidedPrepaymentQuestionsPage from "./GuidedPrepaymentQuestionsPage";

global.IS_REACT_ACT_ENVIRONMENT = true;
const mockNavigate = jest.fn();
let mockToken = "private-lead-token";
jest.mock("react-router-dom", () => ({ useNavigate: () => mockNavigate,
  useSearchParams: () => [new URLSearchParams(`token=${mockToken}`)] }), { virtual: true });
jest.mock("axios", () => ({ get: jest.fn(), put: jest.fn() }));
jest.mock("@/game/gameShared", () => ({ BfgShell: ({ children }) => <div>{children}</div> }));
jest.mock("@/game/SpeakButton", () => ({ __esModule: true, default: () => <button type="button">SPEAK MY ANSWER</button> }));

async function mount(product) {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<GuidedPrepaymentQuestionsPage product={product} />));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}

beforeEach(() => { mockNavigate.mockReset(); axios.get.mockReset(); axios.put.mockReset(); localStorage.clear(); window.scrollTo = jest.fn(); });

test("recommitment resumes at the missing fourth answer and saves it before the sales video", async () => {
  axios.get.mockResolvedValue({ data: { product: "board-recommitment", organization: "BrightPath",
    prepayment_answers: { mission: "Youth opportunity", why_recommit: "Our board needs to step up",
      board_help_accomplish: "Build partnerships" } } });
  axios.put.mockResolvedValue({ data: { complete: true } });
  const { node, cleanup } = await mount("board-recommitment");
  try {
    expect(node.textContent).toContain("4 OF 4");
    expect(node.textContent).toContain("By when do you need the board to recommit");
    await act(async () => {
      const input = node.querySelector('input[type="date"]');
      const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
      set.call(input, "2026-11-15"); input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await act(async () => node.querySelector(".guided-preflow-navigation .bfg-btn-primary").click());
    expect(axios.put).toHaveBeenCalledWith(expect.stringContaining("/guided/context/private-lead-token/answers"),
      expect.objectContaining({ answers: expect.objectContaining({ need_by: "2026-11-15", mission: "Youth opportunity" }) }));
    expect(mockNavigate).toHaveBeenCalledWith("/board-recommitment/video?token=private-lead-token");
  } finally { await cleanup(); }
});

test("strategic planning resumes on a separate program page and preserves its other sections", async () => {
  axios.get.mockResolvedValue({ data: { product: "strategic-planning", prepayment_answers: {
    mission: "Youth opportunity", goals: "Reach more young people", objectives: "Open two centers",
    program_details: [{ name: "Mentoring", description: "Mentors support young people", present_work: "Weekly sessions" }],
  } } });
  axios.put.mockResolvedValue({ data: { complete: false } });
  const { node, cleanup } = await mount("strategic-planning");
  try {
    expect(node.textContent).toContain("Team and leadership");
    await act(async () => node.querySelector(".guided-preflow-navigation .bfg-btn-ghost").click());
    expect(node.textContent).toContain("PROGRAM 1");
    expect(node.querySelector('input[placeholder="What do you call this program?"]').value).toBe("Mentoring");
    await act(async () => node.querySelector(".guided-preflow-program-actions .bfg-btn").click());
    expect(node.textContent).toContain("PROGRAM 2");
    expect(axios.put).toHaveBeenCalledWith(expect.stringContaining("/guided/context/private-lead-token/answers"),
      expect.objectContaining({ answers: expect.objectContaining({ program_details: [expect.objectContaining({ name: "Mentoring" })] }) }));
  } finally { await cleanup(); }
});
