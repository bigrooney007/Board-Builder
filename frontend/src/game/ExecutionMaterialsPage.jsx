import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

export default function ExecutionMaterialsPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Execution Materials | Board Fundraising Game"; }, []);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    memberApi.get("/game/portfolios").then((r) => setData(r.data))
      .catch((err) => setError(err.response?.status === 409
        ? "Compile your final fundraising strategy before opening Execution Materials."
        : "We could not load your execution materials."));
  }, [loading, member, navigate]);

  if (loading || (!data && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-em-back-dashboard">Back to Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-execution-materials-page" style={{ maxWidth: 960 }}>
        <div className="bfg-panel">
          <h1>Execution Materials</h1>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            The tools and materials created for every board member to carry out the responsibilities they selected.
          </p>
          <div className="bfg-bm-actions" style={{ marginTop: 12 }}>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/relationships")}
              data-testid="bfg-em-relationship-link">
              Open Relationship Mapping
            </button>
          </div>
        </div>
        {error && <div className="bfg-panel"><p className="bfg-error">{error}</p></div>}
        {data && (data.portfolios || []).length === 0 && (
          <div className="bfg-panel" data-testid="bfg-em-empty">
            <p className="bfg-note">No board portfolios have been created yet. Create Board Fundraising Portfolios first — execution materials are generated from each approved portfolio.</p>
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 12 }}
              onClick={() => navigate("/game/portfolios")} data-testid="bfg-em-open-portfolios-btn">
              Open Board Portfolios
            </button>
          </div>
        )}
        {data && (data.portfolios || []).map((row) => (
          <div className="bfg-panel" key={row.portfolio_id} data-testid={`bfg-em-row-${row.portfolio_id}`}>
            <div className="bfg-panel-head">
              <div>
                <h2>{row.member_name}</h2>
                <p className="bfg-panel-sub" style={{ marginTop: 4 }}>
                  Execution Materials: <strong style={{ color: row.toolkit_status === "ready" ? "#059669" : "#6B7280" }}>
                    {row.toolkit_status === "ready" ? "Ready" : row.toolkit_status === "generating" ? "Generating…" : "Waiting For Portfolio Approval"}
                  </strong>
                </p>
              </div>
              <div className="bfg-bm-actions" style={{ marginTop: 0 }}>
                {row.toolkit_status === "ready" ? (
                  <button className="bfg-btn bfg-btn-primary bfg-btn-sm"
                    onClick={() => navigate(`/game/portfolios/${row.portfolio_id}/toolkit`)} data-testid={`bfg-em-view-${row.portfolio_id}`}>
                    View Execution Materials
                  </button>
                ) : (
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm"
                    onClick={() => navigate(`/game/portfolios/${row.portfolio_id}`)} data-testid={`bfg-em-portfolio-${row.portfolio_id}`}>
                    Open Portfolio
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </main>
    </BfgShell>
  );
}
