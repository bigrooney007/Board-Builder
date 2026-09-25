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
  const [selected, setSelected] = useState(() => new Set(
    overview.recipients.filter((row) => row.delegation?.founder_approved).map((row) => row.member_id)
  ));
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
          <p style={{ marginTop: 14, fontWeight: 700, color: "#059669" }} data-testid="bfg-delivery-sent-count">Sent Successfully: {result.sent}</p>
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
          Choose the participants whose delegation you have approved. Anyone still marked Review Required must be reviewed before their strategy email can be sent.
        </p>
        <div style={{ marginTop: 14, maxHeight: 320, overflowY: "auto" }}>
          {overview.recipients.map((row) => {
            const delegationApproved = Boolean(row.delegation?.founder_approved);
            return (
            <label className="bfg-ht-check" key={row.member_id} style={{ color: delegationApproved ? "#374151" : "#94a3b8" }} data-testid={`bfg-delivery-recipient-${row.member_id}`}>
              <input type="checkbox" disabled={!delegationApproved} checked={selected.has(row.member_id)} onChange={() => toggle(row.member_id)} />
              <span style={{ textDecoration: "none", color: "#374151" }}>
                <strong>{row.full_name}</strong> — {row.email}
                <br />
                <small style={{ color: "#6B7280" }}>
                  {row.game_status}
                  {row.group_joined && " · Joined Group Game"}
                  {" · "}
                  {delegationApproved ? "Delegation founder-approved" : "Delegation review required"}
                  {" · "}
                  {row.delivery.status === "sent" ? `Strategy sent ${fmtDateTime(row.delivery.sent_at)}` : row.delivery.status === "delivery_failed" ? "Delivery failed" : "Strategy not sent"}
                </small>
              </span>
            </label>
          )})}
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
  const [relationshipBusy, setRelationshipBusy] = useState(false);
  const [relationshipNotice, setRelationshipNotice] = useState("");

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
  const relationshipSent = overview.recipients.filter((row) => row.relationship_delivery?.status === "sent").length;
  const sendRelationshipMapping = async () => {
    setRelationshipBusy(true); setRelationshipNotice("");
    try {
      const eligible = overview.recipients.filter((row) => row.delivery?.status === "sent").map((row) => row.member_id);
      const response = await memberApi.post("/game/postgame/relationships/send", { member_ids: eligible, origin_url: window.location.origin });
      setRelationshipNotice(`Relationship-mapping email sent to ${response.data.sent} participant${response.data.sent === 1 ? "" : "s"}.`);
      load();
    } catch (err) { setRelationshipNotice(err.response?.data?.detail || "The relationship-mapping emails could not be sent."); }
    setRelationshipBusy(false);
  };

  return (
    <BfgShell nav={
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/dashboard")} data-testid="bfg-gc-back-btn">Back To Dashboard</button>
    }>
      <main className="bfg-flow" data-testid="bfg-game-complete-page" style={{ maxWidth: 860, margin: "0 auto", padding: "26px 16px 70px" }}>
        <section className="bfg-panel">
          <p className="bfg-eyebrow">{overview.organization_name}</p>
          <h1>Game Night Complete</h1>
          <div className="bfg-night-summary" style={{ marginTop: 12 }} data-testid="bfg-gc-header-meta">
            <div className="bfg-summary-row"><span>Fundraising Goal</span><strong>{overview.goal_display}</strong></div>
            <div className="bfg-summary-row"><span>Strategy Status</span><strong style={{ color: "#059669" }}>Adopted</strong></div>
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
              <p key={step} style={{ marginTop: 6, color: "#374151" }} data-testid={`bfg-gc-journey-${step.replace(/\s+/g, "-").toLowerCase()}`}>
                <span style={{ color: "#059669", fontWeight: 700, marginRight: 8 }}>✓</span>{step}
              </p>
            ))}
          </div>
          <div className="bfg-night-summary" style={{ marginTop: 16 }}>
            <div className="bfg-summary-row"><span>Board Portfolios</span>
              <strong data-testid="bfg-gc-journey-portfolios">{portfolios.total > 0 ? `${portfolios.approved_count} of ${portfolios.total} approved` : "Not Started"}</strong>
            </div>
          </div>
        </section>

        <section className="bfg-panel" data-testid="bfg-gc-action-portfolios">
          <h2>1. Review And Approve Each Participant's Delegation</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Review the proposed fundraising responsibilities and activities for every participant. Edit anything that does not match what was agreed, then approve it yourself.
          </p>
          <p style={{ marginTop: 12, fontWeight: 700 }}>
            {overview.recipients.filter((row) => row.delegation?.founder_approved).length} of {overview.total_recipients} Delegations Founder-Approved
          </p>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 12 }} onClick={() => navigate("/game/portfolios")}
            data-testid="bfg-gc-portfolios-btn">REVIEW DELEGATIONS</button>
        </section>

        <section className="bfg-panel" data-testid="bfg-gc-action-send">
          <h2>2. Send The Strategy To Your Board</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Once a person's delegation is approved, send one email containing their final strategy link, Board Fundraising Portfolio link and personal fundraising assistant link. Ask them to bookmark it.
          </p>
          <p style={{ marginTop: 12, fontWeight: 700 }} data-testid="bfg-gc-delivery-count">
            {overview.sent_count} of {overview.total_recipients} Participants Sent
          </p>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 12 }} onClick={() => setShowSend(true)}
            data-testid="bfg-gc-send-strategy-btn">
            {overview.sent_count >= overview.total_recipients && overview.total_recipients > 0 ? "Manage Delivery" : "Send Strategy, Portfolio And Assistant"}
          </button>
        </section>

        <section className="bfg-panel" data-testid="bfg-gc-action-execution">
          <h2>3. Start Relationship Mapping</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Send this as a separate email about 24 hours after the strategy, Portfolio and assistant email. Board Members will recommend people, businesses and grantors in their networks who match the funding audiences your Board agreed to pursue.
          </p>
          {overview.relationship_recommended_at && <p style={{ marginTop: 10 }}><strong>Recommended send time:</strong> {new Date(overview.relationship_recommended_at).toLocaleString()}</p>}
          <p style={{ marginTop: 10, fontWeight: 700 }}>{relationshipSent} of {overview.total_recipients} Relationship-Mapping Emails Sent</p>
          {relationshipNotice && <p className="bfg-note" style={{ marginTop: 10 }}>{relationshipNotice}</p>}
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 12 }} disabled={relationshipBusy || overview.sent_count === 0} onClick={sendRelationshipMapping} data-testid="bfg-send-relationship-mapping">
            {relationshipBusy ? "SENDING…" : relationshipSent ? "RESEND RELATIONSHIP MAPPING" : "START RELATIONSHIP MAPPING"}
          </button>
        </section>

        <section className="bfg-panel" data-testid="bfg-gc-action-execution">
          <h2>4. Help Your Board Execute</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Once Board Members approve their Portfolios, their Executive Assistant recommends useful materials at the top. They create only what they need when they are ready to use it, or ask the assistant for help.
          </p>
          <div className="bfg-night-summary" style={{ marginTop: 12 }}>
            <div className="bfg-summary-row"><span>Portfolios Approved</span><strong data-testid="bfg-gc-approved-count">{portfolios.approved_count} of {portfolios.total}</strong></div>
          </div>
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 12 }} onClick={() => navigate("/game/portfolios")}
            data-testid="bfg-gc-readiness-btn">View Board Execution Readiness</button>
        </section>
      </main>

      {showSend && <DeliveryModal overview={overview} onClose={() => setShowSend(false)} onSent={load} />}
    </BfgShell>
  );
}
