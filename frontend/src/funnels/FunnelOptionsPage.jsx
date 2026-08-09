import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import { Check, ExternalLink, LockKeyhole } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { CALENDLY_URL, funnelConfigs } from "./funnelConfig";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const recruitment97Includes = [
  "Complete Board Recruitment training",
  "Step-by-step recruitment process",
  "Recruitment strategy instructions",
  "Board opportunity template",
  "Board application template",
  "Recruitment messaging templates",
  "Recruitment email templates",
  "LinkedIn recruitment instructions",
  "Social media recruitment templates",
  "Interview framework",
  "Reference-check process",
  "Background-check resources",
  "Onboarding resources",
];

const recruitment497Includes = [
  "Everything in the $97 program",
  "Guided module-by-module execution",
  "Personalized recruitment strategy",
  "Recruitment material generation",
  "Hosted board application form",
  "Board Applicant Network distribution",
  "Applicant management",
  "CV review",
  "Applicant-specific interview guides",
  "Interview communications",
  "Reference-check materials",
  "Onboarding materials",
  "Board Member Agreement",
  "Confidentiality Agreement",
  "Conflict of Interest Agreement",
  "New Board Member 90-Day Plan",
  "Saved execution workspace",
  "Support requests inside every module",
];

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

  const openCheckout = async (tier) => {
    const context = JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}");
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
        <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Accomplished" idPrefix={`${config.slug}-options`} />
        {checkoutError && <p className="submit-error options-error" data-testid="options-checkout-error">{checkoutError}</p>}
        <section className="pricing-grid">
          <article className="pricing-card" data-testid={`${offerSource}-tier-97`}>
            <span className="tier-label">Learn and execute</span>
            <h2>{config.option97}</h2>
            <div className="price"><strong>$97</strong><span>One Time</span></div>
            <p>{isRecruitment ? "For nonprofit founders and leaders who are comfortable using technology and want the complete process, instructions and resources required to recruit their board themselves." : "For nonprofit founders and leaders who are comfortable using technology and want the complete process, training, instructions and ready-to-use resources."}</p>
            <ul>{(isRecruitment ? recruitment97Includes : ["Complete training and process", "Step-by-step instructions", "Examples and ready-to-use resources", "Your team executes everything"]).map((item) => <li key={item}><Check size={15} />{item}</li>)}</ul>
            {buyButton("97", live97, isRecruitment ? "Get the $97 Recruitment Program" : "Get the $97 Program", `${offerSource}-tier-97-button`)}
          </article>
          <article className="pricing-card featured" data-testid={`${offerSource}-tier-497`}>
            <span className="tier-label">Self-guided system</span>
            <h2>{config.option497}</h2>
            <div className="price"><strong>$497</strong><span>One Time</span></div>
            <p>{isRecruitment ? "Follow the entire recruitment process inside the platform. Watch each lesson, complete the work for that stage and use the platform to create the materials you need to execute." : "The full training plus the guided execution platform that walks you through the process and helps create the materials required to execute."}</p>
            <ul>{(isRecruitment ? recruitment497Includes : ["Complete training and resources", "Guided execution platform", "Help creating required materials", "You lead execution with structured support"]).map((item) => <li key={item}><Check size={15} />{item}</li>)}</ul>
            {buyButton("497", live497, isRecruitment ? "Get the Self-Guided Recruitment System" : "Get the Self-Guided System", `${offerSource}-tier-497-button`)}
          </article>
          <article className="pricing-card high-support" data-testid={`${offerSource}-tier-3497`}>
            <span className="tier-label">Higher-support execution</span>
            <h2>{config.option3497}</h2>
            <div className="price"><strong>$3,497</strong></div>
            <p>{isRecruitment ? "We launch the recruitment campaign, you interview the applicants, and we help onboard the board members you select." : "Work directly with Nonprofit Board Builder through the higher-support execution option to move the complete process forward with you."}</p>
            <ul><li><Check size={15} />Execution planning</li><li><Check size={15} />Direct strategic support</li><li><Check size={15} />Offer-specific implementation guidance</li><li><Check size={15} />A clear path from decision to execution</li></ul>
            <a className="button" href={CALENDLY_URL} target="_blank" rel="noreferrer" data-testid={`${offerSource}-calendly-button`}>Schedule My Execution Planning Call <ExternalLink size={16} /></a>
          </article>
        </section>
      </main>
    </FunnelLayout>
  );
}
