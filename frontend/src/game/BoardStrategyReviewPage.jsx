import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

const SECTIONS = [
  { key: "priority", title: "Group Game Priorities", sub: "Ideas your board ranked and prioritized during the Group Game.",
    actions: [["additional", "Move To Additional Ideas"]] , keepLabel: "Keep As Priority" },
  { key: "additional", title: "Additional Board Ideas", sub: "Valid ideas contributed by participants that did not become Group Game priorities.",
    actions: [["priority", "Add To Board Priorities"], ["not_now", "Not Now"]], keepLabel: "Keep As Additional Idea" },
  { key: "recommendation", title: "Recommended Based On Rooney's Fundraising Process", sub: "New recommendations generated after your Group Game.",
    actions: [["priority", "Add To Board Priorities"], ["not_now", "Not Now"]], keepLabel: "Keep As Recommendation" },
];

export default function BoardStrategyReviewPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [review, setReview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    try { setReview((await memberApi.get("/game/review")).data); }
    catch (err) {
      setError(err.response?.status === 409
        ? "Complete your Group Game first. The Board Strategy Review becomes available after all six decisions are completed."
        : "We could not load the Board Strategy Review.");
    }
  }, []);

  useEffect(() => { document.title = "Board Strategy Review | Board Fundraising Game"; }, []);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    load();
  }, [loading, member, navigate, load]);

  const generate = async () => {
    setBusy("generate");
    try { await memberApi.post("/game/review/recommendations"); await load(); }
    catch { setError("We could not generate recommendations. Please try again."); }
    setBusy("");
  };

  const decide = async (item, status) => {
    setBusy(item.item_id);
    try { await memberApi.post("/game/review/decision", { item_id: item.item_id, status }); await load(); }
    catch { /* keep current state */ }
    setBusy("");
  };

  if (loading || (!review && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const items = review?.items || [];

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-review-back">Back to Dashboard</Link>}>
      <main className="bfg-dash" style={{ maxWidth: 960 }} data-testid="bfg-board-review-page">
        <div className="bfg-panel">
          <h1>Board Strategy Review</h1>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Use this during the remainder of your board meeting. Review your priorities, the additional ideas and Rooney's recommendations, then decide together what your organization should prioritize. Only explicit decisions change an idea's status.
          </p>
        </div>
        {error && <div className="bfg-panel"><p className="bfg-error" data-testid="bfg-review-error">{error}</p></div>}
        {review && SECTIONS.map((section) => {
          const rows = items.filter((item) => item.status === section.key);
          return (
            <div className="bfg-panel" key={section.key} data-testid={`bfg-review-${section.key}`}>
              <h2>{section.title}</h2>
              <p className="bfg-panel-sub" style={{ marginTop: 6 }}>{section.sub}</p>
              {section.key === "recommendation" && !review.recommendations_generated && (
                <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 12 }} disabled={busy === "generate"}
                  onClick={generate} data-testid="bfg-generate-recommendations-btn">
                  {busy === "generate" ? "Generating…" : "Generate Rooney's Recommendations"}
                </button>
              )}
              {rows.length === 0 && (section.key !== "recommendation" || review.recommendations_generated) && (
                <p className="bfg-note" style={{ marginTop: 12 }}>Nothing here right now.</p>
              )}
              {rows.map((item) => (
                <div className="bfg-card" key={item.item_id} style={{ marginTop: 12, padding: 16, textAlign: "left" }} data-testid={`bfg-review-item-${item.item_id}`}>
                  <p className="bfg-eyebrow" style={{ fontSize: 11 }}>{item.area}{item.source === "ROONEY_PROCESS_RECOMMENDATION" ? " · Rooney's Process" : ""}</p>
                  <p style={{ marginTop: 6 }}>{item.text}</p>
                  <div className="bfg-bm-actions" style={{ marginTop: 10 }}>
                    <span className="bfg-note" style={{ alignSelf: "center" }}>{section.keepLabel}</span>
                    {section.actions.map(([status, label]) => (
                      <button key={status} className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={busy === item.item_id}
                        onClick={() => decide(item, status)} data-testid={`bfg-review-${status}-${item.item_id}`}>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          );
        })}
        {review && (
          <div className="bfg-panel">
            <p className="bfg-panel-sub">Items marked Not Now: {items.filter((item) => item.status === "not_now").length}</p>
            <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 12 }}
              onClick={async () => { await memberApi.post("/game/review/complete"); navigate("/game/dashboard"); }}
              data-testid="bfg-review-complete-btn">
              Finish Board Strategy Review
            </button>
            <p className="bfg-note" style={{ marginTop: 8 }}>Next: add your meeting transcript in Complete Your Board Meeting so these decisions shape the final strategy.</p>
          </div>
        )}
      </main>
    </BfgShell>
  );
}
