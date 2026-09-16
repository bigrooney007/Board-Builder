import { useCallback, useEffect, useRef, useState } from "react";

const STEPS = [
  { key: "working-strategy", title: "Working Fundraising Strategy",
    text: "This is where your current fundraising strategy lives. View the most recent version at any time or generate an updated version as new information becomes available from your organization and board." },
  { key: "board-participation", title: "Board Participation",
    text: "This is where you can see who has been invited to play the Board Fundraising Game and who has completed their game before your board meeting." },
  { key: "prepare-meeting", title: "Prepare For Fundraising Day/Night",
    text: "Add the details of your next board meeting so your Board Fundraising Day/Night is connected to a specific date, time and meeting." },
  { key: "meeting-resources", title: "Meeting Resources",
    text: "Use the Call Script, Facilitation Guide and Checklist to prepare your board members and run the meeting." },
  { key: "group-game", title: "Group Game",
    text: "During your Board Fundraising Day/Night, use the Group Game to bring everyone's ideas together, review them and identify the board's fundraising priorities." },
  { key: "complete-meeting", title: "Complete Your Board Meeting",
    text: "After the Group Game, add your meeting transcript so we can capture the decisions, changes, assignments and additional ideas discussed by the board." },
  { key: "final-strategy", title: "Final Fundraising Strategy",
    text: "Once your meeting is complete, your final strategy brings together your organization's information, board ideas, priorities and meeting decisions into one fundraising strategy." },
  { key: "board-portfolios", title: "Board Portfolios",
    text: "Each board member receives a personal portfolio showing exactly how they will participate in building the fundraising system and raising money." },
  { key: "execution-materials", title: "Execution Materials",
    text: "Each board member receives the tools and materials they need to carry out the responsibilities they selected." },
  { key: "relationship-mapping", title: "Relationship Mapping",
    text: "Board members use Relationship Mapping to identify people, businesses and grantors in their own networks who match the funder profiles identified in your fundraising strategy." },
];

export const DashboardTour = ({ onClose }) => {
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState(null);
  const timer = useRef(null);
  const step = STEPS[index];

  const measure = useCallback(() => {
    const element = document.querySelector(`[data-tour="${STEPS[index].key}"]`);
    if (!element) { setRect(null); return; }
    const box = element.getBoundingClientRect();
    setRect({ top: box.top, left: box.left, width: box.width, height: box.height });
  }, [index]);

  useEffect(() => {
    const element = document.querySelector(`[data-tour="${step.key}"]`);
    if (element) element.scrollIntoView({ behavior: "smooth", block: "center" });
    setRect(null);
    clearTimeout(timer.current);
    timer.current = setTimeout(measure, 420);
    const onMove = () => measure();
    window.addEventListener("resize", onMove);
    window.addEventListener("scroll", onMove, true);
    return () => {
      clearTimeout(timer.current);
      window.removeEventListener("resize", onMove);
      window.removeEventListener("scroll", onMove, true);
    };
  }, [index, measure, step.key]);

  const last = index === STEPS.length - 1;
  const panelTop = rect
    ? (rect.top + rect.height + 240 < window.innerHeight ? rect.top + rect.height + 16 : Math.max(16, rect.top - 236))
    : window.innerHeight / 2 - 130;
  const panelLeft = rect ? Math.min(Math.max(16, rect.left), window.innerWidth - 396) : window.innerWidth / 2 - 190;

  return (
    <div data-testid="bfg-dashboard-tour" style={{ position: "fixed", inset: 0, zIndex: 4000 }}>
      {rect ? (
        <div style={{
          position: "fixed", top: rect.top - 8, left: rect.left - 8,
          width: rect.width + 16, height: rect.height + 16, borderRadius: 14,
          boxShadow: "0 0 0 9999px rgba(15, 23, 42, 0.62)", border: "2px solid #ffffff",
          pointerEvents: "none", transition: "all 260ms ease",
        }} />
      ) : (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15, 23, 42, 0.62)" }} />
      )}
      <div style={{
        position: "fixed", top: panelTop, left: panelLeft, width: 380, maxWidth: "calc(100vw - 32px)",
        background: "#ffffff", borderRadius: 14, padding: "20px 22px",
        boxShadow: "0 18px 50px rgba(0,0,0,0.35)", transition: "all 260ms ease",
      }} data-testid={`bfg-tour-step-${step.key}`}>
        <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: "#6B7280", textTransform: "uppercase", margin: 0 }}>
          Step {index + 1} of {STEPS.length}
        </p>
        <h3 style={{ margin: "8px 0 0", fontSize: 18, color: "#111827" }}>{step.title}</h3>
        <p style={{ marginTop: 10, fontSize: 14, lineHeight: 1.6, color: "#374151" }}>{step.text}</p>
        <div style={{ display: "flex", gap: 8, marginTop: 18, alignItems: "center" }}>
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={onClose} data-testid="bfg-tour-exit-btn">Exit Tutorial</button>
          <span style={{ flex: 1 }} />
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={index === 0}
            onClick={() => setIndex(index - 1)} data-testid="bfg-tour-back-btn">Back</button>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm"
            onClick={() => (last ? onClose() : setIndex(index + 1))} data-testid="bfg-tour-next-btn">
            {last ? "Finish" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardTour;
