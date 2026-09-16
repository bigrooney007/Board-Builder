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
      <main className="bfg-dash" data-testid="bfg-member-final-page" style={{ maxWidth: 900 }}>
        <div className="bfg-panel" data-testid="bfg-member-final-actions">
          <div className="bfg-panel-head">
            <div>
              <h2>{data.member_first_name ? `${data.member_first_name}, here` : "Here"} is your board's final fundraising strategy</h2>
              <p className="bfg-panel-sub" style={{ marginTop: 6 }}>
                It brings together the ideas contributed by the board, the priorities selected during the Group Game and the decisions made during your board meeting.
              </p>
            </div>
          </div>
          <div className="bfg-bm-actions" style={{ marginTop: 14 }}>
            {data.portfolio_token ? (
              <button className="bfg-btn bfg-btn-primary" onClick={() => navigate(`/board-portfolio/${data.portfolio_token}`)}
                data-testid="bfg-see-how-involved-btn">
                See How I Am Involved
              </button>
            ) : (
              <p className="bfg-note" data-testid="bfg-portfolio-pending-note">Your personal Board Fundraising Portfolio is being prepared.</p>
            )}
            <button className="bfg-btn bfg-btn-ghost" onClick={() => navigate(`/relationship-mapping/${token}`)}
              data-testid="bfg-complete-relationship-mapping-btn">
              Complete My Relationship Mapping
            </button>
          </div>
        </div>
        <StrategyDocument strategy={data.strategy} />
      </main>
    </BfgShell>
  );
}
