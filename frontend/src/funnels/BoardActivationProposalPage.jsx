import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ShieldCheck } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const OUTCOMES = [
  "Board participation in fundraising planning",
  "Board ideas and relationships incorporated into the strategy",
  "One clear Fundraising Strategy Plan",
  "Board review of the plan",
  "A structured plan-adoption process",
  "Clear Board fundraising responsibilities",
  "Practical execution tools",
  "Individual clarity around how Board Members can contribute",
  "A Fundraising Board structure the organization can continue building from",
];

export default function BoardActivationProposalPage() {
  usePageMeta(...PAGE_META.boardActivationProposal);
  const location = useLocation();
  const cancelled = new URLSearchParams(location.search).get("checkout") === "cancelled";
  const [ctaNotice, setCtaNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const makePayment = async () => {
    setBusy(true);
    setCtaNotice("");
    try {
      const response = await axios.post(`${API}/payments/activation-project-checkout`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setCtaNotice("We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="ap-page">
        <section className="funnel-hero-banner brp-hero" data-testid="ap-hero">
          <p className="eyebrow" data-testid="ap-hero-eyebrow">Board Fundraising Activation Project Proposal</p>
          <h1 data-testid="ap-headline">Turn Your Board Into Fundraising Champions for Your Mission</h1>
          <p className="funnel-hero-banner-supporting" data-testid="ap-hero-supporting"><strong>Stop Carrying Fundraising Alone — We Will Activate Your Board Together</strong></p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section brp-summary" data-testid="ap-summary-section">
          <h2 className="brp-section-title" data-testid="ap-summary-heading">Executive Summary</h2>
          <p>Fundraising should not sit almost entirely on the founder or executive director while the Board remains on the sidelines.</p>
          <p>The purpose of this project is to work with your organization through a structured Board Fundraising Activation process that gets Board Members involved in building the fundraising plan, reviewing and adopting the strategy, accepting clear responsibilities and becoming equipped to help execute it.</p>
          <p><strong>The outcome is not simply a fundraising document.</strong></p>
          <p data-testid="ap-summary-goal">The outcome is a Board that understands the fundraising direction, has participated in shaping it, knows what it is responsible for and is better equipped to help the organization raise money.</p>
        </section>

        <section className="brp-section brp-result" data-testid="ap-outcomes-section">
          <h2 className="brp-section-title" data-testid="ap-outcomes-heading">What We Will Accomplish Together</h2>
          <ul className="brp-list icon-list" data-testid="ap-outcomes-list">
            {OUTCOMES.map((point) => <li key={point}><Check size={16} aria-hidden="true" /><span>{point}</span></li>)}
          </ul>
          <p data-testid="ap-with-rooney-line">I work through the process <strong>with</strong> you — your organization is not simply purchasing documents.</p>
        </section>

        <section className="brp-section brp-investment" data-testid="ap-investment-section">
          <h2 className="brp-section-title" data-testid="ap-investment-heading">Your Investment</h2>
          <p className="brp-today-price" data-testid="ap-today-price">$2,497</p>
          <p className="dyi-payment-line" data-testid="ap-payment-line"><strong>One-time payment.</strong></p>
        </section>

        <section className="brp-section brp-guarantee" data-testid="ap-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 className="brp-section-title" data-testid="ap-guarantee-heading">100% Money-Back Guarantee</h2>
          <p data-testid="ap-guarantee-copy">Your investment is protected by our <strong>100% money-back guarantee.</strong></p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="ap-cta-section">
          {cancelled && <p className="rwr-cta-notice" data-testid="ap-cancelled-notice">Your payment was not completed. You can get started whenever you're ready.</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="ap-cta-button">{busy ? "Preparing Checkout…" : "MAKE PAYMENT — LET'S ACTIVATE YOUR BOARD TOGETHER"}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="ap-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/activate-your-board-yourself" data-testid="ap-diy-cross-link">Prefer to Do It By Yourself?</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="ap" />
      </main>
    </FunnelLayout>
  );
}
