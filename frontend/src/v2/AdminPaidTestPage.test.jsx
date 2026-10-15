import React, { act } from "react";
import { createRoot } from "react-dom/client";
import AdminPaidTestPage from "./AdminPaidTestPage";
import { v2Api } from "./api";
import { adminTestApiPath } from "./api";

global.IS_REACT_ACT_ENVIRONMENT = true;
let mockProduct = "recruit";
const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({ useParams: () => ({ product: mockProduct }), useNavigate: () => mockNavigate, Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a> }));
jest.mock("./V2Shell", () => ({ __esModule: true, default: ({ children }) => <main>{children}</main>, Loading: ({ children }) => <p role="status">{children}</p>, ErrorNotice: ({ error }) => error ? <p role="alert">{error}</p> : null }));
jest.mock("./api", () => { const actual = jest.requireActual("./api"); return { ...actual, v2Api: { get: jest.fn(), post: jest.fn() } }; });
const mount = async () => {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<AdminPaidTestPage />));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
};
beforeEach(() => { jest.clearAllMocks(); mockProduct = "recruit"; v2Api.get.mockImplementation(async (path) => ({ data: path.endsWith("/inbox") ? { emails: [] } : { journey: null } })); });

test.each(["recruit", "board-fundraising-game", "strategic-planning", "board-recommitment"])("%s test launcher opens the actual paid setup without checkout", async (product) => {
  mockProduct = product;
  const jid = `admin-test-${product}--sample`;
  v2Api.post.mockResolvedValue({ data: { next: `/v2/setup/${jid}` } });
  const { node, cleanup } = await mount();
  try {
    expect(node.textContent).toContain("No payment is taken");
    const start = [...node.querySelectorAll("button")].find((button) => button.textContent === "Start a fresh paid test");
    await act(async () => start.click());
    expect(v2Api.post).toHaveBeenCalledWith(`/admin/test-journeys/${product}`);
    expect(mockNavigate).toHaveBeenCalledWith(`/v2/setup/${jid}`);
    expect(v2Api.post.mock.calls.some(([path]) => /checkout/.test(path))).toBe(false);
  } finally { await cleanup(); }
});

test("test email content is rendered as text and saved test resources reopen", async () => {
  v2Api.get.mockImplementation(async (path) => ({ data: path.endsWith("/inbox") ? { emails: [{ event_id: "sample", subject: "Sample approval", to: "board@example.test", text: "<script>unsafe()</script>", action_path: "/v2/library/admin-test-recruit--sample" }] } : { journey: { journey_id: "admin-test-recruit--sample", setup_complete: true } } }));
  const { node, cleanup } = await mount();
  try {
    expect(node.querySelector("script")).toBeNull();
    expect(node.textContent).toContain("Captured for testing, not delivered");
    expect(node.querySelector('a[href="/v2/resources/admin-test-recruit--sample"]')).not.toBeNull();
  } finally { await cleanup(); }
});

test("only visibly marked admin test resources use the isolated API", () => {
  for (const prefix of ["journeys", "forms", "meeting"]) {
    expect(adminTestApiPath(`/${prefix}/admin-test-recruit--sample`)).toBe(`/admin/test-api/${prefix}/admin-test-recruit--sample`);
    expect(adminTestApiPath(`/${prefix}/actual-customer`)).toBe(`/${prefix}/actual-customer`);
  }
  expect(adminTestApiPath("/catalog")).toBe("/catalog");
});
