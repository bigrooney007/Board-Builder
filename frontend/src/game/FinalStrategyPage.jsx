import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { STRATEGY_SECTIONS, SectionBody, StrategyDocument, sectionToText } from "./strategyRender";

export default function FinalStrategyPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [state, setState] = useState(null);
  const [strategy, setStrategy] = useState(null);
  const [approvals, setApprovals] = useState(null);
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saveState, setSaveState] = useState("");
  const [showAdopt, setShowAdopt] = useState(false);
  const [adoptChecked, setAdoptChecked] = useState(false);
  const [adopting, setAdopting] = useState(false);
  const [revising, setRevising] = useState(false);
  const [reviseFailed, setReviseFailed] = useState(false);
  const reviseTimer = useRef(null);

  useEffect(() => { document.title = "Final Fundraising Strategy | Board Fundraising Game"; }, []);
  useEffect(() => () => clearInterval(reviseTimer.current), []);

  const loadAll = useCallback(async () => {
    try {
      const data = (await memberApi.get("/game/meeting-review/state")).data;
      setState(data);
      const review = data.review;
      if (review.status === "reviewing") { navigate("/game/meeting-review", { replace: true }); return; }
      if (review.status === "review_complete" || review.status === "decisions_processed") {
        navigate("/game/meeting-review/decisions", { replace: true }); return;
      }
      if (review.final_strategy_id) {
        setStrategy((await memberApi.get(`/game/strategy/view/${review.final_strategy_id}`)).data.strategy);
        setApprovals((await memberApi.get("/game/meeting-review/approvals")).data);
      }
    } catch (err) {
      if (err.response?.status === 404) navigate("/game/dashboard", { replace: true });
    }
  }, [navigate]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    loadAll();
  }, [loading, member, navigate, loadAll]);

  useEffect(() => {
    if (!state?.review || state.review.status !== "final_strategy_created") return undefined;
    const timer = setInterval(async () => {
      try { setApprovals((await memberApi.get("/game/meeting-review/approvals")).data); } catch { /* ignore */ }
    }, 4000);
    return () => clearInterval(timer);
  }, [state?.review?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading || !state || !strategy) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const review = state.review;
  const adopted = strategy.status === "adopted";
  const finalReviewing = review.final_review_status === "reviewing";
  const finalIndex = review.final_section_index || 0;
  const section = STRATEGY_SECTIONS[finalIndex];

  const copyLink = async () => {
    const link = `${window.location.origin}/strategy/${strategy.share_token}`;
    try { await navigator.clipboard.writeText(link); } catch { window.prompt("Copy this strategy link:", link); }
    setCopied(true); setTimeout(() => setCopied(false), 2500);
  };

  const finalReviewAction = async (action, index = 0) => {
    try {
      await memberApi.post("/game/meeting-review/final-review", { action, index });
      setEditing(false); setSaveState("");
      await loadAll();
      window.scrollTo({ top: 0 });
    } catch { /* ignore */ }
  };

  const startEdit = () => {
    const edits = strategy.section_edits || {};
    setDraft(edits[section.key] !== undefined && edits[section.key] !== ""
      ? edits[section.key]
      : sectionToText(section, (strategy.data || {})[section.key]));
    setSaveState(""); setEditing(true);
  };

  const saveEdit = async () => {
    setSaveState("saving");
    try {
      await memberApi.put(`/game/strategy/view/${strategy.strategy_id}/section`, { section_key: section.key, text: draft });
      setStrategy((current) => ({ ...current, section_edits: { ...(current.section_edits || {}), [section.key]: draft } }));
      setSaveState("saved"); setEditing(false);
    } catch { setSaveState("error"); }
  };

  const generateRevised = async () => {
    setRevising(true); setReviseFailed(false);
    try {
      await memberApi.post("/game/meeting-review/generate-final");
      clearInterval(reviseTimer.current);
      reviseTimer.current = setInterval(async () => {
        try {
          const data = (await memberApi.get("/game/meeting-review/final-status")).data;
          if (data.status === "done" && data.final_strategy_id) {
            clearInterval(reviseTimer.current); setRevising(false); await loadAll();
          } else if (data.status === "failed") {
            clearInterval(reviseTimer.current); setRevising(false); setReviseFailed(true);
          }
        } catch { /* keep polling */ }
      }, 4000);
    } catch { setRevising(false); setReviseFailed(true); }
  };

  const adopt = async () => {
    setAdopting(true);
    try {
      await memberApi.post("/game/meeting-review/adopt", { confirmed: true });
      setShowAdopt(false);
      await loadAll();
      window.scrollTo({ top: 0 });
    } catch { /* ignore */ }
    setAdopting(false);
  };

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-fs-back-dashboard">Back to Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-final-strategy-page" style={{ maxWidth: 960 }}>

        {adopted && (
          <div className="bfg-panel" style={{ textAlign: "center" }} data-testid="bfg-adopted-banner">
            <p className="bfg-eyebrow">{strategy.organization_name}</p>
            <h1>Fundraising Strategy</h1>
            <p className="bfg-success" style={{ fontWeight: 700, fontSize: 16, marginTop: 10 }}>Adopted</p>
            {strategy.adopted_at && <p className="bfg-note">Adopted on {new Date(strategy.adopted_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}</p>}
            <p className="bfg-note" style={{ marginTop: 8 }}>
              This is your organization's current working fundraising strategy. It is now read-only.
            </p>
            <button className="bfg-btn bfg-btn-ghost" style={{ marginTop: 14 }} onClick={copyLink} data-testid="bfg-adopted-copy-link-btn">
              {copied ? "Link Copied" : "Copy Strategy Link"}
            </button>
          </div>
        )}

        {!adopted && !finalReviewing && (
          <>
            <div className="bfg-panel" data-testid="bfg-final-header">
              <p className="bfg-eyebrow">{strategy.organization_name}</p>
              <h1>Final Fundraising Strategy</h1>
              <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
                Status: <strong style={{ color: "#facc15" }}>Final Draft</strong>
                {strategy.data?.fundraising_goal?.amount && <> · Fundraising Goal: <strong>{strategy.data.fundraising_goal.amount}</strong></>}
                {strategy.data?.fundraising_goal?.deadline && <> · Deadline: <strong>{strategy.data.fundraising_goal.deadline}</strong></>}
              </p>
              <div className="bfg-bm-actions">
                <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => finalReviewAction("start")} data-testid="bfg-review-final-btn">
                  Review Final Strategy
                </button>
                <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={copyLink} data-testid="bfg-final-copy-link-btn">
                  {copied ? "Link Copied" : "Copy Strategy Link"}
                </button>
              </div>
            </div>

            <div className="bfg-panel" data-testid="bfg-board-approval-panel">
              <h2>Board Approval</h2>
              {approvals && approvals.participant_count > 0 ? (
                <>
                  <div className="bfg-gg-playerlist" style={{ marginTop: 12 }}>
                    {approvals.members.map((row, rowIndex) => (
                      <div className="bfg-summary-row" key={rowIndex} data-testid={`bfg-approval-row-${rowIndex}`}>
                        <span>{row.name}</span>
                        <strong style={{ color: row.approval_status === "approved" ? "#059669" : row.approval_status === "change_requested" ? "#facc15" : "#64748b" }}>
                          {row.approval_status === "approved" ? "Approved" : row.approval_status === "change_requested" ? "Requested Change" : "No Response Yet"}
                        </strong>
                      </div>
                    ))}
                  </div>
                  {approvals.members.filter((row) => row.change_request).map((row, rowIndex) => (
                    <p className="bfg-note" key={rowIndex} data-testid={`bfg-change-request-${rowIndex}`}>
                      <strong style={{ color: "#facc15" }}>{row.name}:</strong> {row.change_request}
                    </p>
                  ))}
                  <p className="bfg-panel-sub" style={{ marginTop: 12 }} data-testid="bfg-approval-summary">
                    {approvals.approved_count} of {approvals.participant_count} participating board members approved
                  </p>
                </>
              ) : (
                <p className="bfg-note" style={{ marginTop: 10 }}>Board member responses will appear here after you review the final strategy with your board.</p>
              )}
              <p className="bfg-note" style={{ marginTop: 8 }}>
                Not every participant is required to approve before adoption — your organization's normal board decision-making process applies.
              </p>
              <div className="bfg-bm-actions" style={{ marginTop: 14 }}>
                {revising ? (
                  <div data-testid="bfg-revising">
                    <p className="bfg-note" style={{ fontWeight: 700 }}>Generating Revised Final Draft...</p>
                    <div className="bfg-doc-loading"><span /><span /><span /></div>
                  </div>
                ) : (
                  <>
                    <button className="bfg-btn bfg-btn-primary" onClick={() => setShowAdopt(true)} data-testid="bfg-adopt-btn">
                      Adopt This Fundraising Strategy
                    </button>
                    <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={generateRevised} data-testid="bfg-revise-final-btn">
                      Generate Revised Final Draft
                    </button>
                  </>
                )}
              </div>
              {reviseFailed && <p className="bfg-error">We could not generate a revised final draft. Please try again.</p>}
            </div>
          </>
        )}

        {!adopted && finalReviewing && (
          <div className="bfg-panel" data-testid="bfg-final-review-panel">
            <p className="bfg-eyebrow">Final Strategy Review — Section {finalIndex + 1} of {STRATEGY_SECTIONS.length}</p>
            <h2>{section.title}</h2>
            {!editing ? (
              <>
                <div style={{ marginTop: 14 }} data-testid="bfg-final-review-content">
                  {(strategy.section_edits || {})[section.key] ? (
                    <p className="bfg-doc-text" style={{ whiteSpace: "pre-line" }}>{strategy.section_edits[section.key]}</p>
                  ) : (
                    <SectionBody section={section} data={(strategy.data || {})[section.key]} mode={strategy.mode} />
                  )}
                </div>
                {saveState === "saved" && <p className="bfg-success">Changes Saved</p>}
                <div className="bfg-form-actions">
                  <button className="bfg-btn bfg-btn-ghost" style={{ visibility: finalIndex === 0 ? "hidden" : "visible" }}
                    onClick={() => finalReviewAction("section", finalIndex - 1)} data-testid="bfg-final-prev-btn">Previous Section</button>
                  <button className="bfg-btn bfg-btn-ghost" onClick={startEdit} data-testid="bfg-final-edit-btn">Edit Section</button>
                  {finalIndex < STRATEGY_SECTIONS.length - 1 ? (
                    <button className="bfg-btn bfg-btn-primary" onClick={() => finalReviewAction("section", finalIndex + 1)} data-testid="bfg-final-next-btn">Next Section</button>
                  ) : (
                    <button className="bfg-btn bfg-btn-primary" onClick={() => finalReviewAction("finish")} data-testid="bfg-final-finish-btn">Finish Final Review</button>
                  )}
                </div>
              </>
            ) : (
              <>
                <p className="bfg-note" style={{ marginTop: 8 }}>Manual edits update the Final Draft — no AI call is made.</p>
                <label className="bfg-field">
                  <span>Strategy text for this section</span>
                  <textarea rows={14} value={draft} onChange={(event) => setDraft(event.target.value)} data-testid="bfg-final-edit-text" />
                </label>
                {saveState === "error" && <p className="bfg-error">We could not save your changes. Please try again.</p>}
                <div className="bfg-form-actions">
                  <button className="bfg-btn bfg-btn-ghost" onClick={() => setEditing(false)} data-testid="bfg-final-edit-cancel-btn">Cancel</button>
                  <button className="bfg-btn bfg-btn-primary" disabled={saveState === "saving"} onClick={saveEdit} data-testid="bfg-final-edit-save-btn">
                    {saveState === "saving" ? "Saving…" : "Save Changes"}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {(adopted || !finalReviewing) && <StrategyDocument strategy={strategy} />}

        {showAdopt && (
          <div className="bfg-modal-overlay" data-testid="bfg-adopt-modal">
            <div className="bfg-modal">
              <h2>Adopt This Fundraising Strategy?</h2>
              <p className="bfg-panel-sub" style={{ marginTop: 10 }}>
                Adopting this strategy will mark it as your organization's current working fundraising strategy.
              </p>
              <label className={`bfg-check ${adoptChecked ? "checked" : ""}`} style={{ marginTop: 16 }}>
                <input type="checkbox" checked={adoptChecked} onChange={(event) => setAdoptChecked(event.target.checked)}
                  data-testid="bfg-adopt-checkbox" />
                I confirm that this strategy has been reviewed and adopted according to our organization's normal board decision-making process.
              </label>
              <div className="bfg-form-actions">
                <button className="bfg-btn bfg-btn-ghost" onClick={() => setShowAdopt(false)} data-testid="bfg-adopt-cancel-btn">Cancel</button>
                <button className="bfg-btn bfg-btn-primary" disabled={!adoptChecked || adopting} onClick={adopt} data-testid="bfg-adopt-confirm-btn">
                  {adopting ? "Adopting…" : "Adopt Fundraising Strategy"}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </BfgShell>
  );
}
