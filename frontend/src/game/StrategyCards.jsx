import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { MODE_LABELS } from "./strategyRender";

export const WorkingStrategyCard = () => {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState(null);
  const [phase, setPhase] = useState("idle");
  const timer = useRef(null);

  const load = useCallback(async () => {
    try {
      const rows = (await memberApi.get("/game/strategies")).data.strategies || [];
      setStrategies(rows);
      const status = (await memberApi.get("/game/strategy/status", { params: { mode: "working" } })).data;
      if (status.status === "running") { setPhase("generating"); startPolling(); }
    } catch { setStrategies([]); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const startPolling = () => {
    clearInterval(timer.current);
    timer.current = setInterval(async () => {
      try {
        const status = (await memberApi.get("/game/strategy/status", { params: { mode: "working" } })).data;
        if (status.status === "done" && status.strategy_id) {
          clearInterval(timer.current); setPhase("idle");
          navigate(`/game/strategy/view/${status.strategy_id}`);
        } else if (status.status === "failed") {
          clearInterval(timer.current); setPhase("failed");
        }
      } catch { /* keep polling */ }
    }, 4000);
  };

  useEffect(() => { load(); return () => clearInterval(timer.current); }, [load]);

  const generate = async () => {
    setPhase("generating");
    try { await memberApi.post("/game/strategy/generate", { mode: "working" }); startPolling(); }
    catch { setPhase("failed"); }
  };

  if (strategies === null) return null;
  const working = strategies.filter((row) => row.mode === "working");
  const latest = working[0];

  return (
    <section className="bfg-panel" data-testid="bfg-working-strategy-card">
      <div className="bfg-panel-head">
        <div>
          <h2>Working Fundraising Strategy</h2>
          <p className="bfg-panel-sub">Generate a working fundraising strategy at any time using the information currently available from your organisation and board.</p>
        </div>
      </div>
      {phase === "generating" ? (
        <div style={{ marginTop: 14 }} data-testid="bfg-working-generating">
          <p className="bfg-note">Generating Your Fundraising Strategy...</p>
          <p className="bfg-note">We are bringing together your fundraising goal, organisation information and board ideas to build your strategy.</p>
          <div className="bfg-doc-loading"><span /><span /><span /></div>
        </div>
      ) : phase === "failed" ? (
        <div style={{ marginTop: 14 }} data-testid="bfg-working-failed">
          <p className="bfg-error">We Couldn't Generate Your Strategy — your information has been saved. Please try generating the strategy again.</p>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 10 }} onClick={generate} data-testid="bfg-working-try-again-btn">Try Again</button>
        </div>
      ) : latest ? (
        <div style={{ marginTop: 14 }}>
          <p className="bfg-success" style={{ fontWeight: 700 }}>Working Strategy Available</p>
          <div className="bfg-bm-actions">
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => navigate(`/game/strategy/view/${latest.strategy_id}`)} data-testid="bfg-view-working-strategy-btn">View Strategy</button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={generate} data-testid="bfg-generate-updated-btn">Generate Updated Version</button>
          </div>
          <p className="bfg-note" style={{ marginTop: 8 }}>This will create a new version using the information currently available. Your previous strategy will remain saved.</p>
        </div>
      ) : (
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 14 }} onClick={generate} data-testid="bfg-generate-working-btn">
          Generate Working Strategy
        </button>
      )}
    </section>
  );
};

export const AdoptedStrategyCard = ({ goalDisplay }) => {
  const navigate = useNavigate();
  const [adopted, setAdopted] = useState(null);
  const [portfolioSummary, setPortfolioSummary] = useState(null);
  useEffect(() => {
    memberApi.get("/game/strategies").then((r) => {
      const row = (r.data.strategies || []).find((item) => item.status === "adopted") || false;
      setAdopted(row);
      if (row) {
        memberApi.get("/game/portfolios").then((res) => setPortfolioSummary(res.data)).catch(() => {});
      }
    }).catch(() => setAdopted(false));
  }, []);
  if (!adopted) return null;
  return (
    <section className="bfg-panel" data-testid="bfg-adopted-strategy-card">
      <div className="bfg-panel-head">
        <div>
          <h2>Fundraising Strategy</h2>
          <p className="bfg-panel-sub">
            Status: <strong style={{ color: "#34d399" }}>Adopted</strong>
            {goalDisplay && <> · Goal: {goalDisplay}</>}
            {adopted.adopted_at && <> · Adopted: {new Date(adopted.adopted_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}</>}
          </p>
        </div>
        <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 0 }}
          onClick={() => navigate(`/game/strategy/view/${adopted.strategy_id}`)} data-testid="bfg-view-adopted-strategy-btn">
          View Adopted Strategy
        </button>
      </div>
      {portfolioSummary?.execution_ready && (
        <div style={{ marginTop: 16 }} data-testid="bfg-execution-ready">
          <p className="bfg-eyebrow" style={{ marginBottom: 6 }}>Your Board Fundraising Game — Strategy Adopted</p>
          <p style={{ fontWeight: 700, color: "#34d399" }}>Execution Ready</p>
          <p className="bfg-note">
            Your fundraising strategy has been adopted, board roles are being confirmed and approved board members can now access the resources they need to execute.
          </p>
        </div>
      )}
      <div style={{ marginTop: 16 }}>
        <p className="bfg-eyebrow" style={{ marginBottom: 6 }}>Next Step</p>
        <p style={{ fontWeight: 700, color: "#f8fafc" }}>
          {portfolioSummary && portfolioSummary.total > 0 ? "Board Fundraising Portfolios" : "Create Board Fundraising Portfolios"}
        </p>
        <p className="bfg-note">
          Turn your board's participation choices and Game Night commitments into a clear fundraising role for every board member.
        </p>
        {portfolioSummary && portfolioSummary.total > 0 && (
          <p className="bfg-note" data-testid="bfg-dash-portfolio-counts">
            {portfolioSummary.approved_count} of {portfolioSummary.total} portfolios approved · {portfolioSummary.toolkit_ready_count} of {portfolioSummary.total} execution toolkits ready
          </p>
        )}
        <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 12 }}
          onClick={() => navigate("/game/portfolios")} data-testid="bfg-create-portfolios-link">
          {portfolioSummary && portfolioSummary.total > 0 ? "Open Board Fundraising Portfolios" : "Create Board Fundraising Portfolios"}
        </button>
      </div>
    </section>
  );
};

export const StrategiesHistoryCard = () => {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState(null);
  useEffect(() => {
    memberApi.get("/game/strategies").then((r) => setStrategies(r.data.strategies || [])).catch(() => setStrategies([]));
  }, []);
  if (!strategies || strategies.length === 0) return null;
  return (
    <section className="bfg-panel" data-testid="bfg-strategies-history-card">
      <h2>Fundraising Strategies</h2>
      <div className="bfg-gg-playerlist" style={{ marginTop: 14 }}>
        {strategies.map((row) => (
          <div className="bfg-summary-row" key={row.strategy_id} data-testid={`bfg-strategy-row-${row.strategy_id}`}>
            <span>
              <strong style={{ color: "#f8fafc" }}>{MODE_LABELS[row.mode] || row.mode} — Version {row.version}</strong>
              <br /><small style={{ color: "#94a3b8" }}>{row.generated_at ? new Date(row.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : ""}</small>
            </span>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate(`/game/strategy/view/${row.strategy_id}`)} data-testid={`bfg-view-strategy-${row.strategy_id}`}>View</button>
          </div>
        ))}
      </div>
    </section>
  );
};
