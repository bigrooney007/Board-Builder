import { ArrowRight } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { FunnelForm } from "./FunnelForm";
import { funnelConfigs } from "./funnelConfig";

const recruitmentStages = [
  ["01", "Identify", "Understand what the organization needs from the board."],
  ["02", "Strategize", "Build the recruitment process around those needs."],
  ["03", "Launch", "Take the opportunity to the right people and places."],
  ["04", "Interview", "Determine which applicants can genuinely strengthen the board."],
  ["05", "Verify", "Conduct references and appropriate background checks."],
  ["06", "Onboard", "Prepare selected board members to understand the organization, expectations and their responsibilities."],
];

export default function FunnelLandingPage({ offerSource }) {
  const config = funnelConfigs[offerSource];
  const scrollToForm = () => document.getElementById("offer-form")?.scrollIntoView({ behavior: "smooth" });
  return <FunnelLayout><main data-testid={`${offerSource}-landing-page`}><section className={`funnel-hero ${offerSource}`}><div><p className="eyebrow" data-testid={`${offerSource}-eyebrow`}>{config.eyebrow}</p><h1 data-testid={`${offerSource}-headline`}>{config.heading}</h1><p data-testid={`${offerSource}-supporting`}>{config.supporting}</p><button className="button" onClick={scrollToForm} data-testid={`${offerSource}-hero-button`}>{config.heroCta} <ArrowRight size={18} /></button></div><div className="funnel-hero-mark" aria-hidden="true"><span>{offerSource === "recruitment" ? "RECRUIT" : offerSource === "reactivation" ? "REACTIVATE" : "ACTIVATE"}</span><strong>{offerSource === "recruitment" ? "Find the right people" : offerSource === "reactivation" ? "Reset expectations" : "Turn strengths into action"}</strong><i /></div></section>{offerSource === "recruitment" && <section className="section recruitment-process" data-testid="recruitment-process-section"><p className="eyebrow">From needs to onboarding</p><h2>A Complete Board Recruitment Process</h2><div className="recruitment-process-grid">{recruitmentStages.map(([number, title, text]) => <article key={title}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div></section>}<FunnelForm offerSource={offerSource} /></main></FunnelLayout>;
}