import React, { act } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import { memberApi } from "../api";
import { AutomatedReferenceChecks, InterviewsWorkspace, Module4Applicants, OnboardingPreparation, OnboardingSessionWorkspace } from "./ApplicantModules";
import { Module3Launch } from "./WorkspaceModules";
import { ApplicationForm } from "../../public/OpportunityPages";
import { PlatformVideosSection } from "../../admin/PlatformVideosSection";
import { RecruitmentGameIntake } from "../RecruitmentGameIntake";

jest.mock("../api", () => ({ memberApi: { get: jest.fn(), post: jest.fn(), put: jest.fn(), patch: jest.fn() } }));
jest.mock("axios", () => {
  const client = { get: jest.fn(), post: jest.fn(), put: jest.fn() };
  return { __esModule: true, default: { ...client, create: () => client } };
});
jest.mock("react-router-dom", () => ({ Link: ({ children }) => <span>{children}</span>, useNavigate: () => jest.fn(), useParams: () => ({}) }), { virtual: true });
jest.mock("@/funnels/FunnelLayout", () => ({ FunnelLayout: ({ children }) => children }), { virtual: true });
jest.mock("@/admin/DashboardSectionAudioAdmin", () => () => null, { virtual: true });

let root, container, applications, materials, session, videoId;
const resource = (type, applicationId = "", status = "Approved") => ({ type, application_id: applicationId, material_id: type + applicationId, status, current_version: 1, versions: [{ version: 1, display_text: "Prepared " + type, created_at: "2026-09-27T12:00:00Z" }] });
const byId = (id) => container.querySelector(`[data-testid="${id}"]`);
const render = async (element) => { await act(async () => { root.render(element); }); };
const click = async (element) => { expect(element).not.toBeNull(); await act(async () => { element.click(); }); };
const change = async (element, value) => {
  await act(async () => {
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
};

beforeEach(() => {
  jest.clearAllMocks();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
  window.URL.createObjectURL = jest.fn(() => "blob:test-cv"); window.URL.revokeObjectURL = jest.fn();
  applications = [{ application_id: "alex", profile_snapshot: { full_name: "Alex Candidate", profession: "Director", location: "London" }, applicant_email: "alex@example.org", status: "Applied", cv_filename: "alex.pdf", journey: {}, answers: { why_interested: "I can help build partnerships" } }];
  materials = [];
  session = { date: "2026-10-15", time: "14:30", timezone: "Europe/London", format: "Virtual", link: "https://example.org/meeting" };
  videoId = "tESJV4jJVWs";
  memberApi.get.mockImplementation(async (path) => {
    if (path === "/workspace/applications") return { data: { applications: applications.map((app) => ({ ...app, journey: { ...app.journey } })), statuses: [] } };
    if (path === "/workspace/applications/alex") return { data: { application: applications[0] } };
    if (path.endsWith("/cv")) return { data: new Blob(["CV"], { type: "application/pdf" }) };
    if (path === "/workspace/materials") return { data: { materials: [...materials] } };
    if (path === "/workspace/onboarding-session") return { data: { session: { ...session } } };
    if (path === "/workspace/branding") return { data: { branding: {} } };
    if (path === "/workspace/opportunity") return { data: { opportunity: { slug: "community", status: "Draft", application_saved: true }, readiness: {}, core_questions: [], preparation: {} } };
    return { data: {} };
  });
  memberApi.post.mockImplementation(async (path, payload) => {
    if (path === "/workspace/generate") {
      materials.push(resource(payload.type, payload.application_id || "", "Generated"));
      const flags = { interview_invitation: "interview_invitation_generated", interview_guide: "interview_guide_generated", conditional_offer: "conditional_offer_generated", unconditional_offer: "unconditional_offer_generated" };
      if (flags[payload.type]) applications[0].journey[flags[payload.type]] = true;
    }
    return { data: {} };
  });
  memberApi.put.mockImplementation(async (path, payload) => {
    if (path === "/workspace/onboarding-session") session = { ...payload };
    return { data: { session } };
  });
  axios.get.mockImplementation(async (path) => ({ data: path.includes("recruitment-section-videos") ? { videos: [{ key: "launch", url: `https://youtu.be/${videoId}`, youtube_id: videoId }] } : { videos: [], assets: [] } }));
  axios.put.mockImplementation(async (path, payload) => { videoId = payload.url.split("/").pop(); return { data: { status: "saved" } }; });
});

afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

test("applicant has four choices, opens one item, and moves into Interviews without reload", async () => {
  await render(<><Module4Applicants /><InterviewsWorkspace /></>);
  const row = byId("applicant-row-alex");
  expect(row.querySelectorAll("button").length).toBe(4);
  await click(byId("view-full-application-alex"));
  expect(byId("application-answers").textContent).toContain("I can help build partnerships");
  await click(byId("interview-invite-alex"));
  expect(byId("application-answers")).toBeNull();
  expect(byId("material-interview_invitation-display").textContent).toContain("Prepared interview_invitation");
  expect(byId("recruitment-interviews-workspace").textContent).toContain("Alex Candidate");
  expect(memberApi.post.mock.calls).toEqual([["/workspace/generate", { type: "interview_invitation", application_id: "alex" }]]);
  await click(byId("view-cv-alex"));
  expect(byId("candidate-email-interview_invitation")).toBeNull();
  expect(byId("applicant-cv-preview").querySelector("iframe").src).toBe("blob:test-cv");
  await click(byId("interview-invite-alex"));
  expect(memberApi.post).toHaveBeenCalledTimes(1);
});

test("reference choices generate only the selected reply email", async () => {
  applications[0].journey.interview_guide_generated = true;
  await render(<AutomatedReferenceChecks />);
  expect(byId("reference-candidate-alex").querySelectorAll("button").length).toBe(2);
  await click(byId("ask-references-alex"));
  expect(byId("material-candidate_referee_request-display")).not.toBeNull();
  await click(byId("confirm-references-alex"));
  expect(byId("candidate-email-candidate_referee_request")).toBeNull();
  expect(byId("material-reference_request_email-display")).not.toBeNull();
  expect(memberApi.post.mock.calls.map(([path, payload]) => [path, payload.type])).toEqual([
    ["/workspace/generate", "candidate_referee_request"], ["/workspace/generate", "reference_request_email"],
  ]);
  expect(container.textContent).not.toContain("Send Email");
});

test("onboarding offers require saved details and generation unlocks the mounted session", async () => {
  applications[0].journey.interview_guide_generated = true;
  materials = ["organization_overview", "board_manual", "board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"].map((type) => resource(type));
  await render(<><OnboardingPreparation /><OnboardingSessionWorkspace /></>);
  await click(Array.from(byId("appointment-email-stage").querySelectorAll("button")).find((button) => button.textContent === "Alex Candidate"));
  expect(byId("generate-conditional_offer")).not.toBeNull();
  expect(byId("generate-unconditional_offer")).not.toBeNull();
  const start = () => Array.from(byId("onboarding-session-workspace").querySelectorAll("button")).find((button) => button.textContent === "START THE ONBOARDING SESSION");
  expect(start().disabled).toBe(true);
  await change(byId("session-date"), "2026-10-16");
  expect(byId("appointment-offer-panel")).toBeNull();
  await click(byId("save-session-button"));
  expect(byId("generate-conditional_offer")).not.toBeNull();
  await click(byId("generate-conditional_offer"));
  expect(start().disabled).toBe(false);
  await click(byId("open-onboarding-organization_overview"));
  expect(byId("material-organization_overview")).not.toBeNull();
  await click(byId("open-onboarding-board_manual"));
  expect(byId("material-organization_overview")).toBeNull();
  expect(byId("material-board_manual")).not.toBeNull();
});

test("public application is one page and accepts an optional CV", async () => {
  const answers = { full_name: "Alex", email: "alex@example.org", location: "London", profession: "Director", why_interested: "Partnerships" };
  const questions = Object.keys(answers).map((id) => ({ id, label: id, required: true, type: id === "email" ? "email" : id === "why_interested" ? "textarea" : "text" }));
  const submit = jest.fn().mockResolvedValue(undefined);
  await render(<ApplicationForm questions={questions} initialAnswers={answers} submitLabel="Apply" onSubmit={submit} />);
  expect(container.querySelectorAll("input:not([type=file]), textarea").length).toBe(5);
  expect(container.querySelector("input[type=file]").required).toBe(false);
  await click(byId("application-submit"));
  expect(submit).toHaveBeenCalledWith(answers, null);
});

test("admin can replace the campaign video and the dashboard link refreshes", async () => {
  await render(<><PlatformVideosSection /><Module3Launch mode="campaign" /></>);
  expect(byId("launch-recruitment-video").href).toContain("tESJV4jJVWs");
  await change(byId("recruitment-launch-video-url"), "https://youtu.be/AbCdEf12345");
  await click(byId("save-recruitment-launch-video"));
  expect(axios.put).toHaveBeenCalledWith("/admin/platform/recruitment-section-videos/launch", { url: "https://youtu.be/AbCdEf12345" });
  expect(byId("launch-recruitment-video").href).toContain("AbCdEf12345");
});

test("the public six-question assessment resumes and saves each answer before checkout", async () => {
  const saved = { mission: "We serve young people" };
  axios.get.mockImplementation(async (path) => path.includes("/recruit/free/")
    ? { data: { token: "saved-token", desired_count: 2, answers: saved } }
    : { data: { clips: {} } });
  axios.put.mockImplementation(async (_path, payload) => {
    saved[["mission", "current_board", "desired_board_members", "board_type", "support_needs", "why_join"][payload.question - 1]] = payload.text;
    return { data: { status: "saved" } };
  });
  const done = jest.fn();
  await render(<RecruitmentGameIntake publicToken="saved-token" onComplete={done} />);
  expect(byId("recruitment-question-2")).not.toBeNull();
  for (let question = 2; question <= 6; question += 1) {
    const input = byId(`recruitment-question-${question}-input`);
    await act(async () => {
      Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set.call(input, `Answer ${question}`);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await click(Array.from(byId(`recruitment-question-${question}`).querySelectorAll("button"))
      .find((button) => /NEXT QUESTION|SAVE MY ANSWERS/.test(button.textContent)));
  }
  expect(byId("recruitment-questions-complete")).not.toBeNull();
  expect(done).toHaveBeenCalledTimes(1);
  expect(axios.put.mock.calls.map(([, payload]) => payload.question)).toEqual([2, 3, 4, 5, 6]);
  expect(axios.put.mock.calls[3][1].desired_count).toBe("2");
  expect(axios.post).not.toHaveBeenCalled();
});

test("campaign launch waits for the communication drafts to be approved", async () => {
  const originalGet = memberApi.get.getMockImplementation();
  memberApi.get.mockImplementation((path, options) => path === "/workspace/opportunity"
    ? Promise.resolve({ data: { opportunity: { slug: "community", status: "Draft", application_saved: true }, core_questions: [],
      readiness: { profiles_approved: true, scheduling_saved: true, application_saved: true,
        materials_approved: true, onboarding_approved: true, support_approved: false } } })
    : originalGet(path, options));
  await render(<Module3Launch mode="launch" />);
  expect(byId("publish-button").disabled).toBe(true);
  expect(byId("publish-panel").textContent).toContain("Interview, check and offer communications approved");
  expect(memberApi.post).not.toHaveBeenCalledWith("/workspace/opportunity/publish");
});
