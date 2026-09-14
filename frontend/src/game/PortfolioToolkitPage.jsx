import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { ToolkitView } from "./ToolkitView";

export default function PortfolioToolkitPage() {
  const { portfolioId } = useParams();
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Execution Toolkit | Board Fundraising Game"; }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    memberApi.get(`/game/portfolios/${portfolioId}/toolkit`)
      .then((response) => setData(response.data))
      .catch(() => setError("Execution materials are not ready for this board member yet."));
  }, [loading, member, navigate, portfolioId]);

  if (loading || (!data && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm bfg-no-print" to="/game/portfolios" data-testid="bfg-pt-back">Back to Portfolios</Link>}>
      <main className="bfg-dash" data-testid="bfg-portfolio-toolkit-page" style={{ maxWidth: 960 }}>
        {error && <div className="bfg-panel"><p className="bfg-error">{error}</p></div>}
        {data && (
          <div className="bfg-pf-doc">
            <header className="bfg-pf-header">
              <p className="bfg-pf-eyebrow">Execution Toolkit</p>
              <h1>{data.member_name}</h1>
              <p className="bfg-pf-sub">
                Execution materials generated for the responsibilities approved in their Board Fundraising Portfolio.
              </p>
            </header>
            <ToolkitView toolkit={data.toolkit} />
          </div>
        )}
      </main>
    </BfgShell>
  );
}
