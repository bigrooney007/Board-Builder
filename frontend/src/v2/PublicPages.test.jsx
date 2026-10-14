import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { OfferPage, PaymentPage, ProductLandingPage } from "./PublicPages";
import { CALENDLY_URL } from "./content";
import { v2Api } from "./api";

global.IS_REACT_ACT_ENVIRONMENT = true;
let mockProduct = "recruit";
let mockSearch = "journey=test-journey";
const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  useParams: () => ({ product: mockProduct }),
  useNavigate: () => mockNavigate,
  useSearchParams: () => [new URLSearchParams(mockSearch)],
  Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
  useLocation: () => ({ pathname: `/v2/${mockProduct}`, search: `?${mockSearch}` }),
}));
jest.mock("./api", () => ({ v2Api: { get: jest.fn(), post: jest.fn(), put: jest.fn() },
  errorMessage: (error, fallback) => error?.response?.data?.detail || fallback,
  saveDraftAccess: jest.fn(),
  readSessionValue: () => "",
}));
jest.mock("./V2Shell", () => ({ __esModule: true,
  default: ({ children }) => <main>{children}</main>,
  AssistanceLink: () => <a href="https://calendly.com/boardbuilder/recruitboard">Book a Call</a>,
  Loading: ({ children }) => <p role="status">{children}</p>,
  ErrorNotice: ({ error, children }) => error || children ? <p role="alert">{error || children}</p> : null,
}));
jest.mock("@/components/TestimonialCarousel", () => ({ TestimonialCarousel: () => <div data-testid="genuine-carousel" /> }));
jest.mock("@/game/SpeakButton", () => ({ __esModule: true, default: () => null, SpeakButton: () => null }));

async function mount(Component) {
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<Component />));
  return { node, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}
beforeEach(() => { mockProduct = "recruit"; mockSearch = "journey=test-journey"; mockNavigate.mockReset(); v2Api.get.mockReset(); v2Api.post.mockReset(); v2Api.put.mockReset(); });

test.each(["recruit", "board-fundraising-game", "strategic-planning", "board-recommitment"])("%s education page keeps free entry, genuine carousel and separate $197 product offer", async (product) => {
  mockProduct = product;
  const { node, cleanup } = await mount(ProductLandingPage);
  try {
    expect(node.querySelectorAll(`a[href="/v2/${product}/start"]`).length).toBeGreaterThanOrEqual(2);
    expect(node.textContent).toContain("$197");
    expect(node.querySelector('[data-testid="genuine-carousel"]')).not.toBeNull();
    expect(node.querySelector("iframe, video")).toBeNull();
    expect([...node.querySelectorAll("a")].some((a) => /dashboard|portfolio/.test(a.href))).toBe(false);
  } finally { await cleanup(); }
});

test.each(["recruit", "board-fundraising-game", "strategic-planning", "board-recommitment"])("%s offer goes directly to checkout without collecting branding", async (product) => {
  mockProduct = product;
  v2Api.get.mockResolvedValue({ data: { journey_id: "test-journey", product, state: "free", name: "Test Leader", organization: "Test Community Charity", answers: { mission: "Make community learning accessible", support_needs: "Find experienced education leaders" } } });
  const { node, cleanup } = await mount(OfferPage);
  try {
    expect(node.textContent).toContain("Test Community Charity");
    expect(node.querySelector("iframe, video, input, textarea, select")).toBeNull();
    expect(node.querySelector(`a[href="${CALENDLY_URL}"]`)).not.toBeNull();
    const buy = [...node.querySelectorAll("button")].find((button) => button.textContent.includes("$197"));
    expect(buy.disabled).toBe(false);
    v2Api.post.mockRejectedValue({ response: { data: { detail: "Test checkout unavailable" } } });
    await act(async () => buy.click());
    expect(v2Api.post).toHaveBeenCalledWith("/journeys/test-journey/checkout");
    expect(v2Api.put).not.toHaveBeenCalled();
    expect(node.textContent).toContain("Test checkout unavailable");
  } finally { await cleanup(); }
});

test("the provider's journey_id return link opens paid setup only after payment verification", async () => {
  mockSearch = "journey_id=test-journey&session_id=test-checkout";
  v2Api.get.mockResolvedValue({ data: { payment_status: "paid", journey_id: "test-journey", state: "paid" } });
  const { cleanup } = await mount(PaymentPage);
  try {
    expect(v2Api.get).toHaveBeenCalledWith("/journeys/test-journey/payment", { params: { session_id: "test-checkout" } });
    expect(mockNavigate).toHaveBeenCalledWith("/v2/setup/test-journey", { replace: true });
  } finally { await cleanup(); }
});
