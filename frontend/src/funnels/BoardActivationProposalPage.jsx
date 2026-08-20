import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ShieldCheck } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";
import { SITE_CONTENT, boardActivationProposalPageText } from "@/content/siteContent";

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
          <p className="eyebrow" data-testid="ap-hero-eyebrow">{boardActivationProposalPageText.boardFundraisingActivationProjectProposal}</p>
          <h1 data-testid="ap-headline">{SITE_CONTENT.activateProposal.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="ap-hero-supporting"><strong>{boardActivationProposalPageText.stopCarryingFundraisingAloneWe}</strong></p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section brp-summary" data-testid="ap-summary-section">
          <h2 className="brp-section-title" data-testid="ap-summary-heading">Executive Summary</h2>
          <p>{boardActivationProposalPageText.fundraisingShouldNotSitAlmost}</p>
          <p>{boardActivationProposalPageText.thePurposeOfThisProject}</p>
          <p><strong>{boardActivationProposalPageText.theOutcomeIsNotSimply}</strong></p>
          <p data-testid="ap-summary-goal">{boardActivationProposalPageText.theOutcomeIsABoard}</p>
        </section>

        <section className="brp-section brp-result" data-testid="ap-outcomes-section">
          <h2 className="brp-section-title" data-testid="ap-outcomes-heading">{boardActivationProposalPageText.whatWeWillAccomplishTogether}</h2>
          <ul className="brp-list icon-list" data-testid="ap-outcomes-list">
            {OUTCOMES.map((point) => <li key={point}><Check size={16} aria-hidden="true" /><span>{point}</span></li>)}
          </ul>
          <p data-testid="ap-with-rooney-line">{boardActivationProposalPageText.iWorkThroughTheProcess}<strong>with</strong>{boardActivationProposalPageText.youYourOrganizationIsNot}</p>
        </section>

        <section className="brp-section brp-investment" data-testid="ap-investment-section">
          <h2 className="brp-section-title" data-testid="ap-investment-heading">Your Investment</h2>
          <p className="brp-today-price" data-testid="ap-today-price">$5,497</p>
          <p className="dyi-payment-line" data-testid="ap-payment-line"><strong>One-time payment.</strong></p>
        </section>

        <section className="brp-section brp-guarantee" data-testid="ap-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 className="brp-section-title" data-testid="ap-guarantee-heading">{SITE_CONTENT.shared.guaranteeHeading}</h2>
          <p data-testid="ap-guarantee-copy">{SITE_CONTENT.shared.guaranteePrefix}<strong>{SITE_CONTENT.shared.guaranteeStrong}</strong></p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="ap-cta-section">
          {cancelled && <p className="rwr-cta-notice" data-testid="ap-cancelled-notice">{boardActivationProposalPageText.yourPaymentWasNotCompleted}</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="ap-cta-button">{busy ? "Preparing Checkout…" : SITE_CONTENT.activateProposal.cta}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="ap-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/activate-your-board-yourself" data-testid="ap-diy-cross-link">{boardActivationProposalPageText.preferToDoItBy}</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="ap" />
      </main>
    </FunnelLayout>
  );
}
