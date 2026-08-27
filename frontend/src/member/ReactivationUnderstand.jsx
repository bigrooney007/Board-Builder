import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Brain, Eye, X } from "lucide-react";
import { memberApi } from "./api";
import { ResponseView } from "./ReactivationStep2";
import { reactivationContent, reactivationUnderstandText } from "../content/appContent";

const C = reactivationContent.step3;
const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const Modal = ({ children, onClose, testId }) => (
  <div style={overlayStyle} data-testid={testId}>
    <div style={{ background: "#fff", maxWidth: 860, width: "100%", padding: 28, borderRadius: 8, position: "relative" }}>
      <button type="button" onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testId}-close`}><X size={20} /></button>
      {children}
    </div>
  </div>
);

const MemberUnderstanding = ({ row, reload }) => {
  const id = row.member_record_id;
  const [busy, setBusy] = useState(false);
  const [material, setMaterial] = useState(null);
  const [viewing, setViewing] = useState(false);
  const [response, setResponse] = useState(null);
  const analysisStatus = material?.status || row.analysis?.status;

  const poll = useCallback(async (materialId) => {
    setBusy(true);
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 4000));
      try {
        const res = await memberApi.get(`/reactivation/materials/${materialId}`);
        if (res.data.status !== "Generating") {
          if (res.data.status !== "Failed") setMaterial(res.data);
          break;
        }
      } catch { break; }
    }
    setBusy(false);
    reload();
  }, [reload]);

  useEffect(() => {
    if (row.analysis?.status === "Generating" && !busy) poll(row.analysis.material_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [row.analysis?.status]);

  const generate = async () => {
    setBusy(true);
    try {
      const res = await memberApi.post(`/reactivation/board-members/${id}/analysis`);
      await poll(res.data.material_id);
    } catch (err) {
      window.alert(err.response?.data?.detail || "That did not work. Please try again.");
      setBusy(false);
    }
  };

  const openView = async () => {
    const m = material?.display_text ? material : (await memberApi.get(`/reactivation/materials/${material?.material_id || row.analysis.material_id}`)).data;
    setMaterial(m);
    setViewing(true);
  };

  if (row.status !== "COMPLETED") {
    return (
      <article className="member-card" data-testid={`understand-waiting-${id}`}>
        <h3 style={{ margin: 0 }}>{row.name}</h3>
        <p style={{ margin: "4px 0 8px" }}>{row.role || "Board Member"}</p>
        <p className="eyebrow">{C.waitingBadge}</p>
      </article>
    );
  }

  const ready = (row.analysis || material) && !["Generating", "Failed"].includes(analysisStatus) && !busy;
  return (
    <article className="member-card" data-testid={`understand-member-${id}`}>
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div>
          <h3 style={{ margin: 0 }}>{row.name}</h3>
          <p style={{ margin: "4px 0 0" }}>
            {row.role || "Board Member"}
            {row.professional_role && <> · {row.professional_role}{row.employer ? `, ${row.employer}` : ""}</>}
          </p>
        </div>
        <span className="eyebrow" style={{ alignSelf: "flex-start", padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid={`understand-status-${id}`}>
          {ready ? "UNDERSTOOD" : "RESPONSE RECEIVED"}
        </span>
      </div>
      <div style={{ borderLeft: "4px solid #000", padding: "10px 14px", margin: "14px 0", background: "#fafafa" }}>
        <p className="eyebrow" style={{ margin: 0 }}>Recommitment Response</p>
        <p style={{ margin: "4px 0 0", fontWeight: 700 }} data-testid={`understand-recommitment-${id}`}>{row.recommitment}</p>
      </div>
      {row.expertise?.length > 0 && <p style={{ margin: "6px 0 0" }}><strong>Expertise:</strong> {row.expertise.slice(0, 6).join(", ")}</p>}
      {row.contribution_interests?.length > 0 && <p style={{ margin: "6px 0 0" }}><strong>{reactivationUnderstandText.wantsToContributeIn}</strong> {row.contribution_interests.slice(0, 4).join(", ")}</p>}
      {row.monthly_availability && <p style={{ margin: "6px 0 0" }}><strong>Availability:</strong> {row.monthly_availability}</p>}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
        <button type="button" className="button" onClick={generate} disabled={busy} data-testid={`understand-generate-${id}`}>
          <Brain size={15} /> {busy ? C.analyzingLabel : (row.analysis || material) ? C.regenerateButton : C.understandButton}
        </button>
        {ready && <button type="button" className="button button-outline" onClick={openView} data-testid={`understand-view-${id}`}><Eye size={15} /> {C.viewUnderstandingButton}</button>}
        <button type="button" className="button button-outline" onClick={async () => setResponse((await memberApi.get(`/reactivation/board-members/${id}/response`)).data)} data-testid={`understand-view-response-${id}`}>{C.viewResponseButton}</button>
      </div>
      {analysisStatus === "Failed" && !busy && <p style={{ marginTop: 8 }} data-testid={`understand-failed-${id}`}>{C.failedLabel}</p>}
      {viewing && material && (
        <Modal onClose={() => setViewing(false)} testId={`understand-modal-${id}`}>
          <h2>Understanding {row.name}'s Response</h2>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 18, borderRadius: 6, maxHeight: 520, overflowY: "auto" }} data-testid={`understand-text-${id}`}>{material.display_text}</div>
          <Link className="button" style={{ marginTop: 14 }} to="/app/reactivation/self-guided/module/4" data-testid={`understand-go-conversation-${id}`}>PREPARE THE CONVERSATION</Link>
        </Modal>
      )}
      {response && (
        <Modal onClose={() => setResponse(null)} testId={`understand-response-modal-${id}`}>
          <h2>{row.name} — Recommitment Response</h2>
          <ResponseView data={response} testPrefix="understand" />
        </Modal>
      )}
    </article>
  );
};

const BoardSummary = ({ hasResponses }) => {
  const [summary, setSummary] = useState(null);
  const [busy, setBusy] = useState(false);
  const [viewing, setViewing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try { setSummary((await memberApi.get("/reactivation/board-summary")).data); } catch { /* best effort */ }
  }, []);
  useEffect(() => { load(); }, [load]);

  const poll = useCallback(async () => {
    setBusy(true);
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 4000));
      try {
        const res = await memberApi.get("/reactivation/board-summary");
        if (res.data.status !== "Generating") { setSummary(res.data); break; }
      } catch { break; }
    }
    setBusy(false);
  }, []);

  useEffect(() => { if (summary?.status === "Generating" && !busy) poll(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary?.status]);

  const generate = async () => {
    setError("");
    setBusy(true);
    try {
      await memberApi.post("/reactivation/board-summary");
      await poll();
    } catch (err) {
      setError(err.response?.data?.detail || "That did not work. Please try again.");
      setBusy(false);
    }
  };

  const ready = summary && !["NONE", "Generating", "Failed"].includes(summary.status) && !busy;
  return (
    <section className="member-card" style={{ borderLeft: "4px solid #1d3a2f" }} data-testid="board-summary-section">
      <h2>Summary of Your Entire Board</h2>
      <p>Understanding one board member is useful. Understanding your whole board is where the picture becomes clear. This summary combines everything you told me with everything your board members told you — who is ready to recommit, who needs a conversation, what strengths you already have, what is missing, and who you need to recruit to build a powerhouse board.</p>
      {error && <p className="submit-error" data-testid="board-summary-error">{error}</p>}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <button type="button" className="button" onClick={generate} disabled={busy || !hasResponses} data-testid="board-summary-generate">
          <Brain size={15} /> {busy ? "Analyzing your board…" : ready ? "Regenerate the Summary" : "Summarize My Entire Board"}
        </button>
        {ready && <button type="button" className="button button-outline" onClick={() => setViewing(true)} data-testid="board-summary-view"><Eye size={15} /> View the Summary</button>}
      </div>
      {!hasResponses && <p style={{ marginTop: 8 }} data-testid="board-summary-waiting">You need at least one completed Recommitment Form before I can summarize your board.</p>}
      {summary?.status === "Failed" && !busy && <p style={{ marginTop: 8 }} data-testid="board-summary-failed">The summary did not complete. Nothing is lost — generate it again.</p>}
      {viewing && ready && (
        <Modal onClose={() => setViewing(false)} testId="board-summary-modal">
          <h2>Summary of Your Entire Board</h2>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 18, borderRadius: 6, maxHeight: 520, overflowY: "auto" }} data-testid="board-summary-text">{summary.display_text}</div>
          <Link className="button" style={{ marginTop: 14 }} to="/app/reactivation/self-guided/module/4" data-testid="board-summary-go-conversation">PREPARE THE CONVERSATIONS</Link>
        </Modal>
      )}
    </section>
  );
};

export default function ReactivationUnderstand() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    memberApi.get("/reactivation/understand").then((res) => setData(res.data)).catch(() => setError("We could not load this step."));
  }, []);
  useEffect(load, [load]);

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">Loading your Board…</p>;
  const responded = data.members.filter((m) => m.status === "COMPLETED");
  const waiting = data.members.filter((m) => m.status !== "COMPLETED");

  return (
    <div data-testid="reactivation-understand">
      <section className="member-card" data-testid="understand-intro">
        <h2>{C.heading}</h2>
        {C.intro.map((p) => <p key={p}>{p}</p>)}
        <p className="eyebrow" data-testid="understand-progress">{C.progress(data.progress)}</p>
      </section>
      <BoardSummary hasResponses={responded.length > 0} />
      {responded.length === 0 && (
        <section className="member-card" data-testid="understand-empty">
          <p>{C.emptyState}</p>
          <Link className="button button-outline" to="/app/reactivation/self-guided/module/2">{reactivationUnderstandText.goToStep2}</Link>
        </section>
      )}
      {responded.map((row) => <MemberUnderstanding key={row.member_record_id} row={row} reload={load} />)}
      {waiting.map((row) => <MemberUnderstanding key={row.member_record_id} row={row} reload={load} />)}
    </div>
  );
}
