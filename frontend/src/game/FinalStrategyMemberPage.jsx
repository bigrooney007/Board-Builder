import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "./gameShared";
import { StrategyDocument } from "./strategyRender";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function FinalStrategyMemberPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [showCta, setShowCta] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      const first = document.getElementById("strategy-executive_summary");
      if (first && first.getBoundingClientRect().top < window.innerHeight * 0.85) setShowCta(true);
    };
    window.addEventListener("scroll", onScroll);
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, [data]);

  useEffect(() => { document.title = "Your Board Fundraising Strategy | Board Fundraising Game"; }, []);
  useEffect(() => {
    axios.get(`${API}/game/final/${token}`)
      .then((response) => setData(response.data))
      .catch(() => setError("This link is not valid."));
  }, [token]);

  if (error) {
    return (
      <BfgShell>
        <main className="bfg-flow" style={{ textAlign: "center" }}>
          <p className="bfg-error" style={{ marginTop: 40 }}>{error}</p>
        </main>
      </BfgShell>
    );
  }
  if (!data) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  if (!data.ready) {
    return (
      <BfgShell>
        <main className="bfg-flow" style={{ textAlign: "center" }} data-testid="bfg-member-final-pending">
          <h1 style={{ marginTop: 40 }}>Your Final Fundraising Strategy Is Being Prepared</h1>
          <p style={{ marginTop: 14 }}>{data.organization_name} will let you know as soon as it is ready.</p>
        </main>
      </BfgShell>
    );
  }

  return (
    <BfgShell>
      <main className="bfg-dash" data-testid="bfg-member-final-page" style={{ maxWidth: 900, paddingBottom: 110 }}>
        <div style={{ textAlign: "right", marginBottom: 10 }}>
          <a className="bfg-btn bfg-btn-ghost bfg-btn-sm" data-testid="bfg-member-final-download"
            href={`${API}/game/final/${token}/download`}>
            Download Strategy
          </a>
        </div>
        <StrategyDocument strategy={data.strategy} />
        {showCta && data.portfolio_token && data.participant_role === "board_member" && (
          <div style={{
            position: "fixed", left: 0, right: 0, bottom: 0, zIndex: 500,
            background: "rgba(255,255,255,0.96)", borderTop: "1px solid #e5e7eb",
            padding: "12px 20px", display: "flex", justifyContent: "center",
            boxShadow: "0 -8px 24px rgba(0,0,0,0.08)",
          }} data-testid="bfg-member-final-sticky-cta">
            <button className="bfg-btn bfg-btn-primary" onClick={() => navigate(`/board-portfolio/${data.portfolio_token}`)}
              data-testid="bfg-see-how-involved-btn">
              How Do I Get Involved?
            </button>
          </div>
        )}
      </main>
    </BfgShell>
  );
}
