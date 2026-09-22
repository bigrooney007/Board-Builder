import { Link } from "react-router-dom";

export const HostToolsSection = () => (
  <section className="bfg-panel" data-testid="bfg-host-tools-section">
    <div className="bfg-panel-head">
      <div>
        <p className="bfg-eyebrow">STEP 5</p>
        <h2>Board Fundraising Game Guide</h2>
        <p className="bfg-panel-sub">Use the facilitation guide if you want a step-by-step reference for running the Group Game with your board. Call scripts stay with each Board Member inside the invitation section where you actually need them.</p>
      </div>
      <Link className="bfg-btn bfg-btn-primary bfg-btn-sm" to="/game/host/facilitation" data-testid="bfg-open-facilitation-btn">Open Fundraising Game Guide</Link>
    </div>
  </section>
);

export default HostToolsSection;
