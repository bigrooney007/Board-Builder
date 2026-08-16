import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ExternalLink, LockKeyhole } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { CALENDLY_URL, funnelConfigs } from "./funnelConfig";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { funnelOptionsText } from "../content/appContent";
import { funnelOptionsPageText } from "../content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MatchBadge = ({ tier }) => <span className="match-badge" data-testid={`recruitment-match-badge-${tier}`}>{funnelOptionsPageText.matchesTheSupportYouSelected}</span>;

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
        {enabled ? (opening === tier ? "Opening checkout…" : liveLabel) : <><LockKeyhole size={16} />{funnelOptionsPageText.programAccessOpeningSoon}</>}
      </button>
    );
  };

  return (
    <FunnelLayout>
      <main className="options-page" data-testid={`${offerSource}-options-page`}>
        <section className="options-heading">
          <p className="eyebrow">{funnelOptionsPageText.chooseHowYouWantTo}</p>
          <h1 data-testid={`${offerSource}-options-heading`}>{config.optionsHeading}</h1>
          <p>{config.optionsSupporting}</p>
        </section>
        {checkoutError && <p className="submit-error options-error" data-testid="options-checkout-error">{checkoutError}</p>}
        {isRecruitment ? (
          <section className="pricing-grid recruitment-offers">
            <article className={`pricing-card simple-offer ${matched === "diy" ? "matched" : ""}`} data-testid="recruitment-tier-97">
              {matched === "diy" && <MatchBadge tier="97" />}
              <span className="tier-label">{funnelOptionsPageText.iWantToDoIt}</span>
              <h2>{funnelOptionsText.h_doItYourself}</h2>
              <div className="price"><strong>$97</strong><span>One Time</span></div>
              <p>{funnelOptionsPageText.recruitTheQualityBoardMembers}</p>
              {buyButton("97", live97, "I’ll Do It Myself — $97", "recruitment-tier-97-button")}
            </article>
            <article className={`pricing-card featured simple-offer most-popular ${matched === "self_guided" ? "matched" : ""}`} data-testid="recruitment-tier-497">
              <span className="popular-ribbon" data-testid="recruitment-most-popular">Most Popular</span>
              {matched === "self_guided" && <MatchBadge tier="497" />}
              <span className="tier-label">{funnelOptionsPageText.iWantGuidanceWhileI}</span>
              <h2>{funnelOptionsText.h_selfguidedRecruitment}</h2>
              <div className="price"><strong>$497</strong><span>One Time</span></div>
              <p>{funnelOptionsPageText.buildTheStrongerBoardYour}</p>
              {buyButton("497", live497, "Help Me Recruit My Board — $497", "recruitment-tier-497-button")}
            </article>
            <article className={`pricing-card high-support simple-offer ${matched === "done_with_you" ? "matched" : ""}`} data-testid="recruitment-tier-3497">
              {matched === "done_with_you" && <MatchBadge tier="3497" />}
              <span className="tier-label">{funnelOptionsPageText.iWantSomeoneToWork}</span>
              <h2>{funnelOptionsText.h_doneWithYou}</h2>
              <div className="price"><strong>$3,497</strong></div>
              <p>{funnelOptionsPageText.getTheBoardMembersYour}</p>
              <a className="button" href={CALENDLY_URL} target="_blank" rel="noreferrer" data-testid="recruitment-calendly-button">{funnelOptionsPageText.helpMeRecruitMyBoard}<ExternalLink size={16} /></a>
            </article>
          </section>
        ) : (
          <section className="pricing-grid">
            <article className="pricing-card" data-testid={`${offerSource}-tier-97`}>
              <span className="tier-label">Learn and execute</span>
              <h2>{config.option97}</h2>
              <div className="price"><strong>$97</strong><span>One Time</span></div>
              <p>{funnelOptionsPageText.forNonprofitFoundersAndLeaders}</p>
              <ul>{["Complete training and process", "Step-by-step instructions", "Examples and ready-to-use resources", "Your team executes everything"].map((item) => <li key={item}><Check size={15} />{item}</li>)}</ul>
              {buyButton("97", live97, "Get the $97 Program", `${offerSource}-tier-97-button`)}
            </article>
            <article className="pricing-card featured" data-testid={`${offerSource}-tier-497`}>
              <span className="tier-label">Self-guided system</span>
              <h2>{config.option497}</h2>
              <div className="price"><strong>$497</strong><span>One Time</span></div>
              <p>{funnelOptionsPageText.theFullTrainingPlusThe}</p>
              <ul>{["Complete training and resources", "Guided execution platform", "Help creating required materials", "You lead execution with structured support"].map((item) => <li key={item}><Check size={15} />{item}</li>)}</ul>
              {buyButton("497", live497, "Get the Self-Guided System", `${offerSource}-tier-497-button`)}
            </article>
            <article className="pricing-card high-support" data-testid={`${offerSource}-tier-3497`}>
              <span className="tier-label">Higher-support execution</span>
              <h2>{config.option3497}</h2>
              <div className="price"><strong>$3,497</strong></div>
              <p>{funnelOptionsPageText.workDirectlyWithNonprofitBoard}</p>
              <ul><li><Check size={15} />Execution planning</li><li><Check size={15} />Direct strategic support</li><li><Check size={15} />{funnelOptionsPageText.offerSpecificImplementationGuidance}</li><li><Check size={15} />{funnelOptionsPageText.aClearPathFromDecision}</li></ul>
              <a className="button" href={CALENDLY_URL} target="_blank" rel="noreferrer" data-testid={`${offerSource}-calendly-button`}>{funnelOptionsPageText.scheduleMyExecutionPlanningCall}<ExternalLink size={16} /></a>
            </article>
          </section>
        )}
        <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Accomplished" idPrefix={`${config.slug}-options`} />
      </main>
    </FunnelLayout>
  );
}
