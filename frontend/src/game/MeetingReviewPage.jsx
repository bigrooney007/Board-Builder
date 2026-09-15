import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { STRATEGY_SECTIONS, SectionBody, sectionToText } from "./strategyRender";
import { MeetingTranscript } from "./MeetingTranscript";

export default function MeetingReviewPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [state, setState] = useState(null);
  const [strategy, setStrategy] = useState(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saveState, setSaveState] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { document.title = "Board Strategy Review | Board Fundraising Game"; }, []);

  const loadState = useCallback(async () => {
    try { setState((await memberApi.get("/game/meeting-review/state")).data); }
    catch (err) {
      if (err.response?.status === 404) navigate("/game/dashboard", { replace: true });
      else setError("We could not load the strategy review.");
    }
  }, [navigate]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    loadState();
  }, [loading, member, navigate, loadState]);

  useEffect(() => {
    if (!state?.review) return undefined;
    if (state.review.status !== "reviewing") return undefined;
    const timer = setInterval(loadState, 3000);
    return () => clearInterval(timer);
  }, [state?.review?.status, loadState]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!state?.review?.strategy_id) return;
    memberApi.get(`/game/strategy/view/${state.review.strategy_id}`)
      .then((response) => setStrategy(response.data.strategy)).catch(() => {});
  }, [state?.review?.strategy_id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const status = state?.review?.status;
    if (status === "decisions_processed") navigate("/game/meeting-review/decisions", { replace: true });
    if (status === "final_strategy_created" || status === "adopted") navigate("/game/meeting-review/final", { replace: true });
  }, [state?.review?.status, navigate]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading || (!state && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const review = state?.review;
  const index = review?.current_section_index || 0;
  const section = STRATEGY_SECTIONS[index];
  const feedback = state?.section_feedback;

  const move = async (nextIndex) => {
    setBusy(true);
    try {
      await memberApi.post("/game/meeting-review/section", { index: nextIndex });
      setEditing(false); setSaveState("");
      await loadState();
      window.scrollTo({ top: 0 });
    } catch { /* keep */ }
    setBusy(false);
  };

  const startEdit = () => {
    const edits = strategy?.section_edits || {};
    setDraft(edits[section.key] !== undefined && edits[section.key] !== ""
      ? edits[section.key]
      : sectionToText(section, (strategy?.data || {})[section.key]));
    setSaveState("");
    setEditing(true);
  };

  const saveEdit = async () => {
    setSaveState("saving");
    try {
      await memberApi.put("/game/meeting-review/edit-section", { section_key: section.key, text: draft });
      setStrategy((current) => ({ ...current, section_edits: { ...(current.section_edits || {}), [section.key]: draft } }));
      setSaveState("saved");
      setEditing(false);
    } catch { setSaveState("error"); }
  };

  const finishReview = async () => {
    setBusy(true);
    try { await memberApi.post("/game/meeting-review/finish-review"); await loadState(); window.scrollTo({ top: 0 }); }
    catch { /* keep */ }
    setBusy(false);
  };

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-mr-back-dashboard">Back to Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-meeting-review-page" style={{ maxWidth: 960 }}>
        {error && <div className="bfg-panel"><p className="bfg-error">{error}</p></div>}

        {review && review.status === "review_complete" && (
          <div className="bfg-panel" style={{ textAlign: "center" }} data-testid="bfg-review-complete-summary">
            <h1>Strategy Review Complete</h1>
            <p className="bfg-panel-sub" style={{ marginTop: 12 }}>
              Your board has reviewed the Board-Prioritized Fundraising Strategy. The next step is to process the decisions made during the discussion and create the Final Fundraising Strategy.
            </p>
            <div className="bfg-gg-playerlist" style={{ marginTop: 20, textAlign: "left" }}>
              <div className="bfg-summary-row"><span>Sections Reviewed</span><strong>{state.total_sections} of {state.total_sections}</strong></div>
              <div className="bfg-summary-row"><span>Board Feedback Received</span><strong data-testid="bfg-summary-feedback-count">{state.feedback_count}</strong></div>
              <div className="bfg-summary-row"><span>Transcript Available</span><strong>{state.transcript_available ? "Yes" : "No"}</strong></div>
              <div className="bfg-summary-row"><span>Meeting Notes Available</span><strong>{state.notes_available ? "Yes" : "No"}</strong></div>
            </div>
            <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }}
              onClick={() => navigate("/game/meeting-review/decisions")} data-testid="bfg-review-decisions-btn">
              Review Meeting Decisions
            </button>
          </div>
        )}

        {review && review.status === "reviewing" && (
          <>
            <div className="bfg-panel" data-testid="bfg-mr-header">
              <p className="bfg-eyebrow">Board Strategy Review</p>
              <h1>{state.organization_name}</h1>
              <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
                {state.goal_display && <>Fundraising Goal: <strong>{state.goal_display}</strong> · </>}
                Strategy: Board-Prioritized Draft
              </p>
              <p className="bfg-note" data-testid="bfg-mr-joined-count">{state.joined_count} board member{state.joined_count === 1 ? "" : "s"} connected through the Group Game link.</p>
            </div>

            <div className="bfg-panel" data-testid="bfg-mr-section-panel">
              <p className="bfg-eyebrow" data-testid="bfg-mr-section-counter">Section {index + 1} of {state.total_sections}</p>
              <h2>{section.title}</h2>
              {!editing ? (
                <>
                  <div style={{ marginTop: 14 }} data-testid="bfg-mr-section-content">
                    {strategy && ((strategy.section_edits || {})[section.key] ? (
                      <p className="bfg-doc-text" style={{ whiteSpace: "pre-line" }}>{strategy.section_edits[section.key]}</p>
                    ) : (
                      <SectionBody section={section} data={(strategy.data || {})[section.key]} mode={strategy.mode} />
                    ))}
                  </div>
                  {saveState === "saved" && <p className="bfg-success" data-testid="bfg-mr-edit-saved">Changes Saved</p>}
                  <div className="bfg-form-actions">
                    <button className="bfg-btn bfg-btn-ghost" style={{ visibility: index === 0 ? "hidden" : "visible" }}
                      disabled={busy} onClick={() => move(index - 1)} data-testid="bfg-mr-prev-btn">Previous Section</button>
                    <button className="bfg-btn bfg-btn-ghost" onClick={startEdit} data-testid="bfg-mr-edit-btn">Edit Section</button>
                    {index < STRATEGY_SECTIONS.length - 1 ? (
                      <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={() => move(index + 1)} data-testid="bfg-mr-next-btn">Next Section</button>
                    ) : (
                      <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={finishReview} data-testid="bfg-mr-finish-btn">Finish Strategy Review</button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <p className="bfg-note" style={{ marginTop: 8 }}>Manual edits update the Board-Prioritized Draft — no AI call is made.</p>
                  <label className="bfg-field">
                    <span>Strategy text for this section</span>
                    <textarea rows={14} value={draft} onChange={(event) => setDraft(event.target.value)} data-testid="bfg-mr-edit-text" />
                  </label>
                  {saveState === "error" && <p className="bfg-error">We could not save your changes. Please try again.</p>}
                  <div className="bfg-form-actions">
                    <button className="bfg-btn bfg-btn-ghost" onClick={() => setEditing(false)} data-testid="bfg-mr-edit-cancel-btn">Cancel</button>
                    <button className="bfg-btn bfg-btn-primary" disabled={saveState === "saving"} onClick={saveEdit} data-testid="bfg-mr-edit-save-btn">
                      {saveState === "saving" ? "Saving…" : "Save Changes"}
                    </button>
                  </div>
                </>
              )}
            </div>

            <div className="bfg-panel" data-testid="bfg-mr-feedback-panel">
              <h2>Board Feedback</h2>
              <div className="bfg-mr-counts">
                <span data-testid="bfg-mr-approve-count"><strong>{feedback?.approve || 0}</strong> Approve</span>
                <span data-testid="bfg-mr-change-count"><strong>{feedback?.suggest_change || 0}</strong> Suggested Changes</span>
                <span data-testid="bfg-mr-discussion-count"><strong>{feedback?.needs_discussion || 0}</strong> Need More Discussion</span>
              </div>
              {(feedback?.comments || []).length > 0 && (
                <div className="bfg-gg-playerlist" style={{ marginTop: 14 }}>
                  {feedback.comments.map((comment, commentIndex) => (
                    <div className="bfg-summary-row" key={commentIndex} style={{ flexDirection: "column", gap: 4, alignItems: "flex-start" }}
                      data-testid={`bfg-mr-comment-${commentIndex}`}>
                      <span>{comment.name} — {comment.response_type === "suggest_change" ? "Suggested Change" : "Needs More Discussion"}</span>
                      <strong style={{ textAlign: "left" }}>{comment.comment}</strong>
                    </div>
                  ))}
                </div>
              )}
              {(feedback?.comments || []).length === 0 && <p className="bfg-note">No comments for this section yet. The board may be discussing verbally — you can continue at any time.</p>}
            </div>

            <MeetingTranscript sectionKey={section.key} consented={Boolean(review.transcript_consent)} />
          </>
        )}
      </main>
    </BfgShell>
  );
}
