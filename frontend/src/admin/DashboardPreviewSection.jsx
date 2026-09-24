import { useState } from "react";
import axios from "axios";
import { clearAdminPreview } from "@/adminPreview";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

const DASHBOARDS = [
  { key: "recruitment", name: "Board Recruitment", description: "Test the six Recruitment Questions, recommended Board profiles, campaign, applicants, onboarding and final Board Member Portfolio." },
  { key: "board-fundraising-game", name: "Board Fundraising Game", description: "Test the founder Game, Board invitations, Group Game, fundraising strategy, delegations and execution." },
  { key: "strategic-planning", name: "Strategic Planning", description: "Test organization setup, Board forms, live planning session, Strategic Plan, confirmed roles and Leadership Portfolios." },
  { key: "board-recommitment", name: "Board Recommitment", description: "Test the four setup questions, two Recommitment Forms, responses, conversations, final outcomes and Board Member Portfolios." },
];

export const DashboardPreviewSection = () => {
  const [opening, setOpening] = useState("");
  const [error, setError] = useState("");

  const launch = async (product, mode) => {
    const key = `${mode}-${product}`;
    setOpening(key);
    setError("");
    try {
      const endpoint = mode === "fresh"
        ? `/admin/dashboard-preview/fresh/${product}`
        : `/admin/dashboard-preview/${product}`;
      const response = await client.post(endpoint);
      clearAdminPreview();
      window.location.assign(response.data.start_url || response.data.dashboard_url);
    } catch (err) {
      setError(err.response?.data?.detail || "The client test could not be opened.");
      setOpening("");
    }
  };

  return <section data-testid="admin-dashboard-previews">
    <div className="admin-funnel-numbers-head">
      <div>
        <h2>Client Testing Center</h2>
        <p>
          Your Admin login is the only gate. Each launch creates an isolated test-customer session, never charges Stripe,
          never changes a real customer account, and never uses your Admin password as a customer password.
        </p>
      </div>
    </div>

    <div className="member-card" style={{ marginBottom: 18 }}>
      <p className="eyebrow">HOW TO TEST</p>
      <h3>Use Both Test Modes</h3>
      <p><strong>Start Fresh Client Test</strong> begins at the real post-payment entry point with only the information a genuine customer would already have supplied before payment. Use this to test the journey in order.</p>
      <p><strong>Open Fully Preloaded Journey</strong> gives you completed forms, participant responses, transcripts, decisions, plans, Portfolios and downstream records so you can inspect later stages without repeating all the work.</p>
      <p>Public homepages, demonstration videos and checkout pages remain normal public pages. The Admin launcher replaces only the payment step.</p>
    </div>

    {error && <p className="submit-error" data-testid="dashboard-preview-error">{error}</p>}

    <div className="admin-preview-dashboard-grid">
      {DASHBOARDS.map((dashboard, index) => {
        const freshKey = `fresh-${dashboard.key}`;
        const loadedKey = `loaded-${dashboard.key}`;
        return <article className="member-card" key={dashboard.key} data-testid={`dashboard-preview-${dashboard.key}`}>
          <p className="eyebrow">PATHWAY {index + 1}</p>
          <h3>{dashboard.name}</h3>
          <p>{dashboard.description}</p>

          <div style={{ display: "grid", gap: 8, marginTop: 16 }}>
            <button
              className="button button-small"
              onClick={() => launch(dashboard.key, "fresh")}
              disabled={Boolean(opening)}
              data-testid={`start-fresh-${dashboard.key}`}
            >
              {opening === freshKey ? "OPENING FRESH TEST…" : "START FRESH CLIENT TEST"}
            </button>

            <button
              className="button button-back button-small"
              onClick={() => launch(dashboard.key, "loaded")}
              disabled={Boolean(opening)}
              data-testid={`open-dashboard-${dashboard.key}`}
            >
              {opening === loadedKey ? "OPENING PRELOADED JOURNEY…" : "OPEN FULLY PRELOADED JOURNEY"}
            </button>
          </div>
        </article>;
      })}
    </div>
  </section>;
};
