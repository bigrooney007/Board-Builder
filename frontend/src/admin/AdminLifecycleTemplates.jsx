import { useEffect, useState } from "react";
import axios from "axios";

const api = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });

const EMPTY = { product: "board_fundraising_game", payment_state: "unpaid", stage: 0, sequence: 1, subject: "", body: "", cta_label: "Continue", cta_destination: "" };
const SEQ_LABELS = { 1: "Day 1", 2: "Day 3", 3: "Day 5", 4: "Day 7", 5: "Monthly Callback" };

export const AdminLifecycleTemplates = () => {
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = () => api.get("/admin/contacts/lifecycle-templates").then((r) => setTemplates(r.data.templates || [])).catch(() => setMessage("Could not load templates."));
  useEffect(load, []); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const save = async () => {
    setBusy(true); setMessage("");
    try {
      await api.post("/admin/contacts/lifecycle-templates", { ...form, stage: Number(form.stage), sequence: Number(form.sequence) });
      setMessage("Template saved."); setForm(EMPTY); load();
    } catch { setMessage("Save failed."); }
    setBusy(false);
  };

  const remove = async (templateId) => {
    setBusy(true); setMessage("");
    try { await api.delete(`/admin/contacts/lifecycle-templates/${encodeURIComponent(templateId)}`); load(); }
    catch { setMessage("Delete failed."); }
    setBusy(false);
  };

  const edit = (template) => setForm({
    product: template.product, payment_state: template.payment_state, stage: template.stage,
    sequence: template.sequence, subject: template.subject || "", body: template.body || "",
    cta_label: template.cta_label || "Continue", cta_destination: template.cta_destination || "",
  });

  return (
    <div data-testid="admin-lifecycle-templates" style={{ marginTop: 28, borderTop: "2px solid #e5e7eb", paddingTop: 16 }}>
      <h3>Lifecycle Email Templates</h3>
      <p style={{ fontSize: 13, color: "#6b7280" }}>Day 1 / 3 / 5 / 7 sequences plus the monthly callback. The engine sends nothing until a template's subject and body are saved here. Stage 0 applies to every stage of that lifecycle; a stage-specific template overrides it. Use [FIRST NAME] for personalization.</p>
      {message && <p style={{ fontSize: 13, color: message.includes("failed") || message.includes("Could not") ? "#b91c1c" : "#047857" }} data-testid="lifecycle-template-message">{message}</p>}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        <select value={form.product} onChange={set("product")} data-testid="lifecycle-template-product">
          <option value="board_fundraising_game">Board Fundraising Game</option>
          <option value="board_recruitment">Board Recruitment</option>
        </select>
        <select value={form.payment_state} onChange={set("payment_state")} data-testid="lifecycle-template-state">
          <option value="unpaid">Unpaid</option>
          <option value="paid">Paid</option>
        </select>
        <select value={form.stage} onChange={set("stage")} data-testid="lifecycle-template-stage">
          {[0, 1, 2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n === 0 ? "All stages" : `Stage ${n}`}</option>)}
        </select>
        <select value={form.sequence} onChange={set("sequence")} data-testid="lifecycle-template-sequence">
          {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{SEQ_LABELS[n]}</option>)}
        </select>
      </div>
      <input value={form.subject} onChange={set("subject")} placeholder="Email subject" style={{ width: "100%", marginBottom: 6 }} data-testid="lifecycle-template-subject" />
      <textarea value={form.body} onChange={set("body")} placeholder="Email body (exact approved copy, word for word)" rows={7} style={{ width: "100%", marginBottom: 6 }} data-testid="lifecycle-template-body" />
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <input value={form.cta_label} onChange={set("cta_label")} placeholder="Button label" data-testid="lifecycle-template-cta-label" />
        <input value={form.cta_destination} onChange={set("cta_destination")} placeholder="Button path e.g. /game/unlock (blank = stage default)" style={{ flex: 1 }} data-testid="lifecycle-template-cta-destination" />
        <button onClick={save} disabled={busy} data-testid="lifecycle-template-save">Save Template</button>
      </div>
      <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left" }}><th>Product</th><th>State</th><th>Stage</th><th>Email</th><th>Subject</th><th></th><th></th></tr>
        </thead>
        <tbody>
          {templates.map((template) => (
            <tr key={template.template_id} style={{ borderTop: "1px solid #e5e7eb" }} data-testid={`lifecycle-template-${template.template_id}`}>
              <td>{template.product}</td><td>{template.payment_state}</td>
              <td>{template.stage === 0 ? "All" : template.stage}</td>
              <td>{SEQ_LABELS[template.sequence] || template.sequence}</td>
              <td>{template.subject || <em style={{ color: "#b91c1c" }}>body pending</em>}</td>
              <td><button onClick={() => edit(template)} disabled={busy} data-testid={`lifecycle-template-edit-${template.template_id}`}>Edit</button></td>
              <td><button onClick={() => remove(template.template_id)} disabled={busy} data-testid={`lifecycle-template-delete-${template.template_id}`}>Delete</button></td>
            </tr>
          ))}
          {templates.length === 0 && <tr><td colSpan={7} style={{ padding: 8 }}>No templates yet — the lifecycle engine is running but will skip every send until templates are saved.</td></tr>}
        </tbody>
      </table>
    </div>
  );
};

export default AdminLifecycleTemplates;
