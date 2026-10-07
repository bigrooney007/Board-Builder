import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import DashboardWalkthroughVideo from "./DashboardWalkthroughVideo";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("axios", () => ({ get: jest.fn() }));

test.each([
  ["recruitment", "recruitment_dashboard", "recruitment_welcome"],
  ["board-fundraising-game", "game_dashboard", "game_welcome"],
  ["strategic-planning", "strategic_planning_dashboard", "strategic_planning_welcome"],
  ["board-recommitment", "board_recommitment_dashboard", "board_recommitment_welcome"],
])("%s walkthrough uses its onboarding link, then refreshes to its separately saved dashboard video", async (flow, key, fallbackKey) => {
  let rows = [{ key: fallbackKey, youtube_id: "AbCdEf12345" }, { key, youtube_id: "" }];
  axios.get.mockImplementation(async () => ({ data: { videos: rows } }));
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  try {
    await act(async () => root.render(<DashboardWalkthroughVideo flow={flow} />));
    expect(node.querySelector("a").href).toBe("https://www.youtube.com/watch?v=AbCdEf12345");
    expect(node.querySelector("a").target).toBe("_blank");
    rows = [{ key: fallbackKey, youtube_id: "AbCdEf12345" }, { key, youtube_id: "ZyXwVu54321" }];
    await act(async () => window.dispatchEvent(new Event("platform-videos-changed")));
    expect(node.querySelector("a").href).toBe("https://www.youtube.com/watch?v=ZyXwVu54321");
    rows = [{ key: fallbackKey, youtube_id: "AbCdEf12345" }, { key, youtube_id: "" }];
    await act(async () => window.dispatchEvent(new Event("focus")));
    expect(node.querySelector("a").href).toBe("https://www.youtube.com/watch?v=AbCdEf12345");
    rows = [];
    await act(async () => window.dispatchEvent(new Event("focus")));
    expect(node.querySelector("a")).toBeNull();
    expect(node.textContent).toContain("Dashboard video coming soon");
  } finally { await act(async () => root.unmount()); node.remove(); }
});
