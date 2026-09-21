import { useCallback, useEffect, useState } from "react";
import { Mail, RefreshCw } from "lucide-react";
import { memberApi } from "./api";

export default function RecommitmentInviteBoardMembers({ onChanged }) {
  const [roster, setRoster] = useState([]);
  const [form, setForm] = useState({ name: "", email: "", form_variant: "full" });
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(() => memberApi.get("/reactivation/roster").then((r) => setRoster(r.data.members || [])).catch(() => setRoster([])), []);
  useEffect(() => { load(); }, [load]);

  const invite = async () => {
    setBusy("new"); setMessage("");
    try {
      const created = await memberApi.post("/reactivation/board-members", form);
      const person = created.data.member;
      await memberApi.post(`/reactivation/board-members/${person.member_record_id}/send`, { type: "initial" });
      setForm({ name: "", email: "", form_variant: "full" });
      setMessage(`The Recommitment Form was sent to ${person.name}.`);
      await load(); if (onChanged) onChanged();
    } catch (error) { setMessage(error.response?.data?.detail || "The invitation could not be sent."); }
    setBusy("");
  };

  const resend = async (person) => {
    setBusy(person.member_record_id); setMessage("");
    try {
      await memberApi.post(`/reactivation/board-members/${person.member_record_id}/send`, { type: "reminder" });
      setMessage(`A reminder was sent to ${person.name}.`); await load();
    } catch (error) { setMessage(error.response?.data?.detail || "The reminder could not be sent."); }
    setBusy("");
  };

  return <div data-testid="recommitment-invitations">
    <p>Enter each Board Member's name and email, choose the correct version of the form, then send their personal invitation.</p>
    <div className="member-card">
      <label className="field"><span>Board Member Name</span><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
      <label className="field"><span>Board Member Email</span><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
      <label className="field"><span>Which form should this person receive?</span><select value={form.form_variant} onChange={(e) => setForm({ ...form, form_variant: e.target.value })}>
        <option value="full">Full Recommitment Form, including graceful transition options</option>
        <option value="standard">Continue-Serving Form, without the step-down option</option>
      </select></label>
      <button className="button" disabled={busy || !form.name.trim() || !form.email.includes("@")} onClick={invite}><Mail size={15} /> {busy === "new" ? "SENDING…" : "SEND RECOMMITMENT FORM"}</button>
    </div>
    {message && <p className="member-success">{message}</p>}
    {roster.length > 0 && <div style={{ marginTop: 16 }}>{roster.map((person) => <article className="member-card" key={person.member_record_id}>
      <h3>{person.name}</h3><p>{person.email} · <strong>{person.status === "COMPLETED" ? "Response received" : person.status === "SENT" ? "Invitation sent" : "Not sent"}</strong></p>
      {person.status !== "COMPLETED" && <button className="button button-outline" disabled={Boolean(busy)} onClick={() => resend(person)}><RefreshCw size={15} /> {busy === person.member_record_id ? "SENDING…" : "SEND REMINDER"}</button>}
    </article>)}</div>}
  </div>;
}
