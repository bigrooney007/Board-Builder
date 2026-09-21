import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, FileText, RefreshCw, X } from "lucide-react";
import { memberApi } from "./api";
import { ResponseView } from "./ReactivationStep2";
import { reactivationContent, reactivationStep3Text } from "../content/appContent";
import { OutcomeEmailWorkflow, PortfolioWorkflow } from "./ReactivationStep5";

const C = reactivationContent.step4;

const OUTCOME_LABELS = {
  "Continuing as an Active Board Member": "ACTIVE — RECOMMITTED",
  "Follow-Up Conversation Needed": "FOLLOW-UP NEEDED",
  "Transitioning to an Advisory Role": "TRANSITIONING TO ADVISORY",
  "Transitioning to Another Support Role": "TRANSITIONING TO SUPPORT ROLE",
  "Stepping Down From the Board": "STEPPING DOWN",
};

const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };

const Modal = ({ children, onClose, testId, wide }) => (
  <div style={overlayStyle} data-testid={testId}>
    <div style={{ background: "#fff", maxWidth: wide ? 860 : 720, width: "100%", padding: 28, borderRadius: 8, position: "relative" }}>
      <button type="button" onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testId}-close`}><X size={20} /></button>
      {children}
    </div>
  </div>
);

const MemberConversation = ({ row, outcomeOptions, directions, reload, conclusionsOnly = false }) => {
  const [busy, setBusy] = useState("");
  const [material, setMaterial] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draftText, setDraftText] = useState("");
  const [viewing, setViewing] = useState(false);
  const [response, setResponse] = useState(null);
  const [understanding, setUnderstanding] = useState(null);
  const [conclusion, setConclusion] = useState(row.conversation_conclusion || "");
  const [conclusionSaved, setConclusionSaved] = useState(false);
  const [outcome, setOutcome] = useState(row.conversation_outcome || "");
  const [direction, setDirection] = useState(row.conversation_direction || "");
  const id = row.member_record_id;

  const saveDirection = async (value) => {
    setDirection(value);
    await memberApi.put(`/reactivation/board-members/${id}/direction`, { direction: value });
    reload();
  };

  const loadMaterial = useCallback(async () => {
    if (!row.script) return null;
    const res = await memberApi.get(`/reactivation/materials/${row.script.material_id}`);
    setMaterial(res.data);
    return res.data;
  }, [row.script]);

  const pollForScript = useCallback(async (materialId) => {
    setBusy("generate");
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 4000));
      try {
        const poll = await memberApi.get(`/reactivation/materials/${materialId}`);
        if (poll.data.status !== "Generating") {
          if (poll.data.status !== "Failed") setMaterial(poll.data);
          break;
        }
      } catch { break; }
    }
    setBusy("");
    reload();
  }, [reload]);

  const generate = async () => {
    setBusy("generate");
    try {
      const res = await memberApi.post(`/reactivation/board-members/${id}/conversation-script`);
      await pollForScript(res.data.material_id);
    } catch (err) {
      window.alert(err.response?.data?.detail || "Generation failed. Please try again.");
      setBusy("");
    }
  };

  useEffect(() => {
    if (row.script?.status === "Generating" && busy !== "generate") pollForScript(row.script.material_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [row.script?.status]);

  const openView = async () => { const m = material || (await loadMaterial()); if (m) setViewing(true); };
  const openEdit = async () => { const m = material || (await loadMaterial()); if (m) { setDraftText(m.display_text); setEditing(true); } };

  const saveEdit = async () => {
    setBusy("save");
    await memberApi.put(`/reactivation/materials/${material.material_id}`, { display_text: draftText });
    setMaterial({ ...material, display_text: draftText, status: "Draft" });
    setEditing(false);
    setBusy("");
    reload();
  };

  const approve = async () => {
    setBusy("approve");
    await memberApi.post(`/reactivation/materials/${material?.material_id || row.script.material_id}/approve`);
    if (material) setMaterial({ ...material, status: "Approved" });
    setBusy("");
    reload();
  };

  const download = async () => {
    const materialId = material?.material_id || row.script.material_id;
    const res = await memberApi.get(`/reactivation/materials/${materialId}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `Difficult-Conversation-Script-${row.name.replace(/[^a-zA-Z0-9]+/g, "-")}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const openResponse = async () => {
    const res = await memberApi.get(`/reactivation/board-members/${id}/response`);
    setResponse(res.data);
  };

  const openUnderstanding = async () => {
    if (!row.analysis) return;
    const res = await memberApi.get(`/reactivation/materials/${row.analysis.material_id}`);
    setUnderstanding(res.data);
  };

  const saveConclusion = async () => {
    await memberApi.put(`/reactivation/board-members/${id}/conclusion`, { conclusion });
    setConclusionSaved(true);
    reload();
  };

  const saveOutcome = async (value) => {
    setOutcome(value);
    if (value) { await memberApi.put(`/reactivation/board-members/${id}/outcome`, { outcome: value }); reload(); }
  };

  const scriptStatus = material?.status || row.script?.status;

  if (row.status !== "COMPLETED") {
    return (
      <article className="member-card" data-testid={`step3-waiting-${id}`}>
        <h3 style={{ marginBottom: 4 }}>{row.name}</h3>
        <p style={{ margin: "0 0 8px" }}>{row.role || "Board Member"}</p>
        <p className="eyebrow" data-testid={`step3-waiting-badge-${id}`}>{reactivationStep3Text.waitingForRecommitmentForm}</p>
        <p>{reactivationStep3Text.thisBoardMemberHasNot}</p>
        <Link className="button button-outline" to="/app/reactivation/self-guided/module/2" data-testid={`step3-return-step2-${id}`}>{reactivationStep3Text.returnToStep2}</Link>
      </article>
    );
  }

  return (
    <article className="member-card" data-testid={`step3-member-${id}`}>
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div>
          <h3 style={{ margin: 0 }}>{row.name}</h3>
          <p style={{ margin: "4px 0 0" }}>{row.role || "Board Member"}</p>
        </div>
        {row.conversation_outcome && (
          <span className="eyebrow" style={{ alignSelf: "flex-start", padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid={`step3-status-${id}`}>{OUTCOME_LABELS[row.conversation_outcome]}</span>
        )}
      </div>
      <div style={{ borderLeft: "4px solid #000", padding: "10px 14px", margin: "14px 0", background: "#fafafa" }} data-testid={`step3-recommitment-${id}`}>
        <p className="eyebrow" style={{ margin: 0 }}>Recommitment Response</p>
        <p style={{ margin: "4px 0 0", fontWeight: 700 }}>{row.recommitment}</p>
      </div>
      {!conclusionsOnly && <div style={{ margin: "6px 0 12px" }} data-testid={`step3-direction-block-${id}`}>
        <h3 style={{ marginBottom: 4 }}>{C.directionLabel}</h3>
        <p style={{ marginTop: 0 }}>{C.directionHint}</p>
        <select value={direction} onChange={(e) => saveDirection(e.target.value)} data-testid={`step3-direction-${id}`} style={{ maxWidth: 420 }}>
          <option value="">{C.directionPlaceholder}</option>
          {directions.map((option) => <option key={option}>{option}</option>)}
        </select>
      </div>}
      {!conclusionsOnly && <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <button type="button" className="button button-outline" onClick={openResponse} data-testid={`step3-view-response-${id}`}>VIEW RECOMMITMENT RESPONSE</button>
        {row.analysis && !["Generating", "Failed"].includes(row.analysis.status) && (
          <button type="button" className="button button-outline" onClick={openUnderstanding} data-testid={`step3-view-understanding-${id}`}>VIEW UNDERSTANDING</button>
        )}
        <button type="button" className="button" onClick={generate} disabled={busy === "generate"} data-testid={`step3-generate-${id}`}>
          {busy === "generate" ? "Generating…" : row.script ? <><RefreshCw size={15} /> {C.regenerateScript}</> : <><FileText size={15} /> {C.generateScript}</>}
        </button>
        {(row.script || material) && !["Generating", "Failed"].includes(scriptStatus) && busy !== "generate" && (
          <>
            <button type="button" className="button button-outline" onClick={openView} data-testid={`step3-view-online-${id}`}>VIEW ONLINE</button>
            <button type="button" className="button button-outline" onClick={openEdit} data-testid={`step3-edit-${id}`}>EDIT</button>
            <button type="button" className="button button-outline" onClick={approve} disabled={busy === "approve" || scriptStatus === "Approved"} data-testid={`step3-approve-${id}`}>{scriptStatus === "Approved" ? "APPROVED" : "APPROVE"}</button>
            <button type="button" className="button button-outline" onClick={download} data-testid={`step3-download-${id}`}><Download size={15} /> DOWNLOAD</button>
          </>
        )}
      </div>}
      {busy === "generate" && <p className="workspace-note" data-testid={`conversation-script-generation-wait-${id}`}>This may take a few minutes. If it isn't ready immediately, check back in about 5 minutes.</p>}
      {scriptStatus === "Failed" && busy !== "generate" && (
        <p style={{ marginTop: 8 }} data-testid={`step3-generation-failed-${id}`}>{reactivationStep3Text.scriptGenerationDidNotComplete}</p>
      )}

      <div style={{ marginTop: 20 }}>
        <h3 style={{ marginBottom: 4 }}>{C.conclusionHeading}</h3>
        <p style={{ marginTop: 0 }}>{C.conclusionHint}</p>
        <textarea rows={4} value={conclusion} onChange={(e) => { setConclusion(e.target.value); setConclusionSaved(false); }}
          placeholder={C.conclusionPlaceholder}
          style={{ width: "100%" }} data-testid={`step3-conclusion-${id}`} />
        <button type="button" className="button" onClick={saveConclusion} style={{ marginTop: 8 }} data-testid={`step3-save-conclusion-${id}`}>{conclusionSaved ? C.conclusionSaved : C.saveConclusion}</button>
      </div>

      <div style={{ marginTop: 18 }}>
        <h3 style={{ marginBottom: 4 }}>{C.outcomeHeading}</h3>
        <select value={outcome} onChange={(e) => saveOutcome(e.target.value)} data-testid={`step3-outcome-${id}`} style={{ maxWidth: 420 }}>
          <option value="">{reactivationStep3Text.chooseTheActualOutcome}</option>
          {outcomeOptions.map((option) => <option key={option}>{option}</option>)}
        </select>
      </div>

      {conclusionsOnly && conclusion.trim() && outcome === "Continuing as an Active Board Member" && <div style={{ marginTop: 18 }}><PortfolioWorkflow row={{...row,conversation_conclusion:conclusion,conversation_outcome:outcome}} reload={reload}/><OutcomeEmailWorkflow row={row} label="GENERATE RECOMMITMENT CONFIRMATION EMAIL" reload={reload}/></div>}
      {conclusionsOnly && conclusion.trim() && outcome === "Transitioning to an Advisory Role" && <OutcomeEmailWorkflow row={row} label="GENERATE ADVISORY BOARD TRANSITION EMAIL" reload={reload}/>}
      {conclusionsOnly && conclusion.trim() && outcome === "Transitioning to Another Support Role" && <><PortfolioWorkflow row={{...row,conversation_conclusion:conclusion,conversation_outcome:outcome}} reload={reload}/><OutcomeEmailWorkflow row={row} label="GENERATE SUPPORT ROLE CONFIRMATION EMAIL" reload={reload}/></>}
      {conclusionsOnly && conclusion.trim() && outcome === "Stepping Down From the Board" && <OutcomeEmailWorkflow row={row} label="GENERATE BOARD DEPARTURE EMAIL" reload={reload}/>}

      {viewing && material && (
        <Modal onClose={() => setViewing(false)} testId={`step3-view-modal-${id}`} wide>
          <h2>Difficult Conversation Script — {row.name}</h2>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 18, borderRadius: 6, maxHeight: 520, overflowY: "auto" }} data-testid={`step3-script-text-${id}`}>{material.display_text}</div>
        </Modal>
      )}
      {editing && (
        <Modal onClose={() => setEditing(false)} testId={`step3-edit-modal-${id}`} wide>
          <h2>Edit Conversation Script</h2>
          <textarea rows={22} value={draftText} onChange={(e) => setDraftText(e.target.value)} style={{ width: "100%", fontFamily: "inherit" }} data-testid={`step3-edit-text-${id}`} />
          <button type="button" className="button" onClick={saveEdit} disabled={busy === "save"} data-testid={`step3-save-edit-${id}`}>{busy === "save" ? "Saving…" : "SAVE"}</button>
        </Modal>
      )}
      {response && (
        <Modal onClose={() => setResponse(null)} testId={`step3-response-modal-${id}`} wide>
          <h2>{row.name} — Recommitment Response</h2>
          <ResponseView data={response} testPrefix="step3" />
        </Modal>
      )}
      {understanding && (
        <Modal onClose={() => setUnderstanding(null)} testId={`step3-understanding-modal-${id}`} wide>
          <h2>Understanding {row.name}'s Response</h2>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 18, borderRadius: 6, maxHeight: 520, overflowY: "auto" }} data-testid={`step3-understanding-text-${id}`}>{understanding.display_text}</div>
        </Modal>
      )}
    </article>
  );
};

export default function ReactivationStep3({ conclusionsOnly = false }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    Promise.all([memberApi.get("/reactivation/step3"), memberApi.get("/reactivation/my-board")]).then(([step, board]) => {
      const resourceRows = Object.values(board.data.groups || {}).flat();
      const byId = Object.fromEntries(resourceRows.map((row) => [row.member_record_id, row]));
      setData({ ...step.data, members: step.data.members.map((row) => ({ ...row, ...(byId[row.member_record_id] || {}) })) });
    }).catch(() => setError("We could not load this step."));
  }, []);
  useEffect(load, [load]);

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">Loading your Board…</p>;

  return (
    <div data-testid="reactivation-step3">
      {!conclusionsOnly && <section className="member-card" data-testid="step3-intro">
        <h2>{C.heading}</h2>
        {C.intro.map((p) => <p key={p}>{p}</p>)}
      </section>}

      <section className="member-card" data-testid="step3-progress">
        <h2>Difficult Conversation Progress</h2>
        <p data-testid="step3-progress-counts">
          <strong>{data.progress.total}</strong> Current Board Member{data.progress.total === 1 ? "" : "s"} · <strong>{data.progress.conversations_completed}</strong> Conversation{data.progress.conversations_completed === 1 ? "" : "s"} Completed
          {data.progress.follow_up_needed > 0 && <> · <strong>{data.progress.follow_up_needed}</strong> Follow-Up Needed</>}
          {data.progress.waiting_for_form > 0 && <> · <strong>{data.progress.waiting_for_form}</strong>{reactivationStep3Text.waitingForRecommitmentForm2}</>}
        </p>
      </section>

      {!data.members.length && (
        <section className="member-card" data-testid="step3-empty">
          <p>{reactivationStep3Text.noCurrentBoardMembersYet}</p>
          <Link className="button" to="/app/reactivation/self-guided/module/2">{reactivationStep3Text.goToStep2}</Link>
        </section>
      )}

      {data.members.map((row) => (
        <MemberConversation key={row.member_record_id} row={row} outcomeOptions={data.outcome_options} directions={data.directions || ["Remain and Step Up", "Step Down", "Move to Advisory Board"]} reload={load} conclusionsOnly={conclusionsOnly} />
      ))}
    </div>
  );
}
