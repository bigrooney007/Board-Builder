import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import { RecruitmentGameIntake } from "./RecruitmentGameIntake";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("axios", () => ({ get: jest.fn(), put: jest.fn() }));
jest.mock("./api", () => ({ memberApi: { get: jest.fn(), put: jest.fn() } }));
jest.mock("@/game/useGuidedNarration", () => ({ useGuidedNarration: () => ({ muted: false, toggle: jest.fn(), stop: jest.fn() }) }));
jest.mock("@/game/SpeakButton", () => ({ SpeakButton: () => null }));

test("public recruitment begins with its welcome, saves six distinct answers, then opens the existing campaign", async () => {
  axios.get.mockResolvedValue({ data: { desired_count: "3", answers: {} } });
  axios.put.mockResolvedValue({ data: {} });
  const onComplete = jest.fn();
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  try {
    await act(async () => root.render(<RecruitmentGameIntake publicToken="test-token" onComplete={onComplete} />));
    expect(node.querySelector('[data-testid="recruitment-questions-welcome"]')).toBeTruthy();
    await act(async () => node.querySelector('[data-testid="recruitment-start-six"]').click());
    for (let index = 1; index <= 6; index += 1) {
      expect(node.querySelector(`[data-testid="recruitment-question-${index}"]`)).toBeTruthy();
      expect(node.textContent).toContain(`QUESTION ${index} OF 6`);
      expect(node.querySelector('[data-testid="guided-audio-toggle"]')).toBeTruthy();
      await act(async () => {
        const input = node.querySelector(`[data-testid="recruitment-question-${index}-input"]`);
        Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set.call(input, `My answer ${index}`);
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
      await act(async () => [...node.querySelectorAll("button")].find((button) => button.textContent.includes(index === 6 ? "SAVE MY ANSWERS" : "NEXT QUESTION")).click());
      expect(axios.put).toHaveBeenLastCalledWith(expect.stringContaining("/recruit/free/test-token/answer"),
        expect.objectContaining({ question: index, text: `My answer ${index}` }));
    }
    expect(onComplete).toHaveBeenCalledTimes(1);
  } finally { await act(async () => root.unmount()); node.remove(); }
});
