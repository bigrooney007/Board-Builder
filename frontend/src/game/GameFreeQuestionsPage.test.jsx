import React, { act } from "react";
import { createRoot } from "react-dom/client";
import GameFreeQuestionsPage from "./GameFreeQuestionsPage";
import { FIVE_QUESTIONS, fiveQuestionText } from "./gameFiveQuestions";
import { memberApi } from "@/member/api";

global.IS_REACT_ACT_ENVIRONMENT = true;
const mockNavigate = jest.fn();
const mockMember = { email: "founder@example.org" };
jest.mock("react-router-dom", () => ({ useNavigate: () => mockNavigate }), { virtual: true });
jest.mock("@/member/MemberAuthContext", () => ({ useMemberAuth: () => ({ member: mockMember, loading: false }) }), { virtual: true });
jest.mock("@/member/api", () => ({ memberApi: { get: jest.fn(), put: jest.fn() } }), { virtual: true });
jest.mock("./gameShared", () => ({
  BfgShell: ({ children }) => <div>{children}</div>,
  money: (value) => `$${Number(value).toLocaleString("en-US")}`,
}));
jest.mock("./useGuidedNarration", () => ({ useGuidedNarration: () => ({ muted: false, toggle: jest.fn(), stop: jest.fn() }) }));
jest.mock("./SpeakButton", () => ({ SpeakButton: () => null }));

test("saves five original answers in sequence and opens upgrade with no review or AI step", async () => {
  window.scrollTo = jest.fn();
  const answers = ["  Local business owners  ", "At their trade network", "Invite them to visit", "Ask for $5,000", "Meet, listen, follow up, then ask"];
  memberApi.get.mockResolvedValue({ data: { answers: Object.fromEntries(answers.map((answer, index) => [String(index + 1), answer])), next_question: 1, goal_amount: 250000, organization_name: "Our Cause", complete: false } });
  memberApi.put.mockResolvedValue({ data: {} });
  const node = document.createElement("div"); document.body.appendChild(node); const root = createRoot(node);
  try {
    await act(async () => root.render(<GameFreeQuestionsPage />));
    expect(node.textContent).toContain("$250,000");
    expect(node.querySelector('[data-testid="bfg-free-welcome"]')).toBeTruthy();
    expect(node.querySelector('[data-testid="bfg-free-question"]')).toBeNull();
    await act(async () => node.querySelector('[data-testid="bfg-free-start"]').click());
    for (let index = 0; index < 5; index += 1) {
      expect(node.querySelector('[data-testid="bfg-free-question"]').textContent)
        .toBe(fiveQuestionText(index, answers[0]));
      expect(node.querySelector('[data-testid="bfg-free-answer"]').value).toBe(answers[index]);
      expect(node.querySelector('[data-testid="bfg-free-continue"]').disabled).toBe(false);
      await act(async () => node.querySelector('[data-testid="bfg-free-continue"]').click());
      expect(memberApi.put).toHaveBeenNthCalledWith(index + 1, `/game/free/${index + 1}`, { answer: answers[index] });
    }
    expect(memberApi.put).toHaveBeenCalledTimes(FIVE_QUESTIONS.length);
    expect(mockNavigate).toHaveBeenCalledWith("/game/upgrade");
  } finally { await act(async () => root.unmount()); node.remove(); }
});

test("foundation and company answers receive a natural second question", () => {
  expect(FIVE_QUESTIONS[0].title).toContain("why do you think they would give");
  expect(fiveQuestionText(1, "local foundations")).toContain("Where do they spend their time");
  expect(fiveQuestionText(1, "local foundations")).toContain("funders you just identified");
  expect(fiveQuestionText(1, "small businesses")).toContain("organizations you just identified");
});
