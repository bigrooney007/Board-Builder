import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";

const client = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });
const err = (e) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Action failed.");
const AREA_STATUSES = ["NOT ASSIGNED", "ASSIGNED", "IN DEVELOPMENT", "SUBMITTED", "READY FOR BOARD"];

const EmailPreviewModal = ({ preview, onSend, onClose, busy }) => (
  <div className="admin-profile-overlay" data-testid="sp-email-preview">
    <div className="admin-profile-panel">
      <button className="profile-close" onClick={onClose}>×</button>
      <p className="eyebrow">Prepared email — nothing is sent until you choose Send</p>
      <p><strong>To:</strong> {preview.to_name} &lt;{preview.to_email}&gt;</p>
      <p><strong>Subject:</strong> {preview.subject}</p>
      <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "14px", borderRadius: "8px" }}>{preview.body}</pre>
      <p><strong>Secure link:</strong> <a href={preview.form_link} target="_blank" rel="noreferrer">{preview.form_link}</a></p>
      <div className="admin-profile-actions">
        {onSend && <button className="button" disabled={busy} onClick={onSend} data-testid="sp-email-send">{busy ? "Sending…" : "Send This Email Now"}</button>}
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

export const StrategicPlanningSection = () => {
  const [projects, setProjects] = useState([]);
  const [detail, setDetail] = useState(null);
  const [create, setCreate] = useState({ organization_name: "", founder_name: "", founder_email: "", founder_title: "", mission: "" });
  const [participant, setParticipant] = useState({ name: "", email: "", role: "", expertise: "" });
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState(null);
  const [response, setResponse] = useState(null);
  const [reviews, setReviews] = useState(null);
  const [suggestions, setSuggestions] = useState(null);
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
    const generating = detail.form.status === "Generating" || detail.plan.status === "Generating" ||
      detail.final_plan.status === "Generating" || detail.areas.some((a) => a.pack_status === "Generating");
    if (generating && !pollRef.current) pollRef.current = setInterval(() => loadDetail(pid), 4000);
    if (!generating && pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [detail, pid, loadDetail]);

  const act = async (fn, okMessage) => {
    setMessage("");
    try { await fn(); if (okMessage) setMessage(okMessage); if (pid) await loadDetail(pid); await loadProjects(); }
    catch (e) { setMessage(err(e)); if (pid) await loadDetail(pid); }
  };

  const createProject = () => act(async () => {
    const r = await client.post("/admin/sp/projects", create);
    setCreate({ organization_name: "", founder_name: "", founder_email: "", founder_title: "", mission: "" });
    await loadDetail(r.data.project.project_id);
  }, "Project created.");

  const uploadForm = () => act(async () => {
    if (!file) throw { response: { data: { detail: "Choose the master Strategic Planning Form file first." } } };
    const form = new FormData(); form.append("file", file);
    await client.post(`/admin/sp/projects/${pid}/form/upload`, form);
    setFile(null);
  }, "Converting your uploaded form into the hosted Board form…");

  const openPreview = async (url, sendUrl) => {
    setMessage("");
    try { const r = await client.get(url); setPreview({ ...r.data, sendUrl }); } catch (e) { setMessage(err(e)); }
  };
  const sendPrepared = () => act(async () => {
    setBusy("send"); try { await client.post(preview.sendUrl); } finally { setBusy(""); }
    setPreview(null);
  }, "Email sent.");

  if (!detail) {
    return (
      <section data-testid="admin-sp-section">
        <h2 className="reference-heading">Strategic Planning</h2>
        <p className="admin-message">Admin service-delivery pathway: facilitate a client organization's strategic planning using hosted Board forms, secure links and consolidated plans.</p>
        {message && <p className="admin-message" data-testid="sp-message">{message}</p>}
        <div className="admin-import-panel" data-testid="sp-create-project">
          <h3>Create Strategic Planning Project</h3>
          {["organization_name", "founder_name", "founder_email", "founder_title"].map((k) => (
            <input key={k} placeholder={k.replaceAll("_", " ")} value={create[k]} onChange={(e) => setCreate({ ...create, [k]: e.target.value })} data-testid={`sp-create-${k}`} style={{ display: "block", width: "100%", marginBottom: "8px" }} />
          ))}
          <textarea placeholder="mission (optional)" rows="2" value={create.mission} onChange={(e) => setCreate({ ...create, mission: e.target.value })} style={{ width: "100%" }} />
          <button className="button button-small" onClick={createProject} data-testid="sp-create-project-button">Create Strategic Planning Project</button>
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

  const { project, participants, form, plan, areas, final_plan: finalPlan } = detail;
  const byId = Object.fromEntries(participants.map((p) => [p.participant_id, p]));
  return (
    <section data-testid="admin-sp-project">
      <button className="button button-back button-small" onClick={() => setDetail(null)}>← All Projects</button>
      <h2 className="reference-heading">{project.organization_name} — Strategic Planning</h2>
      <p className="admin-message">Founder: {project.founder_name} ({project.founder_email})</p>
      {message && <p className="admin-message" data-testid="sp-message">{message}</p>}

      <h3>1. Board Members</h3>
      <div className="admin-filters">
        {["name", "email", "role", "expertise"].map((k) => (
          <input key={k} placeholder={k} value={participant[k]} onChange={(e) => setParticipant({ ...participant, [k]: e.target.value })} data-testid={`sp-participant-${k}`} />
        ))}
        <button className="button button-small" onClick={() => act(async () => { await client.post(`/admin/sp/projects/${pid}/participants`, participant); setParticipant({ name: "", email: "", role: "", expertise: "" }); })} data-testid="sp-add-participant">Add Board Member</button>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr>{["Name", "Email", "Role", "Form Status", "Review Status", "Actions"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>{participants.map((p) => (
            <tr key={p.participant_id} data-testid={`sp-row-${p.participant_id.slice(0, 8)}`}>
              <td>{p.name}</td><td>{p.email}</td><td>{p.role}</td><td>{p.status}</td><td>{p.review_status}</td>
              <td style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                <button className="table-link" onClick={() => openPreview(`/admin/sp/projects/${pid}/participants/${p.participant_id}/email-preview`, `/admin/sp/projects/${pid}/participants/${p.participant_id}/send`)} data-testid={`sp-form-email-${p.participant_id.slice(0, 8)}`}>Form Email</button>
                {p.status === "COMPLETED" && <button className="table-link" onClick={() => act(async () => { const r = await client.get(`/admin/sp/projects/${pid}/participants/${p.participant_id}/response`); setResponse(r.data); })} data-testid={`sp-response-${p.participant_id.slice(0, 8)}`}>View Response</button>}
                {plan.status === "Approved" && <button className="table-link" onClick={() => openPreview(`/admin/sp/projects/${pid}/participants/${p.participant_id}/review-email-preview`, `/admin/sp/projects/${pid}/participants/${p.participant_id}/send-review`)} data-testid={`sp-review-email-${p.participant_id.slice(0, 8)}`}>Review Email</button>}
                {p.status === "NOT SENT" && <button className="table-link" onClick={() => act(() => client.delete(`/admin/sp/projects/${pid}/participants/${p.participant_id}`))}>Remove</button>}
              </td>
            </tr>))}
          </tbody>
        </table>
      </div>

      <h3 style={{ marginTop: "24px" }}>2. Strategic Planning Form — status: {form.status}{form.source_filename ? ` (source: ${form.source_filename})` : ""}</h3>
      {form.generation_error && <p className="submit-error">{form.generation_error}</p>}
      <div className="admin-filters">
        <input type="file" accept=".docx,.pdf,.txt,.doc" onChange={(e) => setFile(e.target.files?.[0] || null)} data-testid="sp-form-file" />
        <button className="button button-small" onClick={uploadForm} data-testid="sp-form-upload">Upload / Import Master Form</button>
        {form.status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/form/approve`), "Form approved — you can now send secure links.")} data-testid="sp-form-approve">Approve Form</button>}
        {["Draft", "Approved"].includes(form.status) && <button className="button button-back button-small" onClick={() => setEditing(editing === "form" ? "" : "form")} data-testid="sp-form-edit-toggle">{editing === "form" ? "Close Editor" : "Review / Edit Form"}</button>}
      </div>
      {editing === "form" && form.sections && (
        <FormEditor pid={pid} form={form} onSaved={() => { setEditing(""); loadDetail(pid); }} onError={setMessage} />
      )}

      <h3 style={{ marginTop: "24px" }}>3. Foundational Strategic Plan — status: {plan.status}</h3>
      {plan.generation_error && <p className="submit-error">{plan.generation_error}</p>}
      <div className="admin-filters">
        <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/plan/generate`), "Generating the Foundational Strategic Plan from every Board response…")} data-testid="sp-plan-generate">Generate Foundational Strategic Plan</button>
        {plan.status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/plan/approve`), "Plan approved — send it to Board Members for review & refinement.")} data-testid="sp-plan-approve">Approve for Board Review</button>}
        {["Draft", "Approved"].includes(plan.status) && <button className="button button-back button-small" onClick={() => setEditing(editing === "plan" ? "" : "plan")} data-testid="sp-plan-edit-toggle">{editing === "plan" ? "Close Editor" : "Edit Draft"}</button>}
        {["Approved", "Finalized"].includes(plan.status) && <button className="button button-back button-small" onClick={() => act(async () => { const r = await client.get(`/admin/sp/projects/${pid}/reviews`); setReviews(r.data.reviews); })} data-testid="sp-view-reviews">View Board Refinement</button>}
        {plan.status === "Approved" && <button className="button button-small" onClick={() => setEditing("finalize")} data-testid="sp-finalize-toggle">Finalize Foundational Plan</button>}
      </div>
      {plan.display_text && editing !== "plan" && editing !== "finalize" && <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "14px", borderRadius: "8px", maxHeight: "340px", overflow: "auto" }} data-testid="sp-plan-text">{plan.display_text}</pre>}
      {editing === "plan" && <TextEditor label="Foundational Strategic Plan (draft)" initial={plan.display_text} testid="sp-plan-editor" onSave={(text) => act(async () => { await client.put(`/admin/sp/projects/${pid}/plan`, { text }); setEditing(""); }, "Draft saved.")} />}
      {editing === "finalize" && <TextEditor label="Finalized Foundational Plan (incorporate the Board's refinement, then Save to FINALIZE)" initial={plan.display_text} testid="sp-finalize-editor" onSave={(text) => act(async () => { await client.post(`/admin/sp/projects/${pid}/plan/finalize`, { text }); setEditing(""); }, "Foundational Plan finalized — you can now assign strategic areas.")} />}
      {reviews && (
        <div className="admin-import-panel" data-testid="sp-reviews">
          <h4>Board Review & Refinement responses</h4>
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

      <h3 style={{ marginTop: "24px" }}>4. Strategic Areas, Owners & Development Packs</h3>
      {plan.status !== "Finalized" && <p className="admin-message">Finalize the Foundational Plan to unlock area assignment.</p>}
      {plan.status === "Finalized" && (
        <button className="button button-small" onClick={() => act(async () => { const r = await client.post(`/admin/sp/projects/${pid}/areas/suggest-owners`); setSuggestions(r.data.suggestions); })} data-testid="sp-suggest-owners">Suggest Area Owners (you make the final assignment)</button>
      )}
      {areas.map((a) => {
        const suggestion = (suggestions || []).find((s) => s.area_key === a.area_key);
        return (
          <div className="admin-import-panel" key={a.area_key} data-testid={`sp-area-${a.area_key}`}>
            <h4>{a.area} — {a.status}</h4>
            {suggestion?.suggested_name && <p className="admin-message">Suggested owner: <strong>{suggestion.suggested_name}</strong> ({suggestion.basis})</p>}
            <div className="admin-filters">
              <select value={a.owner_participant_id || ""} disabled={plan.status !== "Finalized"} onChange={(e) => act(() => client.put(`/admin/sp/projects/${pid}/areas/${a.area_key}/owner`, { participant_id: e.target.value }), "Area Owner recorded.")} data-testid={`sp-owner-${a.area_key}`}>
                <option value="">— Assign Area Owner —</option>
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

      <h3 style={{ marginTop: "24px" }}>5. Final Strategic Plan — status: {finalPlan.status}</h3>
      {finalPlan.generation_error && <p className="submit-error">{finalPlan.generation_error}</p>}
      <div className="admin-filters">
        <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/final-plan/generate`), "Combining the adopted area plans into one Strategic Plan…")} data-testid="sp-final-generate">Build Final Strategic Plan</button>
        {finalPlan.status === "Draft" && <button className="button button-small" onClick={() => act(() => client.post(`/admin/sp/projects/${pid}/final-plan/approve`), "Final Strategic Plan approved.")} data-testid="sp-final-approve">Approve Final Plan</button>}
        {["Draft", "Approved"].includes(finalPlan.status) && <button className="button button-back button-small" onClick={() => setEditing(editing === "final" ? "" : "final")}>Edit Final Plan</button>}
        {finalPlan.display_text && <a className="button button-back button-small" href={`${process.env.REACT_APP_BACKEND_URL}/api/admin/sp/projects/${pid}/final-plan/pdf`} data-testid="sp-final-pdf">Download PDF</a>}
      </div>
      {finalPlan.display_text && editing !== "final" && <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "14px", borderRadius: "8px", maxHeight: "340px", overflow: "auto" }} data-testid="sp-final-text">{finalPlan.display_text}</pre>}
      {editing === "final" && <TextEditor label="Final Strategic Plan" initial={finalPlan.display_text} testid="sp-final-editor" onSave={(text) => act(async () => { await client.put(`/admin/sp/projects/${pid}/final-plan`, { text }); setEditing(""); }, "Final plan saved.")} />}

      {preview && <EmailPreviewModal preview={preview} busy={busy === "send"} onSend={sendPrepared} onClose={() => setPreview(null)} />}
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
