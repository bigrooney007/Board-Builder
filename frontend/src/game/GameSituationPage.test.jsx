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
jest.mock("./GameNightSection", () => ({ GameNightSection: ({ onSaved }) => <button data-testid="save-existing-night" onClick={() => onSaved({ meeting_date: "2026-10-20", start_time: "12:00", funding_deadline: "2026-12-31" })}>Save meeting and deadline</button> }));
jest.mock("./NarrationControl", () => ({ NarrationControl: () => null, isNarrationMuted: () => true }));
jest.mock("./SpeakButton", () => ({ SpeakButton: () => null }));

const noFunders = { individuals_status: "none", businesses_status: "none", grantors_status: "none", reviewed: "yes", setup_version: "present_funders_v3" };

beforeEach(() => {
  jest.clearAllMocks();
  mockSearch.value = "";
  window.scrollTo = jest.fn();
  memberApi.put.mockResolvedValue({ data: { status: "saved" } });
  memberApi.post.mockImplementation((path) => Promise.resolve({ data: path === "/game/self-play" ? { token: "lead-token" } : { status: "complete" } }));
});

function savedState(situation = { sections: {}, current_step: 0, completed: false }, participated = false, night = {}) {
  memberApi.get.mockImplementation((path) => Promise.resolve({ data: path === "/game/situation" ? situation : { night } }));
  axios.get.mockImplementation((url) => Promise.resolve({ data: url.includes("audience-response")
    ? { response: { game_version: 5, completed: participated } } : { clips: {} } }));
}

async function render() {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<GameSituationPage />));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}

async function click(node, text) {
  await act(async () => [...node.querySelectorAll("button")].find((item) => item.textContent === text).click());
}

async function fill(input, value) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

test("skipping absent funders goes directly to participation without a resources form", async () => {
  savedState({ sections: { current_reality: { current_individual_donor_profile: "Previously saved donors" }, team: { who_handles: "Staff" } }, current_step: 0, completed: false });
  const { node, cleanup } = await render();
  try {
    for (const title of ["Your Present Individual Donors", "Your Present Business Sponsors Or Partners", "Your Present Grantors"]) {
      expect(node.textContent).toContain(title);
      expect(node.querySelector('[data-testid="bfg-current-capacity"]')).toBeNull();
      expect(node.querySelector('[data-testid="bfg-setup-meeting"]')).toBeNull();
      await click(node, "WE DO NOT HAVE THESE SUPPORTERS YET");
    }
    const last = memberApi.put.mock.calls[2][1];
    expect(last.current_step).toBe(3);
    expect(last.sections.current_reality).toMatchObject(noFunders);
    expect(last.sections.current_reality.current_individual_donor_profile).toBe("Previously saved donors");
    expect(Object.keys(last.sections)).toEqual(["current_reality"]);
    expect(memberApi.post).not.toHaveBeenCalledWith("/game/situation/complete");
    expect(mockNavigate).toHaveBeenCalledWith("/play/lead-token");
  } finally { await cleanup(); }
});

test("each group has four questions about who and why, where, process and ask", async () => {
  savedState();
  const { node, cleanup } = await render();
  try {
    const prefixes = ["individual_donor", "business", "grantor"];
    for (let group = 0; group < 3; group++) {
      expect(node.querySelectorAll("textarea")).toHaveLength(0);
      await click(node, "YES, WE HAVE THESE SUPPORTERS");
      const fields = [...node.querySelectorAll("textarea")];
      expect(fields).toHaveLength(4);
      expect(node.textContent).toMatch(/why/i);
      expect(node.textContent).toMatch(/Where/);
      expect(node.textContent).toMatch(/process|from first contact/);
      expect(node.textContent).toMatch(/how much/);
      for (let field = 0; field < 4; field++) await fill(fields[field], `${prefixes[group]} answer ${field}`);
      await click(node, group === 2 ? "CONTINUE TO MY PARTICIPATION" : "CONTINUE");
    }
    const last = memberApi.put.mock.calls[2][1].sections.current_reality;
    prefixes.forEach((prefix) => ["profile", "where", "process", "support"].forEach((field, i) => {
      expect(last[`current_${prefix}_${field}`]).toBe(`${prefix} answer ${i}`);
    }));
    expect(mockNavigate).toHaveBeenCalledWith("/play/lead-token");
  } finally { await cleanup(); }
});

test("incomplete answers stay on their four questions without requesting a meeting", async () => {
  savedState();
  const { node, cleanup } = await render();
  try {
    await click(node, "YES, WE HAVE THESE SUPPORTERS");
    await fill(node.querySelector("textarea"), "Our present donors support youth opportunity.");
    await click(node, "CONTINUE");
    expect(node.querySelector('[role="alert"]').textContent).toContain("Answer the four questions");
    expect(node.querySelectorAll("textarea")).toHaveLength(4);
    expect(memberApi.put).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  } finally { await cleanup(); }
});

test("customers at the old resources step resume at participation with motivations preserved", async () => {
  const reality = { reviewed: "yes", setup_version: "post_payment_v2" };
  for (const [group, prefix] of [["individuals", "individual_donor"], ["businesses", "business"], ["grantors", "grantor"]]) {
    reality[group + "_status"] = "current";
    for (const field of ["profile", "where", "process", "support"]) reality[`current_${prefix}_${field}`] = `${prefix} ${field}`;
  }
  reality.current_individual_donor_motivation = "They trust the mission";
  savedState({ sections: { current_reality: reality }, current_step: 4, completed: false });
  const { cleanup } = await render();
  try {
    expect(memberApi.put).toHaveBeenCalledWith("/game/situation", expect.objectContaining({ current_step: 3 }));
    const migrated = memberApi.put.mock.calls[0][1].sections.current_reality;
    expect(migrated.current_individual_donor_profile).toContain("They trust the mission");
    expect(migrated.setup_version).toBe("present_funders_v3");
    expect(mockNavigate).toHaveBeenCalledWith("/play/lead-token", { replace: true });
  } finally { await cleanup(); }
});

test("meeting follows saved participation and completes before invitations", async () => {
  savedState({ sections: { current_reality: noFunders }, current_step: 3, completed: false }, true);
  const { node, cleanup } = await render();
  try {
    expect(node.querySelector('[data-testid="bfg-setup-meeting"]')).toBeTruthy();
    expect(node.textContent).toContain("Your participation answer is saved");
    expect(node.textContent).not.toContain("INVITE MY BOARD MEMBERS");
    await act(async () => node.querySelector('[data-testid="save-existing-night"]').click());
    await click(node, "INVITE MY BOARD MEMBERS");
    expect(memberApi.post).toHaveBeenCalledWith("/game/situation/complete");
    expect(mockNavigate).toHaveBeenCalledWith("/game/dashboard#bfg-board-members-section");
  } finally { await cleanup(); }
});

test("reviewing a completed game opens its reality without redirecting or losing progress", async () => {
  mockSearch.value = "?review=1";
  savedState({ sections: { current_reality: noFunders }, current_step: 3, completed: true }, true,
    { meeting_date: "2026-10-20", start_time: "12:00", funding_deadline: "2026-12-31" });
  const { node, cleanup } = await render();
  try {
    expect(node.querySelector('[data-testid="bfg-current-fundraising"]')).toBeTruthy();
    expect(node.textContent).toContain("Your Present Individual Donors");
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(memberApi.put).not.toHaveBeenCalled();
  } finally { await cleanup(); }
});
