import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { usePageMeta } from "@/seo";
import { strategyPlanText } from "../content/appContent";
import { strategyPlanPageText } from "../content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategyPlanPage() {
  usePageMeta("Fundraising Strategy Plan | Nonprofit Board Builder", "Review your organization's current Fundraising Strategy Plan before the adoption meeting.", true);
  const { token } = useParams();
  const [context, setContext] = useState(null);
  const [state, setState] = useState("loading");

  useEffect(() => {
    axios.get(`${API}/strategy-plan/${token}`).then((res) => {
      setContext(res.data);
      setState("ready");
    }).catch(() => setState("invalid"));
  }, [token]);

  if (state === "loading") return <FunnelLayout restrained isolated><main><div className="intake-card" data-testid="sp-plan-loading"><h2>{strategyPlanText.h_loading}</h2></div></main></FunnelLayout>;
  if (state === "invalid") {
    return <FunnelLayout restrained isolated><main><div className="intake-card" data-testid="sp-plan-invalid"><h2>{strategyPlanText.h_thisPlanLinkIsNot}</h2><p>{strategyPlanPageText.pleaseContactThePersonWho}</p></div></main></FunnelLayout>;
  }

  return (
    <FunnelLayout restrained isolated>
      <main data-testid="sp-plan-page">
        <section className="funnel-hero-banner brp-hero intake-hero" data-testid="sp-plan-hero">
          <h1 data-testid="sp-plan-title">{strategyPlanText.h_fundraisingStrategyPlan}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="sp-plan-organization">{context.organization_name}</p>
          <i aria-hidden="true" />
        </section>
        <section className="intake-shell" data-testid="sp-plan-body">
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 20, background: "#fff" }} data-testid="sp-plan-text">{context.text}</div>
        </section>
      </main>
    </FunnelLayout>
  );
}
