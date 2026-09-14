import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

const JOURNEY_STEPS = [
  "Board Members Invited",
  "Individual Ideas Collected",
  "Board Priorities Identified",
  "Fundraising Strategy Created",
  "Board Strategy Reviewed",
  "Fundraising Strategy Adopted",
];

const fmtDateTime = (raw) => {
  if (!raw) return "";
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
};

const DeliveryModal = ({ overview, onClose, onSent }) => {
  const [selected, setSelected] = useState(() => new Set(overview.recipients.map((row) => row.member_id)));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [retrying, setRetrying] = useState("");
  const origin = { origin_url: window.location.origin };

  const toggle = (memberId) => setSelected((current) => {
    const next = new Set(current);
    if (next.has(memberId)) next.delete(memberId); else next.add(memberId);
    return next;
  });

  const send = async () => {
    setBusy(true); setError("");
    try {
      const response = await memberApi.post("/game/postgame/send", { member_ids: [...selected], ...origin });
      setResult(response.data);
      onSent();
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "The strategy could not be sent. Please try again.");
    }
    setBusy(false);
  };

  const retry = async (row) => {
    setRetrying(row.member_id);
    try {
      await memberApi.post(`/game/postgame/send/${row.member_id}`, origin);
      setResult((current) => ({ sent: current.sent + 1, failed: current.failed.filter((item) => item.member_id !== row.member_id) }));
      onSent();
    } catch { /* keep in failed list */ }
    setRetrying("");
  };

  if (result) {
    return (
      <div className="bfg-modal-overlay" data-testid="bfg-delivery-result-modal">
        <div className="bfg-modal" style={{ maxWidth: 620 }}>
          <h2>Adopted Strategy Sent</h2>
          <p className="bfg-note" style={{ marginTop: 10 }}>Your board members now have access to the fundraising strategy they created together.</p>
          <p style={{ marginTop: 14, fontWeight: 700, color: "#34d399" }} data-testid="bfg-delivery-sent-count">Sent Successfully: {result.sent}</p>
          {result.failed.length > 0 && (
            <div style={{ marginTop: 10 }} data-testid="bfg-delivery-failed-list">
              <p style={{ fontWeight: 700 }} className="bfg-error">Could Not Be Sent: {result.failed.length}</p>
              {result.failed.map((row) => (
                <div className="bfg-summary-row" key={row.member_id} data-testid={`bfg-delivery-failed-${row.member_id}`}>
                  <span>{row.full_name} — {row.email}</span>
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={retrying === row.member_id}
                    onClick={() => retry(row)} data-testid={`bfg-delivery-retry-${row.member_id}`}>
                    {retrying === row.member_id ? "Retrying…" : "Retry"}
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="bfg-form-actions" style={{ marginTop: 18 }}>
            <span />
            <button className="bfg-btn bfg-btn-primary" onClick={onClose} data-testid="bfg-delivery-result-close">Close</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bfg-modal-overlay" data-testid="bfg-delivery-modal">
      <div className="bfg-modal" style={{ maxWidth: 640 }}>
        <h2>Send Your Adopted Fundraising Strategy</h2>
        <p className="bfg-note" style={{ marginTop: 10 }}>
          Your Board Fundraising Game is complete. Choose the board members who should receive the strategy your board adopted.
        </p>
        <div style={{ marginTop: 14, maxHeight: 320, overflowY: "auto" }}>
          {overview.recipients.map((row) => (
            <label className="bfg-ht-check" key={row.member_id} style={{ color: "#e2e8f0" }} data-testid={`bfg-delivery-recipient-${row.member_id}`}>
              <input type="checkbox" checked={selected.has(row.member_id)} onChange={() => toggle(row.member_id)} />
              <span style={{ textDecoration: "none", color: "#e2e8f0" }}>
                <strong>{row.full_name}</strong> — {row.email}
                <br />
                <small style={{ color: "#94a3b8" }}>
                  {row.game_status}
                  {row.group_joined && " · Joined Game Night"}
                  {" · "}
                  {row.delivery.status === "sent" ? `Strategy sent ${fmtDateTime(row.delivery.sent_at)}` : row.delivery.status === "delivery_failed" ? "Delivery failed" : "Strategy not sent"}
                </small>
              </span>
            </label>
          ))}
        </div>
        <p style={{ marginTop: 12, fontWeight: 700 }} data-testid="bfg-delivery-selected-count">{selected.size} Board Members Selected</p>
        {error && <p className="bfg-error" data-testid="bfg-delivery-error">{error}</p>}
        <div className="bfg-form-actions" style={{ marginTop: 16 }}>
          <button className="bfg-btn bfg-btn-ghost" onClick={onClose} data-testid="bfg-delivery-cancel">Cancel</button>
          <button className="bfg-btn bfg-btn-primary" disabled={busy || selected.size === 0} onClick={send} data-testid="bfg-delivery-send-btn">
            {busy ? "Sending…" : "Send Strategy"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default function GameNightCompletePage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { member, loading } = useMemberAuth();
  const [overview, setOverview] = useState(null);
  const [showSend, setShowSend] = useState(false);

  useEffect(() => { document.title = "Game Night Complete | Board Fundraising Game"; }, []);

  const load = useCallback(() => {
    memberApi.get("/game/postgame/overview")
      .then((response) => {
        if (!response.data.adopted) { navigate("/game/dashboard", { replace: true }); return; }
        setOverview(response.data);
      })
      .catch(() => navigate("/game/dashboard", { replace: true }));
  }, [navigate]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    load();
  }, [loading, member, navigate, load]);

  useEffect(() => {
    if (overview && params.get("send") === "1") {
      setShowSend(true);
      setParams({}, { replace: true });
    }
  }, [overview, params, setParams]);

  if (!overview) return <div className="bfg" style={{ minHeight: "100vh" }} />;
  const portfolios = overview.portfolios || {};

  return (
    <BfgShell nav={
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/dashboard")} data-testid="bfg-gc-back-btn">Back To Dashboard</button>
    }>
      <main className="bfg-flow" data-testid="bfg-game-complete-page" style={{ maxWidth: 860, margin: "0 auto", padding: "26px 16px 70px" }}>
        <section className="bfg-panel">
          <p className="bfg-eyebrow">{overview.organisation_name}</p>
          <h1>Game Night Complete</h1>
          <div className="bfg-night-summary" style={{ marginTop: 12 }} data-testid="bfg-gc-header-meta">
            <div className="bfg-summary-row"><span>Fundraising Goal</span><strong>{overview.goal_display}</strong></div>
            <div className="bfg-summary-row"><span>Strategy Status</span><strong style={{ color: "#34d399" }}>Adopted</strong></div>
            {overview.adopted_at && <div className="bfg-summary-row"><span>Adopted</span><strong>{fmtDateTime(overview.adopted_at)}</strong></div>}
          </div>
          <h2 style={{ marginTop: 20 }}>Your Board Fundraising Game Is Complete</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Your board has moved from individual ideas to collective priorities, created its fundraising strategy and adopted the plan it will execute.
          </p>
        </section>

        <section className="bfg-panel" data-testid="bfg-gc-journey">
          <h2>Your Board's Journey</h2>
          <div style={{ marginTop: 12 }}>
            {JOURNEY_STEPS.map((step) => (
              <p key={step} style={{ marginTop: 6, color: "#e2e8f0" }} data-testid={`bfg-gc-journey-${step.replace(/\s+/g, "-").toLowerCase()}`}>
                <span style={{ color: "#34d399", fontWeight: 700, marginRight: 8 }}>✓</span>{step}
              </p>
            ))}
          </div>
          <div className="bfg-night-summary" style={{ marginTop: 16 }}>
            <div className="bfg-summary-row"><span>Board Portfolios</span>
              <strong data-testid="bfg-gc-journey-portfolios">{portfolios.total > 0 ? `${portfolios.approved_count} of ${portfolios.total} approved` : "Not Started"}</strong>
            </div>
            <div className="bfg-summary-row"><span>Execution Toolkits</span>
              <strong data-testid="bfg-gc-journey-toolkits">{portfolios.total > 0 ? `${portfolios.toolkit_ready_count} of ${portfolios.total} ready` : "Not Started"}</strong>
            </div>
          </div>
        </section>

        <section className="bfg-panel" data-testid="bfg-gc-action-send">
          <h2>1. Send The Strategy To Your Board</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>Give every participating board member access to the strategy your board adopted together.</p>
          <p style={{ marginTop: 12, fontWeight: 700 }} data-testid="bfg-gc-delivery-count">
            {overview.sent_count} of {overview.total_recipients} Board Members Sent
          </p>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 12 }} onClick={() => setShowSend(true)}
            data-testid="bfg-gc-send-strategy-btn">
            {overview.sent_count >= overview.total_recipients && overview.total_recipients > 0 ? "Manage Strategy Delivery" : "Send Adopted Strategy"}
          </button>
        </section>

        <section className="bfg-panel" data-testid="bfg-gc-action-portfolios">
          <h2>2. Create Board Fundraising Portfolios</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>Turn each board member's participation choices and Game Night commitments into a clear execution role.</p>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 12 }} onClick={() => navigate("/game/portfolios")}
            data-testid="bfg-gc-portfolios-btn">
            {portfolios.total > 0 ? "Manage Board Portfolios" : "Create Board Fundraising Portfolios"}
          </button>
        </section>

        <section className="bfg-panel" data-testid="bfg-gc-action-execution">
          <h2>3. Equip Your Board To Execute</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Once board members approve their portfolios, they can generate the tools, scripts, templates and resources required to perform their role.
          </p>
          <div className="bfg-night-summary" style={{ marginTop: 12 }}>
            <div className="bfg-summary-row"><span>Portfolios Approved</span><strong data-testid="bfg-gc-approved-count">{portfolios.approved_count} of {portfolios.total}</strong></div>
            <div className="bfg-summary-row"><span>Execution Toolkits Ready</span><strong data-testid="bfg-gc-toolkits-count">{portfolios.toolkit_ready_count} of {portfolios.total}</strong></div>
          </div>
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 12 }} onClick={() => navigate("/game/portfolios")}
            data-testid="bfg-gc-readiness-btn">View Board Execution Readiness</button>
        </section>
      </main>

      {showSend && <DeliveryModal overview={overview} onClose={() => setShowSend(false)} onSent={load} />}
    </BfgShell>
  );
}
