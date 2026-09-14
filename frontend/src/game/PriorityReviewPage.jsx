import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

export default function PriorityReviewPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [areas, setAreas] = useState(null);
  const [error, setError] = useState("");
  const [phase, setPhase] = useState("review");
  const timer = useRef(null);

  useEffect(() => { document.title = "Review Your Board's Priorities | Board Fundraising Game"; }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    memberApi.get("/game/strategy/priority-review")
      .then((response) => setAreas(response.data.areas))
      .catch((err) => setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Complete the Group Review Game first."));
  }, [loading, member, navigate]);

  useEffect(() => () => clearInterval(timer.current), []);

  const updateArea = (sectionKey, updater) => setAreas((current) => current.map((area) =>
    area.section_key === sectionKey ? updater(area) : area));

  const moveToPriorities = (sectionKey, idea) => updateArea(sectionKey, (area) => ({
    ...area, priorities: [...area.priorities, idea], additional: area.additional.filter((item) => item.idea_id !== idea.idea_id) }));

  const moveToAdditional = (sectionKey, idea) => updateArea(sectionKey, (area) => ({
    ...area, priorities: area.priorities.filter((item) => item.idea_id !== idea.idea_id), additional: [idea, ...area.additional] }));

  const reorder = (sectionKey, index, direction) => updateArea(sectionKey, (area) => {
    const priorities = [...area.priorities];
    const target = index + direction;
    if (target < 0 || target >= priorities.length) return area;
    [priorities[index], priorities[target]] = [priorities[target], priorities[index]];
    return { ...area, priorities };
  });

  const generate = async () => {
    setPhase("starting"); setError("");
    try {
      await memberApi.put("/game/strategy/priority-review", {
        areas: Object.fromEntries(areas.map((area) => [area.section_key, {
          priorities: area.priorities.map((item) => item.idea_id),
          additional: area.additional.map((item) => item.idea_id),
        }])),
      });
      await memberApi.post("/game/strategy/generate", { mode: "board_prioritized" });
      setPhase("generating");
      timer.current = setInterval(async () => {
        try {
          const status = (await memberApi.get("/game/strategy/status", { params: { mode: "board_prioritized" } })).data;
          if (status.status === "done" && status.strategy_id) {
            clearInterval(timer.current);
            navigate(`/game/strategy/view/${status.strategy_id}`);
          } else if (status.status === "failed") {
            clearInterval(timer.current);
            setPhase("failed");
          }
        } catch { /* keep polling */ }
      }, 4000);
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not start generation. Please try again.");
      setPhase("review");
    }
  };

  if (loading || (!areas && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/group?results=1" data-testid="bfg-pr-back">Back to Results</Link>}>
      <main className="bfg-dash" data-testid="bfg-priority-review-page" style={{ maxWidth: 860 }}>
        {phase === "generating" || phase === "starting" ? (
          <div className="bfg-panel" style={{ textAlign: "center" }} data-testid="bfg-strategy-generating">
            <h2>Building Your Fundraising Strategy</h2>
            <p className="bfg-panel-sub" style={{ marginTop: 12 }}>
              We are bringing together your fundraising goal, organisation information and board ideas to build your strategy.
            </p>
            <div className="bfg-doc-loading"><span /><span /><span /></div>
          </div>
        ) : phase === "failed" ? (
          <div className="bfg-panel" style={{ textAlign: "center" }} data-testid="bfg-strategy-failed">
            <h2>We Couldn't Generate Your Strategy</h2>
            <p className="bfg-panel-sub" style={{ marginTop: 12 }}>Your information has been saved. Please try generating the strategy again.</p>
            <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} onClick={generate} data-testid="bfg-strategy-try-again-btn">Try Again</button>
          </div>
        ) : (
          <>
            <p className="bfg-eyebrow">Board-Prioritised Strategy</p>
            <h1>Review Your Board's Priorities</h1>
            <p style={{ marginTop: 10, maxWidth: 640 }}>
              These are the ideas your board prioritised during the Group Review Game. Review them before generating your fundraising strategy.
            </p>
            {error && <div className="bfg-panel" style={{ marginTop: 16 }}><p className="bfg-error">{error}</p></div>}
            {(areas || []).map((area) => (
              <div className="bfg-panel" key={area.section_key} style={{ marginTop: 18 }} data-testid={`bfg-pr-area-${area.section_key}`}>
                <h2>{area.title.replace(/^Round \d+: /, "")}</h2>
                <p className="bfg-panel-sub" style={{ marginTop: 10 }}>Board Priorities</p>
                {area.priorities.length === 0 && <p className="bfg-note">No priorities selected for this area.</p>}
                <div className="bfg-gg-playerlist">
                  {area.priorities.map((idea, index) => (
                    <div className="bfg-pr-row" key={idea.idea_id} data-testid={`bfg-pr-priority-${idea.idea_id}`}>
                      <span className="bfg-gg-pos">#{index + 1}</span>
                      <span className="bfg-pr-text">{idea.text}</span>
                      <span className="bfg-pr-actions">
                        <button onClick={() => reorder(area.section_key, index, -1)} disabled={index === 0} aria-label="Move up" data-testid={`bfg-pr-up-${idea.idea_id}`}>↑</button>
                        <button onClick={() => reorder(area.section_key, index, 1)} disabled={index === area.priorities.length - 1} aria-label="Move down" data-testid={`bfg-pr-down-${idea.idea_id}`}>↓</button>
                        <button onClick={() => moveToAdditional(area.section_key, idea)} data-testid={`bfg-pr-demote-${idea.idea_id}`}>Move To Additional Board Ideas</button>
                      </span>
                    </div>
                  ))}
                </div>
                <p className="bfg-panel-sub" style={{ marginTop: 16 }}>Additional Board Ideas</p>
                {area.additional.length === 0 && <p className="bfg-note">No additional ideas for this area.</p>}
                <div className="bfg-gg-playerlist">
                  {area.additional.map((idea) => (
                    <div className="bfg-pr-row" key={idea.idea_id} data-testid={`bfg-pr-additional-${idea.idea_id}`}>
                      <span className="bfg-pr-text">{idea.text}</span>
                      <span className="bfg-pr-actions">
                        <button onClick={() => moveToPriorities(area.section_key, idea)} data-testid={`bfg-pr-promote-${idea.idea_id}`}>Move To Board Priorities</button>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {areas && (
              <div className="bfg-panel" style={{ textAlign: "center", marginTop: 18 }}>
                <button className="bfg-btn bfg-btn-primary" onClick={generate} data-testid="bfg-generate-strategy-btn">
                  Generate Our Fundraising Strategy
                </button>
                <p className="bfg-note" style={{ marginTop: 12 }}>
                  Your Board Priorities will guide the strategy. Additional Board Ideas will remain available as secondary opportunities and will not be discarded.
                </p>
              </div>
            )}
          </>
        )}
      </main>
    </BfgShell>
  );
}
