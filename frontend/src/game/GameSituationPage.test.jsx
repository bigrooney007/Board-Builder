import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import { memberApi } from "@/member/api";
import GameSituationPage from "./GameSituationPage";

global.IS_REACT_ACT_ENVIRONMENT = true;
const mockNavigate = jest.fn();
const mockMember = { email: "lead@example.org" };
const mockSearch = { value: "" };
jest.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate, useLocation: () => ({ search: mockSearch.value }),
}), { virtual: true });
jest.mock("@/member/MemberAuthContext", () => ({
  useMemberAuth: () => ({ member: mockMember, loading: false }),
}), { virtual: true });
jest.mock("@/member/api", () => ({ memberApi: { get: jest.fn(), put: jest.fn(), post: jest.fn() } }), { virtual: true });
jest.mock("axios", () => ({ get: jest.fn() }));
jest.mock("./gameShared", () => ({ BfgShell: ({ children }) => <div>{children}</div> }));
jest.mock("./GameNightSection", () => ({ GameNightSection: ({ onSaved }) => <button data-testid="save-existing-night" onClick={() => onSaved({ meeting_date: "2026-10-10", funding_deadline: "2026-12-31" })}>Save meeting and deadline</button> }));
jest.mock("./NarrationControl", () => ({ NarrationControl: () => null, isNarrationMuted: () => true }));
jest.mock("./SpeakButton", () => ({ SpeakButton: () => null }));

test("meeting, separate relevant funder pages and resources precede the lead's participation and invitations", async () => {
  window.scrollTo = jest.fn();
  const response = { game_version: 5, original_answers: { "1": "People", "2": "Network", "3": "Story", "4": "Ask", "5": "Meet and follow up" }, completed: false };
  const capacity = { team: { who_handles: "Staff", board_involvement: "Introductions" },
    technology: { tools: "Spreadsheet", tech_working: "Needs follow-up" }, materials: { materials: "Case for support" } };
  memberApi.get.mockImplementation((path) => Promise.resolve({ data: path === "/game/situation"
    ? { sections: capacity, current_step: 0, completed: false }
    : path === "/game/night" ? { night: {} } : { branding: {} } }));
  memberApi.post.mockResolvedValueOnce({ data: { token: "lead-token" } }).mockResolvedValue({ data: { status: "complete" } });
  memberApi.put.mockResolvedValue({ data: { status: "saved" } });
  axios.get.mockImplementation((url) => Promise.resolve({ data: url.includes("audience-response") ? { response } : { clips: {} } }));
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  try {
    await act(async () => root.render(<GameSituationPage />));
    expect(node.querySelector('[data-testid="bfg-setup-meeting"]')).toBeTruthy();
    expect(node.querySelector('[data-testid="bfg-current-fundraising"]')).toBeNull();
    await act(async () => node.querySelector('[data-testid="save-existing-night"]').click());
    await act(async () => [...node.querySelectorAll("button")].find((item) => item.textContent.includes("CONTINUE TO MY PRESENT FUNDRAISING")).click());
    for (const title of ["Your Present Individual Donors", "Your Present Business Sponsors Or Partners", "Your Present Grantors"]) {
      expect(node.textContent).toContain(title);
      await act(async () => [...node.querySelectorAll("button")].find((item) => item.textContent.includes("WE DO NOT HAVE THESE SUPPORTERS YET")).click());
    }
    const savedReality = memberApi.put.mock.calls[2][1].sections.current_reality;
    expect([savedReality.individuals_status, savedReality.businesses_status, savedReality.grantors_status]).toEqual(["none", "none", "none"]);
    expect(savedReality.current_grantor_profile).toBe("");
    expect(node.querySelector('[data-testid="bfg-current-capacity"]')).toBeTruthy();
    expect(memberApi.post).not.toHaveBeenCalledWith("/game/situation/complete");
    await act(async () => [...node.querySelectorAll("button")].find((item) => item.textContent.includes("CONTINUE TO MY PARTICIPATION")).click());
    expect(memberApi.post).toHaveBeenCalledWith("/game/situation/complete");
    expect(node.querySelector('[data-testid="bfg-setup-play-first"]')).toBeTruthy();
    expect(memberApi.put).toHaveBeenCalledWith("/game/situation", expect.objectContaining({ current_step: 4 }));
    await act(async () => [...node.querySelectorAll("button")].find((item) => item.textContent.includes("CONTINUE TO MY PARTICIPATION")).click());
    expect(mockNavigate).toHaveBeenCalledWith("/play/lead-token");
  } finally { await act(async () => root.unmount()); node.remove(); }
});

test("only asks detailed funder questions after the lead confirms an existing supporter category", async () => {
  mockNavigate.mockClear(); memberApi.get.mockReset(); memberApi.post.mockReset(); axios.get.mockReset();
  memberApi.get.mockImplementation((path) => Promise.resolve({ data: path === "/game/situation"
    ? { sections: {}, current_step: 0, completed: false }
    : path === "/game/night" ? { night: { meeting_date: "2026-10-10", start_time: "12:00", funding_deadline: "2026-12-31" } } : { branding: {} } }));
  memberApi.post.mockResolvedValue({ data: { token: "lead-token" } });
  axios.get.mockImplementation((url) => Promise.resolve({ data: url.includes("audience-response")
    ? { response: { game_version: 5, completed: false } } : { clips: {} } }));
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  try {
    await act(async () => root.render(<GameSituationPage />));
    expect(node.textContent).toContain("Your Present Individual Donors");
    expect(node.textContent).not.toContain("Why do you think these donors choose to give");
    expect(node.querySelectorAll("textarea")).toHaveLength(0);
    await act(async () => [...node.querySelectorAll("button")].find((item) => item.textContent.includes("YES, WE HAVE THESE SUPPORTERS")).click());
    expect(node.textContent).toContain("Why do you think these donors choose to give");
    expect(node.textContent).toContain("What are you hoping to raise from individual donors now");
  } finally { await act(async () => root.unmount()); node.remove(); }
});

test("reviewing a completed game opens the separate present-reality pages without losing progress", async () => {
  mockSearch.value = "?review=1";
  mockNavigate.mockClear(); memberApi.get.mockReset(); memberApi.post.mockReset(); axios.get.mockReset();
  memberApi.get.mockImplementation((path) => Promise.resolve({ data: path === "/game/situation"
    ? { sections: { current_reality: { reviewed: "yes" } }, current_step: 3, completed: true }
    : path === "/game/night" ? { night: { meeting_date: "2026-10-10", start_time: "12:00", funding_deadline: "2026-12-31" } } : { branding: {} } }));
  memberApi.post.mockResolvedValue({ data: { token: "lead-token" } });
  axios.get.mockImplementation((url) => Promise.resolve({ data: url.includes("audience-response")
    ? { response: { game_version: 5, completed: true } } : { clips: {} } }));
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  try {
    await act(async () => root.render(<GameSituationPage />));
    expect(node.querySelector('[data-testid="bfg-current-fundraising"]')).toBeTruthy();
    expect(node.textContent).toContain("Your Present Individual Donors");
    expect(mockNavigate).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); node.remove(); mockSearch.value = ""; }
});
