import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { Check } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FINISH_POINTS = [
  "You will understand the process.",
  "You will have your recruitment materials.",
  "And you will know how to recruit quality board members again anytime your organization needs them.",
];

export default function RecruitYourBoardYourselfPage() {
  usePageMeta(...PAGE_META.recruitYourBoardYourself);
  const location = useLocation();
  const cancelled = new URLSearchParams(location.search).get("checkout") === "cancelled";
  const [ctaNotice, setCtaNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const makePayment = async () => {
    setBusy(true);
    setCtaNotice("");
    try {
      const response = await axios.post(`${API}/payments/diy-checkout`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setCtaNotice("We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="dyi-page">
        <section className="funnel-hero-banner brp-hero" data-testid="dyi-hero">
          <h1 data-testid="dyi-headline">Recruit Your Board Yourself</h1>
          <p className="funnel-hero-banner-supporting" data-testid="dyi-hero-supporting">Watch me run the recruitment process, then do what I do for your own nonprofit.</p>
          <p className="funnel-hero-banner-secondary" data-testid="dyi-hero-secondary">You will receive the instructions, the execution materials you need, and the ability to reach out for support as you move through the process.</p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section" data-testid="dyi-offer-section">
          <h2 className="brp-section-title" data-testid="dyi-offer-heading">You Don't Have to Figure Out the Process Yourself</h2>
          <p>I will show you exactly how I run the board recruitment process.</p>
          <p>You watch me do it.</p>
          <p>Then you follow what I do for your own organization.</p>
          <p>You will have the instructions and execution materials you need to recruit your board without having to create everything from scratch.</p>
          <p>And if you get stuck or need help as you go through the process, you can reach out for support.</p>
        </section>

        <section className="brp-section brp-result" data-testid="dyi-result-section">
          <h2 className="brp-section-title" data-testid="dyi-result-heading">When You Finish</h2>
          <p className="brp-result-headline" data-testid="dyi-result-headline">You will not only have recruited the board members your nonprofit needs.</p>
          <ul className="icon-list icon-list-centered" data-testid="dyi-result-list">
            {FINISH_POINTS.map((point) => <li key={point}><Check size={16} aria-hidden="true" /><span>{point}</span></li>)}
          </ul>
        </section>

        <section className="brp-section brp-investment" data-testid="dyi-investment-section">
          <h2 className="brp-section-title" data-testid="dyi-investment-heading">Your Investment</h2>
          <p className="brp-today-price" data-testid="dyi-price">$497</p>
          <p className="dyi-payment-line" data-testid="dyi-payment-line"><strong>One payment.</strong></p>
          <p className="dyi-payment-line" data-testid="dyi-no-membership-line">No monthly membership.</p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="dyi-cta-section">
          {cancelled && <p className="rwr-cta-notice" data-testid="dyi-cancelled-notice">Your payment was not completed. You can get started whenever you're ready.</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="dyi-cta-button">{busy ? "Preparing Checkout…" : "MAKE PAYMENT AND START RECRUITING MY BOARD"}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="dyi-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/board-recruitment-proposal" data-testid="dyi-dwm-cross-link">Want Me To Do It With You?</Link>
          </div>
        </section>
      </main>
    </FunnelLayout>
  );
}
