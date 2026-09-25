import { useNavigate } from "react-router-dom";

export const CompleteGameNightSection = ({ overview }) => {
  const navigate = useNavigate();
  if (!overview?.adopted) return null;
  const portfolios = overview.portfolios || {};
  const founderApproved = overview.recipients?.filter((row) => row.delegation?.founder_approved).length || 0;
  const deliveryStatus = overview.sent_count > 0
    ? `Sent To ${overview.sent_count} Participant${overview.sent_count === 1 ? "" : "s"}`
    : "Not Sent";
  const portfolioStatus = portfolios.total > 0
    ? `${founderApproved} of ${overview.total_recipients || portfolios.total} delegations founder-approved`
    : "Preparing";
  const executionStatus = portfolios.total > 0
    ? `${portfolios.approved_count || 0} of ${portfolios.total} Portfolios approved, assistants available on approval`
    : "Waiting for Portfolios";

  return (
    <section className="bfg-panel" data-testid="bfg-complete-game-night-section">
      <div className="bfg-panel-head">
        <div>
          <h2>Complete Game Night</h2>
          <p className="bfg-panel-sub">Your Board's fundraising strategy is ready. Confirm each participant's delegation first, then share the strategy and move into execution.</p>
        </div>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 0 }} onClick={() => navigate("/game/complete")} data-testid="bfg-open-complete-page-btn">
          Open Game Night Complete
        </button>
      </div>
      <div className="bfg-night-summary" style={{ marginTop: 14 }}>
        <div className="bfg-summary-row"><span>1. Review Participant Delegations</span><strong data-testid="bfg-cgn-portfolio-status">{portfolioStatus}</strong></div>
        <div className="bfg-summary-row"><span>2. Send The Final Strategy</span><strong data-testid="bfg-cgn-delivery-status">{deliveryStatus}</strong></div>
        <div className="bfg-summary-row"><span>3. Move Into Execution</span><strong data-testid="bfg-cgn-execution-status">{executionStatus}</strong></div>
      </div>
      <div className="bfg-bm-actions" style={{ marginTop: 16 }}>
        <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => navigate("/game/portfolios")} data-testid="bfg-review-delegations-btn">
          REVIEW PARTICIPANT DELEGATIONS
        </button>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/complete?send=1")} data-testid="bfg-manage-strategy-delivery-btn">
          {overview.sent_count > 0 ? "MANAGE STRATEGY DELIVERY" : "SEND APPROVED STRATEGY"}
        </button>
      </div>
    </section>
  );
};

export default CompleteGameNightSection;
