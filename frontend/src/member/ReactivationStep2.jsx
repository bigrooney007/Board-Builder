import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Copy, Mail, Phone, Plus, UserPlus, X } from "lucide-react";
import { memberApi } from "./api";

const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const dialogStyle = { background: "#fff", maxWidth: 720, width: "100%", padding: "28px", borderRadius: 8, position: "relative" };

const Modal = ({ children, onClose, testId }) => (
  <div style={overlayStyle} data-testid={testId}>
    <div style={dialogStyle}>
      <button type="button" onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testId}-close`}><X size={20} /></button>
      {children}
    </div>
  </div>
);

const RESPONSE_SECTIONS = [
  ["Professional Profile", ["full_name", "preferred_name", "email", "phone", "city_state", "linkedin", "current_position", "employer", "industry", "years_experience"]],
  ["Professional Expertise", ["expertise", "expertise_other"]],
  ["Networks", ["networks"]],
  ["Experience on the Board", ["why_joined", "how_recruited", "original_role_expectation", "role_clarity", "clarity_help", "board_experience", "participation_barriers", "board_improvement", "strategic_clarity", "planning_participation", "planning_involvement_desire"]],
  ["Areas of Contribution", ["contribution_interests", "ownership_areas", "leadership_interest"]],
  ["Fundraising Participation", ["fundraising_comfort"]],
  ["Availability", ["monthly_availability", "meeting_participation", "constraints"]],
  ["Support Needed", ["support_needed"]],
  ["Additional Comments", ["meaningful_service", "anything_else"]],
];

const LABELS = {
  full_name: "Full Name", preferred_name: "Preferred Name", email: "Email", phone: "Phone", city_state: "City / State / Region", linkedin: "LinkedIn",
  current_position: "Current Professional Position", employer: "Organization / Employer", industry: "Industry / Professional Field", years_experience: "Years of Professional Experience",
  expertise: "Professional skills, experience or expertise", expertise_other: "Other expertise", networks: "Relationships / professional networks",
  why_joined: "What originally interested them in serving", how_recruited: "How they originally became involved", original_role_expectation: "What they understood their role to be",
  role_clarity: "Role clarity today", clarity_help: "What would give greater clarity", board_experience: "Experience serving on the Board", participation_barriers: "What has made participation difficult",
  board_improvement: "What would help the Board work more effectively", strategic_clarity: "Clarity about organization direction", planning_participation: "Strategic planning participation",
  planning_involvement_desire: "Desired planning involvement", contribution_interests: "Where they would most like to contribute", ownership_areas: "Responsibility they would take ownership of",
  leadership_interest: "Leadership interest", fundraising_comfort: "Fundraising activities they are comfortable with", monthly_availability: "Monthly availability",
  meeting_participation: "Meeting participation", constraints: "Availability / circumstances to understand", support_needed: "Support, information or resources needed",
  meaningful_service: "What would make Board service meaningful", anything_else: "Anything else",
};

export const ResponseView = ({ data, testPrefix = "step2" }) => (
  <div data-testid={`${testPrefix}-response-view`}>
    <div className="member-card" style={{ borderLeft: "4px solid #000", marginBottom: 18 }} data-testid={`${testPrefix}-recommitment-answer`}>
      <p className="eyebrow">Recommitment Response</p>
      <p style={{ fontSize: "1.05rem", fontWeight: 700, margin: 0 }}>{data.response.recommitment}</p>
      {data.response.advisory_openness && <p style={{ margin: "8px 0 0" }}>Open to an Advisory role: <strong>{data.response.advisory_openness}</strong></p>}
      {data.response.support_role_openness && <p style={{ margin: "8px 0 0" }}>Open to another support role: <strong>{data.response.support_role_openness}</strong></p>}
    </div>
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

export default function ReactivationStep2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [roster, setRoster] = useState(null);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ name: "", email: "", phone: "", role: "" });
  const [addError, setAddError] = useState("");
  const [preview, setPreview] = useState(null);
  const [sending, setSending] = useState(false);
  const [script, setScript] = useState(null);
  const [notes, setNotes] = useState("");
  const [notesSaved, setNotesSaved] = useState(false);
  const [response, setResponse] = useState(null);
  const [copied, setCopied] = useState("");

  const load = useCallback(() => {
    memberApi.get("/reactivation/roster").then((res) => setRoster(res.data)).catch(() => setError("We could not load your Board."));
  }, []);
  useEffect(load, [load]);

  const openResponse = useCallback((memberId) => {
    memberApi.get(`/reactivation/board-members/${memberId}/response`).then((res) => setResponse(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const memberId = searchParams.get("member");
    if (memberId && roster) {
      openResponse(memberId);
      setSearchParams({}, { replace: true });
    }
  }, [roster, searchParams, setSearchParams, openResponse]);

  const addMember = async () => {
    setAddError("");
    if (!addForm.name.trim() || !addForm.email.trim()) { setAddError("Full Name and Email Address are required."); return; }
    try {
      await memberApi.post("/reactivation/board-members", addForm);
      setShowAdd(false);
      setAddForm({ name: "", email: "", phone: "", role: "" });
      load();
    } catch (err) {
      setAddError(err.response?.data?.detail?.[0]?.msg || err.response?.data?.detail || "Could not add this Board Member.");
    }
  };

  const importPerson = async (applicationId) => {
    try { await memberApi.post("/reactivation/board-members/import", { application_id: applicationId }); load(); } catch { /* ignore */ }
  };

  const openPreview = (member, type) => {
    memberApi.get(`/reactivation/board-members/${member.member_record_id}/email-preview`, { params: { type } })
      .then((res) => setPreview({ ...res.data, member, type }))
      .catch(() => {});
  };

  const sendEmail = async () => {
    setSending(true);
    try {
      await memberApi.post(`/reactivation/board-members/${preview.member.member_record_id}/send`, { type: preview.type });
      setPreview(null);
      load();
    } catch { /* keep modal open */ }
    setSending(false);
  };

  const openScript = (member) => {
    memberApi.get(`/reactivation/board-members/${member.member_record_id}/call-script`).then((res) => {
      setScript({ ...res.data, member });
      setNotes(res.data.call_notes || "");
      setNotesSaved(false);
    }).catch(() => {});
  };

  const saveNotes = async () => {
    await memberApi.put(`/reactivation/board-members/${script.member.member_record_id}/call-notes`, { notes });
    setNotesSaved(true);
    load();
  };

  const copyLink = async (member) => {
    const res = await memberApi.get(`/reactivation/board-members/${member.member_record_id}/email-preview`, { params: { type: "initial" } });
    try { await navigator.clipboard.writeText(res.data.form_link); } catch { window.prompt("Copy this form link:", res.data.form_link); }
    setCopied(member.member_record_id);
    setTimeout(() => setCopied(""), 2500);
  };

  if (error) return <p className="submit-error">{error}</p>;
  if (!roster) return <p className="sh-loading">Loading your Board…</p>;

  return (
    <div data-testid="reactivation-step2">
      <section className="member-card" data-testid="step2-intro">
        <h2>Find Out Who Is Ready to Stand Up</h2>
        <p>Before you start having difficult conversations, give every current Board Member an opportunity to tell you where they are, what they can realistically contribute, and whether they are willing and able to continue serving actively.</p>
        <p>Their responses will help you understand who is ready to stand up, who needs clearer responsibility, and who may need to step down or transition into another role.</p>
      </section>

      <section className="member-card" data-testid="step2-progress-summary">
        <h2>Board Recommitment Progress</h2>
        <p data-testid="step2-progress-counts">
          <strong>{roster.progress.total}</strong> Current Board Member{roster.progress.total === 1 ? "" : "s"} · <strong>{roster.progress.completed}</strong> Completed · <strong>{roster.progress.waiting}</strong> Waiting for Response
        </p>
      </section>

      {roster.existing_people.length > 0 && (
        <section className="member-card" data-testid="step2-existing-people">
          <h2>Board Members Already in Your Account</h2>
          <p>These people joined your Board through Recruitment. Add anyone who is currently serving so they can complete their Recommitment Form.</p>
          {roster.existing_people.map((person) => (
            <div key={person.application_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #eee" }}>
              <span><strong>{person.name}</strong> · {person.email}</span>
              <button type="button" className="button button-outline" onClick={() => importPerson(person.application_id)} data-testid={`step2-import-${person.application_id}`}><UserPlus size={15} /> Add to Current Board</button>
            </div>
          ))}
        </section>
      )}

      <section className="member-card" data-testid="step2-roster">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2 style={{ margin: 0 }}>Your Current Board</h2>
          <button type="button" className="button" onClick={() => setShowAdd(true)} data-testid="step2-add-member-button"><Plus size={16} /> ADD CURRENT BOARD MEMBER</button>
        </div>
        {!roster.members.length && <p data-testid="step2-empty-roster" style={{ marginTop: 14 }}>No current Board Members yet. Add your current Board Members to begin.</p>}
        {roster.members.map((member) => (
          <article key={member.member_record_id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 16 }} data-testid={`step2-member-card-${member.member_record_id}`}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
              <div>
                <h3 style={{ margin: 0 }}>{member.name}</h3>
                <p style={{ margin: "4px 0 0" }}>{member.role || "Board Member"} · {member.email}</p>
              </div>
              <span className="eyebrow" data-testid={`step2-status-${member.member_record_id}`} style={{ alignSelf: "flex-start", padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }}>{member.status}</span>
            </div>
            <p className="eyebrow" style={{ marginTop: 10 }}>
              {member.last_sent_at && <>Form sent {new Date(member.last_sent_at).toLocaleDateString()} · </>}
              {member.last_reminder_at && <>Last reminder {new Date(member.last_reminder_at).toLocaleDateString()}</>}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
              {member.status === "NOT SENT" && (
                <button type="button" className="button" onClick={() => openPreview(member, "initial")} data-testid={`step2-send-form-${member.member_record_id}`}><Mail size={15} /> SEND RECOMMITMENT FORM</button>
              )}
              {member.status === "SENT" && (
                <>
                  <button type="button" className="button button-outline" onClick={() => copyLink(member)} data-testid={`step2-copy-link-${member.member_record_id}`}><Copy size={15} /> {copied === member.member_record_id ? "Link Copied" : "COPY FORM LINK"}</button>
                  <button type="button" className="button button-outline" onClick={() => openPreview(member, "reminder")} data-testid={`step2-send-reminder-${member.member_record_id}`}><Mail size={15} /> SEND REMINDER EMAIL</button>
                  <button type="button" className="button button-outline" onClick={() => openScript(member)} data-testid={`step2-call-script-${member.member_record_id}`}><Phone size={15} /> VIEW REMINDER CALL SCRIPT</button>
                  <button type="button" className="button button-outline" onClick={() => openPreview(member, "initial")} data-testid={`step2-resend-${member.member_record_id}`}>RESEND FORM</button>
                </>
              )}
              {member.status === "COMPLETED" && (
                <button type="button" className="button" onClick={() => openResponse(member.member_record_id)} data-testid={`step2-view-response-${member.member_record_id}`}>VIEW RESPONSE</button>
              )}
            </div>
          </article>
        ))}
      </section>

      <section style={{ textAlign: "center", margin: "26px 0" }}>
        <Link className="button rwr-cta-button" to="/app/reactivation/self-guided/module/3" data-testid="step2-continue-step3">CONTINUE TO STEP 3 — HAVE THE DIFFICULT CONVERSATIONS</Link>
      </section>

      {showAdd && (
        <Modal onClose={() => setShowAdd(false)} testId="step2-add-modal">
          <h2>Add Current Board Member</h2>
          <p>The Board Member will complete their own profile through their secure form. You only need their contact details.</p>
          <label className="field"><span>Full Name <b>*</b></span><input value={addForm.name} onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} data-testid="step2-add-name" /></label>
          <label className="field"><span>Email Address <b>*</b></span><input type="email" value={addForm.email} onChange={(e) => setAddForm({ ...addForm, email: e.target.value })} data-testid="step2-add-email" /></label>
          <label className="field"><span>Phone Number</span><input value={addForm.phone} onChange={(e) => setAddForm({ ...addForm, phone: e.target.value })} data-testid="step2-add-phone" /></label>
          <label className="field"><span>Current Board Role / Position</span>
            <select value={addForm.role} onChange={(e) => setAddForm({ ...addForm, role: e.target.value })} data-testid="step2-add-role">
              <option value="">Choose one…</option>
              {["Board Member", "Chair", "Treasurer", "Secretary", "Advisory Board Member", "Other"].map((role) => <option key={role}>{role}</option>)}
            </select>
          </label>
          {addError && <p className="submit-error" data-testid="step2-add-error">{addError}</p>}
          <button type="button" className="button" onClick={addMember} data-testid="step2-add-submit">Add Board Member</button>
        </Modal>
      )}

      {preview && (
        <Modal onClose={() => setPreview(null)} testId="step2-send-modal">
          <h2>{preview.type === "reminder" ? "Review Reminder Email" : "Review Recommitment Form Email"}</h2>
          <p><strong>To:</strong> {preview.to_name} &lt;{preview.to_email}&gt;</p>
          <p><strong>Subject:</strong> <span data-testid="step2-email-subject">{preview.subject}</span></p>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 320, overflowY: "auto" }} data-testid="step2-email-body">{preview.body}</div>
          <p style={{ marginTop: 10 }}><strong>Secure Form Link:</strong> <span style={{ wordBreak: "break-all" }} data-testid="step2-email-link">{preview.form_link}</span></p>
          <button type="button" className="button" onClick={sendEmail} disabled={sending} data-testid="step2-send-confirm">{sending ? "Sending…" : "SEND"}</button>
        </Modal>
      )}

      {script && (
        <Modal onClose={() => setScript(null)} testId="step2-script-modal">
          <h2>Reminder Call Script</h2>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6 }} data-testid="step2-script-body">{script.script}</div>
          <label className="field" style={{ marginTop: 14 }}><span>Call Notes (optional)</span>
            <textarea rows={4} value={notes} onChange={(e) => { setNotes(e.target.value); setNotesSaved(false); }} data-testid="step2-call-notes" />
          </label>
          <button type="button" className="button" onClick={saveNotes} data-testid="step2-save-notes">{notesSaved ? "Notes Saved" : "Save Call Notes"}</button>
        </Modal>
      )}

      {response && (
        <Modal onClose={() => setResponse(null)} testId="step2-response-modal">
          <h2>{response.member.name} — Recommitment Response</h2>
          <ResponseView data={response} />
        </Modal>
      )}
    </div>
  );
}
