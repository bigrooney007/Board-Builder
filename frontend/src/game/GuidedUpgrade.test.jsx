import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import { memberApi } from "@/member/api";
import GameUpgradePage from "./GameUpgradePage";
import RecruitWalkthroughPage from "@/funnels/RecruitWalkthroughPage";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("react-router-dom", () => ({
  useNavigate: () => jest.fn(), useSearchParams: () => [new URLSearchParams("token=lead-token")],
}), { virtual: true });
jest.mock("@/member/MemberAuthContext", () => ({ useMemberAuth: () => ({ member: { email: "founder@example.org" }, loading: false }) }));
jest.mock("@/member/api", () => ({ memberApi: { get: jest.fn(), post: jest.fn() } }));
jest.mock("axios", () => ({ get: jest.fn(), post: jest.fn() }));
jest.mock("@/clean/platform", () => ({ trackPlatformEvent: jest.fn(), usePlatformVideo: () => null }));
jest.mock("@/clean/TrackedYouTubeVideo", () => ({ __esModule: true, default: ({ placeholder }) => <div>{placeholder}</div> }));
jest.mock("./gameShared", () => ({ BfgShell: ({ children }) => <div>{children}</div>, money: (value) => `$${Number(value).toLocaleString()}` }));

async function render(Page) {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<Page />));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}

test("fundraising payment page presents the goal, video space, clear price and post-payment order", async () => {
  memberApi.get.mockResolvedValue({ data: { complete: true, unlocked: false, goal_amount: 250000 } });
  const { node, cleanup } = await render(GameUpgradePage);
  try {
    expect(node.textContent).toContain("$250,000");
    expect(node.textContent).toContain("A short message from Rooney will appear here.");
    expect(node.querySelector('[data-testid="board-fundraising-game-supported-buy"]')).toBeTruthy();
    expect(node.textContent).toContain("$2,997");
    expect(node.querySelector('[data-testid="bfg-invite-board-cta"]').textContent).toContain("$497");
    expect(node.textContent).toContain("You invite your board after that setup.");
    expect(node.textContent).not.toContain("Watch Product Demonstration");
  } finally { await cleanup(); }
});

test("recruitment payment page presents its own video space and two clear checkout actions", async () => {
  axios.get.mockResolvedValue({ data: { token: "lead-token", lead_id: "lead-1", organization: "Bright Path",
    answers: { mission: "a", current_board: "b", desired_board_members: "c", board_type: "d", support_needs: "e", why_join: "f" } } });
  const { node, cleanup } = await render(RecruitWalkthroughPage);
  try {
    expect(node.textContent).toContain("A short message from Rooney will appear here.");
    expect(node.querySelectorAll('[data-testid^="recruit-checkout-button"]')).toHaveLength(2);
    expect(node.textContent).toContain("$497");
    expect(node.querySelector('[data-testid="recruitment-supported-buy"]')).toBeTruthy();
    expect(node.textContent).toContain("$2,997");
    expect(node.textContent).toContain("existing dashboard");
  } finally { await cleanup(); }
});
