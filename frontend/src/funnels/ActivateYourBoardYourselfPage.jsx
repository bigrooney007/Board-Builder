import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ShieldCheck } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const OUTCOMES = [
  ["Get Your Board Involved in Fundraising Planning", "Instead of building the fundraising plan alone and handing it down, you will bring your Board into the planning process from the start."],
  ["Collect the Board's Ideas, Experience and Relationships", "You will gather each Board Member's ideas, professional experience and relationships so the plan reflects what your Board can actually contribute."],
  ["Turn Those Contributions Into One Fundraising Strategy", "The Board's contributions become one organization-specific fundraising strategy your organization can execute."],
  ["Bring the Strategy Back to the Board for Review", "The Board reviews the strategy so members see their own ideas reflected in it before anything is adopted."],
  ["Facilitate the Board's Adoption of the Fundraising Direction", "You will lead a structured adoption process so the fundraising direction becomes the Board's plan — not just yours."],
  ["Establish Clear Fundraising Responsibilities", "Every participating Board Member will know exactly what they are responsible for."],
  ["Equip Board Members With Practical Tools", "Board Members receive practical emails, text messages and call scripts they can use to begin taking action."],
  ["Clarify How Each Member Helps Execute the Strategy", "No more vague requests to 'help with fundraising.' Each participating member has individual clarity about their contribution."],
  ["Create an Individual Fundraising Portfolio for Board Members", "After the process, Board Members receive an individual Fundraising Portfolio showing how they contribute to the strategy."],
  ["Build a Fundraising Structure You Can Continue Using", "You will leave with a fundraising structure the organization can continue using — not a one-time effort."],
];

export default function ActivateYourBoardYourselfPage() {
  usePageMeta(...PAGE_META.activateYourBoardYourself);
  const location = useLocation();
  const cancelled = new URLSearchParams(location.search).get("checkout") === "cancelled";
  const [ctaNotice, setCtaNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const makePayment = async () => {
    setBusy(true);
    setCtaNotice("");
    try {
      const response = await axios.post(`${API}/payments/activation-diy-checkout`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setCtaNotice("We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="adiy-page">
        <section className="funnel-hero-banner brp-hero" data-testid="adiy-hero">
          <h1 data-testid="adiy-headline">Activate Your Board to Start Raising Money</h1>
          <p className="funnel-hero-banner-supporting" data-testid="adiy-hero-supporting"><strong>Stop Carrying Fundraising Alone</strong></p>
          <p className="funnel-hero-banner-secondary" data-testid="adiy-hero-copy">You should not be the only person carrying the fundraising responsibility for your organization. Your Board should understand what the organization is trying to fund, help build the fundraising strategy, take ownership of the plan, accept clear responsibilities and have the tools they need to begin taking action.</p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section" data-testid="adiy-positioning-section">
          <h2 className="brp-section-title" data-testid="adiy-positioning-heading">People Who Plan Together Execute Together</h2>
          <p data-testid="adiy-positioning-copy">The goal is not to create a fundraising plan by yourself and then hand it to your Board. The Board participates in building the plan so members understand where the strategy came from, see their own ideas reflected in it, and are more prepared to take ownership of execution.</p>
        </section>

        <section className="brp-section brp-result" data-testid="adiy-result-section">
          <h2 className="brp-section-title" data-testid="adiy-result-heading">What Changes When You Follow the Process</h2>
          <div data-testid="adiy-result-list">
            {OUTCOMES.map(([title, copy]) => (
              <div className="dyi-outcome" key={title} style={{ textAlign: "left", margin: "0 auto 22px", maxWidth: 720 }}>
                <h3 style={{ marginBottom: 6 }}><Check size={16} aria-hidden="true" /> {title}</h3>
                <p style={{ margin: 0 }}>{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="brp-section" data-testid="adiy-support-section">
          <h2 className="brp-section-title" data-testid="adiy-support-heading">You Are Doing It Yourself. You Are Not Doing It Alone.</h2>
          <p data-testid="adiy-support-copy">You are following my complete process for taking a Board from limited fundraising participation to ownership and execution — and you have the tools and support structure you need to execute it.</p>
        </section>

        <section className="brp-section brp-investment" data-testid="adiy-investment-section">
          <h2 className="brp-section-title" data-testid="adiy-investment-heading">Your Investment</h2>
          <p className="brp-today-price" data-testid="adiy-price">$497</p>
          <p className="dyi-payment-line" data-testid="adiy-payment-line"><strong>One-time payment.</strong></p>
          <p className="dyi-payment-line" data-testid="adiy-no-membership-line">No monthly membership. No subscription.</p>
        </section>

        <section className="brp-section brp-guarantee" data-testid="adiy-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 className="brp-section-title" data-testid="adiy-guarantee-heading">100% Money-Back Guarantee</h2>
          <p data-testid="adiy-guarantee-copy">Your investment is protected by our <strong>100% money-back guarantee.</strong></p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="adiy-cta-section">
          {cancelled && <p className="rwr-cta-notice" data-testid="adiy-cancelled-notice">Your payment was not completed. You can get started whenever you're ready.</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="adiy-cta-button">{busy ? "Preparing Checkout…" : "MAKE PAYMENT AND START ACTIVATING MY BOARD"}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="adiy-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/board-activation-proposal" data-testid="adiy-dwm-cross-link">Want Me To Do It With You?</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="adiy" />
      </main>
    </FunnelLayout>
  );
}
