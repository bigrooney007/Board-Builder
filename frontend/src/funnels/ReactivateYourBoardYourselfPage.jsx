import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ShieldCheck } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";
import { SITE_CONTENT } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const OUTCOMES = [
  ["A Clear Understanding of Why Your Board Disengaged", "You will stop guessing why people are not participating and work through the actual causes of disengagement in your organization."],
  ["Clarity About Who Is Ready to Stand Up", "Every Board Member will have an opportunity to clarify whether they are willing and able to continue serving actively and how they are realistically prepared to contribute."],
  ["A Way to Deal With the Dead Weight", "You should not have to continue carrying Board Members who are not prepared to carry Board responsibility. The process helps you identify who is ready to recommit and who needs to step down or transition into another appropriate relationship with the organization."],
  ["The Information You Need Before Having Difficult Conversations", "Instead of calling Board Members blindly, you will have information about their interests, capacity, professional expertise, current experience on the Board and willingness to continue."],
  ["A Clear Conversation for Every Board Member", "You will know how to approach the difficult conversations without attacking, pressuring or destroying relationships."],
  ["Clear Responsibilities for the People Who Stay", "The goal is not simply to get someone to say: \"Yes, I still want to be on the Board.\" The people who continue should leave the process knowing where they can contribute and what responsibility they are prepared to carry."],
  ["A Board Member Portfolio for Each Person Who Recommits", "The people who remain will have a clear written portfolio showing how their expertise, interests and agreed responsibilities can help move the organization forward."],
  ["A Reactivated Board You Can Start Building With", "You will be able to see who is active, what they bring to the Board and where they have agreed to contribute."],
  ["A Process You Can Use Again", "You will understand how to address Board disengagement, recommitment and responsibility instead of allowing inactivity to continue indefinitely."],
  ["Real-Time Support From Rooney", "You are doing the process yourself, but you are not doing it alone. When you get stuck, need clarification, want something reviewed or need help working through a difficult step, you can reach out to Rooney for support."],
];

export default function ReactivateYourBoardYourselfPage() {
  usePageMeta(...PAGE_META.reactivateYourBoardYourself);
  const location = useLocation();
  const cancelled = new URLSearchParams(location.search).get("checkout") === "cancelled";
  const [ctaNotice, setCtaNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const makePayment = async () => {
    setBusy(true);
    setCtaNotice("");
    try {
      const response = await axios.post(`${API}/payments/reactivation-diy-checkout`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setCtaNotice("We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="rxdiy-page">
        <section className="funnel-hero-banner brp-hero" data-testid="rxdiy-hero">
          <h1 data-testid="rxdiy-headline">{SITE_CONTENT.reactivateDiy.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="rxdiy-hero-supporting"><strong>Stop Carrying Board Members Who Are Not Carrying the Mission</strong></p>
          <p className="funnel-hero-banner-secondary" data-testid="rxdiy-hero-copy">Follow the process to find out who is ready to stand up, who needs clearer responsibility, and who is no longer prepared to serve — without pressuring people, destroying relationships or continuing to carry dead weight on your Board.</p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section" data-testid="rxdiy-positioning-section">
          <h2 className="brp-section-title" data-testid="rxdiy-positioning-heading">Reactivate the Board You Already Have</h2>
          <p data-testid="rxdiy-positioning-copy">You will work through your current Board one person at a time, understand what caused the disengagement, find out who is willing and able to recommit, have the conversations that need to happen, and give the people who remain clear areas of responsibility.</p>
        </section>

        <section className="brp-section brp-result" data-testid="rxdiy-result-section">
          <h2 className="brp-section-title" data-testid="rxdiy-result-heading">What You Will Walk Away With</h2>
          <div data-testid="rxdiy-result-list">
            {OUTCOMES.map(([title, copy]) => (
              <div className="dyi-outcome" key={title} style={{ textAlign: "left", margin: "0 auto 22px", maxWidth: 720 }}>
                <h3 style={{ marginBottom: 6 }}><Check size={16} aria-hidden="true" /> {title}</h3>
                <p style={{ margin: 0 }}>{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="brp-section" data-testid="rxdiy-support-section">
          <h2 className="brp-section-title" data-testid="rxdiy-support-heading">You Are Doing It Yourself. You Are Not Doing It Alone.</h2>
          <p data-testid="rxdiy-support-copy">I will show you the process, the platform will give you what you need to execute it, and when you get stuck, you can reach out to me for help.</p>
        </section>

        <section className="brp-section brp-investment" data-testid="rxdiy-investment-section">
          <h2 className="brp-section-title" data-testid="rxdiy-investment-heading">Your Investment</h2>
          <p className="brp-today-price" data-testid="rxdiy-price">$497</p>
          <p className="dyi-payment-line" data-testid="rxdiy-payment-line"><strong>One payment.</strong></p>
          <p className="dyi-payment-line" data-testid="rxdiy-no-membership-line">No monthly membership.</p>
        </section>

        <section className="brp-section brp-guarantee" data-testid="rxdiy-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 className="brp-section-title" data-testid="rxdiy-guarantee-heading">{SITE_CONTENT.shared.guaranteeHeading}</h2>
          <p data-testid="rxdiy-guarantee-copy">{SITE_CONTENT.shared.guaranteePrefix}<strong>{SITE_CONTENT.shared.guaranteeStrong}</strong></p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="rxdiy-cta-section">
          {cancelled && <p className="rwr-cta-notice" data-testid="rxdiy-cancelled-notice">Your payment was not completed. You can get started whenever you're ready.</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="rxdiy-cta-button">{busy ? "Preparing Checkout…" : SITE_CONTENT.reactivateDiy.cta}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="rxdiy-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/board-reactivation-proposal" data-testid="rxdiy-dwm-cross-link">Want Me To Do It With You?</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="rxdiy" />
      </main>
    </FunnelLayout>
  );
}
