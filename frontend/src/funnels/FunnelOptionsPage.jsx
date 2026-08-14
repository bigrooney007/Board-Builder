import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ExternalLink, LockKeyhole } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { CALENDLY_URL, funnelConfigs } from "./funnelConfig";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { funnelOptionsText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MatchBadge = ({ tier }) => <span className="match-badge" data-testid={`recruitment-match-badge-${tier}`}>Matches the support you selected</span>;

export default function FunnelOptionsPage({ offerSource }) {
  const config = funnelConfigs[offerSource];
  const location = useLocation();
  const internalTest = new URLSearchParams(location.search).get("internal") === "true";
  const [flags, setFlags] = useState({ paid_programs_live: false, recruitment_97_live: false, recruitment_497_live: false });
  const [checkoutError, setCheckoutError] = useState("");
  const [opening, setOpening] = useState("");
  useEffect(() => { axios.get(`${API}/payments/config`).then((response) => setFlags(response.data)).catch(() => {}); }, []);

  const isRecruitment = offerSource === "recruitment";
  const live97 = isRecruitment ? flags.recruitment_97_live : flags.paid_programs_live;
  const live497 = isRecruitment ? flags.recruitment_497_live : flags.paid_programs_live;
  const context = JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}");
  const matched = isRecruitment && context.lead_id && context.offer_source === "recruitment" ? (context.support_preference || "") : "";

  const openCheckout = async (tier) => {
    if (!context.lead_id || context.offer_source !== offerSource) { setCheckoutError(isRecruitment ? "Complete the recruitment form before selecting a program." : "Complete the starting-point form before selecting a paid program."); return; }
    setOpening(tier);
    try {
      const response = await axios.post(`${API}/payments/checkout`, { lead_id: context.lead_id, tier, origin_url: window.location.origin, internal_test: internalTest }, { withCredentials: true });
      window.location.assign(response.data.checkout_url);
    } catch (error) { setCheckoutError(error.response?.data?.detail || "Checkout could not be opened."); setOpening(""); }
  };

  const buyButton = (tier, live, liveLabel, testId) => {
    const enabled = live || internalTest;
    return (
      <button className="button disabled-program-button" disabled={!enabled || opening === tier} onClick={() => openCheckout(tier)} data-testid={testId}>
        {enabled ? (opening === tier ? "Opening checkout…" : liveLabel) : <><LockKeyhole size={16} /> Program Access Opening Soon</>}
      </button>
    );
  };

  return (
    <FunnelLayout>
      <main className="options-page" data-testid={`${offerSource}-options-page`}>
        <section className="options-heading">
          <p className="eyebrow">Choose how you want to move forward</p>
          <h1 data-testid={`${offerSource}-options-heading`}>{config.optionsHeading}</h1>
          <p>{config.optionsSupporting}</p>
        </section>
        {checkoutError && <p className="submit-error options-error" data-testid="options-checkout-error">{checkoutError}</p>}
        {isRecruitment ? (
          <section className="pricing-grid recruitment-offers">
            <article className={`pricing-card simple-offer ${matched === "diy" ? "matched" : ""}`} data-testid="recruitment-tier-97">
              {matched === "diy" && <MatchBadge tier="97" />}
              <span className="tier-label">I want to do it myself.</span>
              <h2>{funnelOptionsText.h_doItYourself}</h2>
              <div className="price"><strong>$97</strong><span>One Time</span></div>
              <p>Recruit the quality board members your nonprofit needs without guessing what to do next. Get the knowledge and resources you need to confidently build a stronger, more capable board yourself.</p>
              {buyButton("97", live97, "I’ll Do It Myself — $97", "recruitment-tier-97-button")}
            </article>
            <article className={`pricing-card featured simple-offer most-popular ${matched === "self_guided" ? "matched" : ""}`} data-testid="recruitment-tier-497">
              <span className="popular-ribbon" data-testid="recruitment-most-popular">Most Popular</span>
              {matched === "self_guided" && <MatchBadge tier="497" />}
              <span className="tier-label">I want guidance while I recruit my board.</span>
              <h2>{funnelOptionsText.h_selfguidedRecruitment}</h2>
              <div className="price"><strong>$497</strong><span>One Time</span></div>
              <p>Build the stronger board your nonprofit has been missing. Attract qualified professionals, choose the right people for your organization, and come out of the process with committed new board members ready to help your nonprofit move forward.</p>
              {buyButton("497", live497, "Help Me Recruit My Board — $497", "recruitment-tier-497-button")}
            </article>
            <article className={`pricing-card high-support simple-offer ${matched === "done_with_you" ? "matched" : ""}`} data-testid="recruitment-tier-3497">
              {matched === "done_with_you" && <MatchBadge tier="3497" />}
              <span className="tier-label">I want someone to work with me.</span>
              <h2>{funnelOptionsText.h_doneWithYou}</h2>
              <div className="price"><strong>$3,497</strong></div>
              <p>Get the board members your nonprofit needs without carrying the recruitment process alone. Bring in qualified professionals with the skills, experience, relationships and fundraising capacity your organization needs, and get them properly onboarded and ready to serve.</p>
              <a className="button" href={CALENDLY_URL} target="_blank" rel="noreferrer" data-testid="recruitment-calendly-button">Help Me Recruit My Board <ExternalLink size={16} /></a>
            </article>
          </section>
        ) : (
          <section className="pricing-grid">
            <article className="pricing-card" data-testid={`${offerSource}-tier-97`}>
              <span className="tier-label">Learn and execute</span>
              <h2>{config.option97}</h2>
              <div className="price"><strong>$97</strong><span>One Time</span></div>
              <p>For nonprofit founders and leaders who are comfortable using technology and want the complete process, training, instructions and ready-to-use resources.</p>
              <ul>{["Complete training and process", "Step-by-step instructions", "Examples and ready-to-use resources", "Your team executes everything"].map((item) => <li key={item}><Check size={15} />{item}</li>)}</ul>
              {buyButton("97", live97, "Get the $97 Program", `${offerSource}-tier-97-button`)}
            </article>
            <article className="pricing-card featured" data-testid={`${offerSource}-tier-497`}>
              <span className="tier-label">Self-guided system</span>
              <h2>{config.option497}</h2>
              <div className="price"><strong>$497</strong><span>One Time</span></div>
              <p>The full training plus the guided execution platform that walks you through the process and helps create the materials required to execute.</p>
              <ul>{["Complete training and resources", "Guided execution platform", "Help creating required materials", "You lead execution with structured support"].map((item) => <li key={item}><Check size={15} />{item}</li>)}</ul>
              {buyButton("497", live497, "Get the Self-Guided System", `${offerSource}-tier-497-button`)}
            </article>
            <article className="pricing-card high-support" data-testid={`${offerSource}-tier-3497`}>
              <span className="tier-label">Higher-support execution</span>
              <h2>{config.option3497}</h2>
              <div className="price"><strong>$3,497</strong></div>
              <p>Work directly with Nonprofit Board Builder through the higher-support execution option to move the complete process forward with you.</p>
              <ul><li><Check size={15} />Execution planning</li><li><Check size={15} />Direct strategic support</li><li><Check size={15} />Offer-specific implementation guidance</li><li><Check size={15} />A clear path from decision to execution</li></ul>
              <a className="button" href={CALENDLY_URL} target="_blank" rel="noreferrer" data-testid={`${offerSource}-calendly-button`}>Schedule My Execution Planning Call <ExternalLink size={16} /></a>
            </article>
          </section>
        )}
        <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Accomplished" idPrefix={`${config.slug}-options`} />
      </main>
    </FunnelLayout>
  );
}
