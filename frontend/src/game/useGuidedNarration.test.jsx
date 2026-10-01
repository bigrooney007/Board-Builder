import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import GuidedAudioButton from "./GuidedAudioButton";
import { useGuidedNarration } from "./useGuidedNarration";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("axios", () => ({ get: jest.fn() }));

function Harness({ id, words }) {
  const narration = useGuidedNarration("fundraising-free", id, words);
  return <GuidedAudioButton narration={narration} />;
}

test("free game reads each screen and the speaker turns audio off and back on", async () => {
  sessionStorage.removeItem("bfg_narration_muted");
  axios.get.mockResolvedValue({ data: { clips: {} } });
  const speak = jest.fn();
  const cancel = jest.fn();
  Object.defineProperty(window, "speechSynthesis", { configurable: true, value: { speak, cancel } });
  Object.defineProperty(window, "SpeechSynthesisUtterance", { configurable: true, value: function Utterance(text) { this.text = text; } });
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  try {
    await act(async () => root.render(<Harness id="fundraising-free-welcome" words="Welcome" />));
    expect(speak).toHaveBeenCalledTimes(1);
    expect(speak.mock.calls[0][0].text).toBe("Welcome");
    await act(async () => node.querySelector("button").click());
    expect(sessionStorage.getItem("bfg_narration_muted")).toBe("1");
    await act(async () => root.render(<Harness id="fundraising-free-question-1" words="Question one" />));
    expect(speak).toHaveBeenCalledTimes(1);
    await act(async () => node.querySelector("button").click());
    expect(sessionStorage.getItem("bfg_narration_muted")).toBe("0");
    expect(speak.mock.calls.at(-1)[0].text).toBe("Question one");
  } finally {
    await act(async () => root.unmount()); node.remove();
    sessionStorage.removeItem("bfg_narration_muted");
  }
});
