import { useState } from "react";
import axios from "axios";
import { clearAdminPreview } from "@/adminPreview";
import { storeMemberToken } from "@/member/api";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

const DASHBOARDS = [
  { key: "recruitment", name: "Board Recruitment", description: "Test the current admin-published questions, guided $497 payment, branding, booking and Recruitment service workspace." },
  { key: "board-fundraising-game", name: "Board Fundraising Game", description: "Test audience-by-audience questions, personal participation, meeting setup, Board invitations, group adoption and the final approved strategy." },
  { key: "strategic-planning", name: "Strategic Planning", description: "Begin at payment confirmation with the organization answers already saved. Continue through onboarding, the dashboard, Board forms and the planning session." },
  { key: "board-recommitment", name: "Board Recommitment", description: "Begin at payment confirmation with the four answers already saved. Continue through onboarding, the dashboard, responses and Portfolios." },
];

export const DashboardPreviewSection = () => {
  const [opening, setOpening] = useState("");
  const [error, setError] = useState("");

  const launch = async (product, mode) => {
    const key = `${mode}-${product}`;
    setOpening(key);
    setError("");
    try {
      const endpoint = mode === "intro" ? `/admin/dashboard-preview/intro/${product}` : mode === "fresh"
        ? `/admin/dashboard-preview/fresh/${product}`
        : `/admin/dashboard-preview/${product}`;
      const response = await client.post(endpoint);
      clearAdminPreview();
      sessionStorage.removeItem("operateAsUserId");
      storeMemberToken(response.data.token);
      sessionStorage.setItem("adminClientTest", "1");
      sessionStorage.setItem("adminClientTestVersion", [response.data.workflow_version || "original-current",response.data.build_identifier].filter(Boolean).join(" / "));
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
      <p><strong>Open Fully Preloaded Journey</strong> opens a fully preloaded test journey with sample forms and participant responses ready to review using the current customer workflow so you can inspect later stages without repeating all the work.</p>
      <p>The test uses the same customer pages and questions. Payments are bypassed, test records are isolated, and outgoing emails are captured. Use the introductory questionnaire button to test the updated leader questions as well.</p>
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

          {dashboard.key === "recruitment" ? <div style={{display:"grid",gap:8,marginTop:16}}><a className="button" href="/admin/services/recruitment">OPEN CURRENT RECRUITMENT TESTS AND WORKSPACE</a></div> : <div style={{ display: "grid", gap: 8, marginTop: 16 }}>
            {["strategic-planning", "board-fundraising-game"].includes(dashboard.key) && <button className="button button-small button-outline" disabled={Boolean(opening)} onClick={() => launch(dashboard.key, "intro")}>TEST CURRENT INTRODUCTORY QUESTIONS</button>}
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
          </div>}
        </article>;
      })}
    </div>
  </section>;
};
