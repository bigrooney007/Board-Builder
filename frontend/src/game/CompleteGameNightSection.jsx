import { useNavigate } from "react-router-dom";

export const CompleteGameNightSection = ({ overview }) => {
  const navigate = useNavigate();
  if (!overview?.adopted) return null;
  const portfolios = overview.portfolios || {};
  const deliveryStatus = overview.sent_count > 0
    ? `Sent To ${overview.sent_count} Board Member${overview.sent_count === 1 ? "" : "s"}`
    : "Not Sent";
  const portfolioStatus = portfolios.total > 0
    ? `${portfolios.approved_count} of ${portfolios.total} portfolios approved`
    : "Not Started";
  const executionStatus = portfolios.execution_ready
    ? "Execution Ready"
    : portfolios.total > 0
      ? `${portfolios.toolkit_ready_count} of ${portfolios.total} execution toolkits ready`
      : "Waiting for portfolios";

  return (
    <section className="bfg-panel" data-testid="bfg-complete-game-night-section">
      <div className="bfg-panel-head">
        <div>
          <h2>Complete Game Night</h2>
          <p className="bfg-panel-sub">Your board has adopted its fundraising strategy. Send the final strategy to everyone who participated and move your board into execution.</p>
        </div>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 0 }} onClick={() => navigate("/game/complete")} data-testid="bfg-open-complete-page-btn">
          Open Game Night Complete
        </button>
      </div>
      <div className="bfg-night-summary" style={{ marginTop: 14 }}>
        <div className="bfg-summary-row"><span>1. Send The Final Strategy</span><strong data-testid="bfg-cgn-delivery-status">{deliveryStatus}</strong></div>
        <div className="bfg-summary-row"><span>2. Create Board Fundraising Portfolios</span><strong data-testid="bfg-cgn-portfolio-status">{portfolioStatus}</strong></div>
        <div className="bfg-summary-row"><span>3. Move Into Execution</span><strong data-testid="bfg-cgn-execution-status">{executionStatus}</strong></div>
      </div>
      {overview.sent_count === 0 ? (
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16 }} onClick={() => navigate("/game/complete?send=1")} data-testid="bfg-send-adopted-strategy-btn">
          Send Final Strategy To Board
        </button>
      ) : (
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 16 }} onClick={() => navigate("/game/complete?send=1")} data-testid="bfg-manage-strategy-delivery-btn">
          Manage Strategy Delivery
        </button>
      )}
    </section>
  );
};

export default CompleteGameNightSection;
