import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { strategicPlanningAdminContent as SP } from "../content/appContent";

const client = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });
const err = (e) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Action failed.");
const AREA_STATUSES = ["NOT ASSIGNED", "ASSIGNED", "IN DEVELOPMENT", "SUBMITTED", "READY FOR BOARD"];

const EmailPreviewModal = ({ preview, onSend, onClose, busy, sendLabel = "Send This Email Now" }) => (
  <div className="admin-profile-overlay" data-testid="sp-email-preview">
    <div className="admin-profile-panel">
      <button className="profile-close" onClick={onClose}>×</button>
      <p className="eyebrow">Prepared email — nothing is sent until you choose Send</p>
      {preview.recipients && (
        <p><strong>To ({preview.recipients.length} Board Members):</strong> {preview.recipients.map((r) => `${r.name} <${r.email}>`).join(", ")}</p>
      )}
      {preview.to_email && <p><strong>To:</strong> {preview.to_name} &lt;{preview.to_email}&gt;</p>}
      <p><strong>Subject:</strong> {preview.subject}</p>
      <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "14px", borderRadius: "8px" }}>{preview.body}</pre>
      {preview.form_link && <p><strong>Secure link:</strong> <a href={preview.form_link} target="_blank" rel="noreferrer">{preview.form_link}</a></p>}
      <div className="admin-profile-actions">
        <button className="button button-back" onClick={() => navigator.clipboard?.writeText(`Subject: ${preview.subject}\n\n${preview.body}`)} data-testid="sp-email-copy">Copy Email</button>
        {onSend && <button className="button" disabled={busy} onClick={onSend} data-testid="sp-email-send">{busy ? "Sending…" : sendLabel}</button>}
        <button className="button button-back" onClick={onClose}>Close Without Sending</button>
      </div>
    </div>
  </div>
);

const TextEditor = ({ label, initial, onSave, testid }) => {
  const [text, setText] = useState(initial || "");
  useEffect(() => { setText(initial || ""); }, [initial]);
  return (
    <div style={{ marginTop: "10px" }}>
      <label style={{ display: "block", fontWeight: 600 }}>{label}</label>
      <textarea rows="14" style={{ width: "100%" }} value={text} onChange={(e) => setText(e.target.value)} data-testid={testid} />
      <button className="button button-small" onClick={() => onSave(text)} data-testid={`${testid}-save`}>Save</button>
    </div>
  );
};

const FormDistributionPanel = ({ pid, project, onError }) => {
  const [email, setEmail] = useState(null);
  const [copied, setCopied] = useState("");
  const link = project.generic_form_token ? `${window.location.origin}/strategic-planning-form/${project.generic_form_token}` : "";
  const loadEmail = async () => {
    try { const r = await client.get(`/admin/sp/projects/${pid}/form-email`); setEmail(r.data); }
    catch (e) { onError(err(e)); }
  };
  const copy = async (text, tag) => { await navigator.clipboard?.writeText(text); setCopied(tag); };
  return (
    <div className="admin-import-panel" data-testid="sp-distribution-panel">
      <h4>Form Link</h4>
      <p className="admin-message">Send this one secure link to your Board Members — each person enters their own name and email when they complete the form. You do not need to enter Board Member emails first.</p>
      <div className="admin-filters">
        <code style={{ background: "#f6f6f2", padding: "8px 12px", borderRadius: "6px", wordBreak: "break-all" }} data-testid="sp-form-link">{link}</code>
        <button className="button button-small" onClick={() => copy(link, "link")} data-testid="sp-copy-form-link">{copied === "link" ? "Copied!" : "Copy Form Link"}</button>
      </div>
      <h4 style={{ marginTop: "14px" }}>Email to Send</h4>
      {!email && <button className="button button-small" onClick={loadEmail} data-testid="sp-show-form-email">Show Prepared Email</button>}
      {email && (
        <>
          <p><strong>Subject:</strong> {email.subject}</p>
          <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "14px", borderRadius: "8px" }} data-testid="sp-form-email-body">{email.body}</pre>
          <button className="button button-small" onClick={() => copy(`Subject: ${email.subject}\n\n${email.body}`, "email")} data-testid="sp-copy-form-email">{copied === "email" ? "Copied!" : "Copy Email"}</button>
        </>
      )}
    </div>
  );
};

export const StrategicPlanningSection = () => {
  const [projects, setProjects] = useState([]);
  const [detail, setDetail] = useState(null);
  const [create, setCreate] = useState({ organization_name: "", founder_name: "", founder_email: "", founder_title: "", mission: "", form_content: "" });
  const [participant, setParticipant] = useState({ name: "", email: "", role: "", expertise: "" });
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState(null);
  const [response, setResponse] = useState(null);
  const [reviews, setReviews] = useState(null);
  const [editing, setEditing] = useState("");
  const [busy, setBusy] = useState("");
  const pollRef = useRef(null);
  const pid = detail?.project?.project_id;

  const loadProjects = useCallback(async () => {
    try { const r = await client.get("/admin/sp/projects"); setProjects(r.data.projects); } catch (e) { setMessage(err(e)); }
  }, []);
  const loadDetail = useCallback(async (projectId) => {
    try { const r = await client.get(`/admin/sp/projects/${projectId}`); setDetail(r.data); } catch (e) { setMessage(err(e)); }
  }, []);
  useEffect(() => { loadProjects(); }, [loadProjects]);

  useEffect(() => {
    if (!pid) return undefined;
    const generating = detail.form.status === "Generating" || ["Generating", "Synchronizing"].includes(detail.plan.status) ||
      detail.final_plan.status === "Generating" || detail.action_plan?.status === "Generating" ||
      detail.plan.suggestion_status === "Generating" || detail.areas.some((a) => a.pack_status === "Generating");
    if (generating && !pollRef.current) pollRef.current = setInterval(() => loadDetail(pid), 4000);
    if (!generating && pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [detail, pid, loadDetail]);

  const act = async (fn, okMessage) => {
    setMessage("");
    try { await fn(); if (okMessage) setMessage(okMessage); if (pid) await loadDetail(pid); await loadProjects(); }
    catch (e) { setMessage(err(e)); if (pid) await loadDetail(pid); }
  };

  const generateProject = () => act(async () => {
    const r = await client.post("/admin/sp/projects/generate", create);
    setCreate({ organization_name: "", founder_name: "", founder_email: "", founder_title: "", mission: "", form_content: "" });
    await loadDetail(r.data.project.project_id);
  }, "Creating the Strategic Planning Form, secure form link and prepared email…");

  const uploadForm = () => act(async () => {
    if (!file) throw { response: { data: { detail: "Choose the master Strategic Planning Form file first." } } };
    const form = new FormData(); form.append("file", file);
    await client.post(`/admin/sp/projects/${pid}/form/upload`, form);
    setFile(null);
  }, "Converting your uploaded form into the hosted Board form…");

  const openPreview = async (url, sendUrl, sendLabel) => {
    setMessage("");
    try { const r = await client.get(url); setPreview({ ...r.data, sendUrl, sendLabel }); } catch (e) { setMessage(err(e)); }
  };
  const sendPrepared = () => act(async () => {
    setBusy("send"); try { await client.post(preview.sendUrl); } finally { setBusy(""); }
    setPreview(null);
  }, "Email sent.");

  if (!detail) {
    return (
      <section data-testid="admin-sp-section">
        <h2 className="reference-heading">Strategic Planning</h2>
        <p className="admin-message">Paste the Strategic Planning Form content below and click Generate. The multi-step Board form, its secure link and the prepared email are created automatically.</p>
        {message && <p className="admin-message" data-testid="sp-message">{message}</p>}
        <div className="admin-import-panel" data-testid="sp-create-project">
          <h3>Create Strategic Planning Project</h3>
          <div className="admin-filters">
            {["organization_name", "founder_name", "founder_email", "founder_title"].map((k) => (
              <input key={k} placeholder={k.replaceAll("_", " ")} value={create[k]} onChange={(e) => setCreate({ ...create, [k]: e.target.value })} data-testid={`sp-create-${k}`} />
            ))}
          </div>
          <textarea placeholder="mission (optional)" rows="2" value={create.mission} onChange={(e) => setCreate({ ...create, mission: e.target.value })} style={{ width: "100%", marginTop: "8px" }} />
          <label style={{ display: "block", fontWeight: 600, marginTop: "10px" }}>Strategic Planning Form Content</label>
          <textarea placeholder="Paste the full content / instructions of the Strategic Planning Form here — it is the source authority for the generated form." rows="10" value={create.form_content} onChange={(e) => setCreate({ ...create, form_content: e.target.value })} style={{ width: "100%" }} data-testid="sp-create-form-content" />
          <button className="button" style={{ marginTop: "10px" }} onClick={generateProject} data-testid="sp-generate-project-button">{SP.buttons.generateProject}</button>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr>{["Organization", "Founder", "Board Members", "Responses", "Plan", "Created", ""].map((h) => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {projects.length === 0 && <tr><td colSpan="7" data-testid="sp-empty">No Strategic Planning projects yet.</td></tr>}
              {projects.map((p) => (
                <tr key={p.project_id}>
                  <td>{p.organization_name}</td><td>{p.founder_name}</td><td>{p.participant_count}</td>
                  <td>{p.responses_received}</td><td>{p.plan_status}</td><td>{p.created_at?.slice(0, 10)}</td>
                  <td><button className="button button-small" onClick={() => loadDetail(p.project_id)} data-testid={`sp-open-${p.project_id.slice(0, 8)}`}>Open Project</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    );
  }

  const { project, participants, form, plan, areas, final_plan: finalPlan, action_plan: actionPlan } = detail;
  const byId = Object.fromEntries(participants.map((p) => [p.participant_id, p]));
  const respondents = participants.filter((p) => p.status === "COMPLETED");
  const suggestions = plan.owner_suggestions || [];
  return (
    <section data-testid="admin-sp-project">
      <button className="button button-back button-small" onClick={() => setDetail(null)}>← All Projects</button>
      <h2 className="reference-heading">{project.organization_name} — Strategic Planning</h2>
      <p className="admin-message">Founder: {project.founder_name} ({project.founder_email})</p>
      {message && <p className="admin-message" data-testid="sp-message">{message}</p>}

      <h3>{SP.sections.form} — status: {form.status}{form.source_filename ? ` (source: ${form.source_filename})` : ""}</h3>
      {form.status === "Generating" && <p className="admin-message" data-testid="sp-form-generating">Creating the hosted multi-step form from your supplied content…</p>}
      {form.generation_error && <p className="submit-error">{form.generation_error}</p>}
      {form.status === "Approved" && <FormDistributionPanel pid={pid} project={project} onError={setMessage} />}
      <div className="admin-filters">
        {["Draft", "Approved", "Failed", "NONE"].includes(form.status) && (
          <>
            <input type="file" accept=".docx,.pdf,.txt,.doc" onChange={(e) => setFile(e.target.files?.[0] || null)} data-testid="sp-form-file" />
            <button className="button button-back button-small" onClick={uploadForm} data-testid="sp-form-upload">Replace via File Upload</button>
          </>
        )}
        {form.status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/form/approve`), "Form approved — the form link is live.")} data-testid="sp-form-approve">Approve Form</button>}
        {["Draft", "Approved"].includes(form.status) && <button className="button button-back button-small" onClick={() => setEditing(editing === "form" ? "" : "form")} data-testid="sp-form-edit-toggle">{editing === "form" ? "Close Editor" : "Review / Edit Form"}</button>}
      </div>
      {editing === "form" && form.sections && (
        <FormEditor pid={pid} form={form} onSaved={() => { setEditing(""); loadDetail(pid); }} onError={setMessage} />
      )}

      <h3 style={{ marginTop: "24px" }}>{SP.sections.responses} ({respondents.length})</h3>
      <p className="admin-message">Everyone who completes the form appears here automatically with their submitted name and email — you never re-enter them.</p>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr>{["Name", "Email", "Role", "Form Status", "Review Status", "Actions"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>{participants.map((p) => (
            <tr key={p.participant_id} data-testid={`sp-row-${p.participant_id.slice(0, 8)}`}>
              <td>{p.name}</td><td>{p.email}</td><td>{p.role}</td><td>{p.status}</td><td>{p.review_status}</td>
              <td style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                <button className="table-link" onClick={() => openPreview(`/admin/sp/projects/${pid}/participants/${p.participant_id}/email-preview`, `/admin/sp/projects/${pid}/participants/${p.participant_id}/send`)} data-testid={`sp-form-email-${p.participant_id.slice(0, 8)}`}>Form Email</button>
                {p.status === "COMPLETED" && <button className="table-link" onClick={() => act(async () => { const r = await client.get(`/admin/sp/projects/${pid}/participants/${p.participant_id}/response`); setResponse(r.data); })} data-testid={`sp-response-${p.participant_id.slice(0, 8)}`}>View Response</button>}
                {["Approved", "Synchronized", "Finalized"].includes(plan.status) && <button className="table-link" onClick={() => openPreview(`/admin/sp/projects/${pid}/participants/${p.participant_id}/review-email-preview`, `/admin/sp/projects/${pid}/participants/${p.participant_id}/send-review`)} data-testid={`sp-review-email-${p.participant_id.slice(0, 8)}`}>Review Email</button>}
                {p.status === "NOT SENT" && <button className="table-link" onClick={() => act(() => client.delete(`/admin/sp/projects/${pid}/participants/${p.participant_id}`))}>Remove</button>}
              </td>
            </tr>))}
          </tbody>
        </table>
      </div>
      <details style={{ marginTop: "8px" }}>
        <summary>Add a Board Member manually (optional)</summary>
        <div className="admin-filters" style={{ marginTop: "8px" }}>
          {["name", "email", "role", "expertise"].map((k) => (
            <input key={k} placeholder={k} value={participant[k]} onChange={(e) => setParticipant({ ...participant, [k]: e.target.value })} data-testid={`sp-participant-${k}`} />
          ))}
          <button className="button button-small" onClick={() => act(async () => { await client.post(`/admin/sp/projects/${pid}/participants`, participant); setParticipant({ name: "", email: "", role: "", expertise: "" }); })} data-testid="sp-add-participant">Add Board Member</button>
        </div>
      </details>

      <h3 style={{ marginTop: "24px" }}>{SP.sections.draft} — status: {plan.status}</h3>
      {plan.status === "Synchronizing" && <p className="admin-message" data-testid="sp-synchronizing">Synchronizing the Board's review into the Foundational Plan…</p>}
      {plan.generation_error && <p className="submit-error">{plan.generation_error}</p>}
      <div className="admin-filters">
        <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/plan/generate`), "Generating the Draft Plan from every Board response…")} data-testid="sp-plan-generate">{SP.buttons.generateDraft}</button>
        {plan.status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/plan/approve`), "Draft approved — you can now email it to the Board for review.")} data-testid="sp-plan-approve">Approve Draft</button>}
        {["Approved", "Synchronized"].includes(plan.status) && <button className="button button-small" onClick={() => openPreview(`/admin/sp/projects/${pid}/review-email-preview`, `/admin/sp/projects/${pid}/send-review-all`, "Send to Every Respondent")} data-testid="sp-email-draft-to-board">{SP.buttons.emailDraftToBoard}</button>}
        {["Draft", "Approved", "Synchronized"].includes(plan.status) && <button className="button button-back button-small" onClick={() => setEditing(editing === "plan" ? "" : "plan")} data-testid="sp-plan-edit-toggle">{editing === "plan" ? "Close Editor" : "Edit Draft"}</button>}
        {["Approved", "Synchronized", "Finalized"].includes(plan.status) && <button className="button button-back button-small" onClick={() => act(async () => { const r = await client.get(`/admin/sp/projects/${pid}/reviews`); setReviews(r.data.reviews); })} data-testid="sp-view-reviews">View Board Refinement</button>}
        {["Approved", "Synchronized"].includes(plan.status) && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/plan/synchronize`), "Synchronizing the Board's responses, draft and review comments…")} data-testid="sp-synchronize">{SP.buttons.synchronize}</button>}
        {["Approved", "Synchronized"].includes(plan.status) && <button className="button button-small" onClick={() => setEditing("finalize")} data-testid="sp-finalize-toggle">{SP.buttons.finalize}</button>}
      </div>
      {plan.display_text && editing !== "plan" && editing !== "finalize" && <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "14px", borderRadius: "8px", maxHeight: "340px", overflow: "auto" }} data-testid="sp-plan-text">{plan.display_text}</pre>}
      {editing === "plan" && <TextEditor label="Draft Plan" initial={plan.display_text} testid="sp-plan-editor" onSave={(text) => act(async () => { await client.put(`/admin/sp/projects/${pid}/plan`, { text }); setEditing(""); }, "Draft saved.")} />}
      {editing === "finalize" && <TextEditor label="Finalized Foundational Plan (review the synchronized plan, then Save to FINALIZE)" initial={plan.display_text} testid="sp-finalize-editor" onSave={(text) => act(async () => { await client.post(`/admin/sp/projects/${pid}/plan/finalize`, { text }); setEditing(""); }, "Foundational Plan finalized — you can now assign strategic areas.")} />}
      {reviews && (
        <div className="admin-import-panel" data-testid="sp-reviews">
          <h4>Board Review &amp; Refinement responses</h4>
          {reviews.length === 0 && <p>No reviews submitted yet.</p>}
          {reviews.map((r) => (
            <div key={r.participant.participant_id} style={{ marginBottom: "10px" }}>
              <strong>{r.participant.name}</strong> — {r.review_submitted_at?.slice(0, 10)}
              <ul>{r.responses.map((a, i) => <li key={i}>[{a.area_key}] {a.choice}{a.comment ? ` — ${a.comment}` : ""}</li>)}</ul>
            </div>
          ))}
          <button className="button button-back button-small" onClick={() => setReviews(null)}>Close</button>
        </div>
      )}

      <h3 style={{ marginTop: "24px" }}>{SP.sections.areas}</h3>
      {plan.status !== "Finalized" && <p className="admin-message">Finalize the Foundational Plan to unlock area assignment.</p>}
      {plan.status === "Finalized" && (
        <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/areas/suggest-owners`), "Reviewing each Board Member's skills, experience and responses to recommend area owners…")} data-testid="sp-suggest-owners">
          {plan.suggestion_status === "Generating" ? "Recommending Area Owners…" : SP.buttons.suggestOwners}
        </button>
      )}
      {areas.map((a) => {
        const suggestion = suggestions.find((s) => s.area_key === a.area_key);
        return (
          <div className="admin-import-panel" key={a.area_key} data-testid={`sp-area-${a.area_key}`}>
            <h4>{a.area} — {a.status}</h4>
            {suggestion && (suggestion.suggested_name
              ? <p className="admin-message" data-testid={`sp-suggestion-${a.area_key}`}>AI Recommendation: <strong>{suggestion.suggested_name}</strong> — {suggestion.basis}</p>
              : <p className="admin-message" data-testid={`sp-suggestion-${a.area_key}`}>AI Recommendation: no clear fit — assign manually or leave unassigned.</p>)}
            <div className="admin-filters">
              {suggestion?.suggested_participant_id && a.owner_participant_id !== suggestion.suggested_participant_id && plan.status === "Finalized" && (
                <button className="button button-small" onClick={() => act(() => client.put(`/admin/sp/projects/${pid}/areas/${a.area_key}/owner`, { participant_id: suggestion.suggested_participant_id }), "Recommendation approved and Area Owner recorded.")} data-testid={`sp-approve-suggestion-${a.area_key}`}>Approve Recommendation</button>
              )}
              <select value={a.owner_participant_id || ""} disabled={plan.status !== "Finalized"} onChange={(e) => act(() => client.put(`/admin/sp/projects/${pid}/areas/${a.area_key}/owner`, { participant_id: e.target.value }), e.target.value ? "Area Owner recorded." : "Area left unassigned.")} data-testid={`sp-owner-${a.area_key}`}>
                <option value="">{SP.leaveUnassigned}</option>
                {participants.map((p) => <option key={p.participant_id} value={p.participant_id}>{p.name}</option>)}
              </select>
              <select value={a.status} onChange={(e) => act(() => client.put(`/admin/sp/projects/${pid}/areas/${a.area_key}/status`, { status: e.target.value }))} data-testid={`sp-status-${a.area_key}`}>
                {AREA_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              {a.owner_participant_id && plan.status === "Finalized" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/areas/${a.area_key}/pack/generate`), "Generating the Area Development Pack…")} data-testid={`sp-pack-generate-${a.area_key}`}>Generate Development Pack</button>}
              {a.pack_status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/areas/${a.area_key}/pack/approve`), "Pack approved.")} data-testid={`sp-pack-approve-${a.area_key}`}>Approve Pack</button>}
              {["Draft", "Approved"].includes(a.pack_status) && <button className="button button-back button-small" onClick={() => setEditing(editing === `pack-${a.area_key}` ? "" : `pack-${a.area_key}`)}>Edit Pack</button>}
              {a.pack_status === "Approved" && <button className="button button-small" onClick={() => openPreview(`/admin/sp/projects/${pid}/areas/${a.area_key}/pack-email-preview`, `/admin/sp/projects/${pid}/areas/${a.area_key}/pack/send`)} data-testid={`sp-pack-email-${a.area_key}`}>Area Owner Email</button>}
            </div>
            {a.pack_status && a.pack_status !== "NONE" && <p>Pack: {a.pack_status} {a.pack_generation_error && <span className="submit-error">{a.pack_generation_error}</span>} — owner: {byId[a.owner_participant_id]?.name || "unassigned"}</p>}
            {editing === `pack-${a.area_key}` && <PackEditor pid={pid} areaKey={a.area_key} onSaved={() => { setEditing(""); loadDetail(pid); }} onError={setMessage} />}
            {a.submitted_plan && (
              <>
                <h5>Submitted detailed plan ({a.plan_submitted_at?.slice(0, 10)})</h5>
                <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "12px", borderRadius: "8px", maxHeight: "220px", overflow: "auto" }}>{a.submitted_plan}</pre>
                <AdoptionRecorder area={a} onRecord={(payload) => act(() => client.put(`/admin/sp/projects/${pid}/areas/${a.area_key}/adoption`, payload), "Board discussion outcome recorded.")} />
              </>
            )}
            {a.adoption_conclusion && <p><strong>Board conclusion:</strong> {a.adoption_conclusion} — {a.adopted ? "ADOPTED" : "NOT ADOPTED YET"}</p>}
          </div>
        );
      })}

      <h3 style={{ marginTop: "24px" }}>{SP.sections.actionPlan} — status: {actionPlan?.status || "NONE"}</h3>
      {actionPlan?.generation_error && <p className="submit-error">{actionPlan.generation_error}</p>}
      <div className="admin-filters">
        <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/action-plan/generate`), "Generating the one-page Action Planning document…")} data-testid="sp-action-generate">{SP.buttons.generateActionPlan}</button>
        {actionPlan?.status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/action-plan/approve`), "Action Plan approved.")} data-testid="sp-action-approve">Approve Action Plan</button>}
        {["Draft", "Approved"].includes(actionPlan?.status) && <button className="button button-back button-small" onClick={() => setEditing(editing === "action" ? "" : "action")} data-testid="sp-action-edit-toggle">{editing === "action" ? "Close Editor" : "Edit Action Plan"}</button>}
        {actionPlan?.text && <a className="button button-back button-small" href={`${process.env.REACT_APP_BACKEND_URL}/api/admin/sp/projects/${pid}/action-plan/pdf`} data-testid="sp-action-pdf">Download PDF</a>}
        {actionPlan?.status === "Approved" && <button className="button button-small" onClick={() => openPreview(`/admin/sp/projects/${pid}/action-plan/email-preview`, `/admin/sp/projects/${pid}/action-plan/send`)} data-testid="sp-action-email">Prepare / Send Email</button>}
        {actionPlan?.status === "Approved" && actionPlan.share_token && <a className="button button-back button-small" href={`/strategic-action-plan/${actionPlan.share_token}`} target="_blank" rel="noreferrer" data-testid="sp-action-view-online">View Online</a>}
      </div>
      {actionPlan?.text && editing !== "action" && <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "14px", borderRadius: "8px", maxHeight: "300px", overflow: "auto" }} data-testid="sp-action-text">{actionPlan.text}</pre>}
      {editing === "action" && <TextEditor label="One-Page Action Plan" initial={actionPlan?.text} testid="sp-action-editor" onSave={(text) => act(async () => { await client.put(`/admin/sp/projects/${pid}/action-plan`, { text }); setEditing(""); }, "Action Plan saved.")} />}

      <h3 style={{ marginTop: "24px" }}>{SP.sections.finalPlan} — status: {finalPlan.status}</h3>
      {finalPlan.generation_error && <p className="submit-error">{finalPlan.generation_error}</p>}
      <div className="admin-filters">
        <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/final-plan/generate`), "Combining the adopted area plans into one Strategic Plan…")} data-testid="sp-final-generate">{SP.buttons.buildFinalPlan}</button>
        {finalPlan.status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/final-plan/approve`), "Final Strategic Plan approved.")} data-testid="sp-final-approve">Approve Final Plan</button>}
        {["Draft", "Approved"].includes(finalPlan.status) && <button className="button button-back button-small" onClick={() => setEditing(editing === "final" ? "" : "final")}>Edit Final Plan</button>}
        {finalPlan.display_text && <a className="button button-back button-small" href={`${process.env.REACT_APP_BACKEND_URL}/api/admin/sp/projects/${pid}/final-plan/pdf`} data-testid="sp-final-pdf">Download PDF</a>}
        {finalPlan.status === "Approved" && <button className="button button-small" onClick={() => openPreview(`/admin/sp/projects/${pid}/final-plan/email-preview`, `/admin/sp/projects/${pid}/final-plan/send`)} data-testid="sp-final-email">Prepare / Send Delivery Email</button>}
        {finalPlan.status === "Approved" && finalPlan.share_token && <a className="button button-back button-small" href={`/strategic-plan/${finalPlan.share_token}`} target="_blank" rel="noreferrer" data-testid="sp-final-view-online">View Online</a>}
        {plan.status === "Finalized" && (
          <button className="button button-back button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/meeting-guide/generate`), "Generating the Adoption Meeting Facilitation Guide…")} data-testid="sp-meeting-guide-generate">{SP.buttons.generateMeetingGuide}</button>
        )}
      </div>
      {finalPlan.meeting_status && finalPlan.meeting_status !== "NONE" && (
        <div className="admin-import-panel" data-testid="sp-meeting-guide">
          <h4>Adoption Meeting Facilitation Guide — {finalPlan.meeting_status}</h4>
          {finalPlan.meeting_generation_error && <p className="submit-error">{finalPlan.meeting_generation_error}</p>}
          <div className="admin-filters">
            {finalPlan.meeting_status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/meeting-guide/approve`), "Meeting guide approved.")} data-testid="sp-meeting-approve">Approve Guide</button>}
            {["Draft", "Approved"].includes(finalPlan.meeting_status) && <button className="button button-back button-small" onClick={() => setEditing(editing === "meeting" ? "" : "meeting")}>Edit Guide</button>}
            {finalPlan.meeting_guide_text && <a className="button button-back button-small" href={`${process.env.REACT_APP_BACKEND_URL}/api/admin/sp/projects/${pid}/meeting-guide/pdf`} data-testid="sp-meeting-pdf">Download PDF</a>}
          </div>
          {finalPlan.meeting_guide_text && editing !== "meeting" && <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "12px", borderRadius: "8px", maxHeight: "260px", overflow: "auto" }}>{finalPlan.meeting_guide_text}</pre>}
          {editing === "meeting" && <TextEditor label="Adoption Meeting Facilitation Guide" initial={finalPlan.meeting_guide_text} testid="sp-meeting-editor" onSave={(text) => act(async () => { await client.put(`/admin/sp/projects/${pid}/meeting-guide`, { text }); setEditing(""); }, "Guide saved.")} />}
        </div>
      )}
      {finalPlan.display_text && editing !== "final" && <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "14px", borderRadius: "8px", maxHeight: "340px", overflow: "auto" }} data-testid="sp-final-text">{finalPlan.display_text}</pre>}
      {editing === "final" && <TextEditor label="Final Strategic Plan" initial={finalPlan.display_text} testid="sp-final-editor" onSave={(text) => act(async () => { await client.put(`/admin/sp/projects/${pid}/final-plan`, { text }); setEditing(""); }, "Final plan saved.")} />}

      {preview && <EmailPreviewModal preview={preview} busy={busy === "send"} sendLabel={preview.sendLabel || "Send This Email Now"} onSend={sendPrepared} onClose={() => setPreview(null)} />}
      {response && (
        <div className="admin-profile-overlay" data-testid="sp-response-modal">
          <div className="admin-profile-panel">
            <button className="profile-close" onClick={() => setResponse(null)}>×</button>
            <h3>{response.participant.name} — original response ({response.submitted_at?.slice(0, 10)})</h3>
            <dl>{response.questions.map((q) => (
              <div key={q.id}><dt style={{ fontWeight: 600 }}>[{q.section}] {q.prompt}</dt>
                <dd>{Array.isArray(response.response[q.id]) ? response.response[q.id].join(", ") : (response.response[q.id] || "—")}</dd></div>
            ))}</dl>
          </div>
        </div>
      )}
    </section>
  );
};

const FormEditor = ({ pid, form, onSaved, onError }) => {
  const [intro, setIntro] = useState(form.introduction || form.content?.introduction || "");
  const [sections, setSections] = useState(JSON.parse(JSON.stringify(form.sections || form.content?.sections || [])));
  const save = async () => {
    try { await client.put(`/admin/sp/projects/${pid}/form`, { introduction: intro, sections }); onSaved(); }
    catch (e) { onError(err(e)); }
  };
  return (
    <div className="admin-import-panel" data-testid="sp-form-editor">
      <label style={{ fontWeight: 600 }}>Introduction</label>
      <textarea rows="4" style={{ width: "100%" }} value={intro} onChange={(e) => setIntro(e.target.value)} data-testid="sp-form-intro" />
      {sections.map((s, si) => (
        <div key={s.key || si} style={{ marginTop: "10px" }}>
          <input style={{ fontWeight: 700, width: "100%" }} value={s.title} onChange={(e) => setSections(sections.map((x, i) => (i === si ? { ...x, title: e.target.value } : x)))} />
          {s.questions.map((q, qi) => (
            <input key={q.id || qi} style={{ width: "100%", marginTop: "4px" }} value={q.prompt}
              onChange={(e) => setSections(sections.map((x, i) => (i === si ? { ...x, questions: x.questions.map((y, j) => (j === qi ? { ...y, prompt: e.target.value } : y)) } : x)))} />
          ))}
        </div>
      ))}
      <p className="admin-message">Saving returns the form to Draft — approve it again to update the live form link.</p>
      <button className="button button-small" style={{ marginTop: "10px" }} onClick={save} data-testid="sp-form-save">Save Form</button>
    </div>
  );
};

const PackEditor = ({ pid, areaKey, onSaved, onError }) => {
  const [text, setText] = useState("");
  useEffect(() => {
    client.get(`/admin/sp/projects/${pid}/areas/${areaKey}/pack`).then((r) => setText(r.data.pack_text)).catch(() => {});
  }, [pid, areaKey]);
  return (
    <div>
      <textarea rows="12" style={{ width: "100%" }} value={text} onChange={(e) => setText(e.target.value)} data-testid={`sp-pack-editor-${areaKey}`} />
      <button className="button button-small" onClick={async () => { try { await client.put(`/admin/sp/projects/${pid}/areas/${areaKey}/pack`, { text }); onSaved(); } catch (e) { onError(err(e)); } }}>Save Pack</button>
    </div>
  );
};

const AdoptionRecorder = ({ area, onRecord }) => {
  const [conclusion, setConclusion] = useState(area.adoption_conclusion || "");
  const [adopted, setAdopted] = useState(!!area.adopted);
  return (
    <div className="admin-filters" style={{ marginTop: "8px" }}>
      <textarea rows="3" style={{ flex: 1, minWidth: "260px" }} placeholder="Board discussion conclusion / modifications for this area" value={conclusion} onChange={(e) => setConclusion(e.target.value)} data-testid={`sp-adoption-conclusion-${area.area_key}`} />
      <label className="terms-check"><input type="checkbox" checked={adopted} onChange={(e) => setAdopted(e.target.checked)} data-testid={`sp-adopted-${area.area_key}`} /> <span>Adopted by the Board</span></label>
      <button className="button button-small" onClick={() => onRecord({ conclusion, adopted })} data-testid={`sp-record-adoption-${area.area_key}`}>Record Outcome</button>
    </div>
  );
};
