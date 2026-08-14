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
  ["The Board Members Your Nonprofit Needs", "The process starts by helping you identify the exact types of people your organization should be recruiting based on the board you have, what is missing and where your organization needs support."],
  ["A Live Board Recruitment Campaign", "You will not leave with a plan sitting on your computer. You will build and launch your actual board recruitment campaign."],
  ["Your Recruitment Materials Ready to Use", "Your organization-specific recruitment materials will be created for you so you can immediately begin putting your opportunity in front of prospective board members — the finished materials needed to recruit through professional opportunity platforms, LinkedIn, social media, email, and referrals from your existing network."],
  ["Your Own Board Application", "You will have a professional application ready to collect board candidates and their information in one place."],
  ["Access to Our Board Applicant Network", "When you launch your campaign, your opportunity can be promoted through our existing network of professionals who have already expressed interest in serving on nonprofit boards."],
  ["A Process for Choosing the Right People", "As applicants come in, you will have what you need to invite the people you want to interview, professionally decline those you do not want to move forward with, and conduct candidate-specific interviews based on each person's actual application and professional background."],
  ["References and Due Diligence", "For the people you want to move forward with, you will be able to collect and verify professional references and work through the final checks your organization requires."],
  ["Your Board Onboarding Resources", "By the time you are ready to bring people into your organization, you will have the professional resources needed to properly onboard them — an Organizational Overview, Board Member Manual, Board Member Agreement, Confidentiality Agreement, Conflict of Interest Policy and Disclosure, and Board Member Profile. You will not have to bring people onto your board without clear expectations or the materials they need."],
  ["Your Board Onboarding Process", "You will have a structured onboarding guide and the communications you need to bring your new members into the organization and prepare them for their first board meeting."],
  ["A Board You Can Actually Start Building With", "The goal is not to finish videos. The goal is to complete the process with the people your nonprofit needs around the table and begin moving the organization forward with them."],
  ["A Process You Can Repeat Anytime", "You will understand how the recruitment process works, you will have your recruitment materials, and the next time your nonprofit needs another board member you will know how to recruit again instead of starting from scratch."],
  ["Real-Time Support From Rooney", "You are not left alone with the platform. As you work through the recruitment process, you can reach out to Rooney whenever you get stuck, need clarification, want something reviewed or need support moving through a step."],
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
          <h1 data-testid="dyi-headline">{SITE_CONTENT.recruitDiy.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="dyi-hero-supporting">Watch me run the recruitment process, then do what I do for your own nonprofit.</p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section" data-testid="dyi-offer-section">
          <h2 className="brp-section-title" data-testid="dyi-offer-heading">Build the Board Your Nonprofit Needs</h2>
          <p data-testid="dyi-instructions-paragraph">This is not a course teaching theory. You will not simply learn about board recruitment — you will follow the process step by step, launch your recruitment campaign, work through your applicants, and properly bring the people you select into your organization.</p>
          <p>I will show you exactly how I run the board recruitment process.</p>
          <p>You watch me do it.</p>
          <p>Then you follow what I do for your own organization, using the materials created specifically for your nonprofit to actually recruit your board.</p>
        </section>

        <section className="brp-section brp-result" data-testid="dyi-result-section">
          <h2 className="brp-section-title" data-testid="dyi-result-heading">What You Will Walk Away With</h2>
          <div data-testid="dyi-result-list">
            {OUTCOMES.map(([title, copy]) => (
              <div className="dyi-outcome" key={title} style={{ textAlign: "left", margin: "0 auto 22px", maxWidth: 720 }}>
                <h3 style={{ marginBottom: 6 }}><Check size={16} aria-hidden="true" /> {title}</h3>
                <p style={{ margin: 0 }}>{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="brp-section" data-testid="dyi-support-section">
          <h2 className="brp-section-title" data-testid="dyi-support-heading">You Are Doing It Yourself. You Are Not Doing It Alone.</h2>
          <p data-testid="dyi-support-copy">I will show you the process, the platform will give you the materials you need to execute, and if you get stuck anywhere along the way, you can reach out to me for help using the Need Help With This Step? support built into every step.</p>
        </section>

        <section className="brp-section" data-testid="dyi-repeatable-section">
          <h2 className="brp-section-title" data-testid="dyi-repeatable-heading">Learn the Process Once. Use It Again Whenever You Need It.</h2>
          <p data-testid="dyi-repeatable-copy">By going through the process yourself, you learn how board recruitment actually works — and you can repeat it whenever your organization needs to recruit again.</p>
        </section>

        <section className="brp-section brp-investment" data-testid="dyi-investment-section">
          <h2 className="brp-section-title" data-testid="dyi-investment-heading">Your Investment</h2>
          <p className="brp-today-price" data-testid="dyi-price">$497</p>
          <p className="dyi-payment-line" data-testid="dyi-payment-line"><strong>One payment.</strong></p>
          <p className="dyi-payment-line" data-testid="dyi-no-membership-line">No monthly membership.</p>
        </section>

        <section className="brp-section brp-guarantee" data-testid="dyi-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 className="brp-section-title" data-testid="dyi-guarantee-heading">{SITE_CONTENT.shared.guaranteeHeading}</h2>
          <p data-testid="dyi-guarantee-copy">{SITE_CONTENT.shared.guaranteePrefix}<strong>{SITE_CONTENT.shared.guaranteeStrong}</strong></p>
        </section>

        <section className="brp-section" data-testid="dyi-after-payment-section">
          <h2 className="brp-section-title" data-testid="dyi-after-payment-heading">Start Immediately</h2>
          <p data-testid="dyi-after-payment-copy">After making payment, tell us about your organization and board and begin following the process immediately. You can work toward launching your board recruitment campaign in the next 30 minutes using the instructions and materials provided.</p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="dyi-cta-section">
          {cancelled && <p className="rwr-cta-notice" data-testid="dyi-cancelled-notice">Your payment was not completed. You can get started whenever you're ready.</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="dyi-cta-button">{busy ? "Preparing Checkout…" : SITE_CONTENT.recruitDiy.cta}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="dyi-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/board-recruitment-proposal" data-testid="dyi-dwm-cross-link">Want Me To Do It With You?</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="dyi" />
      </main>
    </FunnelLayout>
  );
}
