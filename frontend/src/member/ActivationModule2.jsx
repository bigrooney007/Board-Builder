import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Copy, Mail, Phone, Plus, UserPlus, X } from "lucide-react";
import { memberApi } from "./api";
import { activationM2Text } from "../content/appContent";

const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const dialogStyle = { background: "#fff", maxWidth: 760, width: "100%", padding: "28px", borderRadius: 8, position: "relative" };

const Modal = ({ children, onClose, testId }) => (
  <div style={overlayStyle} data-testid={testId}>
    <div style={dialogStyle}>
      <button type="button" onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testId}-close`}><X size={20} /></button>
      {children}
    </div>
  </div>
);

const RESPONSE_SECTIONS = [
  ["Fundraising Goal / Priorities", ["goal_important", "goal_clarity"]],
  ["Potential Funding Audiences", ["funding_audiences", "audiences_why"]],
  ["Fundraising Opportunities", ["opportunities", "opportunity_priority"]],
  ["Relationships / Networks", ["network_categories", "specific_relationships"]],
  ["Fundraising Messaging Ideas", ["why_support", "talk_about"]],
  ["Outreach Ideas", ["outreach_methods", "outreach_add"]],
  ["Personal Participation", ["participation_activities"]],
  ["Areas of Ownership", ["ownership"]],
  ["Support Needed", ["support_needed"]],
  ["90-Day Priorities", ["ninety_day_priorities"]],
  ["Additional Ideas", ["fundraising_idea", "final_thoughts"]],
];

const LABELS = {
  goal_important: "Most important about what we are trying to fund", goal_clarity: "Where greater clarity is needed",
  funding_audiences: "Who we should build relationships with", audiences_why: "Why they may care about our work",
  opportunities: "Opportunities to explore or strengthen", opportunity_priority: "Greatest opportunity right now, and why",
  network_categories: "Relationships / networks they already have", specific_relationships: "Relationships they would be comfortable exploring",
  why_support: "What would make someone want to support us", talk_about: "What we should talk about more",
  outreach_methods: "Best ways to reach potential supporters", outreach_add: "What they would add or do differently",
  participation_activities: "Activities they are comfortable helping with",
  ownership: "What they would be willing to take responsibility for or help lead",
  support_needed: "What would help them participate more effectively",
  ninety_day_priorities: "Three fundraising things for the next 90 days",
  fundraising_idea: "Fundraising idea we should consider", final_thoughts: "Anything else to consider",
};

const ResponseView = ({ data }) => (
  <div data-testid="am2-response-view">
    {RESPONSE_SECTIONS.map(([section, keys]) => {
      const rows = keys.filter((key) => {
        const value = data.response[key];
        return Array.isArray(value) ? value.length : String(value || "").trim();
      });
      if (!rows.length) return null;
      return (
        <div key={section} style={{ marginBottom: 18 }}>
          <h3 style={{ marginBottom: 8 }}>{section}</h3>
          {rows.map((key) => {
            const value = data.response[key];
            return (
              <p key={key} style={{ margin: "0 0 8px" }}>
                <strong>{LABELS[key] || key}:</strong> {Array.isArray(value) ? value.join(", ") : value}
              </p>
            );
          })}
        </div>
      );
    })}
    <p className="eyebrow">Submitted {data.submitted_at ? new Date(data.submitted_at).toLocaleString() : ""}</p>
  </div>
);

const FormPreview = ({ content }) => (
  <div data-testid="am2-form-preview" style={{ border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 14, maxHeight: 420, overflowY: "auto" }}>
    <h3 style={{ marginTop: 0 }}>{content.title}</h3>
    <p style={{ whiteSpace: "pre-wrap" }}>{content.introduction}</p>
    {content.goal_context && <p style={{ whiteSpace: "pre-wrap" }}><strong>{content.goal_context}</strong></p>}
    {content.sections.map((section) => (
      <div key={section.key} style={{ marginTop: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 6 }}>{section.title}</p>
        {section.questions.map((question) => (
          <p key={question.id} style={{ margin: "0 0 6px" }}>
            {question.prompt} {question.required ? "" : "(optional)"}
            {question.type === "multi" && <span style={{ display: "block", fontSize: "0.85rem", color: "#555" }}>Options: {question.options.join(" · ")}</span>}
          </p>
        ))}
      </div>
    ))}
  </div>
);

export default function ActivationModule2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editForm, setEditForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ name: "", email: "", phone: "", role: "" });
  const [addError, setAddError] = useState("");
  const [preview, setPreview] = useState(null);
  const [sending, setSending] = useState(false);
  const [sendingAll, setSendingAll] = useState(false);
  const [script, setScript] = useState(null);
  const [notes, setNotes] = useState("");
  const [notesSaved, setNotesSaved] = useState(false);
  const [response, setResponse] = useState(null);
  const [copied, setCopied] = useState("");
  const pollRef = useRef(null);

  const load = useCallback(() => {
    memberApi.get("/activation/planning").then((res) => setData(res.data)).catch(() => setError("We could not load your fundraising planning workspace."));
  }, []);
  useEffect(load, [load]);

  useEffect(() => {
    if (data?.form?.status === "Generating" && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await memberApi.get("/activation/planning-form");
          if (res.data.status !== "Generating") {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setGenerating(false);
            load();
          }
        } catch { /* keep polling */ }
      }, 3000);
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [data?.form?.status, load]);

  const openResponse = useCallback((participantId) => {
    memberApi.get(`/activation/participants/${participantId}/response`).then((res) => setResponse(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const participantId = searchParams.get("participant");
    if (participantId && data) {
      openResponse(participantId);
      setSearchParams({}, { replace: true });
    }
  }, [data, searchParams, setSearchParams, openResponse]);

  const generate = async () => {
    const form = data?.form;
    if (form?.content && form.edited_since_generation) {
      const ok = window.confirm("You have manually edited this form. Regenerating will replace your edited content with a newly generated version. Do you want to continue?");
      if (!ok) return;
    } else if (form?.content) {
      const ok = window.confirm("This will replace the current form content with a newly generated version. Continue?");
      if (!ok) return;
    }
    setGenerating(true);
    try {
      await memberApi.post("/activation/planning-form/generate");
      load();
    } catch (err) {
      setGenerating(false);
      window.alert(err.response?.data?.detail || "Generation could not start. Please try again.");
    }
  };

  const openEdit = () => {
    const content = data.form.content;
    setEditForm({
      introduction: content.introduction,
      goal_context: content.goal_context,
      question_prompts: Object.fromEntries(content.sections.flatMap((s) => s.questions.map((q) => [q.id, q.prompt]))),
      prompt_list: content.sections.flatMap((s) => s.questions.map((q) => ({ id: q.id, section: s.title }))),
    });
    setShowEdit(true);
  };

  const saveEdit = async () => {
    setSaving(true);
    try {
      await memberApi.put("/activation/planning-form", {
        introduction: editForm.introduction, goal_context: editForm.goal_context,
        question_prompts: editForm.question_prompts,
      });
      setShowEdit(false);
      load();
    } catch { /* keep open */ }
    setSaving(false);
  };

  const approve = async () => {
    try { await memberApi.post("/activation/planning-form/approve"); load(); } catch { /* ignore */ }
  };

  const addMember = async () => {
    setAddError("");
    if (!addForm.name.trim() || !addForm.email.trim()) { setAddError("Full Name and Email are required."); return; }
    try {
      await memberApi.post("/activation/participants", addForm);
      setShowAdd(false);
      setAddForm({ name: "", email: "", phone: "", role: "" });
      load();
    } catch (err) {
      setAddError(err.response?.data?.detail?.[0]?.msg || err.response?.data?.detail || "Could not add this Board Member.");
    }
  };

  const importPerson = async (suggestion) => {
    try { await memberApi.post("/activation/participants/import", { source: suggestion.source, ref_id: suggestion.ref_id }); load(); } catch { /* ignore */ }
  };

  const removeParticipant = async (participant) => {
    try { await memberApi.delete(`/activation/participants/${participant.participant_id}`); load(); } catch { /* ignore */ }
  };

  const openPreview = (participant, type) => {
    memberApi.get(`/activation/participants/${participant.participant_id}/email-preview`, { params: { type } })
      .then((res) => setPreview({ ...res.data, participant, type }))
      .catch(() => {});
  };

  const sendEmail = async () => {
    setSending(true);
    try {
      await memberApi.post(`/activation/participants/${preview.participant.participant_id}/send`, { type: preview.type });
      setPreview(null);
      load();
    } catch (err) {
      window.alert(err.response?.data?.detail || "The email could not be sent.");
    }
    setSending(false);
  };

  const sendAll = async () => {
    setSendingAll(true);
    try { await memberApi.post("/activation/participants/send-all-unsent"); load(); } catch (err) {
      window.alert(err.response?.data?.detail || "The emails could not be sent.");
    }
    setSendingAll(false);
  };

  const openScript = (participant) => {
    memberApi.get(`/activation/participants/${participant.participant_id}/call-script`).then((res) => {
      setScript({ ...res.data, participant });
      setNotes(res.data.call_notes || "");
      setNotesSaved(false);
    }).catch(() => {});
  };

  const saveNotes = async () => {
    await memberApi.put(`/activation/participants/${script.participant.participant_id}/call-notes`, { notes });
    setNotesSaved(true);
    load();
  };

  const copyLink = async (participant) => {
    const res = await memberApi.get(`/activation/participants/${participant.participant_id}/email-preview`, { params: { type: "initial" } });
    try { await navigator.clipboard.writeText(res.data.form_link); } catch { window.prompt("Copy this form link:", res.data.form_link); }
    setCopied(participant.participant_id);
    setTimeout(() => setCopied(""), 2500);
  };

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">Loading your fundraising planning workspace…</p>;

  const form = data.form;
  const formApproved = form.status === "Approved";
  const unsentCount = data.participants.filter((p) => p.status === "NOT SENT").length;

  return (
    <div data-testid="activation-module2">
      <section className="member-card" data-testid="am2-intro">
        <h2>{activationM2Text.h_buildThePlanWithYour}</h2>
        <p>Do not create a fundraising plan and hand it to your Board.</p>
        <p>Get your Board involved in building it.</p>
        <p>Their ideas, professional experience, relationships and willingness to participate should help shape how your organization raises money.</p>
        <p>When people participate in building the plan, they are more likely to understand it, take ownership of it and help execute it.</p>
      </section>

      <section className="member-card" data-testid="am2-form-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2 style={{ margin: 0 }}>Board Fundraising Planning Form</h2>
          <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid="am2-form-status">
            {form.status === "NONE" ? "NOT GENERATED" : form.status.toUpperCase()}{formApproved ? ` · v${form.approved_version}` : ""}
          </span>
        </div>
        <p style={{ marginTop: 10 }}>Generate one organization-specific planning form built from your Activation intake. Review and edit it, approve it, then send every participating Board Member their own secure link to the same approved form.</p>
        {!data.has_intake && <p className="submit-error" data-testid="am2-no-intake">Your Activation intake was not found. Complete the Activation intake before generating your planning form.</p>}
        {form.status === "Failed" && <p className="submit-error" data-testid="am2-generation-error">Generation failed. Please try again.</p>}
        {form.status === "Generating" || generating ? (
          <p data-testid="am2-generating">Generating your Board Fundraising Planning Form… This can take a minute. It will appear here automatically.</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
            <button type="button" className="button" onClick={generate} data-testid="am2-generate-button">
              {form.content ? "REGENERATE" : "GENERATE MY BOARD FUNDRAISING PLANNING FORM"}
            </button>
            {form.content && (
              <>
                <button type="button" className="button button-outline" onClick={openEdit} data-testid="am2-edit-button">EDIT FORM</button>
                {!formApproved && <button type="button" className="button" onClick={approve} data-testid="am2-approve-button">APPROVE FORM</button>}
              </>
            )}
          </div>
        )}
        {form.content && form.status !== "Generating" && <FormPreview content={form.content} />}
        {form.content && !formApproved && <p className="eyebrow" style={{ marginTop: 10 }} data-testid="am2-approval-required">The form must be approved before it can be sent to Board Members.</p>}
      </section>

      <section className="member-card" data-testid="am2-progress-summary">
        <h2>{activationM2Text.h_boardFundraisingPlanningProgress}</h2>
        <p data-testid="am2-progress-counts">
          <strong>{data.progress.invited}</strong> Invited · <strong>{data.progress.received}</strong> Response{data.progress.received === 1 ? "" : "s"} Received · <strong>{data.progress.waiting}</strong> Waiting
        </p>
        {data.progress.invited > 0 && data.progress.received < data.progress.invited && (
          <p data-testid="am2-incomplete-warning">You have responses from {data.progress.received} of {data.progress.invited} Board Members. Any responses not received before you build the Fundraising Strategy Plan will not be included unless you regenerate the plan later.</p>
        )}
      </section>

      {data.suggestions.length > 0 && (
        <section className="member-card" data-testid="am2-suggestions">
          <h2>{activationM2Text.h_boardMembersAlreadyInYour}</h2>
          <p>These current Board Members already exist in your account. Add anyone who should participate in the fundraising planning process.</p>
          {data.suggestions.map((person) => (
            <div key={`${person.source}-${person.ref_id}`} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #eee", flexWrap: "wrap", gap: 8 }}>
              <span><strong>{person.name}</strong> · {person.email} <span className="eyebrow">({person.label})</span></span>
              <button type="button" className="button button-outline" onClick={() => importPerson(person)} data-testid={`am2-import-${person.ref_id}`}><UserPlus size={15} /> Add as Participant</button>
            </div>
          ))}
        </section>
      )}

      <section className="member-card" data-testid="am2-roster">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2 style={{ margin: 0 }}>Participating Board Members</h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" className="button" onClick={() => setShowAdd(true)} data-testid="am2-add-member-button"><Plus size={16} /> ADD BOARD MEMBER</button>
            {formApproved && unsentCount > 1 && (
              <button type="button" className="button button-outline" onClick={sendAll} disabled={sendingAll} data-testid="am2-send-all-button">{sendingAll ? "Sending…" : "SEND TO ALL UNSENT BOARD MEMBERS"}</button>
            )}
          </div>
        </div>
        <p style={{ marginTop: 10 }}>Choose which current Board Members should receive the planning form. Each person receives their own secure link to the same approved form.</p>
        {!data.participants.length && <p data-testid="am2-empty-roster">No participants selected yet. Add the current Board Members who should help build the fundraising plan.</p>}
        {data.participants.map((participant) => (
          <article key={participant.participant_id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 16 }} data-testid={`am2-participant-card-${participant.participant_id}`}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
              <div>
                <h3 style={{ margin: 0 }}>{participant.name}</h3>
                <p style={{ margin: "4px 0 0" }}>{participant.role || "Board Member"} · {participant.email}</p>
              </div>
              <span className="eyebrow" data-testid={`am2-status-${participant.participant_id}`} style={{ alignSelf: "flex-start", padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }}>{participant.status}</span>
            </div>
            <p className="eyebrow" style={{ marginTop: 10 }}>
              {participant.last_sent_at && <>Form sent {new Date(participant.last_sent_at).toLocaleDateString()} · </>}
              {participant.submitted_at && <>Completed {new Date(participant.submitted_at).toLocaleDateString()} · </>}
              {participant.last_reminder_at && <>Last reminder {new Date(participant.last_reminder_at).toLocaleDateString()}</>}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
              {participant.status === "NOT SENT" && (
                <>
                  <button type="button" className="button" onClick={() => openPreview(participant, "initial")} disabled={!formApproved} data-testid={`am2-send-form-${participant.participant_id}`} title={formApproved ? "" : "Approve the form first"}><Mail size={15} /> SEND FUNDRAISING PLANNING FORM</button>
                  <button type="button" className="button button-outline" onClick={() => removeParticipant(participant)} data-testid={`am2-remove-${participant.participant_id}`}>Remove</button>
                </>
              )}
              {participant.status === "SENT" && (
                <>
                  <button type="button" className="button button-outline" onClick={() => copyLink(participant)} data-testid={`am2-copy-link-${participant.participant_id}`}><Copy size={15} /> {copied === participant.participant_id ? "Link Copied" : "COPY FORM LINK"}</button>
                  <button type="button" className="button button-outline" onClick={() => openPreview(participant, "reminder")} data-testid={`am2-send-reminder-${participant.participant_id}`}><Mail size={15} /> SEND REMINDER EMAIL</button>
                  <button type="button" className="button button-outline" onClick={() => openScript(participant)} data-testid={`am2-call-script-${participant.participant_id}`}><Phone size={15} /> VIEW REMINDER CALL SCRIPT</button>
                </>
              )}
              {participant.status === "COMPLETED" && (
                <button type="button" className="button" onClick={() => openResponse(participant.participant_id)} data-testid={`am2-view-response-${participant.participant_id}`}>VIEW RESPONSE</button>
              )}
            </div>
          </article>
        ))}
      </section>

      <section style={{ textAlign: "center", margin: "26px 0" }}>
        <Link className="button rwr-cta-button" to="/app/activation/self-guided/module/3" data-testid="am2-continue-module3">CONTINUE TO MODULE 3 — BUILD THE FUNDRAISING STRATEGY PLAN</Link>
      </section>

      {showAdd && (
        <Modal onClose={() => setShowAdd(false)} testId="am2-add-modal">
          <h2>{activationM2Text.h_addCurrentBoardMember}</h2>
          <p>The Board Member will complete the planning form through their own secure link. You only need their contact details.</p>
          <label className="field"><span>Full Name <b>*</b></span><input value={addForm.name} onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} data-testid="am2-add-name" /></label>
          <label className="field"><span>Email <b>*</b></span><input type="email" value={addForm.email} onChange={(e) => setAddForm({ ...addForm, email: e.target.value })} data-testid="am2-add-email" /></label>
          <label className="field"><span>Phone Number</span><input value={addForm.phone} onChange={(e) => setAddForm({ ...addForm, phone: e.target.value })} data-testid="am2-add-phone" /></label>
          <label className="field"><span>Current Board Role</span>
            <select value={addForm.role} onChange={(e) => setAddForm({ ...addForm, role: e.target.value })} data-testid="am2-add-role">
              <option value="">Choose one…</option>
              {["Board Member", "Chair", "Vice Chair", "Treasurer", "Secretary", "Advisory Board Member", "Other"].map((role) => <option key={role}>{role}</option>)}
            </select>
          </label>
          {addError && <p className="submit-error" data-testid="am2-add-error">{addError}</p>}
          <button type="button" className="button" onClick={addMember} data-testid="am2-add-submit">Add Board Member</button>
        </Modal>
      )}

      {showEdit && editForm && (
        <Modal onClose={() => setShowEdit(false)} testId="am2-edit-modal">
          <h2>{activationM2Text.h_editBoardFundraisingPlanningForm}</h2>
          <label className="field"><span>Introduction</span><textarea rows={7} value={editForm.introduction} onChange={(e) => setEditForm({ ...editForm, introduction: e.target.value })} data-testid="am2-edit-introduction" /></label>
          <label className="field"><span>Fundraising Goal Context (shown to Board Members)</span><textarea rows={4} value={editForm.goal_context} onChange={(e) => setEditForm({ ...editForm, goal_context: e.target.value })} data-testid="am2-edit-goal-context" /></label>
          <h3 style={{ margin: "14px 0 6px" }}>{activationM2Text.h_questions}</h3>
          {editForm.prompt_list.map((entry) => (
            <label className="field" key={entry.id}><span className="eyebrow">{entry.section}</span>
              <input value={editForm.question_prompts[entry.id]} onChange={(e) => setEditForm({ ...editForm, question_prompts: { ...editForm.question_prompts, [entry.id]: e.target.value } })} data-testid={`am2-edit-question-${entry.id}`} />
            </label>
          ))}
          <button type="button" className="button" onClick={saveEdit} disabled={saving} data-testid="am2-save-button">{saving ? "Saving…" : "SAVE"}</button>
        </Modal>
      )}

      {preview && (
        <Modal onClose={() => setPreview(null)} testId="am2-send-modal">
          <h2>{preview.type === "reminder" ? "Review Reminder Email" : "Review Planning Form Email"}</h2>
          <p><strong>To:</strong> {preview.to_name} &lt;{preview.to_email}&gt;</p>
          <p><strong>Subject:</strong> <span data-testid="am2-email-subject">{preview.subject}</span></p>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 320, overflowY: "auto" }} data-testid="am2-email-body">{preview.body}</div>
          <p style={{ marginTop: 10 }}><strong>Secure Form Link:</strong> <span style={{ wordBreak: "break-all" }} data-testid="am2-email-link">{preview.form_link}</span></p>
          <button type="button" className="button" onClick={sendEmail} disabled={sending} data-testid="am2-send-confirm">{sending ? "Sending…" : "SEND"}</button>
        </Modal>
      )}

      {script && (
        <Modal onClose={() => setScript(null)} testId="am2-script-modal">
          <h2>{activationM2Text.h_reminderCallScript}</h2>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6 }} data-testid="am2-script-body">{script.script}</div>
          <label className="field" style={{ marginTop: 14 }}><span>Call Notes (optional)</span>
            <textarea rows={4} value={notes} onChange={(e) => { setNotes(e.target.value); setNotesSaved(false); }} data-testid="am2-call-notes" />
          </label>
          <button type="button" className="button" onClick={saveNotes} data-testid="am2-save-notes">{notesSaved ? "Notes Saved" : "Save Call Notes"}</button>
        </Modal>
      )}

      {response && (
        <Modal onClose={() => setResponse(null)} testId="am2-response-modal">
          <h2>{response.participant.name} — Fundraising Planning Response</h2>
          <ResponseView data={response} />
        </Modal>
      )}
    </div>
  );
}
