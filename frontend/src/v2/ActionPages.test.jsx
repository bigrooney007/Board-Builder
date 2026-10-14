import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CampaignPage, ResourceEditorPage } from "./ResourcePages";
import { SharedMeetingPage } from "./GroupPages";
import { v2Api } from "./api";

jest.mock("./V2Shell", () => ({ __esModule: true, default: ({ children }) => <main>{children}</main>, AssistanceLink: () => <a href="https://calendly.com/boardbuilder/recruitboard">Book a Call</a> }));
jest.mock("./api", () => ({ v2Api: { get: jest.fn(), put: jest.fn(), post: jest.fn() }, resourceUrl: (path) => `/api/v2${path}`, errorMessage: (error) => error?.response?.data?.detail || "Request failed" }));

let node;
let root;
beforeEach(() => { jest.clearAllMocks(); global.IS_REACT_ACT_ENVIRONMENT = true; node = document.createElement("div"); document.body.appendChild(node); root = createRoot(node); });
afterEach(async () => { await act(async () => root.unmount()); node.remove(); });
const render = async (path, pattern, Component) => { await act(async () => { root.render(<MemoryRouter initialEntries={[path]}><Routes><Route path={pattern} element={<Component />} /></Routes></MemoryRouter>); }); };
const click = async (selector) => { await act(async () => node.querySelector(selector).click()); };
const input = async (selector, value) => { await act(async () => { const field = node.querySelector(selector); Object.getOwnPropertyDescriptor(Object.getPrototypeOf(field), "value").set.call(field, value); field.dispatchEvent(new Event("input", { bubbles: true })); }); };

test("resource edits increment the saved revision and approval uses that exact revision", async () => {
  let resource = { resource_id: "r1", title: "Recruitment announcement", key: "announcement", text: "Original wording", status: "approved", revision: 1, approved_revision: 1 };
  v2Api.get.mockImplementation(async () => ({ data: { ...resource } }));
  v2Api.put.mockImplementation(async (_, body) => { resource = { ...resource, text: body.text, revision: 2, approved_revision: null, status: "ready" }; return { data: resource }; });
  v2Api.post.mockImplementation(async () => { resource = { ...resource, approved_revision: 2, status: "approved" }; return { data: { ...resource, email: { status: "queued" } } }; });
  await render("/v2/resources/j1/r1", "/v2/resources/:journeyId/:resourceId", ResourceEditorPage);
  expect(node.querySelector('[data-testid="v2-resource-approve"]').disabled).toBe(true);
  await click('[data-testid="v2-resource-edit"]');
  await input('[data-testid="v2-resource-text"]', "Reviewed wording");
  await click('[data-testid="v2-resource-save"]');
  expect(v2Api.put).toHaveBeenCalledWith("/journeys/j1/resources/r1", { text: "Reviewed wording", expected_revision: 1 });
  await click('[data-testid="v2-resource-approve"]');
  expect(v2Api.post).toHaveBeenCalledWith("/journeys/j1/resources/r1/approve", { expected_revision: 2 });
  expect(node.textContent).toContain("Approved version 2");
  expect(node.querySelector('[data-testid="v2-resource-approve"]').disabled).toBe(true);
});

test("an approved resource whose email queue failed can retry without editing the approved text", async () => {
  const resource = { resource_id: "r1", title: "Approved guide", text: "Exact approved guide", status: "approved", revision: 3, approved_revision: 3, delivery_error: "Delivery needs a retry." };
  v2Api.get.mockResolvedValue({ data: resource });
  v2Api.post.mockResolvedValue({ data: { ...resource, delivery_error: "", email: { status: "queued" } } });
  await render("/v2/resources/j1/r1", "/v2/resources/:journeyId/:resourceId", ResourceEditorPage);
  expect(node.querySelector('[data-testid="v2-resource-approve"]').disabled).toBe(false);
  await click('[data-testid="v2-resource-approve"]');
  expect(v2Api.post).toHaveBeenCalledWith("/journeys/j1/resources/r1/approve", { expected_revision: 3 });
  expect(v2Api.put).not.toHaveBeenCalled();
});

test("campaign launch requires approved materials and the customer's explicit confirmation", async () => {
  const data = { status: "draft", revision: 7, preview: "Approved opportunity", required_resources: ["board_opportunity", "application_questions", "board_recruitment_job_post", "linkedin_post"].map((key) => ({ key, title: key, approved: true })), activities: [] };
  v2Api.get.mockResolvedValue({ data });
  v2Api.post.mockResolvedValue({ data: {} });
  await render("/v2/campaign/j1", "/v2/campaign/:journeyId", CampaignPage);
  expect(node.querySelector('[data-testid="v2-campaign-launch"]').disabled).toBe(true);
  await click('[data-testid="v2-campaign-confirm"]');
  await click('[data-testid="v2-campaign-launch"]');
  expect(v2Api.post).toHaveBeenCalledWith("/journeys/j1/campaign/launch", { confirmed: true, expected_revision: 7 });
});

test("partial campaign launch results retain failure information and offer a safe retry", async () => {
  v2Api.get.mockResolvedValue({ data: { status: "active", required_resources: [], activities: { application: { status: "succeeded", title: "Application form" }, marketplace: { status: "succeeded", title: "Marketplace" }, network: { status: "failed", title: "Applicant network", error: "Provider unavailable" } } } });
  v2Api.post.mockResolvedValue({ data: {} });
  await render("/v2/campaign/j1", "/v2/campaign/:journeyId", CampaignPage);
  expect(node.textContent).toContain("Provider unavailable");
  const retry = [...node.querySelectorAll("button")].find((button) => button.textContent === "Retry unfinished launch activities");
  await act(async () => retry.click());
  expect(v2Api.post).toHaveBeenCalledWith("/journeys/j1/campaign/retry", {});
});

test("participant meeting links show suggestions and decisions without facilitator actions", async () => {
  v2Api.get.mockResolvedValue({ data: { journey: { product: "strategic-planning" }, sections: [{ key: "mission", title: "Mission", ideas: [{ source_id: "s1:mission", name: "Test Member", content: "Protect local habitats" }] }], decisions: [], commitments: [], participants: [] } });
  await render("/v2/meeting/secret", "/v2/meeting/:token", SharedMeetingPage);
  expect(node.textContent).toContain("Protect local habitats");
  expect(node.textContent).not.toContain("Adopt this idea");
  expect(node.textContent).not.toContain("Approve, save and email");
  expect(node.querySelectorAll("input")).toHaveLength(0);
  expect(v2Api.post).not.toHaveBeenCalled();
});
