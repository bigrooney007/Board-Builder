import { useState } from "react";
import axios from "axios";
import { clearAdminPreview } from "@/adminPreview";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

const DASHBOARDS = [
  { key: "recruitment", name: "Board Recruitment", description: "Open the complete customer recruitment workspace and its step-by-step execution flow." },
  { key: "board-fundraising-game", name: "Board Fundraising Game", description: "Open the customer Game dashboard with its preparation, board participation, meeting, strategy, and execution sections." },
  { key: "strategic-planning", name: "Strategic Planning", description: "Open the complete customer Strategic Planning dashboard and board-led planning workflow." },
  { key: "board-recommitment", name: "Board Recommitment", description: "Open the customer Recommitment dashboard, response workflow, conversations, and final board-member outcomes." },
];

export const DashboardPreviewSection = () => {
  const [opening, setOpening] = useState("");
  const [error, setError] = useState("");
  const openDashboard = async (product) => {
    setOpening(product); setError("");
    try {
      const response = await client.post(`/admin/dashboard-preview/${product}`);
      // These launchers create a real, isolated preview-member session. A stale
      // public-funnel preview header would otherwise override that member cookie
      // and split reads and writes between two different preview identities.
      clearAdminPreview();
      window.location.assign(response.data.dashboard_url);
    } catch (err) {
      setError(err.response?.data?.detail || "The dashboard preview could not be opened.");
      setOpening("");
    }
  };
  return <section data-testid="admin-dashboard-previews">
    <div className="admin-funnel-numbers-head"><div><h2>Present The Four Product Dashboards</h2><p>Open each real customer dashboard with a fully preloaded test journey: completed forms, realistic participant responses, transcripts, decisions, materials and downstream outputs. The preview workspace is isolated from customer accounts, Stripe revenue and customer reporting. No separate customer login is required.</p></div></div>
    {error && <p className="submit-error" data-testid="dashboard-preview-error">{error}</p>}
    <div className="admin-preview-dashboard-grid">
      {DASHBOARDS.map((dashboard, index) => <article className="member-card" key={dashboard.key} data-testid={`dashboard-preview-${dashboard.key}`}>
        <p className="eyebrow">DASHBOARD {index + 1}</p><h3>{dashboard.name}</h3><p>{dashboard.description}</p>
        <button className="button button-small" onClick={() => openDashboard(dashboard.key)} disabled={Boolean(opening)} data-testid={`open-dashboard-${dashboard.key}`}>{opening === dashboard.key ? "OPENING…" : "OPEN DASHBOARD"}</button>
      </article>)}
    </div>
  </section>;
};
