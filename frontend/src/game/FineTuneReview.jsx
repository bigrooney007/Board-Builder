import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const FineTuneReview = ({ token, sectionId, copy, areaTitle, onDone }) => {
  const [state, setState] = useState("loading");
  const [proposals, setProposals] = useState([]);
  const [choices, setChoices] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  const load = useCallback(async () => {
    setState("loading"); setError("");
    try {
      const response = await axios.post(`${API}/game/play/${token}/fine-tune/${sectionId}`);
      if (response.data.completed) { doneRef.current(response.data.approved_entries || []); return; }
      setProposals(response.data.proposals || []);
      setChoices({});
      setState("review");
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not fine-tune your ideas. Please try again.");
      setState("error");
    }
  }, [token, sectionId]);
  useEffect(() => { load(); }, [load]);

  const choose = (entryId, decision, refined) => setChoices((current) => ({
    ...current,
    [entryId]: { decision, text: decision === "edited" ? (current[entryId]?.text ?? refined) : "" },
  }));

  const allDecided = proposals.length > 0 && proposals.every((proposal) => {
    const choice = choices[proposal.entry_id];
    return choice && (choice.decision !== "edited" || choice.text.trim());
  });

  const save = async () => {
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/game/play/${token}/fine-tune/${sectionId}/decisions`, {
        entries: proposals.map((proposal) => ({
          entry_id: proposal.entry_id,
          decision: choices[proposal.entry_id].decision,
          text: choices[proposal.entry_id].text || "",
        })),
      });
      doneRef.current(response.data.approved_entries || []);
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your approved ideas. Please try again.");
      setBusy(false);
    }
  };

  if (state === "loading") {
    return (
      <div className="bfg-card" style={{ marginTop: 20, textAlign: "center", padding: 30 }} data-testid="bfg-ft-loading">
        <p style={{ fontWeight: 700 }}>{copy.working}</p>
        <p style={{ marginTop: 8, fontSize: 14 }}>{areaTitle}</p>
      </div>
    );
  }
  if (state === "error") {
    return (
      <div className="bfg-card" style={{ marginTop: 20, textAlign: "center", padding: 30 }} data-testid="bfg-ft-error">
        <p className="bfg-error">{error}</p>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 14 }} onClick={load} data-testid="bfg-ft-retry">Try Again</button>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 8, textAlign: "left" }} data-testid={`bfg-ft-review-${sectionId}`}>
      <h3 style={{ textAlign: "center", marginTop: 14 }}>{areaTitle}</h3>
      {proposals.map((proposal) => {
        const choice = choices[proposal.entry_id];
        return (
          <div className="bfg-card bfg-ft-card" key={proposal.entry_id} style={{ marginTop: 16, padding: 18 }} data-testid={`bfg-ft-card-${proposal.entry_id}`}>
            {proposal.audience && <p className="bfg-eyebrow">{proposal.audience}</p>}
            {proposal.audience_type && !proposal.audience && (
              <p className="bfg-eyebrow">{proposal.audience_type === "individual" ? "Person" : proposal.audience_type === "business" ? "Business" : "Grantor"}</p>
            )}
            <p style={{ fontWeight: 700, marginTop: 6 }}>{copy.your_idea_label}</p>
            <p style={{ marginTop: 4 }}>{proposal.original}</p>
            <p style={{ fontWeight: 700, marginTop: 12, color: "#4f46e5" }}>{copy.refined_label}</p>
            <p style={{ marginTop: 4 }}>{proposal.refined}</p>
            <div className="bfg-ft-choices" style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
              <button type="button" className={`bfg-btn bfg-btn-sm ${choice?.decision === "use_ai" ? "bfg-btn-primary" : "bfg-btn-ghost"}`}
                onClick={() => choose(proposal.entry_id, "use_ai", proposal.refined)} data-testid={`bfg-ft-use-${proposal.entry_id}`}>
                {copy.use_button}
              </button>
              <button type="button" className={`bfg-btn bfg-btn-sm ${choice?.decision === "keep_original" ? "bfg-btn-primary" : "bfg-btn-ghost"}`}
                onClick={() => choose(proposal.entry_id, "keep_original", proposal.refined)} data-testid={`bfg-ft-keep-${proposal.entry_id}`}>
                {copy.keep_button}
              </button>
              <button type="button" className={`bfg-btn bfg-btn-sm ${choice?.decision === "edited" ? "bfg-btn-primary" : "bfg-btn-ghost"}`}
                onClick={() => choose(proposal.entry_id, "edited", proposal.refined)} data-testid={`bfg-ft-edit-${proposal.entry_id}`}>
                {copy.edit_button}
              </button>
            </div>
            {choice?.decision === "edited" && (
              <textarea rows={3} style={{ width: "100%", marginTop: 10 }} value={choice.text}
                onChange={(event) => setChoices((current) => ({ ...current, [proposal.entry_id]: { decision: "edited", text: event.target.value } }))}
                data-testid={`bfg-ft-edit-input-${proposal.entry_id}`} />
            )}
          </div>
        );
      })}
      {error && <p className="bfg-error">{error}</p>}
      <div style={{ textAlign: "center" }}>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} disabled={!allDecided || busy} onClick={save} data-testid={`bfg-ft-save-${sectionId}`}>
          {busy ? "Saving…" : copy.save_button}
        </button>
      </div>
    </div>
  );
};
