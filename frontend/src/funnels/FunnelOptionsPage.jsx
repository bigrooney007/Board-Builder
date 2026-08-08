import { useEffect, useState } from "react";
import axios from "axios";
import { Check, ExternalLink, LockKeyhole } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { CALENDLY_URL, funnelConfigs } from "./funnelConfig";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function FunnelOptionsPage({ offerSource }) {
  const config = funnelConfigs[offerSource];
  const [paidLive, setPaidLive] = useState(false);
  const [checkoutError, setCheckoutError] = useState("");
  useEffect(() => { axios.get(`${API}/payments/config`).then((response) => setPaidLive(response.data.paid_programs_live)).catch(() => setPaidLive(false)); }, []);
  const openCheckout = async (tier) => {
    const context = JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}");
    if (!context.lead_id || context.offer_source !== offerSource) { setCheckoutError("Complete the starting-point form before selecting a paid program."); return; }
    try {
      const response = await axios.post(`${API}/payments/checkout`, { lead_id: context.lead_id, tier, origin_url: window.location.origin, internal_test: false });
      window.location.assign(response.data.checkout_url);
    } catch (error) { setCheckoutError(error.response?.data?.detail || "Checkout could not be opened."); }
  };
  const selfGuided = "For nonprofit founders and leaders who are comfortable using technology and want the complete process, training, instructions and ready-to-use resources.";
  return <FunnelLayout><main className="options-page" data-testid={`${offerSource}-options-page`}><section className="options-heading"><p className="eyebrow">Choose how you want to move forward</p><h1>{config.eyebrow} Options</h1><p>Choose the level of training, technology and execution support that fits your organization.</p></section>{checkoutError && <p className="submit-error options-error" data-testid="options-checkout-error">{checkoutError}</p>}<section className="pricing-grid"><article className="pricing-card" data-testid={`${offerSource}-tier-97`}><span className="tier-label">Learn and execute</span><h2>{config.option97}</h2><div className="price"><strong>$97</strong><span>One Time</span></div><p>{selfGuided}</p><ul><li><Check size={15} />Complete training and process</li><li><Check size={15} />Step-by-step instructions</li><li><Check size={15} />Examples and ready-to-use resources</li><li><Check size={15} />Your team executes everything</li></ul><button className="button disabled-program-button" disabled={!paidLive} onClick={() => openCheckout("97")} data-testid={`${offerSource}-tier-97-button`}>{paidLive ? "Get the $97 Program" : <><LockKeyhole size={16} /> Available When Member Access Opens</>}</button></article><article className="pricing-card featured" data-testid={`${offerSource}-tier-497`}><span className="tier-label">Self-guided system</span><h2>{config.option497}</h2><div className="price"><strong>$497</strong><span>One Time</span></div><p>The full training plus the guided execution platform that walks you through the process and helps create the materials required to execute.</p><ul><li><Check size={15} />Complete training and resources</li><li><Check size={15} />Guided execution platform</li><li><Check size={15} />Help creating required materials</li><li><Check size={15} />You lead execution with structured support</li></ul><button className="button disabled-program-button" disabled={!paidLive} onClick={() => openCheckout("497")} data-testid={`${offerSource}-tier-497-button`}>{paidLive ? "Get the Self-Guided System" : <><LockKeyhole size={16} /> Available When Member Access Opens</>}</button></article><article className="pricing-card high-support" data-testid={`${offerSource}-tier-3497`}><span className="tier-label">Higher-support execution</span><h2>{config.option3497}</h2><div className="price"><strong>$3,497</strong></div><p>Work directly with Nonprofit Board Builder through the higher-support execution option to move the complete process forward with you.</p><ul><li><Check size={15} />Execution planning</li><li><Check size={15} />Direct strategic support</li><li><Check size={15} />Offer-specific implementation guidance</li><li><Check size={15} />A clear path from decision to execution</li></ul><a className="button" href={CALENDLY_URL} target="_blank" rel="noreferrer" data-testid={`${offerSource}-calendly-button`}>Schedule My Execution Planning Call <ExternalLink size={16} /></a></article></section></main></FunnelLayout>;
}