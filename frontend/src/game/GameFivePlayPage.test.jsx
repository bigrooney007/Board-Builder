import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import GameFivePlayPage from "./GameFivePlayPage";

global.IS_REACT_ACT_ENVIRONMENT = true;
const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({ useNavigate: () => mockNavigate, useParams: () => ({ token: "board-token" }) }), { virtual: true });
jest.mock("axios", () => ({ get: jest.fn(), put: jest.fn(), post: jest.fn() }));
jest.mock("./gameShared", () => ({ BfgShell: ({ children }) => <div>{children}</div>, money: (value) => `$${Number(value).toLocaleString()}` }));
jest.mock("./SpeakButton", () => ({ SpeakButton: () => null }));
jest.mock("./useGuidedNarration", () => ({ useGuidedNarration: () => ({ muted: false, toggle: jest.fn(), stop: jest.fn() }) }));

async function render() {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<GameFivePlayPage />));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}

test("the paid lead goes from saved five answers to personal participation, then returns to setup", async () => {
  mockNavigate.mockClear();
  const answers = { "1": "Community alumni", "2": "Local networks", "3": "Invite them to an event", "4": "Ask for $5,000", "5": "Meet, share impact, ask, and follow up" };
  axios.get.mockImplementation((url) => Promise.resolve({ data: url.endsWith("/ideas")
    ? { answers, next_question: 6, involvement: "", completed: false }
    : { member: { is_primary: true }, organization_name: "Our Cause", goal_display: "$250,000" } }));
  axios.post.mockResolvedValue({ data: { status: "completed" } });
  const { node, cleanup } = await render();
  try {
    expect(node.querySelector('[data-testid="bfg-board-welcome"]')).toBeNull();
    expect(node.querySelector('[data-testid="bfg-five-question"]')).toBeNull();
    expect(node.textContent).toContain("Meet, share impact, ask, and follow up");
    await act(async () => {
      const input = node.querySelector('[data-testid="bfg-five-involvement"]');
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
      setter.call(input, "I will make introductions and follow up.");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => node.querySelector('[data-testid="bfg-five-complete"]').click());
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining("/ideas/complete"), { involvement: "I will make introductions and follow up." });
    expect(mockNavigate).toHaveBeenCalledWith("/game/setup", { replace: true });
  } finally { await cleanup(); }
});

test("an invited board member sees the welcome and goal before question one", async () => {
  axios.get.mockImplementation((url) => Promise.resolve({ data: url.endsWith("/ideas")
    ? { answers: {}, next_question: 1, completed: false }
    : { member: { is_primary: false }, goal_display: "$250,000", organization_name: "Our Cause" } }));
  const { node, cleanup } = await render();
  try {
    expect(node.querySelector('[data-testid="bfg-board-welcome"]')).toBeTruthy();
    expect(node.textContent).toContain("$250,000");
    await act(async () => node.querySelector('[data-testid="bfg-board-start"]').click());
    expect(node.querySelector('[data-testid="bfg-five-question"]')).toBeTruthy();
    expect(node.textContent).toContain("QUESTION 1 OF 5");
  } finally { await cleanup(); }
});
