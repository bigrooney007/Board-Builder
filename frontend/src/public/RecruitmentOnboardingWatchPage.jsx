import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "../member/sgr.css";
import "../funnels/strategic-planning-dashboard.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RecruitmentOnboardingWatchPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    axios.get(`${API}/public/onboarding-session/${token}`)
      .then((response) => { setData(response.data); setError(""); })
      .catch((err) => setError(err.response?.data?.detail || "This onboarding session is not available."));
  }, [token]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 2000);
    return () => window.clearInterval(timer);
  }, [load]);

  return (
    <main className="member-page public-form-page" data-testid="public-onboarding-session" style={{ minHeight: "100vh", paddingTop: 50 }}>
      {error && <section className="member-card" style={{ maxWidth: 760, margin: "0 auto" }}><h2>{error}</h2></section>}
      {!error && !data && <section className="member-card" style={{ maxWidth: 760, margin: "0 auto" }}><p>Joining the onboarding session…</p></section>}
      {data && (
        <section className="member-card" style={{ maxWidth: 900, margin: "0 auto" }}>
          <p className="eyebrow">{data.organization_name || "BOARD MEMBER ONBOARDING"}</p>
          {data.status === "NOT STARTED" && <><h1>Onboarding Session</h1><p>The facilitator is preparing the first section. Keep this page open. It will update automatically.</p></>}
          {data.status === "COMPLETED" && <><h1>Onboarding Session Complete</h1><p>Thank you for participating. You can close this page.</p></>}
          {data.status === "IN PROGRESS" && data.section && (
            <>
              <div className="sp-session-topline"><span>Section {data.current_section_index+1} of {data.total_sections}</span><span>FOLLOWING FACILITATOR</span></div>
              <h1>{data.section.title}</h1>
              <div className="detail-section" style={{ whiteSpace: "pre-wrap", textAlign: "left", fontSize: "1.05rem", lineHeight: 1.7 }}>{data.section.content}</div>
              <p className="workspace-note">Your screen follows the facilitator automatically. You do not need to click Next.</p>
            </>
          )}
        </section>
      )}
    </main>
  );
}
