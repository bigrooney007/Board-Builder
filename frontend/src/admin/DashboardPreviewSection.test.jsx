import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import { storeMemberToken } from "@/member/api";
import { DashboardPreviewSection } from "./DashboardPreviewSection";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("axios", () => {
  const client = { post: jest.fn() };
  return { create: () => client, client };
});
jest.mock("@/adminPreview", () => ({ clearAdminPreview: jest.fn() }), { virtual: true });
jest.mock("@/member/api", () => ({ storeMemberToken: jest.fn() }), { virtual: true });

test.each(["fresh", "loaded"])("%s Admin tests replace the previous member session before opening", async (mode) => {
  jest.clearAllMocks();
  sessionStorage.setItem("operateAsUserId", "old-client");
  const original = window.location;
  Object.defineProperty(window, "location", { configurable: true, value: { assign: jest.fn() } });
  const url = mode === "fresh" ? "/purchase/success?session_id=test-paid-session" : "/app/board-recruitment";
  axios.client.post.mockResolvedValue({ data: { token: "new-test-member", start_url: mode === "fresh" ? url : undefined, dashboard_url: url } });
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  try {
    await act(async () => root.render(<DashboardPreviewSection />));
    const id = mode === "fresh" ? "start-fresh-recruitment" : "open-dashboard-recruitment";
    await act(async () => node.querySelector(`[data-testid="${id}"]`).click());
    expect(storeMemberToken).toHaveBeenCalledWith("new-test-member");
    expect(sessionStorage.getItem("operateAsUserId")).toBeNull();
    expect(window.location.assign).toHaveBeenCalledWith(url);
    expect(storeMemberToken.mock.invocationCallOrder[0]).toBeLessThan(window.location.assign.mock.invocationCallOrder[0]);
    expect(node.querySelector('[data-testid="dashboard-preview-error"]')).toBeNull();
  } finally {
    await act(async () => root.unmount()); node.remove();
    Object.defineProperty(window, "location", { configurable: true, value: original });
  }
});
