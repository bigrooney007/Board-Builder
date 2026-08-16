import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ShieldCheck } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";
import { SITE_CONTENT, boardReactivationProposalPageText } from "@/content/siteContent";

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
          <p className="eyebrow" data-testid="rxp-hero-eyebrow">{boardReactivationProposalPageText.boardReactivationProjectProposal}</p>
          <h1 data-testid="rxp-headline">{SITE_CONTENT.reactivateProposal.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="rxp-hero-supporting"><strong>{boardReactivationProposalPageText.reactivateThePeopleWhoAre}</strong></p>
          <p className="funnel-hero-banner-secondary" data-testid="rxp-hero-copy">{boardReactivationProposalPageText.yourBoardShouldHelpCarry}</p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section brp-summary" data-testid="rxp-summary-section">
          <h2 className="brp-section-title" data-testid="rxp-summary-heading">Executive Summary</h2>
          <p>{boardReactivationProposalPageText.yourOrganizationAlreadyHasBoard}</p>
          <p>{boardReactivationProposalPageText.theAnswerIsNotTo}</p>
          <p><strong>{boardReactivationProposalPageText.weWillWorkThroughThe}</strong></p>
          <p>{boardReactivationProposalPageText.weWillUnderstandWhatCaused}</p>
          <p data-testid="rxp-summary-goal">{boardReactivationProposalPageText.theGoalIsAnActive}</p>
        </section>

        <section className="brp-section brp-result" data-testid="rxp-outcomes-section">
          <h2 className="brp-section-title" data-testid="rxp-outcomes-heading">{boardReactivationProposalPageText.whatWeWillAccomplishTogether}</h2>
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
          <h2 className="brp-section-title" data-testid="rxp-guarantee-heading">{SITE_CONTENT.shared.guaranteeHeading}</h2>
          <p data-testid="rxp-guarantee-copy">{SITE_CONTENT.shared.guaranteePrefix}<strong>{SITE_CONTENT.shared.guaranteeStrong}</strong></p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="rxp-cta-section">
          {cancelled && <p className="rwr-cta-notice" data-testid="rxp-cancelled-notice">{boardReactivationProposalPageText.yourPaymentWasNotCompleted}</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="rxp-cta-button">{busy ? "Preparing Checkout…" : SITE_CONTENT.reactivateProposal.cta}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="rxp-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/reactivate-your-board-yourself" data-testid="rxp-diy-cross-link">{boardReactivationProposalPageText.preferToDoItBy}</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="rxp" />
      </main>
    </FunnelLayout>
  );
}
