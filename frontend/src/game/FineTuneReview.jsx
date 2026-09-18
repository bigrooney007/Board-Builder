import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const FineTuneReview = ({ token, sectionId, copy, onDone, onReady, onEdit }) => {
  const [state, setState] = useState("loading");
  const [proposal, setProposal] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const doneRef = useRef(onDone);
  const readyRef = useRef(onReady);
  const editRef = useRef(onEdit);
  doneRef.current = onDone;
  readyRef.current = onReady;
  editRef.current = onEdit;

  const load = useCallback(async () => {
    setState("loading"); setError("");
    try {
      const response = await axios.post(`${API}/game/play/${token}/fine-tune/${sectionId}`);
      if (response.data.completed) { doneRef.current(response.data.approved_entries || []); return; }
      setProposal((response.data.proposals || [])[0] || null);
      setState("review");
      readyRef.current?.();
    } catch (err) {
      const detail = typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not refine your idea. Please try again.";
      if (err.response?.status === 422 && editRef.current) { editRef.current(detail); return; }
      setError(detail);
      setState("error");
    }
  }, [token, sectionId]);
  useEffect(() => { load(); }, [load]);

  const decide = async (decision) => {
    if (busy) return;
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/game/play/${token}/fine-tune/${sectionId}/decisions`, {
        entries: [{ entry_id: "main", decision, text: "" }],
      });
      doneRef.current(response.data.approved_entries || []);
    } catch (err) {
      const detail = typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your choice. Please try again.";
      if ([409, 422].includes(err.response?.status) && editRef.current) { editRef.current(detail); return; }
      setError(detail);
      setBusy(false);
    }
  };

  if (state === "loading") {
    return (
      <div style={{ marginTop: 40, textAlign: "center" }} data-testid="bfg-ft-loading">
        <div className="bfg-thinking-dots" aria-label={copy.refining || "Refining your idea"}><span></span><span></span><span></span></div>
        <p style={{ fontWeight: 700, fontSize: 16, marginTop: 12 }}>{copy.refining || "Refining Your Idea..."}</p>
      </div>
    );
  }
  if (state === "error" || !proposal) {
    return (
      <div style={{ marginTop: 30, textAlign: "center" }} data-testid="bfg-ft-error">
        <p className="bfg-error">{error || "We could not refine your idea. Please try again."}</p>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 14 }} onClick={load} data-testid="bfg-ft-retry">Try Again</button>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 20, textAlign: "left" }} data-testid={`bfg-ft-review-${sectionId}`}>
      <div className="bfg-card" style={{ marginTop: 12, padding: 20 }}>
        <p className="bfg-eyebrow">YOUR ORIGINAL IDEA</p>
        <p style={{ marginTop: 8, whiteSpace: "pre-wrap" }} data-testid="bfg-ft-original">{proposal.original}</p>
      </div>
      <div className="bfg-card" style={{ marginTop: 14, padding: 20, borderLeft: "3px solid #4f46e5" }}>
        <p className="bfg-eyebrow" style={{ color: "#4f46e5" }}>IMPROVED VERSION</p>
        <p style={{ marginTop: 8, whiteSpace: "pre-wrap" }} data-testid="bfg-ft-refined">{proposal.refined}</p>
      </div>
      {error && <p className="bfg-error">{error}</p>}
      <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 22, flexWrap: "wrap" }}>
        <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={() => decide("use_ai")} data-testid="bfg-ft-use">{copy.use_button}</button>
        <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => decide("keep_original")} data-testid="bfg-ft-keep">{copy.keep_button}</button>
        <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => editRef.current?.("")} data-testid="bfg-ft-edit">Edit My Answer</button>
      </div>
    </div>
  );
};
