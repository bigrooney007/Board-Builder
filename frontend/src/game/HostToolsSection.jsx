import { Link } from "react-router-dom";

const TOOLS = [
  {
    key: "call-script",
    title: "Call Script",
    text: "Push board members to complete the game before the meeting and make sure they know the invitation is already in their inbox.",
    button: "Open Call Script",
    to: "/game/host/call-script",
  },
  {
    key: "facilitation",
    title: "Facilitation Guide",
    text: "A step-by-step guide to running your Board Fundraising Day/Night — before, during and after the meeting.",
    button: "Open Facilitation Guide",
    to: "/game/host/facilitation",
  },
  {
    key: "checklist",
    title: "Checklist",
    text: "Make sure your board, game and meeting are ready before, during and after your Board Fundraising Day/Night.",
    button: "Open Checklist",
    to: "/game/host/checklist",
  },
];

export const HostToolsSection = () => (
  <section className="bfg-panel" data-testid="bfg-host-tools-section">
    <div className="bfg-panel-head">
      <div>
        <h2>Meeting Resources</h2>
        <p className="bfg-panel-sub">Use the Call Script, Facilitation Guide and Checklist to prepare your board members and run the meeting.</p>
      </div>
    </div>
    <div className="bfg-ht-cards">
      {TOOLS.map((tool) => (
        <div className="bfg-ht-card" key={tool.key} data-testid={`bfg-host-tool-${tool.key}`}>
          <h4>{tool.title}</h4>
          <p>{tool.text}</p>
          <Link className="bfg-btn bfg-btn-primary bfg-btn-sm" to={tool.to} data-testid={`bfg-open-${tool.key}-btn`}>{tool.button}</Link>
        </div>
      ))}
    </div>
  </section>
);

export default HostToolsSection;
