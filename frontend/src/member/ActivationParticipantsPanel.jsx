import { useCallback, useEffect, useState } from "react";
import { Copy, Mail, Trash2, X } from "lucide-react";
import { memberApi } from "./api";

const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const dialogStyle = { background: "#fff", maxWidth: 760, width: "100%", padding: "28px", borderRadius: 8, position: "relative" };
const err = (e, fallback) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : fallback);

export const ActivationParticipantsPanel = ({ onChange }) => {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ name: "", email: "", role: "" });
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  const [preview, setPreview] = useState(null);
  const [copied, setCopied] = useState("");

  const load = useCallback(() => {
    memberApi.get("/activation/planning").then((res) => { setData(res.data); if (onChange) onChange(res.data); }).catch(() => setMessage("We could not load your Board Members."));
  }, [onChange]);
  useEffect(load, [load]);

  const add = async (event) => {
    event.preventDefault();
    setMessage("");
    try {
      await memberApi.post("/activation/participants", form);
      setForm({ name: "", email: "", role: "" });
      load();
    } catch (e) { setMessage(err(e, "We could not add this Board Member.")); }
  };

  const importSuggestion = async (suggestion) => {
    setMessage("");
    try { await memberApi.post("/activation/participants/import", { source: suggestion.source, ref_id: suggestion.ref_id }); load(); } catch (e) { setMessage(err(e, "We could not add this Board Member.")); }
  };

  const remove = async (participant) => {
    if (!window.confirm(`Remove ${participant.name}?`)) return;
    try { await memberApi.delete(`/activation/participants/${participant.participant_id}`); load(); } catch (e) { setMessage(err(e, "We could not remove this Board Member.")); }
  };

  const openPreview = async (participant) => {
    setMessage("");
    try {
      const res = await memberApi.get(`/activation/participants/${participant.participant_id}/email-preview`);
      setPreview({ participant, ...res.data });
    } catch (e) { setMessage(err(e, "Approve your Planning Form first.")); }
  };

  const send = async (participant, type) => {
    setBusy(participant.participant_id);
    setMessage("");
    try { await memberApi.post(`/activation/participants/${participant.participant_id}/send`, { type }); setPreview(null); load(); } catch (e) { setMessage(err(e, "The email could not be sent.")); }
    setBusy("");
  };

  const sendAll = async () => {
    setBusy("all");
    setMessage("");
    try { const res = await memberApi.post("/activation/participants/send-all-unsent"); setMessage(`Planning Form sent to ${res.data.count} Board Member${res.data.count === 1 ? "" : "s"}.`); load(); } catch (e) { setMessage(err(e, "The emails could not be sent.")); }
    setBusy("");
  };

  const copyText = async (text, key) => {
    try { await navigator.clipboard.writeText(text); } catch { window.prompt("Copy this text:", text); }
    setCopied(key);
    setTimeout(() => setCopied(""), 2500);
  };

  if (!data) return <p className="sh-loading">Loading your Board Members…</p>;
  const unsent = data.participants.filter((p) => p.status === "NOT SENT").length;

  return (
    <section className="member-card" data-testid="activation-participants-panel">
      <h2>Who Needs to Complete the Fundraising Planning Form?</h2>
      <p>Add each Board Member who should share their fundraising ideas. Each person receives their OWN secure planning-form link — no shared link is used.</p>
      {data.suggestions.length > 0 && (
        <div style={{ marginBottom: 14 }} data-testid="app-suggestions">
          <p className="eyebrow" style={{ marginBottom: 6 }}>Board Members we already know about</p>
          {data.suggestions.map((s) => (
            <div key={`${s.source}-${s.ref_id}`} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #eee", gap: 8, flexWrap: "wrap" }}>
              <span><strong>{s.name}</strong> · {s.email} <span className="eyebrow">— {s.label}</span></span>
              <button type="button" className="button button-outline" onClick={() => importSuggestion(s)} data-testid={`app-import-${s.ref_id}`}>ADD</button>
            </div>
          ))}
        </div>
      )}
      <form onSubmit={add} style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end" }} data-testid="app-add-form">
        <label className="field" style={{ flex: "1 1 160px" }}><span>Name <b>*</b></span><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required data-testid="app-add-name" /></label>
        <label className="field" style={{ flex: "1 1 200px" }}><span>Email <b>*</b></span><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required data-testid="app-add-email" /></label>
        <label className="field" style={{ flex: "1 1 140px" }}><span>Role</span><input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} placeholder="Board Member" data-testid="app-add-role" /></label>
        <button type="submit" className="button" data-testid="app-add-button">ADD BOARD MEMBER</button>
      </form>
      {message && <p className="eyebrow" style={{ marginTop: 10 }} data-testid="app-message">{message}</p>}
      <div style={{ marginTop: 14 }} data-testid="app-participant-list">
        {data.participants.length === 0 && <p data-testid="app-empty">No Board Members added yet.</p>}
        {data.participants.map((p) => (
          <div key={p.participant_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #eee", gap: 8, flexWrap: "wrap" }} data-testid={`app-row-${p.participant_id}`}>
            <span><strong>{p.name}</strong> · {p.role || "Board Member"} · {p.email} <span className="eyebrow" data-testid={`app-status-${p.participant_id}`}>— {p.status}{p.submitted_at ? ` ${new Date(p.submitted_at).toLocaleDateString()}` : p.last_sent_at ? ` ${new Date(p.last_sent_at).toLocaleDateString()}` : ""}</span></span>
            <span style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {p.status !== "COMPLETED" && <button type="button" className="button button-outline" onClick={() => openPreview(p)} data-testid={`app-preview-${p.participant_id}`}>VIEW EMAIL &amp; LINK</button>}
              {p.status === "NOT SENT" && <button type="button" className="button" disabled={busy === p.participant_id} onClick={() => send(p, "initial")} data-testid={`app-send-${p.participant_id}`}><Mail size={14} /> SEND FORM</button>}
              {p.status === "SENT" && <button type="button" className="button" disabled={busy === p.participant_id} onClick={() => send(p, "reminder")} data-testid={`app-remind-${p.participant_id}`}><Mail size={14} /> SEND REMINDER</button>}
              {p.status === "NOT SENT" && <button type="button" className="button button-outline" onClick={() => remove(p)} data-testid={`app-remove-${p.participant_id}`}><Trash2 size={14} /></button>}
            </span>
          </div>
        ))}
      </div>
      {unsent > 0 && (
        <button type="button" className="button" style={{ marginTop: 12 }} disabled={busy === "all"} onClick={sendAll} data-testid="app-send-all-button">
          {busy === "all" ? "Sending…" : `SEND PLANNING FORM TO ALL ${unsent} UNSENT`}
        </button>
      )}
      {preview && (
        <div style={overlayStyle} data-testid="app-preview-modal">
          <div style={dialogStyle}>
            <button type="button" onClick={() => setPreview(null)} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid="app-preview-close"><X size={20} /></button>
            <h2>Planning Email — {preview.participant.name}</h2>
            <p><strong>Subject:</strong> <span data-testid="app-preview-subject">{preview.subject}</span></p>
            <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 300, overflowY: "auto" }} data-testid="app-preview-body">{preview.body}</div>
            <p style={{ marginTop: 10 }}><strong>Their Secure Form Link:</strong> <span style={{ wordBreak: "break-all" }} data-testid="app-preview-link">{preview.form_link}</span></p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              {preview.participant.status !== "COMPLETED" && <button type="button" className="button" disabled={busy === preview.participant.participant_id} onClick={() => send(preview.participant, preview.participant.status === "SENT" ? "reminder" : "initial")} data-testid="app-preview-send"><Mail size={15} /> {preview.participant.status === "SENT" ? "SEND REMINDER" : "SEND THIS EMAIL"}</button>}
              <button type="button" className="button button-outline" onClick={() => copyText(preview.body, "body")} data-testid="app-preview-copy-body"><Copy size={15} /> {copied === "body" ? "Email Copied" : "COPY EMAIL"}</button>
              <button type="button" className="button button-outline" onClick={() => copyText(preview.form_link, "link")} data-testid="app-preview-copy-link"><Copy size={15} /> {copied === "link" ? "Link Copied" : "COPY FORM LINK"}</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
