import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { Award, Handshake, LifeBuoy, LockKeyhole, ShieldCheck, Users, X } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { useReviewMode } from "@/reviewMode";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TERMS_VERSION = "2026-06-recruitment-v1";

const OUTCOMES = [
  { icon: Users, title: "The Board Members Your Organization Needs", copy: "Build a board with the skills, experience, relationships and fundraising capacity your nonprofit needs to succeed." },
  { icon: Award, title: "Confidence to Recruit the Right Way", copy: "Understand how strong board recruitment works so you become a leader who knows how to recruit the board your organization needs whenever that need arises." },
  { icon: Handshake, title: "Everything You Need to Execute", copy: "Get real-time access to the resources and support you need to move from needing new board members to actually bringing the right people onto your board." },
  { icon: LifeBuoy, title: "Access to Rooney While You Recruit", copy: "You are not left alone with information. When you need clarification, get stuck or need help moving forward, you can reach out for support." },
];

const BEFORE_START = [
  ["This Is an Execution Program", "The strongest results come from taking action with the tools provided as you move through the system."],
  ["Complete the Steps in Order", "Each stage builds on the decisions and information from the stage before it."],
  ["Use the Support Available to You", "If you need clarification or get stuck, use the support available inside the program."],
  ["You Make the Final Board Decisions", "The platform can help you launch your recruitment campaign, assess applicants and prepare candidates, but you and your organization decide who is appointed to your board."],
];

const GuaranteeModal = ({ close }) => {
  const [terms, setTerms] = useState("");
  useEffect(() => {
    axios.get(`${API}/recruitment-guarantee`).then((response) => setTerms(response.data.terms)).catch(() => setTerms("The Recruitment Guarantee terms will be published here."));
  }, []);
  return (
    <div className="guarantee-modal-overlay" onClick={close} data-testid="guarantee-modal-overlay">
      <div className="guarantee-modal" onClick={(event) => event.stopPropagation()} data-testid="guarantee-modal">
        <button className="guarantee-close" onClick={close} aria-label="Close" data-testid="guarantee-modal-close"><X size={20} /></button>
        <h2>Recruitment Guarantee</h2>
        <p data-testid="guarantee-terms-text">{terms || "Loading…"}</p>
      </div>
    </div>
  );
};

export default function RecruitCheckoutPage() {
  usePageMeta(...PAGE_META.checkout);
  const navigate = useNavigate();
  const location = useLocation();
  const reviewMode = useReviewMode();
  const internalTest = new URLSearchParams(location.search).get("internal") === "true";
  const [flags, setFlags] = useState({ recruitment_497_live: false });
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showGuarantee, setShowGuarantee] = useState(false);
  useEffect(() => { axios.get(`${API}/payments/config`).then((response) => setFlags(response.data)).catch(() => {}); }, []);

  const context = JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}");
  const enabled = flags.recruitment_497_live || internalTest;

  const proceed = async () => {
    setError("");
    if (!context.lead_id || context.offer_source !== "recruitment") { setError("Please complete the recruitment form before purchasing."); return; }
    if (!agreed) { setError("Please confirm you have read and agree to the terms before continuing."); return; }
    setBusy(true);
    try {
      await axios.post(`${API}/terms-agreements`, { lead_id: context.lead_id, terms_version: TERMS_VERSION }, { withCredentials: true });
      const response = await axios.post(`${API}/payments/checkout`, { lead_id: context.lead_id, tier: "497", origin_url: window.location.origin, internal_test: internalTest }, { withCredentials: true });
      window.location.assign(response.data.checkout_url);
    } catch (err) {
      setError(err.response?.data?.detail || "Checkout could not be opened.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout>
      <main className="recruit-checkout-page" data-testid="recruit-checkout-page">
        <section className="checkout-hero">
          <div className="checkout-card">
            <p className="eyebrow" data-testid="checkout-label">Guided Board Recruitment</p>
            <h1 data-testid="checkout-heading">Build the Stronger Board Your Nonprofit Has Been Missing</h1>
            <p className="checkout-price" data-testid="checkout-price">$497 <span>One Time</span></p>
            <p data-testid="checkout-sales-copy">Recruit the committed, capable board members your nonprofit needs to move forward. Get the knowledge, resources, guidance, support and accountability you need to confidently build a stronger board around your mission. You will have what you need to execute and direct access to Rooney whenever you need help along the way. Your investment is also protected by our Recruitment Guarantee.</p>
          </div>
        </section>
        <section className="walkaway-section" data-testid="walkaway-section">
          <p className="eyebrow">The outcome</p>
          <h2>What You Walk Away With</h2>
          <div className="walkaway-grid">
            {OUTCOMES.map(({ icon: Icon, title, copy }) => (
              <article className="walkaway-card" key={title}>
                <Icon size={24} />
                <h3>{title}</h3>
                <p>{copy}</p>
              </article>
            ))}
            <article className="walkaway-card guarantee" onClick={() => setShowGuarantee(true)} role="button" tabIndex={0} onKeyDown={(event) => event.key === "Enter" && setShowGuarantee(true)} data-testid="guarantee-card">
              <ShieldCheck size={24} />
              <h3>Recruitment Guarantee</h3>
              <p>Your investment is protected by our money-back Recruitment Guarantee. Click to read the Recruitment Guarantee terms.</p>
            </article>
          </div>
        </section>
        <section className="before-start-section" data-testid="before-start-section">
          <p className="eyebrow">Before you start</p>
          <h2>Before You Start</h2>
          <div className="before-start-list">
            {BEFORE_START.map(([title, copy]) => (
              <article key={title}><h3>{title}</h3><p>{copy}</p></article>
            ))}
          </div>
        </section>
        <section className="checkout-commit" data-testid="checkout-commit-section">
          <label className="terms-check" data-testid="terms-agreement-label">
            <input type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} data-testid="terms-agreement-checkbox" />
            <span>I have read the program information and agree to the <Link to="/terms" target="_blank">Terms of Purchase</Link>, <Link to="/terms" target="_blank">Refund Policy</Link> and <button type="button" className="link-button inline-link" onClick={(event) => { event.preventDefault(); setShowGuarantee(true); }} data-testid="terms-guarantee-link">Recruitment Guarantee Terms</button>.</span>
          </label>
          {error && <p className="submit-error" data-testid="checkout-error">{error}</p>}
          <button className="button" disabled={!enabled || busy} onClick={proceed} data-testid="checkout-pay-button">
            {enabled ? (busy ? "Opening secure checkout…" : "Start Building My Board — $497") : <><LockKeyhole size={16} /> Program Access Opening Soon</>}
          </button>
          {reviewMode && (
            <button className="button review-bypass-button" onClick={() => navigate("/app/recruitment/self-guided/module/1")} data-testid="owner-review-continue-button">
              Continue in Owner Review Mode
            </button>
          )}
        </section>
        <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Accomplished" idPrefix="recruit-checkout" />
        {showGuarantee && <GuaranteeModal close={() => setShowGuarantee(false)} />}
      </main>
    </FunnelLayout>
  );
}
