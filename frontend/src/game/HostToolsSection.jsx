import { Link } from "react-router-dom";

const TOOLS = [
  {
    key: "call-script",
    title: "Invite Your Board",
    text: "Use this call script to personally introduce the Board Fundraising Game and explain what you need each board member to do before Game Night.",
    button: "Open Invitation Call Script",
    to: "/game/host/call-script",
  },
  {
    key: "facilitation",
    title: "Facilitate Game Night",
    text: "Use this step-by-step facilitation guide to lead your board through the Review Game, fundraising strategy review and adoption process.",
    button: "Open Facilitation Script",
    to: "/game/host/facilitation",
  },
  {
    key: "checklist",
    title: "Prepare For Game Night",
    text: "Use this checklist to make sure your board, game and meeting are ready before you begin.",
    button: "Open Game Night Checklist",
    to: "/game/host/checklist",
  },
];

export const HostToolsSection = () => (
  <section className="bfg-panel" data-testid="bfg-host-tools-section">
    <div className="bfg-panel-head">
      <div>
        <h2>Game Night Tools</h2>
        <p className="bfg-panel-sub">Everything you need to prepare your board and facilitate your Board Fundraising Game.</p>
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
