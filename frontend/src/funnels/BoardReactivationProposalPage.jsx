import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ShieldCheck } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const OUTCOMES = [
  "Understand why the Board disengaged",
  "Get honest recommitment from current Board Members",
  "Identify who is ready to stand up",
  "Identify who is no longer prepared to carry Board responsibility",
  "Preserve relationships through difficult conversations",
  "Transition people appropriately where needed",
  "Clarify how continuing members will contribute",
  "Give continuing members defined areas of ownership",
  "Create Board Member Portfolios",
  "Leave with a reactivated Board you can actually work with",
];

export default function BoardReactivationProposalPage() {
  usePageMeta(...PAGE_META.boardReactivationProposal);
  const location = useLocation();
  const cancelled = new URLSearchParams(location.search).get("checkout") === "cancelled";
  const [ctaNotice, setCtaNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const makePayment = async () => {
    setBusy(true);
    setCtaNotice("");
    try {
      const response = await axios.post(`${API}/payments/reactivation-project-checkout`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setCtaNotice("We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="rxp-page">
        <section className="funnel-hero-banner brp-hero" data-testid="rxp-hero">
          <p className="eyebrow" data-testid="rxp-hero-eyebrow">Board Reactivation Project Proposal</p>
          <h1 data-testid="rxp-headline">Stop Carrying Dead Weight on Your Board</h1>
          <p className="funnel-hero-banner-supporting" data-testid="rxp-hero-supporting"><strong>Reactivate the People Who Are Ready to Serve and Deal With the People Who Aren't</strong></p>
          <p className="funnel-hero-banner-secondary" data-testid="rxp-hero-copy">Your Board should help carry the organization forward. You should not have to keep carrying people who hold Board seats but are not prepared to take responsibility.</p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section brp-summary" data-testid="rxp-summary-section">
          <h2 className="brp-section-title" data-testid="rxp-summary-heading">Executive Summary</h2>
          <p>Your organization already has Board Members. The problem is that some or most of them are no longer actively carrying the responsibilities the organization needs them to carry.</p>
          <p>The answer is not to keep sending reminders, pressuring people to participate or pretending the Board is functioning when the founder is still carrying most of the work.</p>
          <p><strong>We will work through the Board Reactivation process together.</strong></p>
          <p>We will understand what caused the disengagement, give each Board Member an opportunity to recommit, have the difficult conversations that need to happen, identify who is prepared to stand up, help those who are not prepared to serve step down or transition appropriately, and give the people who remain clear areas of responsibility.</p>
          <p data-testid="rxp-summary-goal">The goal is an active Board whose members understand what they own and how they are expected to help move the organization forward.</p>
        </section>

        <section className="brp-section brp-result" data-testid="rxp-outcomes-section">
          <h2 className="brp-section-title" data-testid="rxp-outcomes-heading">What We Will Accomplish Together</h2>
          <ul className="brp-list icon-list" data-testid="rxp-outcomes-list">
            {OUTCOMES.map((point) => <li key={point}><Check size={16} aria-hidden="true" /><span>{point}</span></li>)}
          </ul>
        </section>

        <section className="brp-section brp-investment" data-testid="rxp-investment-section">
          <h2 className="brp-section-title" data-testid="rxp-investment-heading">Your Investment</h2>
          <p className="brp-standard-price" data-testid="rxp-reference-price"><s>$3,997</s></p>
          <p className="brp-today-price" data-testid="rxp-today-price">$1,997</p>
          <p className="dyi-payment-line" data-testid="rxp-payment-line"><strong>One-time payment.</strong></p>
        </section>

        <section className="brp-section brp-guarantee" data-testid="rxp-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 className="brp-section-title" data-testid="rxp-guarantee-heading">100% Money-Back Guarantee</h2>
          <p data-testid="rxp-guarantee-copy">Your investment is protected by our <strong>100% money-back guarantee.</strong></p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="rxp-cta-section">
          {cancelled && <p className="rwr-cta-notice" data-testid="rxp-cancelled-notice">Your payment was not completed. You can get started whenever you're ready.</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="rxp-cta-button">{busy ? "Preparing Checkout…" : "MAKE PAYMENT — LET'S REACTIVATE YOUR BOARD TOGETHER"}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="rxp-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/reactivate-your-board-yourself" data-testid="rxp-diy-cross-link">Prefer to Do It By Yourself?</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="rxp" />
      </main>
    </FunnelLayout>
  );
}
