import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

const TYPE_LABELS = { system_building: "System Building", direct_fundraising: "Direct Fundraising", other: "Other" };

const ChangeCard = ({ change, onUpdate }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(change.edited_content || change.proposed_content);
  const status = change.status;
  return (
    <div className="bfg-mr-decision" data-testid={`bfg-decision-${change.decision_id}`}>
      {change.current_content && (
        <div className="bfg-mr-block"><p className="bfg-eyebrow" style={{ marginBottom: 4 }}>Current</p><p>{change.current_content}</p></div>
      )}
      <div className="bfg-mr-block">
        <p className="bfg-eyebrow" style={{ marginBottom: 4 }}>Proposed Change</p>
        {editing ? (
          <textarea rows={5} value={draft} onChange={(event) => setDraft(event.target.value)} data-testid={`bfg-decision-edit-${change.decision_id}`} style={{ width: "100%" }} className="bfg-mr-segment" />
        ) : (
          <p>{change.edited_content || change.proposed_content}</p>
        )}
      </div>
      {change.reason && (
        <div className="bfg-mr-block"><p className="bfg-eyebrow" style={{ marginBottom: 4 }}>Why</p><p>{change.reason}</p></div>
      )}
      <div className="bfg-bm-actions" style={{ alignItems: "center" }}>
        {editing ? (
          <>
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => { onUpdate(change.decision_id, { status: "accepted", edited_content: draft }); setEditing(false); }}
              data-testid={`bfg-decision-save-accept-${change.decision_id}`}>Save And Accept</button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setEditing(false)}>Cancel</button>
          </>
        ) : (
          <>
            <button className={`bfg-btn bfg-btn-sm ${status === "accepted" ? "bfg-btn-primary" : "bfg-btn-ghost"}`}
              onClick={() => onUpdate(change.decision_id, { status: "accepted" })} data-testid={`bfg-decision-accept-${change.decision_id}`}>
              {status === "accepted" ? "Accepted" : "Accept"}
            </button>
            <button className={`bfg-btn bfg-btn-sm ${status === "rejected" ? "bfg-btn-primary" : "bfg-btn-ghost"}`}
              onClick={() => onUpdate(change.decision_id, { status: "rejected" })} data-testid={`bfg-decision-reject-${change.decision_id}`}>
              {status === "rejected" ? "Rejected" : "Reject"}
            </button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setEditing(true)} data-testid={`bfg-decision-edit-btn-${change.decision_id}`}>Edit</button>
          </>
        )}
      </div>
    </div>
  );
};

const UnresolvedCard = ({ item, onUpdate }) => {
  const [resolving, setResolving] = useState(false);
  const [text, setText] = useState(item.resolution_text || "");
  return (
    <div className="bfg-mr-decision" data-testid={`bfg-unresolved-${item.decision_id}`}>
      <p>{item.proposed_content}</p>
      {item.status === "manually_resolved" && !resolving && (
        <p className="bfg-success" style={{ marginTop: 8 }}>Decision: {item.resolution_text}</p>
      )}
      {resolving ? (
        <div style={{ marginTop: 10 }}>
          <textarea rows={3} className="bfg-mr-segment" style={{ width: "100%" }} value={text}
            onChange={(event) => setText(event.target.value)} placeholder="Type the board's final decision…"
            data-testid={`bfg-unresolved-text-${item.decision_id}`} />
          <div className="bfg-bm-actions">
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" disabled={!text.trim()}
              onClick={() => { onUpdate(item.decision_id, { status: "manually_resolved", resolution_text: text.trim() }); setResolving(false); }}
              data-testid={`bfg-unresolved-save-${item.decision_id}`}>Save Decision</button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setResolving(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <div className="bfg-bm-actions">
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setResolving(true)} data-testid={`bfg-unresolved-resolve-${item.decision_id}`}>Resolved — Add Decision</button>
          <button className={`bfg-btn bfg-btn-sm ${item.status === "unresolved" ? "bfg-btn-primary" : "bfg-btn-ghost"}`}
            onClick={() => onUpdate(item.decision_id, { status: "unresolved" })} data-testid={`bfg-unresolved-leave-${item.decision_id}`}>
            Leave Unresolved
          </button>
        </div>
      )}
    </div>
  );
};

const CommitmentCard = ({ commitment, onUpdate }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(commitment.edited_commitment || commitment.commitment);
  return (
    <div className="bfg-mr-decision" data-testid={`bfg-commitment-${commitment.commitment_id}`}
      style={{ opacity: commitment.review_status === "removed" ? 0.55 : 1 }}>
      <p style={{ fontWeight: 700, color: "#111827" }}>{commitment.board_member_name || "Board Member"}</p>
      {editing ? (
        <textarea rows={3} className="bfg-mr-segment" style={{ width: "100%", marginTop: 8 }} value={draft}
          onChange={(event) => setDraft(event.target.value)} data-testid={`bfg-commitment-edit-${commitment.commitment_id}`} />
      ) : (
        <p style={{ marginTop: 6 }}>{commitment.edited_commitment || commitment.commitment}</p>
      )}
      <p className="bfg-note">
        Type: {TYPE_LABELS[commitment.commitment_type] || "Other"}
        {commitment.deadline && <> · Deadline: {commitment.deadline}</>}
        {commitment.review_status === "removed" && <> · Removed</>}
      </p>
      <div className="bfg-bm-actions">
        {editing ? (
          <>
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm"
              onClick={() => { onUpdate(commitment.commitment_id, { review_status: "edited", edited_commitment: draft }); setEditing(false); }}
              data-testid={`bfg-commitment-save-${commitment.commitment_id}`}>Save</button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setEditing(false)}>Cancel</button>
          </>
        ) : (
          <>
            <button className={`bfg-btn bfg-btn-sm ${commitment.review_status !== "removed" ? "bfg-btn-primary" : "bfg-btn-ghost"}`}
              onClick={() => onUpdate(commitment.commitment_id, { review_status: "keep" })} data-testid={`bfg-commitment-keep-${commitment.commitment_id}`}>Keep</button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm"
              onClick={() => onUpdate(commitment.commitment_id, { review_status: "removed" })} data-testid={`bfg-commitment-remove-${commitment.commitment_id}`}>Remove</button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setEditing(true)} data-testid={`bfg-commitment-edit-btn-${commitment.commitment_id}`}>Edit</button>
          </>
        )}
      </div>
    </div>
  );
};

export default function MeetingDecisionsPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [state, setState] = useState(null);
  const [decisions, setDecisions] = useState(null);
  const [analysing, setAnalysing] = useState(false);
  const [analysisFailed, setAnalysisFailed] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generateFailed, setGenerateFailed] = useState(false);
  const analyseTimer = useRef(null);
  const finalTimer = useRef(null);

  useEffect(() => { document.title = "Review Meeting Decisions | Board Fundraising Game"; }, []);
  useEffect(() => () => { clearInterval(analyseTimer.current); clearInterval(finalTimer.current); }, []);

  const loadDecisions = useCallback(async () => {
    try { setDecisions((await memberApi.get("/game/meeting-review/decisions")).data); } catch { /* ignore */ }
  }, []);

  const loadState = useCallback(async () => {
    try {
      const data = (await memberApi.get("/game/meeting-review/state")).data;
      setState(data);
      const review = data.review;
      if (review.status === "reviewing") { navigate("/game/meeting-review", { replace: true }); return; }
      if (review.status === "adopted") { navigate("/game/meeting-review/final", { replace: true }); return; }
      if (review.analysis_status === "running") { setAnalysing(true); startAnalysisPolling(); }
      if (review.status === "decisions_processed" || review.status === "final_strategy_created") loadDecisions();
      if (review.final_generation_status === "running") { setGenerating(true); startFinalPolling(); }
    } catch (err) {
      if (err.response?.status === 404) navigate("/game/dashboard", { replace: true });
    }
  }, [navigate, loadDecisions]); // eslint-disable-line react-hooks/exhaustive-deps

  const startAnalysisPolling = () => {
    clearInterval(analyseTimer.current);
    analyseTimer.current = setInterval(async () => {
      try {
        const status = (await memberApi.get("/game/meeting-review/analysis-status")).data.status;
        if (status === "done") {
          clearInterval(analyseTimer.current); setAnalysing(false);
          const data = (await memberApi.get("/game/meeting-review/state")).data;
          setState(data);
          loadDecisions();
        } else if (status === "failed") {
          clearInterval(analyseTimer.current); setAnalysing(false); setAnalysisFailed(true);
        }
      } catch { /* keep polling */ }
    }, 4000);
  };

  const startFinalPolling = () => {
    clearInterval(finalTimer.current);
    finalTimer.current = setInterval(async () => {
      try {
        const data = (await memberApi.get("/game/meeting-review/final-status")).data;
        if (data.status === "done" && data.final_strategy_id) {
          clearInterval(finalTimer.current); setGenerating(false);
          navigate("/game/meeting-review/final");
        } else if (data.status === "failed") {
          clearInterval(finalTimer.current); setGenerating(false); setGenerateFailed(true);
        }
      } catch { /* keep polling */ }
    }, 4000);
  };

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    loadState();
  }, [loading, member, navigate, loadState]);

  const analyse = async () => {
    setAnalysing(true); setAnalysisFailed(false);
    try { await memberApi.post("/game/meeting-review/analyse"); startAnalysisPolling(); }
    catch { setAnalysing(false); setAnalysisFailed(true); }
  };

  const generateFinal = async () => {
    setGenerating(true); setGenerateFailed(false);
    try { await memberApi.post("/game/meeting-review/generate-final"); startFinalPolling(); }
    catch { setGenerating(false); setGenerateFailed(true); }
  };

  const updateDecision = async (decisionId, payload) => {
    try { await memberApi.put(`/game/meeting-review/decision/${decisionId}`, { status: "", edited_content: "", resolution_text: "", ...payload }); await loadDecisions(); }
    catch { /* ignore */ }
  };

  const updateCommitment = async (commitmentId, payload) => {
    try { await memberApi.put(`/game/meeting-review/commitment/${commitmentId}`, { edited_commitment: "", ...payload }); await loadDecisions(); }
    catch { /* ignore */ }
  };

  if (loading || !state) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const review = state.review;
  const analysed = review.status === "decisions_processed" || review.status === "final_strategy_created";
  const unresolvedItems = (decisions?.sections || []).flatMap((section) => section.unresolved);

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-md-back-dashboard">Back to Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-meeting-decisions-page" style={{ maxWidth: 960 }}>
        <div className="bfg-panel">
          <p className="bfg-eyebrow">Board Strategy Review</p>
          <h1>Review Meeting Decisions</h1>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Use your board's discussion, section feedback and meeting notes to identify the changes that should be reflected in your Final Fundraising Strategy.
          </p>
        </div>

        {!analysed && (
          <div className="bfg-panel" data-testid="bfg-md-overview">
            <div className="bfg-gg-playerlist">
              <div className="bfg-summary-row"><span>Board Feedback</span><strong>{state.feedback_count} response{state.feedback_count === 1 ? "" : "s"} across the review</strong></div>
              <div className="bfg-summary-row"><span>Meeting Transcript</span><strong>{state.transcript_available ? "Available" : "Not Available"}</strong></div>
              <div className="bfg-summary-row"><span>Meeting Notes</span><strong>{state.notes_available ? "Available" : "Not Available"}</strong></div>
              <div className="bfg-summary-row"><span>Manual Strategy Changes</span><strong>{state.manual_edit_count}</strong></div>
            </div>
            {analysing ? (
              <div style={{ marginTop: 18 }} data-testid="bfg-md-analysing">
                <p className="bfg-note" style={{ fontWeight: 700 }}>Analysing Your Board's Discussion...</p>
                <div className="bfg-doc-loading"><span /><span /><span /></div>
              </div>
            ) : (
              <>
                {analysisFailed && <p className="bfg-error">We could not analyse the meeting discussion. Please try again.</p>}
                <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} onClick={analyse} data-testid="bfg-analyse-btn">
                  Analyse Meeting Discussion
                </button>
              </>
            )}
          </div>
        )}

        {analysed && decisions && (
          <>
            <div className="bfg-panel" data-testid="bfg-md-decisions">
              <h2>Decisions From Your Board Discussion</h2>
              {(decisions.sections || []).filter((section) => section.changes.length > 0).length === 0 && (
                <p className="bfg-note" style={{ marginTop: 10 }}>No proposed strategy changes were identified from the board's discussion.</p>
              )}
              {(decisions.sections || []).map((section) => section.changes.length > 0 && (
                <div key={section.section_key} style={{ marginTop: 20 }}>
                  <h3 style={{ color: "#111827" }}>{section.section_title}</h3>
                  {section.decision_summary && <p className="bfg-note" style={{ marginTop: 4 }}>{section.decision_summary}</p>}
                  {section.changes.map((change) => <ChangeCard key={change.decision_id} change={change} onUpdate={updateDecision} />)}
                </div>
              ))}
            </div>

            {unresolvedItems.length > 0 && (
              <div className="bfg-panel" data-testid="bfg-md-unresolved">
                <h2>Your Board May Need To Decide</h2>
                {unresolvedItems.map((item) => <UnresolvedCard key={item.decision_id} item={item} onUpdate={updateDecision} />)}
              </div>
            )}

            {(decisions.commitments || []).length > 0 && (
              <div className="bfg-panel" data-testid="bfg-md-commitments">
                <h2>Commitments Mentioned During The Meeting</h2>
                <p className="bfg-panel-sub" style={{ marginTop: 6 }}>
                  These commitments will be saved for the Board Portfolio stage. They will not change the fundraising strategy itself.
                </p>
                {decisions.commitments.map((commitment) => (
                  <CommitmentCard key={commitment.commitment_id} commitment={commitment} onUpdate={updateCommitment} />
                ))}
              </div>
            )}

            <div className="bfg-panel" data-testid="bfg-md-generate-final">
              <h2>Create Your Final Fundraising Strategy</h2>
              <p className="bfg-panel-sub" style={{ marginTop: 6 }}>
                Your Board-Prioritized Draft and the decisions accepted from your board discussion will now be combined into the Final Fundraising Strategy.
              </p>
              {generating ? (
                <div style={{ marginTop: 16 }} data-testid="bfg-md-generating">
                  <p className="bfg-note" style={{ fontWeight: 700 }}>Generating Your Final Fundraising Strategy...</p>
                  <div className="bfg-doc-loading"><span /><span /><span /></div>
                </div>
              ) : (
                <>
                  {generateFailed && <p className="bfg-error">We could not generate the final strategy. Your decisions have been saved — please try again.</p>}
                  {review.status === "final_strategy_created" ? (
                    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16 }}
                      onClick={() => navigate("/game/meeting-review/final")} data-testid="bfg-md-view-final-btn">
                      View Final Fundraising Strategy
                    </button>
                  ) : (
                    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16 }} onClick={generateFinal} data-testid="bfg-generate-final-btn">
                      Generate Final Fundraising Strategy
                    </button>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </main>
    </BfgShell>
  );
}
