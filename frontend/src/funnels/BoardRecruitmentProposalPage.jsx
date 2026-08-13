import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { CalendarClock, CheckCircle2, Check, ShieldCheck, X } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const GuaranteeTermsModal = ({ close }) => {
  const [terms, setTerms] = useState("");
  useEffect(() => {
    axios.get(`${API}/recruitment-guarantee`).then((response) => setTerms(response.data.terms)).catch(() => setTerms(""));
  }, []);
  return (
    <div className="guarantee-modal-overlay" onClick={close} data-testid="brp-guarantee-modal-overlay">
      <div className="guarantee-modal" onClick={(event) => event.stopPropagation()} data-testid="brp-guarantee-modal">
        <button className="guarantee-close" onClick={close} aria-label="Close" data-testid="brp-guarantee-modal-close"><X size={20} /></button>
        <h3>Guarantee Terms</h3>
        <p data-testid="brp-guarantee-terms-text">{terms || "Loading…"}</p>
      </div>
    </div>
  );
};

const STEP_TWO_POINTS = ["Skills", "Experience", "Professional background", "Interest in your mission", "Capacity to serve", "Alignment with the organization", "Potential contribution to the board"];

const STEP_THREE_POINTS = [
  "Their role as board members",
  "Their commitment to the organization",
  "What responsibility they are expected to take",
  "How they support the founder or executive director",
  "How they contribute their skills, relationships and experience",
  "How they participate in building and moving the organization forward",
];

const ONBOARDING_DOCUMENTS = ["Board Member Agreement", "Confidentiality Agreement", "Conflict of Interest Agreement", "Board Member Profile Form"];

export default function BoardRecruitmentProposalPage() {
  usePageMeta(...PAGE_META.boardRecruitmentProposal);
  const location = useLocation();
  const cancelled = new URLSearchParams(location.search).get("checkout") === "cancelled";
  const [guaranteeConfigured, setGuaranteeConfigured] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const [ctaNotice, setCtaNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/recruitment-guarantee`).then((response) => setGuaranteeConfigured(Boolean(response.data.configured))).catch(() => {});
  }, []);

  const makePayment = async () => {
    setBusy(true);
    setCtaNotice("");
    try {
      const response = await axios.post(`${API}/payments/direct-project-checkout`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setCtaNotice("We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="brp-page">
        <section className="funnel-hero-banner brp-hero" data-testid="brp-hero">
          <p className="eyebrow" data-testid="brp-hero-eyebrow">Board Recruitment Project Proposal</p>
          <h1 data-testid="brp-headline">Build the Board Your Nonprofit Needs</h1>
          <p className="funnel-hero-banner-supporting" data-testid="brp-hero-intro">Your nonprofit should not have to keep struggling because you do not have the right people around the table.</p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section brp-summary" data-testid="brp-summary-section">
          <h2 className="brp-section-title" data-testid="brp-summary-heading">Executive Summary</h2>
          <p data-testid="brp-summary-whether">Whether you need one new board member or need to build an entirely new board, the objective of this engagement is simple:</p>
          <p className="brp-summary-objective" data-testid="brp-summary-objective">Help you recruit the board members your nonprofit needs to grow, raise money, build relationships and move your mission forward.</p>
          <p data-testid="brp-summary-timeline-line">Over the next two weeks, we will work together to identify, recruit, select and properly bring in skilled professionals with the experience, credibility, relationships and willingness to help your organization succeed.</p>
        </section>

        <section className="brp-section" data-testid="brp-how-section">
          <h2 className="brp-section-title" data-testid="brp-how-heading">Here Is How We Will Work Together</h2>

          <article className="brp-step-card" data-testid="brp-step-1">
            <div className="brp-step-number">1</div>
            <div className="brp-step-body">
              <h3>Launch Your Recruitment Campaign</h3>
              <p>During our first 30-minute session, we will identify the exact board members your nonprofit needs and launch your board recruitment campaign.</p>
              <p>We will launch your recruitment across various platforms using strategies we have mastered over the years.</p>
              <p>The objective is to put your opportunity in front of enough quality people that <strong>you have people to choose from instead of simply accepting whoever happens to show up.</strong></p>
            </div>
          </article>

          <article className="brp-step-card" data-testid="brp-step-2">
            <div className="brp-step-number">2</div>
            <div className="brp-step-body">
              <h3>Decide Who You Want</h3>
              <p>As applications begin coming in, your job is to review every applicant and decide who you want to meet.</p>
              <p>We will invite them in to meet with you so you can better understand their:</p>
              <ul className="brp-list icon-list">
                {STEP_TWO_POINTS.map((point) => <li key={point}><Check size={16} aria-hidden="true" /><span>{point}</span></li>)}
              </ul>
              <p>If you need help with the selection process, we can also provide the guidance and training you need to confidently choose who belongs on your board.</p>
            </div>
          </article>

          <article className="brp-step-card" data-testid="brp-step-3">
            <div className="brp-step-number">3</div>
            <div className="brp-step-body">
              <h3>Get Your Board Members Up To Speed and Ready To Build With You</h3>
              <p>Once you have selected the people you want, we come back in.</p>
              <p>Recruiting somebody is not enough.</p>
              <p>Your new board members need to understand what is expected of them and how they are supposed to support you and the organization.</p>
              <p>We will help make sure your new board members understand:</p>
              <ul className="brp-list icon-list">
                {STEP_THREE_POINTS.map((point) => <li key={point}><Check size={16} aria-hidden="true" /><span>{point}</span></li>)}
              </ul>
              <p>We will also take them through the necessary onboarding documentation, including:</p>
              <ul className="brp-list brp-list-strong">
                {ONBOARDING_DOCUMENTS.map((doc) => <li key={doc}><strong>{doc}</strong></li>)}
              </ul>
              <p>This way, you will gather important information about who they are, their professional experience, skills, relationships and the areas of the organization where they are interested in serving so you can start positioning them.</p>
            </div>
          </article>
        </section>

        <section className="brp-section brp-result" data-testid="brp-result-section">
          <h2 className="brp-section-title">The Result</h2>
          <p className="brp-result-headline" data-testid="brp-result-headline">In Two Weeks, You Will Have the Board Your Nonprofit Needs.</p>
          <p>A board of skilled professionals with the experience, credibility and willingness to help your organization succeed.</p>
          <p>And because you participate in the process with us, you will not only have new board members.</p>
          <p><strong>You will understand how the process works and be able to recruit board members again whenever your nonprofit needs them.</strong></p>
          <p>Plus, you will not have to start from scratch the next time your organization needs another board member. You will understand the process and have the tools and resources to recruit again.</p>
        </section>

        <section className="brp-section brp-timeline" data-testid="brp-timeline-section">
          <h2 className="brp-section-title">Project Timeline</h2>
          <p className="brp-timeline-value" data-testid="brp-timeline-value"><CalendarClock size={34} aria-hidden="true" /> 2 Weeks</p>
          <p className="brp-timeline-note">We also understand that every organization operates differently, so if you need to work within a different timeline, we are open to working with you within your organization's schedule.</p>
        </section>

        <section className="brp-section brp-investment" data-testid="brp-investment-section">
          <h2 className="brp-section-title">Your Investment</h2>
          <p className="brp-standard-price" data-testid="brp-reference-price"><s>$3,997</s></p>
          <p className="brp-discount-line" data-testid="brp-discount-line">But if you are ready to make payment and get started today, we are offering you a discount</p>
          <p className="brp-today-price" data-testid="brp-today-price">TODAY: $1,997</p>
        </section>

        <section className="brp-section brp-guarantee" data-testid="brp-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 className="brp-section-title" data-testid="brp-guarantee-heading">100% Money-Back Guarantee</h2>
          <p data-testid="brp-guarantee-copy">Your investment is protected by our <strong>100% money-back guarantee.</strong></p>
          {guaranteeConfigured && (
            <button type="button" className="link-button rwr-terms-link" onClick={() => setShowTerms(true)} data-testid="brp-guarantee-terms-link">View Guarantee Terms</button>
          )}
        </section>

        <section className="brp-section" data-testid="brp-after-payment-section">
          <h2 className="brp-section-title" data-testid="brp-after-payment-heading">What Happens After You Make Payment</h2>
          <p data-testid="brp-after-payment-copy">After making payment, you will tell us about your organization and board and then choose a convenient time to meet with me for our first session so we can start recruiting your board together.</p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="brp-final-cta-section">
          <h2 className="brp-section-title" data-testid="brp-ready-heading">Ready to Build Your Board?</h2>
          <p>You do not have to spend the next several months trying to figure out where to find board members or how to recruit them.</p>
          <p><strong>Let’s get the right people around your table and get your organization moving forward.</strong></p>
          {cancelled && <p className="rwr-cta-notice" data-testid="brp-cancelled-notice">Your payment was not completed. You can get started whenever you're ready.</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="brp-cta-button">{busy ? "Preparing Checkout…" : "MAKE PAYMENT — LET'S START RECRUITING YOUR BOARD TOGETHER"}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="brp-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/recruit-your-board-yourself" data-testid="brp-diy-cross-link">Prefer to Do It By Yourself?</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="brp" />
      </main>
      {showTerms && <GuaranteeTermsModal close={() => setShowTerms(false)} />}
    </FunnelLayout>
  );
}

export const BoardRecruitmentProposalConfirmedPage = () => {
  const location = useLocation();
  const sessionId = new URLSearchParams(location.search).get("session_id") || "";
  const [state, setState] = useState(sessionId ? "checking" : "missing");

  useEffect(() => {
    if (!sessionId) return undefined;
    let attempts = 0;
    let timer;
    const poll = async () => {
      attempts += 1;
      try {
        const response = await axios.get(`${API}/payments/status/${sessionId}`);
        if (response.data.payment_status === "paid") {
          setState("paid");
          timer = setTimeout(() => window.location.replace(`/board-recruitment-intake?session_id=${sessionId}`), 1800);
          return;
        }
        if (["failed", "expired"].includes(response.data.payment_status)) { setState("failed"); return; }
      } catch { /* keep polling */ }
      if (attempts < 8) timer = setTimeout(poll, 2500);
      else setState("timeout");
    };
    poll();
    return () => clearTimeout(timer);
  }, [sessionId]);

  return (
    <FunnelLayout restrained>
      <main className="brp-confirm-page" data-testid="brp-confirm-page">
        {state === "checking" && (
          <div className="brp-confirm-card" data-testid="brp-confirm-checking">
            <h1>Confirming Your Payment…</h1>
            <p>Please wait while we verify your payment with Stripe.</p>
          </div>
        )}
        {state === "missing" && (
          <div className="brp-confirm-card" data-testid="brp-confirm-missing">
            <h1>Missing Payment Details</h1>
            <p>We could not find a checkout session. If you completed a payment, please contact us.</p>
            <Link className="button" to="/board-recruitment-proposal">Return to the Proposal</Link>
          </div>
        )}
        {(state === "failed" || state === "timeout") && (
          <div className="brp-confirm-card" data-testid="brp-confirm-failed">
            <h1>We Could Not Confirm Your Payment Yet</h1>
            <p>If you completed the payment, it may still be processing. Please refresh this page in a moment or contact us for help.</p>
            <Link className="button" to="/board-recruitment-proposal">Return to the Proposal</Link>
          </div>
        )}
        {state === "paid" && (
          <div className="brp-confirm-card" data-testid="brp-confirm-paid">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Payment confirmed</p>
            <h1>Tell Me About Your Organization and Board</h1>
            <p>Taking you to a short form so we can start your board recruitment…</p>
            <a className="button" href={`/board-recruitment-intake?session_id=${sessionId}`} data-testid="brp-intake-link">Continue</a>
          </div>
        )}
      </main>
    </FunnelLayout>
  );
};
