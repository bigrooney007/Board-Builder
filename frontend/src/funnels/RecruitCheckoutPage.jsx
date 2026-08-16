import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { Award, Handshake, LifeBuoy, LockKeyhole, ShieldCheck, Users, X } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { useReviewMode } from "@/reviewMode";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { PAGE_META, usePageMeta } from "@/seo";
import { recruitCheckoutText } from "../content/appContent";
import { recruitCheckoutPageText } from "../content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TERMS_VERSION = "2026-06-recruitment-v1";

const OUTCOMES = [
  { icon: Users, title: "The Board Members Your Organization Needs", copy: "Build a board with the skills, experience, relationships and fundraising capacity your nonprofit needs to succeed." },
  { icon: Award, title: "Confidence to Recruit the Right Way", copy: "Understand how strong board recruitment works so you become a leader who knows how to recruit the board your organization needs whenever that need arises." },
  { icon: Handshake, title: "Everything You Need to Execute", copy: "Get real-time access to the resources and support you need to move from needing new board members to actually bringing the right people onto your board." },
  { icon: LifeBuoy, title: "Access to Rooney While You Recruit", copy: "You are not left alone with information. When you need clarification, get stuck or need help moving forward, you can reach out for support." },
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
        <h2>{recruitCheckoutText.h_recruitmentGuarantee}</h2>
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
  const { refresh: refreshMember } = useMemberAuth();
  const enterReview = async () => {
    await refreshMember();
    navigate("/app/recruitment/self-guided/module/1");
  };
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
            <h1 data-testid="checkout-heading">{recruitCheckoutText.h_buildTheStrongerBoardYour}</h1>
            <p className="checkout-thirty" data-testid="checkout-thirty-minute">{recruitCheckoutPageText.startRecruitingSkilledProfessionalsIn}</p>
            <p className="checkout-price" data-testid="checkout-price">$497 <span>One Time</span></p>
            <p data-testid="checkout-sales-copy">{recruitCheckoutPageText.recruitTheCommittedCapableBoard}</p>
          </div>
        </section>
        <section className="walkaway-section" data-testid="walkaway-section">
          <p className="eyebrow">The outcome</p>
          <h2>{recruitCheckoutText.h_whatYouWalkAwayWith}</h2>
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
              <h3>{recruitCheckoutText.h_recruitmentGuarantee}</h3>
              <p>{recruitCheckoutPageText.yourInvestmentIsProtectedBy}</p>
            </article>
          </div>
        </section>
        <section className="before-start-section" data-testid="thirty-minute-section">
          <p className="eyebrow">Begin quickly</p>
          <h2>{recruitCheckoutText.h_startRecruitingInLessThan}</h2>
          <div className="before-start-list">
            <article><p>{recruitCheckoutPageText.moveFromKnowingYouNeed}</p></article>
          </div>
        </section>
        <section className="before-start-section" data-testid="board-types-section">
          <p className="eyebrow">{recruitCheckoutPageText.everyKindOfBoard}</p>
          <h2>{recruitCheckoutText.h_buildTheBoardYourOrganization}</h2>
          <div className="before-start-list">
            <article><p>{recruitCheckoutPageText.useTheGuidedProcessTo}</p></article>
          </div>
        </section>
        <section className="checkout-commit" data-testid="checkout-commit-section">
          <label className="terms-check" data-testid="terms-agreement-label">
            <input type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} data-testid="terms-agreement-checkbox" />
            <span>{recruitCheckoutPageText.iHaveReadTheProgram}<Link to="/terms" target="_blank">Terms of Purchase</Link>, <Link to="/terms" target="_blank">Refund Policy</Link> and <button type="button" className="link-button inline-link" onClick={(event) => { event.preventDefault(); setShowGuarantee(true); }} data-testid="terms-guarantee-link">Recruitment Guarantee Terms</button>.</span>
          </label>
          {error && <p className="submit-error" data-testid="checkout-error">{error}</p>}
          <button className="button" disabled={!enabled || busy} onClick={proceed} data-testid="checkout-pay-button">
            {enabled ? (busy ? "Opening secure checkout…" : "Start Building My Board — $497") : <><LockKeyhole size={16} />{recruitCheckoutPageText.programAccessOpeningSoon}</>}
          </button>
          {reviewMode && (
            <button className="button review-bypass-button" onClick={enterReview} data-testid="owner-review-continue-button">
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
