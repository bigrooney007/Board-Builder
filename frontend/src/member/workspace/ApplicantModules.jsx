import React, { useCallback, useEffect, useState } from "react";
import { Download, FileText, RefreshCw, Sparkles, UserCheck } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard, currentVersion, printText } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";

export const useApplications = () => {
  const [applications, setApplications] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const refresh = useCallback(async () => {
    try {
      const response = await memberApi.get("/workspace/applications");
      setApplications(response.data.applications);
      setStatuses(response.data.statuses);
    } catch { /* ignore */ }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { applications, statuses, refresh };
};

const downloadCv = async (application) => {
  try {
    const response = await memberApi.get(`/workspace/applications/${application.application_id}/cv`, { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url; link.download = application.cv_filename || "cv"; link.click();
    URL.revokeObjectURL(url);
  } catch { window.alert("CV could not be downloaded."); }
};

const GuidePanel = ({ application, refresh }) => {
  const guide = application.interview_guide || {};
  const { byType, refresh: refreshMaterials } = useMaterials(application.application_id);
  const [busy, setBusy] = useState(false);
  const generateGuide = async () => {
    setBusy(true);
    try { await memberApi.post(`/workspace/applications/${application.application_id}/interview-guide/retry`); await refresh(); await refreshMaterials(); } catch { /* ignore */ }
    setBusy(false);
  };
  const material = byType.interview_guide;
  const version = currentVersion(material);
  return (
    <div className="detail-section" data-testid="interview-guide-panel">
      <h3>Interview Guide — <span data-testid="guide-status">{guide.status || "Pending"}</span></h3>
      <p className="material-description">An applicant-specific interview guide built from this person's application and CV, your Powerhouse Board Blueprint, your organization information and your Recruitment Strategy. You and your organization make every selection decision.</p>
      {guide.status === "Failed" && (
        <div className="submit-error">Interview Guide Generation Failed{guide.error ? ` — ${guide.error}` : ""}</div>
      )}
      {guide.status === "Generating" && <p className="workspace-note">Generating… <button className="link-button" onClick={refresh}>Refresh status</button></p>}
      {!version && guide.status !== "Generating" && (
        <button className="button" disabled={busy} onClick={generateGuide} data-testid="generate-interview-guide-button"><Sparkles size={15} /> {busy ? "Generating…" : "Generate Interview Guide"}</button>
      )}
      {version && (
        <>
          <pre className="material-display" data-testid="interview-guide-display">{version.display_text}</pre>
          <div className="material-actions">
            <button className="button button-back" onClick={() => printText("Interview Guide", version.display_text)}><Download size={14} /> Download PDF</button>
            <button className="button button-back" disabled={busy} onClick={generateGuide}><RefreshCw size={14} /> Regenerate Guide</button>
          </div>
        </>
      )}
    </div>
  );
};

const InterviewComms = ({ application }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const [invite, setInvite] = useState({ date: "", time: "", format: "Zoom", link: "" });
  return (
    <div className="detail-section">
      <h3>Interview Invitation</h3>
      <div className="two-col-fields">
        <label className="field"><span>Interview date (optional)</span><input value={invite.date} onChange={(event) => setInvite({ ...invite, date: event.target.value })} /></label>
        <label className="field"><span>Interview time (optional)</span><input value={invite.time} onChange={(event) => setInvite({ ...invite, time: event.target.value })} /></label>
        <label className="field"><span>Interview format</span><select value={invite.format} onChange={(event) => setInvite({ ...invite, format: event.target.value })}>{["Zoom", "Phone", "In person", "Other"].map((option) => <option key={option}>{option}</option>)}</select></label>
        <label className="field"><span>Meeting link/location (optional)</span><input value={invite.link} onChange={(event) => setInvite({ ...invite, link: event.target.value })} /></label>
      </div>
      <MaterialCard type="interview_invitation" title={`Interview Invitation for ${application.profile_snapshot?.full_name || "this applicant"}`} buttonLabel={`Generate Interview Invitation for ${application.profile_snapshot?.full_name || "this applicant"}`}
        description="A personalized invitation to a board interview conversation. Nothing is sent automatically — you review it and send it yourself."
        applicationId={application.application_id} material={byType.interview_invitation} refresh={refresh}
        instructions={`Interview details — date: ${invite.date || "to be scheduled"}; time: ${invite.time || "to be scheduled"}; format: ${invite.format}; meeting link/location: ${invite.link || "to be provided"}. Nothing is sent automatically.`} />
    </div>
  );
};

export const ApplicantDetail = ({ applicationId, statuses, onChanged }) => {
  const [detail, setDetail] = useState(null);
  const [notes, setNotes] = useState("");
  const [showApplication, setShowApplication] = useState(false);
  const refresh = useCallback(async () => {
    const response = await memberApi.get(`/workspace/applications/${applicationId}`);
    setDetail(response.data);
    setNotes(response.data.application.notes || "");
  }, [applicationId]);
  useEffect(() => { refresh(); }, [refresh]);
  if (!detail) return <p>Loading applicant…</p>;
  const application = detail.application;
  const snapshot = application.profile_snapshot || {};
  const hasAnswers = Object.keys(application.answers || {}).length > 0;
  const setStatus = async (status) => { await memberApi.patch(`/workspace/applications/${applicationId}`, { status }); await refresh(); if (onChanged) onChanged(); };
  const saveNotes = async () => { await memberApi.patch(`/workspace/applications/${applicationId}`, { notes }); };
  return (
    <div className="applicant-detail" data-testid="applicant-detail">
      <div className="detail-section">
        <h3>Applicant Profile</h3>
        <dl>{Object.entries(snapshot).filter(([, value]) => value).map(([key, value]) => <div key={key}><dt>{key.replace(/_/g, " ")}</dt><dd>{value}</dd></div>)}</dl>
        <div className="material-actions">
          <label className="field status-field"><span>Application status</span>
            <select value={application.status} onChange={(event) => setStatus(event.target.value)} data-testid="applicant-status-select">
              {statuses.map((status) => <option key={status}>{status}</option>)}
            </select>
          </label>
          {hasAnswers && <button className="button button-back" onClick={() => setShowApplication(!showApplication)} data-testid="view-application-button"><FileText size={14} /> {showApplication ? "Hide Application" : "View Application"}</button>}
          {application.cv_file_id && <button className="button button-back" onClick={() => downloadCv(application)} data-testid="download-cv-button"><FileText size={14} /> View CV ({application.cv_filename})</button>}
        </div>
      </div>
      {showApplication && hasAnswers && (
        <div className="detail-section" data-testid="application-answers">
          <h3>Application Answers</h3>
          <dl>{Object.entries(application.answers || {}).map(([key, value]) => key === "custom" ? null : <div key={key}><dt>{key.replace(/_/g, " ")}</dt><dd>{String(value) || "—"}</dd></div>)}</dl>
          {application.answers?.custom && Object.keys(application.answers.custom).length > 0 && <dl>{Object.entries(application.answers.custom).map(([key, value]) => <div key={key}><dt>Custom question</dt><dd>{String(value) || "—"}</dd></div>)}</dl>}
        </div>
      )}
      <GuidePanel application={application} refresh={refresh} />
      <InterviewComms application={application} />
      <div className="detail-section">
        <h3>Private Notes (never shown to the applicant)</h3>
        <textarea rows="4" value={notes} onChange={(event) => setNotes(event.target.value)} data-testid="applicant-notes" />
        <button className="button button-back" onClick={saveNotes} data-testid="save-notes-button">Save Notes</button>
      </div>
    </div>
  );
};

const GeneralModule4Tools = () => {
  const { byType, refresh } = useMaterials();
  return (
    <section className="workspace-panel" data-testid="module4-general-tools">
      <h2>Interview Communications</h2>
      <MaterialCard type="general_interview_invitation" title="General Interview Invitation" buttonLabel="Generate General Interview Invitation"
        description="Use this when inviting an applicant to a board interview conversation and you do not need applicant-specific personalization."
        material={byType.general_interview_invitation} refresh={refresh} />
      <MaterialCard type="general_rejection_email" title="Pre-Interview Rejection Email" buttonLabel="Generate Pre-Interview Rejection Email"
        description="Use this for an applicant your organization has decided not to interview."
        material={byType.general_rejection_email} refresh={refresh} />
    </section>
  );
};

const ExternalApplicantForm = ({ refresh }) => {
  const [name, setName] = useState("");
  const [cvFile, setCvFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const submit = async () => {
    setMessage("");
    if (!name.trim()) { setMessage("Applicant name is required."); return; }
    setBusy(true);
    try {
      const payload = new FormData();
      payload.append("name", name);
      if (cvFile) payload.append("cv", cvFile);
      await memberApi.post("/workspace/applications/external", payload, { headers: { "Content-Type": "multipart/form-data" } });
      setName(""); setCvFile(null);
      setMessage("Applicant added to your Applicant Workspace. You can generate their Interview Guide below.");
      refresh();
    } catch (err) { setMessage(err.response?.data?.detail || "Could not add the applicant."); }
    setBusy(false);
  };
  return (
    <section className="workspace-panel" data-testid="external-applicant-form">
      <h2>Add an Applicant From Outside the Board Application</h2>
      <p className="material-description">Use this for someone who applied through LinkedIn or another recruitment platform rather than through your Board Application link. We only need their name and CV so the system can prepare their interview guide.</p>
      <div className="two-col-fields">
        <label className="field"><span>Applicant Name <b>*</b></span><input value={name} onChange={(event) => setName(event.target.value)} data-testid="external-applicant-name" /></label>
        <label className="field"><span>Upload CV / Résumé</span><input type="file" accept=".pdf,.doc,.docx,.txt" onChange={(event) => setCvFile(event.target.files?.[0] || null)} data-testid="external-applicant-cv" /></label>
      </div>
      <button className="button" disabled={busy} onClick={submit} data-testid="add-external-applicant-button">{busy ? "Adding…" : "Add Applicant"}</button>
      {message && <p className="member-success" data-testid="external-applicant-message">{message}</p>}
    </section>
  );
};

export const Module4Applicants = () => {
  const { applications, statuses, refresh } = useApplications();
  const [openId, setOpenId] = useState("");
  return (
    <div data-testid="module4-workspace">
      <section className="workspace-panel">
        <h2>Your Board Applicants</h2>
        <p className="material-description">Everyone who applies through your Board Application appears here automatically. For each applicant you can view their application, view their CV, generate their Interview Guide and generate their interview invitation.</p>
        {applications.length === 0 && <p className="workspace-note" data-testid="no-applicants">No applications yet. When your recruitment campaign is published, applications will appear here.</p>}
        {applications.map((application) => (
          <div className={`applicant-row ${openId === application.application_id ? "open" : ""}`} key={application.application_id} data-testid={`applicant-row-${application.application_id}`}>
            <button className="applicant-row-head" onClick={() => setOpenId(openId === application.application_id ? "" : application.application_id)}>
              <strong>{application.profile_snapshot?.full_name || application.applicant_email}</strong>
              <span>{application.profile_snapshot?.profession || "—"}</span>
              <span>{new Date(application.created_at).toLocaleDateString()}</span>
              <span className="source-tag">{application.source}</span>
              <span>CV: {application.cv_filename ? "Yes" : "No"}</span>
              <span>Guide: {application.interview_guide?.status || "Pending"}</span>
              <span className={`status-pill status-${application.status.replace(/\s/g, "-").toLowerCase()}`}>{application.status}</span>
            </button>
            {openId === application.application_id && <ApplicantDetail applicationId={application.application_id} statuses={statuses} onChanged={refresh} />}
          </div>
        ))}
      </section>
      <ExternalApplicantForm refresh={refresh} />
      <GeneralModule4Tools />
    </div>
  );
};

// ---------- Module 5 ----------

const ReferenceCheckTools = ({ application, outcomes }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const [reference, setReference] = useState({ reference_name: "", relationship: "", email: "", phone: "", date_contacted: "", notes: "", outcome: "Not completed" });
  const [references, setReferences] = useState(application.references || []);
  const [check, setCheck] = useState(application.background_check || { status: "Not started" });
  const [message, setMessage] = useState("");
  const addReference = async () => {
    if (!reference.reference_name.trim()) { setMessage("Reference name is required."); return; }
    const response = await memberApi.post(`/workspace/applications/${application.application_id}/references`, reference);
    setReferences([...references, response.data]);
    setReference({ reference_name: "", relationship: "", email: "", phone: "", date_contacted: "", notes: "", outcome: "Not completed" });
    setMessage("Reference recorded.");
  };
  const saveCheck = async () => { await memberApi.patch(`/workspace/applications/${application.application_id}`, { background_check: check }); setMessage("Background check record saved."); };
  return (
    <div className="detail-section" data-testid="reference-check-tools">
      <h3>Generate Reference Check — {application.profile_snapshot?.full_name}</h3>
      <p className="material-description">Create the materials to contact and evaluate this applicant's references. You and your organization make every decision — the reference outcome is never decided by AI.</p>
      {[["reference_request_email", "Reference Request Email", "The email you send to each reference asking for a conversation."],
        ["reference_call_script", "Reference Call Guide", "The questions to ask during each reference conversation."],
        ["reference_evaluation_form", "Reference Evaluation Form", "A structured form to record what you learned from each reference."]].map(([type, title, description]) => (
        <MaterialCard key={type} type={type} title={title} buttonLabel={`Generate ${title}`} description={description}
          applicationId={application.application_id} material={byType[type]} refresh={refresh} />
      ))}
      <h3>Reference Records</h3>
      {references.map((record) => <p className="reference-record" key={record.reference_id}><strong>{record.reference_name}</strong> ({record.relationship || "—"}) — {record.outcome}{record.notes ? ` — ${record.notes}` : ""}</p>)}
      <div className="two-col-fields">
        <label className="field"><span>Reference name</span><input value={reference.reference_name} onChange={(event) => setReference({ ...reference, reference_name: event.target.value })} data-testid="reference-name" /></label>
        <label className="field"><span>Relationship to applicant</span><input value={reference.relationship} onChange={(event) => setReference({ ...reference, relationship: event.target.value })} /></label>
        <label className="field"><span>Email</span><input value={reference.email} onChange={(event) => setReference({ ...reference, email: event.target.value })} /></label>
        <label className="field"><span>Phone</span><input value={reference.phone} onChange={(event) => setReference({ ...reference, phone: event.target.value })} /></label>
        <label className="field"><span>Date contacted</span><input value={reference.date_contacted} onChange={(event) => setReference({ ...reference, date_contacted: event.target.value })} /></label>
        <label className="field"><span>Outcome</span><select value={reference.outcome} onChange={(event) => setReference({ ...reference, outcome: event.target.value })} data-testid="reference-outcome">{outcomes.map((option) => <option key={option}>{option}</option>)}</select></label>
      </div>
      <label className="field"><span>Notes</span><textarea rows="2" value={reference.notes} onChange={(event) => setReference({ ...reference, notes: event.target.value })} /></label>
      <button className="button button-back" onClick={addReference} data-testid="add-reference-button">Record Reference</button>
      <h3>Background Check Record</h3>
      <p className="workspace-note">Nonprofit Board Builder does not perform background checks and does not endorse, rank or select any provider. No applicant information is shared. The nonprofit remains responsible for its selection decision.</p>
      <div className="two-col-fields">
        <label className="field"><span>Background check required?</span><select value={check.required || ""} onChange={(event) => setCheck({ ...check, required: event.target.value })}><option value="">Select</option><option>Yes</option><option>No</option></select></label>
        <label className="field"><span>Status</span><select value={check.status || "Not started"} onChange={(event) => setCheck({ ...check, status: event.target.value })} data-testid="background-status">{["Not required", "Not started", "In progress", "Completed", "Follow-up required"].map((option) => <option key={option}>{option}</option>)}</select></label>
        <label className="field"><span>Requested date</span><input value={check.requested_date || ""} onChange={(event) => setCheck({ ...check, requested_date: event.target.value })} /></label>
        <label className="field"><span>Completed date</span><input value={check.completed_date || ""} onChange={(event) => setCheck({ ...check, completed_date: event.target.value })} /></label>
      </div>
      <label className="field"><span>Notes</span><textarea rows="2" value={check.notes || ""} onChange={(event) => setCheck({ ...check, notes: event.target.value })} /></label>
      <button className="button button-back" onClick={saveCheck} data-testid="save-background-button">Save Background Check Record</button>
      {message && <p className="member-success">{message}</p>}
    </div>
  );
};

const DecisionTools = ({ application }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  return (
    <div className="detail-section" data-testid="decision-tools">
      <h3>Decide Who Moves Forward — {application.profile_snapshot?.full_name}</h3>
      <MaterialCard type="conditional_offer" title="Conditional Board Appointment Email" buttonLabel="Generate Conditional Board Appointment Email"
        description="For an applicant you want to move forward with. Tells them your organization would like them to join the board — conditional on completion of the relevant reference/background checks and final organizational requirements — and explains what happens next, including any forms or agreements to complete. This is the beginning of their onboarding transition."
        applicationId={application.application_id} material={byType.conditional_offer} refresh={refresh} />
      <MaterialCard type="after_interview_rejection" title="After-Interview Rejection Email" buttonLabel="Generate After-Interview Rejection Email"
        description="A respectful, concise, professional email for an applicant you interviewed but have decided not to continue with."
        applicationId={application.application_id} material={byType.after_interview_rejection} refresh={refresh} />
    </div>
  );
};

const PREPARE_TOOLS = [
  ["organization_overview", "Organization Overview", "Generate My Organization Overview", true, "A clear introduction to your organization, mission, programs, priorities and leadership for your new board members. Built only from your stored organization information — missing information is marked 'Information to Add', never invented."],
  ["board_manual", "Board Manual", "Generate My Board Manual", true, "One central document explaining the organization, board expectations, responsibilities and key information new board members need to serve effectively."],
  ["board_member_agreement", "Board Member Agreement", "Generate My Board Member Agreement", false, "Sets out the responsibilities, expectations and commitments each new board member is agreeing to accept. Sent through the secure signature workflow in Module 6 — never a public link."],
  ["confidentiality_agreement", "Confidentiality Agreement", "Generate My Confidentiality Agreement", false, "Clear expectations for protecting confidential organizational, board, donor and other sensitive information. Sent through the secure signature workflow in Module 6."],
  ["conflict_of_interest_agreement", "Conflict of Interest Agreement", "Generate My Conflict of Interest Agreement", false, "Helps board members formally disclose and appropriately manage conflicts that may affect their board responsibilities. Sent through the secure signature workflow in Module 6."],
];

export const BoardProfilePanel = () => {
  const [form, setForm] = useState(null);
  const [message, setMessage] = useState("");
  const load = async () => {
    try { const response = await memberApi.get("/workspace/board-profile-form"); setForm(response.data); }
    catch { setMessage("Could not load the profile form."); }
  };
  const copy = async () => {
    await navigator.clipboard?.writeText(`${window.location.origin}/board-profile/${form.share_token}`);
    setMessage("Secure form link copied. Share it with your new board member.");
  };
  return (
    <div className="detail-section" data-testid="board-profile-panel">
      <h3>Board Member Profile Form</h3>
      <p className="material-description">A standard hosted form each selected board member completes so your organization has an accurate profile of the skills, relationships and experience each person brings. Shared through a secure link; submissions are associated with your organization and that board member.</p>
      {!form ? (
        <button className="button" onClick={load} data-testid="generate-board-profile-form">Generate My Board Member Profile Form</button>
      ) : (
        <>
          <div className="material-actions">
            <code className="app-link-code" data-testid="board-profile-link">{`${window.location.origin}/board-profile/${form.share_token}`}</code>
            <button className="button button-back" onClick={copy} data-testid="copy-board-profile-link">Copy Share Link</button>
          </div>
          <h3>Submitted Profiles ({form.responses.length})</h3>
          {form.responses.length === 0 && <p className="workspace-note">No board member profiles submitted yet.</p>}
          {form.responses.map((response) => (
            <div className="detail-section" key={response.response_id}>
              <dl>{Object.entries(response.data).filter(([, value]) => value).map(([key, value]) => <div key={key}><dt>{key.replace(/_/g, " ")}</dt><dd>{value}</dd></div>)}</dl>
              <p className="material-meta">Submitted {new Date(response.submitted_at).toLocaleString()}</p>
            </div>
          ))}
        </>
      )}
      {message && <p className="member-success">{message}</p>}
    </div>
  );
};

export const Module5References = () => {
  const { applications } = useApplications();
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  const [location, setLocation] = useState("");
  const [outcomes, setOutcomes] = useState(["Positive", "Mixed", "Concern", "Unable to verify", "Not completed"]);
  useEffect(() => {
    memberApi.get("/workspace/profile").then((response) => {
      const data = { ...(response.data.prefill || {}), ...(response.data.profile || {}) };
      setLocation([data.city, data.state_region, data.country].filter(Boolean).join(", "));
    }).catch(() => {});
  }, []);
  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    memberApi.get(`/workspace/applications/${selectedId}`).then((response) => { setDetail(response.data.application); setOutcomes(response.data.reference_outcomes); });
  }, [selectedId]);
  return (
    <div data-testid="module5-workspace">
      <section className="workspace-panel" data-testid="module5-verify-section">
        <h2>Verify the Applicants You Want to Move Forward With</h2>
        <p className="material-description">Reference checks are available for every applicant — whether they applied through your Board Application or were added from LinkedIn or another platform.</p>
        <div className="material-actions">
          <button className="button button-back" onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(`background check providers near ${location || "me"}`)}`, "_blank", "noopener")} data-testid="background-check-search-button">Find Background Check Providers Near Me</button>
        </div>
        <p className="workspace-note">If a background check is appropriate for this board appointment, use this search to find providers you can independently review and contact.</p>
        <label className="field"><span>Choose an applicant</span>
          <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} data-testid="module5-applicant-select">
            <option value="">Select an applicant</option>
            {applications.map((application) => <option key={application.application_id} value={application.application_id}>{application.profile_snapshot?.full_name || application.applicant_email} — {application.status} ({application.source})</option>)}
          </select>
        </label>
        {detail && <ReferenceCheckTools application={detail} outcomes={outcomes} key={`ref-${detail.application_id}`} />}
      </section>

      <section className="workspace-panel" data-testid="module5-decide-section">
        <h2>Decide Who Moves Forward</h2>
        <p className="material-description">After references and any background checks, communicate your decision. Your organization decides — never the AI.</p>
        {!detail && <p className="workspace-note">Choose an applicant above to generate their decision communications.</p>}
        {detail && <DecisionTools application={detail} key={`dec-${detail.application_id}`} />}
      </section>

      <section className="workspace-panel" data-testid="module5-prepare-section">
        <h2>Prepare for Their Onboarding</h2>
        <p className="material-description">Generate everything your organization needs to onboard the people you select. These materials are prepared once here and used in Module 6 — you will not need to regenerate them.</p>
        {PREPARE_TOOLS.map(([type, title, buttonLabel, shareable, description]) => (
          <MaterialCard key={type} type={type} title={title} buttonLabel={buttonLabel} description={description} shareable={shareable}
            material={orgMaterials[type]} refresh={refreshOrg} />
        ))}
        <BoardProfilePanel />
      </section>
    </div>
  );
};

// ---------- Module 6 ----------

const SignatureControls = ({ application, agreementType, signatures, refreshSignatures, prepared }) => {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const record = signatures.find((item) => item.agreement_type === agreementType && item.application_id === application.application_id);
  const prepare = async () => {
    setBusy(true); setError("");
    try { await memberApi.post("/workspace/signatures/prepare", { agreement_type: agreementType, application_id: application.application_id }); await refreshSignatures(); }
    catch (err) { setError(err.response?.data?.detail || "Could not prepare for signature."); }
    setBusy(false);
  };
  const send = async () => {
    setBusy(true); setError("");
    try { await memberApi.post(`/workspace/signatures/${record.request_id}/send`); await refreshSignatures(); }
    catch (err) { setError(err.response?.data?.detail || "Could not send for signature."); }
    setBusy(false);
  };
  const downloadSigned = async () => {
    const response = await memberApi.get(`/workspace/signatures/${record.request_id}/download`, { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url; link.download = `${agreementType}-signed.txt`; link.click();
    URL.revokeObjectURL(url);
  };
  const title = { board_member_agreement: "Board Member Agreement", confidentiality_agreement: "Confidentiality Agreement", conflict_of_interest_agreement: "Conflict of Interest Agreement" }[agreementType];
  return (
    <div className="signature-controls" data-testid={`signature-${agreementType}`}>
      <span className="signature-status">{title} — status: <strong data-testid={`signature-status-${agreementType}`}>{record ? record.status : prepared ? "Ready to Prepare" : "Generate in Module 5"}</strong></span>
      <div className="material-actions">
        {!record && prepared && <button className="button button-back" disabled={busy} onClick={prepare} data-testid={`prepare-signature-${agreementType}`}>Prepare for Signature</button>}
        {record && record.status === "Ready for Signature" && <button className="button" disabled={busy} onClick={send} data-testid={`send-signature-${agreementType}`}>Send for Signature</button>}
        {record && record.status === "Sent" && <><span className="workspace-note">Sent to {record.board_member_email}</span><button className="button button-back" disabled={busy} onClick={send}>Resend</button></>}
        {record && record.status === "Signed" && <>
          <button className="button button-back" onClick={downloadSigned} data-testid={`download-signed-${agreementType}`}><Download size={14} /> Download Signed Copy</button>
          <span className="member-success">Signed by {record.signed?.typed_signature} on {record.signed?.date}</span>
        </>}
      </div>
      {error && <p className="submit-error">{error}</p>}
    </div>
  );
};

const SelectedBoardMember = ({ application, orgMaterials }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const [signatures, setSignatures] = useState([]);
  const refreshSignatures = useCallback(async () => {
    const response = await memberApi.get("/workspace/signatures", { params: { application_id: application.application_id } });
    setSignatures(response.data.signatures);
  }, [application.application_id]);
  useEffect(() => { refreshSignatures(); }, [refreshSignatures]);
  return (
    <div className="onboarding-applicant" data-testid={`onboarding-${application.application_id}`}>
      <h3><UserCheck size={17} /> {application.profile_snapshot?.full_name}{application.profile_snapshot?.email ? ` — ${application.profile_snapshot.email}` : ""}</h3>
      {["board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"].map((agreementType) => (
        <SignatureControls key={agreementType} application={application} agreementType={agreementType} signatures={signatures} refreshSignatures={refreshSignatures} prepared={!!orgMaterials[agreementType]} />
      ))}
      <MaterialCard type="onboarding_agenda" title="Onboarding Agenda" buttonLabel="Generate Onboarding Agenda"
        description="A structured agenda for this board member's onboarding session."
        applicationId={application.application_id} material={byType.onboarding_agenda} refresh={refresh} />
      <MaterialCard type="ninety_day_plan" title="New Board Member 90-Day Plan" buttonLabel="Generate 90-Day Plan"
        description="A practical plan for this board member's first ninety days."
        applicationId={application.application_id} material={byType.ninety_day_plan} refresh={refresh} />
    </div>
  );
};

const PreparedResource = ({ type, title, material }) => {
  const [open, setOpen] = useState(false);
  const version = currentVersion(material);
  return (
    <div className="prepared-resource" data-testid={`prepared-${type}`}>
      <div className="material-actions">
        <span className="signature-status"><strong>{title}</strong> — {version ? "Prepared in Module 5" : "Not yet generated — prepare it in Module 5"}</span>
        {version && <button className="button button-back" onClick={() => setOpen(!open)} data-testid={`view-prepared-${type}`}>{open ? "Hide" : "View"}</button>}
        {version && <button className="button button-back" onClick={() => printText(title, version.display_text)}><Download size={14} /> Download PDF</button>}
      </div>
      {open && version && <pre className="material-display">{version.display_text}</pre>}
    </div>
  );
};

const FirstMeetingPanel = ({ orgMaterials, refreshOrg }) => {
  const [meeting, setMeeting] = useState({ date: "", time: "", timezone: "", location: "", prepare: "" });
  return (
    <section className="workspace-panel" data-testid="first-meeting-panel">
      <h2>Invite Your New Board to Its First Board Meeting</h2>
      <p className="material-description">Use this to invite your newly assembled board to its first board meeting and begin serving together. We only need the meeting details — your organization information is already stored.</p>
      <div className="two-col-fields">
        <label className="field"><span>Meeting date</span><input value={meeting.date} onChange={(event) => setMeeting({ ...meeting, date: event.target.value })} data-testid="meeting-date" /></label>
        <label className="field"><span>Meeting time</span><input value={meeting.time} onChange={(event) => setMeeting({ ...meeting, time: event.target.value })} data-testid="meeting-time" /></label>
        <label className="field"><span>Timezone</span><input value={meeting.timezone} onChange={(event) => setMeeting({ ...meeting, timezone: event.target.value })} data-testid="meeting-timezone" /></label>
        <label className="field"><span>Location or virtual meeting link</span><input value={meeting.location} onChange={(event) => setMeeting({ ...meeting, location: event.target.value })} data-testid="meeting-location" /></label>
      </div>
      <label className="field"><span>Anything they should prepare before the meeting (optional)</span><textarea rows="2" value={meeting.prepare} onChange={(event) => setMeeting({ ...meeting, prepare: event.target.value })} data-testid="meeting-prepare" /></label>
      <MaterialCard type="first_board_meeting_invitation" title="First Board Meeting Invitation Email" buttonLabel="Generate First Board Meeting Invitation Email"
        description="One professional, editable email you can send to your new board members. Nothing is sent automatically."
        material={orgMaterials.first_board_meeting_invitation} refresh={refreshOrg}
        instructions={`First board meeting details supplied by the founder — date: ${meeting.date || "not supplied"}; time: ${meeting.time || "not supplied"}; timezone: ${meeting.timezone || "not supplied"}; location or virtual meeting link: ${meeting.location || "not supplied"}; preparation requested: ${meeting.prepare || "none"}. Use these exactly; write '[To be confirmed]' for anything not supplied.`} />
    </section>
  );
};

export const Module6Onboarding = () => {
  const { applications } = useApplications();
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  const selected = applications.filter((application) => application.status === "Selected");
  return (
    <div data-testid="module6-workspace">
      <section className="workspace-panel" data-testid="module6-members-section">
        <h2>Your New Board Members</h2>
        <p className="material-description">The applicants you selected in Module 5 appear here. Use the materials you already prepared — nothing needs to be regenerated.</p>
        {selected.length === 0 && <p className="workspace-note" data-testid="no-selected">Applicants whose status is Selected appear here. Set an applicant's status to Selected once you have decided to bring them onto the board.</p>}
        {selected.map((application) => <SelectedBoardMember application={application} orgMaterials={orgMaterials} key={application.application_id} />)}
      </section>

      <section className="workspace-panel" data-testid="module6-resources-section">
        <h2>Onboarding Resources Prepared in Module 5</h2>
        {[["organization_overview", "Organization Overview"], ["board_manual", "Board Manual"], ["board_member_agreement", "Board Member Agreement"], ["confidentiality_agreement", "Confidentiality Agreement"], ["conflict_of_interest_agreement", "Conflict of Interest Agreement"]].map(([type, title]) => (
          <PreparedResource key={type} type={type} title={title} material={orgMaterials[type]} />
        ))}
        <BoardProfilePanel />
      </section>

      <section className="workspace-panel" data-testid="module6-script-section">
        <h2>Board Member Onboarding Script</h2>
        <MaterialCard type="onboarding_script" title="Board Member Onboarding Script" buttonLabel="Generate My Board Member Onboarding Script"
          description="The script you can use to guide the onboarding conversation or meeting where you formally bring your new board members into the organization."
          material={orgMaterials.onboarding_script} refresh={refreshOrg} />
      </section>

      <FirstMeetingPanel orgMaterials={orgMaterials} refreshOrg={refreshOrg} />
    </div>
  );
};
