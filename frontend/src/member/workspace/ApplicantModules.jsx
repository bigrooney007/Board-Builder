import React, { useCallback, useEffect, useState } from "react";
import { Download, FileText, RefreshCw, UserCheck } from "lucide-react";
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
  const retry = async () => {
    setBusy(true);
    try { await memberApi.post(`/workspace/applications/${application.application_id}/interview-guide/retry`); await refresh(); await refreshMaterials(); } catch { /* ignore */ }
    setBusy(false);
  };
  const material = byType.interview_guide;
  const version = currentVersion(material);
  return (
    <div className="detail-section" data-testid="interview-guide-panel">
      <h3>AI Interview Guide — <span data-testid="guide-status">{guide.status || "Pending"}</span></h3>
      {guide.status === "Failed" && (
        <div className="submit-error">Interview Guide Generation Failed{guide.error ? ` — ${guide.error}` : ""} <button className="link-button" disabled={busy} onClick={retry}>Try Again</button></div>
      )}
      {guide.status === "Generating" && <p className="workspace-note">Generating… <button className="link-button" onClick={refresh}>Refresh status</button></p>}
      {version && (
        <>
          <pre className="material-display" data-testid="interview-guide-display">{version.display_text}</pre>
          <div className="material-actions">
            <button className="button button-back" onClick={() => printText("Interview Guide", version.display_text)}><Download size={14} /> Download PDF</button>
            <button className="button button-back" disabled={busy} onClick={retry}><RefreshCw size={14} /> Regenerate Guide</button>
          </div>
        </>
      )}
    </div>
  );
};

const InterviewComms = ({ application }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const [invite, setInvite] = useState({ date: "", time: "", format: "Zoom", link: "" });
  const [outcome, setOutcome] = useState("Move to next stage");
  return (
    <div className="detail-section">
      <h3>Interview Communications</h3>
      <div className="two-col-fields">
        <label className="field"><span>Interview date (optional)</span><input value={invite.date} onChange={(event) => setInvite({ ...invite, date: event.target.value })} /></label>
        <label className="field"><span>Interview time (optional)</span><input value={invite.time} onChange={(event) => setInvite({ ...invite, time: event.target.value })} /></label>
        <label className="field"><span>Interview format</span><select value={invite.format} onChange={(event) => setInvite({ ...invite, format: event.target.value })}>{["Zoom", "Phone", "In person", "Other"].map((option) => <option key={option}>{option}</option>)}</select></label>
        <label className="field"><span>Meeting link/location (optional)</span><input value={invite.link} onChange={(event) => setInvite({ ...invite, link: event.target.value })} /></label>
      </div>
      <MaterialCard type="interview_invitation" title="Interview Invitation" buttonLabel="Generate Interview Invitation"
        applicationId={application.application_id} material={byType.interview_invitation} refresh={refresh}
        instructions={`Interview details — date: ${invite.date || "to be scheduled"}; time: ${invite.time || "to be scheduled"}; format: ${invite.format}; meeting link/location: ${invite.link || "to be provided"}. Nothing is sent automatically.`} />
      <label className="field"><span>After-interview result</span>
        <select value={outcome} onChange={(event) => setOutcome(event.target.value)} data-testid="after-interview-outcome">
          {["Move to next stage", "Need additional information", "Selected", "Not selected"].map((option) => <option key={option}>{option}</option>)}
        </select>
      </label>
      <MaterialCard type="after_interview_email" title="After-Interview Email" buttonLabel="Generate After-Interview Email"
        applicationId={application.application_id} material={byType.after_interview_email} refresh={refresh}
        instructions={`The founder chose this interview result: "${outcome}". Write a respectful email matching this result. It is reviewed by the customer and never sent automatically.`} />
      <MaterialCard type="conditional_offer" title="Conditional Board Position Offer" buttonLabel="Generate Conditional Board Position Offer"
        description="Use this when you want to move an applicant forward subject to successful completion of the relevant reference or background checks."
        applicationId={application.application_id} material={byType.conditional_offer} refresh={refresh} />
      <MaterialCard type="after_interview_rejection" title="After-Interview Rejection Email" buttonLabel="Generate After-Interview Rejection Email"
        description="Use this when you have interviewed someone but have decided not to move forward with their application."
        applicationId={application.application_id} material={byType.after_interview_rejection} refresh={refresh} />
    </div>
  );
};

export const ApplicantDetail = ({ applicationId, statuses, onChanged }) => {
  const [detail, setDetail] = useState(null);
  const [notes, setNotes] = useState("");
  const refresh = useCallback(async () => {
    const response = await memberApi.get(`/workspace/applications/${applicationId}`);
    setDetail(response.data);
    setNotes(response.data.application.notes || "");
  }, [applicationId]);
  useEffect(() => { refresh(); }, [refresh]);
  if (!detail) return <p>Loading applicant…</p>;
  const application = detail.application;
  const snapshot = application.profile_snapshot || {};
  const setStatus = async (status) => { await memberApi.patch(`/workspace/applications/${applicationId}`, { status }); await refresh(); if (onChanged) onChanged(); };
  const saveNotes = async () => { await memberApi.patch(`/workspace/applications/${applicationId}`, { notes }); };
  return (
    <div className="applicant-detail" data-testid="applicant-detail">
      <div className="detail-section">
        <h3>Applicant Profile</h3>
        <dl>{Object.entries(snapshot).map(([key, value]) => <div key={key}><dt>{key.replace(/_/g, " ")}</dt><dd>{value || "—"}</dd></div>)}</dl>
        <div className="material-actions">
          <label className="field status-field"><span>Application status</span>
            <select value={application.status} onChange={(event) => setStatus(event.target.value)} data-testid="applicant-status-select">
              {statuses.map((status) => <option key={status}>{status}</option>)}
            </select>
          </label>
          {application.cv_file_id && <button className="button button-back" onClick={() => downloadCv(application)} data-testid="download-cv-button"><FileText size={14} /> Download CV ({application.cv_filename})</button>}
        </div>
      </div>
      <div className="detail-section">
        <h3>Application Answers</h3>
        <dl>{Object.entries(application.answers || {}).map(([key, value]) => key === "custom" ? null : <div key={key}><dt>{key.replace(/_/g, " ")}</dt><dd>{String(value) || "—"}</dd></div>)}</dl>
        {application.answers?.custom && Object.keys(application.answers.custom).length > 0 && <dl>{Object.entries(application.answers.custom).map(([key, value]) => <div key={key}><dt>Custom question</dt><dd>{String(value) || "—"}</dd></div>)}</dl>}
      </div>
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
      <h2>Interview and Select the People Who Belong on Your Board</h2>
      <MaterialCard type="general_interview_invitation" title="General Interview Invitation" buttonLabel="Generate General Interview Invitation"
        description="Use this when inviting an applicant to a board introductory/interview conversation and you do not need applicant-specific personalization."
        material={byType.general_interview_invitation} refresh={refresh} />
      <MaterialCard type="general_rejection_email" title="General Applicant Rejection Email" buttonLabel="Generate General Applicant Rejection Email"
        description="Use this when an applicant will not be invited to the interview stage."
        material={byType.general_rejection_email} refresh={refresh} />
    </section>
  );
};

const ExternalApplicantForm = ({ refresh }) => {
  const [form, setForm] = useState({ name: "", email: "", phone: "", linkedin: "", notes: "" });
  const [cvFile, setCvFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const submit = async () => {
    setMessage("");
    if (!form.name.trim() || !form.email.trim()) { setMessage("Applicant name and email are required."); return; }
    setBusy(true);
    try {
      const payload = new FormData();
      Object.entries(form).forEach(([key, value]) => payload.append(key, value));
      if (cvFile) payload.append("cv", cvFile);
      await memberApi.post("/workspace/applications/external", payload, { headers: { "Content-Type": "multipart/form-data" } });
      setForm({ name: "", email: "", phone: "", linkedin: "", notes: "" }); setCvFile(null);
      setMessage("Applicant added to your Applicant Workspace.");
      refresh();
    } catch (err) { setMessage(err.response?.data?.detail || "Could not add the applicant."); }
    setBusy(false);
  };
  return (
    <section className="workspace-panel" data-testid="external-applicant-form">
      <h2>Add an Applicant From Outside the Board Application</h2>
      <p className="material-description">Use this for someone who applied through LinkedIn, another platform or another recruitment channel rather than your Board Builder application.</p>
      <div className="two-col-fields">
        <label className="field"><span>Applicant name *</span><input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} data-testid="external-applicant-name" /></label>
        <label className="field"><span>Email *</span><input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} data-testid="external-applicant-email" /></label>
        <label className="field"><span>Phone (optional)</span><input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
        <label className="field"><span>LinkedIn profile (optional)</span><input value={form.linkedin} onChange={(event) => setForm({ ...form, linkedin: event.target.value })} /></label>
      </div>
      <label className="field"><span>Upload CV/résumé</span><input type="file" accept=".pdf,.doc,.docx,.txt" onChange={(event) => setCvFile(event.target.files?.[0] || null)} data-testid="external-applicant-cv" /></label>
      <label className="field"><span>Notes (optional)</span><textarea rows="2" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
      <button className="button button-back" disabled={busy} onClick={submit} data-testid="add-external-applicant-button">{busy ? "Adding…" : "Add Applicant"}</button>
      {message && <p className="member-success" data-testid="external-applicant-message">{message}</p>}
    </section>
  );
};

export const Module4Applicants = () => {
  const { applications, statuses, refresh } = useApplications();
  const [openId, setOpenId] = useState("");
  return (
    <div data-testid="module4-workspace">
      <GeneralModule4Tools />
      <ExternalApplicantForm refresh={refresh} />
      <section className="workspace-panel">
        <h2>Your Board Applicants</h2>
        {applications.length === 0 && <p className="workspace-note" data-testid="no-applicants">No applications yet. When your recruitment campaign is published, applications will appear here.</p>}
        {applications.map((application) => (
          <div className={`applicant-row ${openId === application.application_id ? "open" : ""}`} key={application.application_id} data-testid={`applicant-row-${application.application_id}`}>
            <button className="applicant-row-head" onClick={() => setOpenId(openId === application.application_id ? "" : application.application_id)}>
              <strong>{application.profile_snapshot?.full_name || application.applicant_email}</strong>
              <span>{application.profile_snapshot?.profession || "—"}</span>
              <span>{application.profile_snapshot?.city ? `${application.profile_snapshot.city}, ${application.profile_snapshot.state_region}` : "—"}</span>
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
    </div>
  );
};

const ReferenceTools = ({ application, outcomes }) => {
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
    <div className="detail-section">
      {["reference_request_email", "reference_call_script", "reference_evaluation_form"].map((type) => (
        <MaterialCard key={type} type={type}
          title={{ reference_request_email: "Reference Request Email", reference_call_script: "Reference Call Script", reference_evaluation_form: "Reference Evaluation Form" }[type]}
          buttonLabel={`Generate ${{ reference_request_email: "Reference Request Email", reference_call_script: "Reference Call Script", reference_evaluation_form: "Reference Evaluation Form" }[type]}`}
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
      <p className="workspace-note">Nonprofit Board Builder does not perform background checks. Use the Background Check Provider Resource area in the $97 program resources. The nonprofit remains responsible for its selection decision.</p>
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

export const Module5References = () => {
  const { applications } = useApplications();
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
      <section className="workspace-panel">
        <h2>References and Background Checks</h2>
        <p className="material-description">Create the materials you need to contact and evaluate each applicant's references. You and your organization make every decision.</p>
        <div className="material-actions">
          <button className="button button-back" onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(`background check providers near ${location || "me"}`)}`, "_blank", "noopener")} data-testid="background-check-search-button">Find Background Check Providers Near Me</button>
        </div>
        <p className="workspace-note">If a background check is appropriate for this board appointment, use this search to find providers you can independently review and contact. Nonprofit Board Builder does not endorse, rank or select any provider, and no applicant information is shared with the search.</p>
        <label className="field"><span>Choose an applicant</span>
          <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} data-testid="module5-applicant-select">
            <option value="">Select an applicant</option>
            {applications.map((application) => <option key={application.application_id} value={application.application_id}>{application.profile_snapshot?.full_name || application.applicant_email} — {application.status}</option>)}
          </select>
        </label>
        {detail && <ReferenceTools application={detail} outcomes={outcomes} key={detail.application_id} />}
      </section>
    </div>
  );
};

const ONBOARDING_TOOLS = [
  ["onboarding_script", "Board Member Onboarding Script", "Generate My Board Member Onboarding Script", false, true, "Use this to guide the conversation or meeting where you formally bring your new board members into the organization."],
  ["onboarding_agenda", "Onboarding Agenda", "Generate My Onboarding Agenda", false, true, "A structured agenda for the onboarding session."],
  ["organization_overview", "Organization Overview", "Generate My Organization Overview", false, true, "Give new board members a clear introduction to the organization, mission, programs, priorities and leadership."],
  ["board_manual", "Board Manual", "Generate My Board Manual", false, true, "Give board members one central document explaining the organization, board expectations, responsibilities and key information they need to serve effectively."],
  ["board_member_agreement", "Board Member Agreement", "Generate My Board Member Agreement", true, false, "Set out the responsibilities, expectations and commitments the new board member is agreeing to accept. Shared through the secure signature link."],
  ["confidentiality_agreement", "Confidentiality Agreement", "Generate My Confidentiality Agreement", true, false, "Set clear expectations for protecting confidential organizational, board, donor and other sensitive information. Shared through the secure signature link."],
  ["conflict_of_interest_agreement", "Conflict of Interest Agreement", "Generate My Conflict of Interest Agreement", true, false, "Help board members formally disclose and appropriately manage conflicts that may affect their board responsibilities. Shared through the secure signature link."],
  ["ninety_day_plan", "New Board Member 90-Day Plan", "Generate My New Board Member 90-Day Plan", false, true, "A practical plan for the new board member's first ninety days."],
];

const SignatureControls = ({ application, agreementType, signatures, refreshSignatures }) => {
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
  return (
    <div className="signature-controls" data-testid={`signature-${agreementType}`}>
      <span className="signature-status">Signature status: <strong data-testid={`signature-status-${agreementType}`}>{record ? record.status : "Draft"}</strong></span>
      <div className="material-actions">
        {!record && <button className="button button-back" disabled={busy} onClick={prepare} data-testid={`prepare-signature-${agreementType}`}>Prepare for Signature</button>}
        {record && record.status === "Ready for Signature" && <button className="button" disabled={busy} onClick={send} data-testid={`send-signature-${agreementType}`}>Send for Signature</button>}
        {record && record.status === "Sent" && <><span className="workspace-note">Sent to {record.board_member_email}</span><button className="button button-back" disabled={busy} onClick={send}>Resend</button></>}
        {record && record.status === "Signed" && <>
          <button className="button button-back" onClick={downloadSigned} data-testid={`download-signed-${agreementType}`}><Download size={14} /> Download Signed Copy</button>
          <span className="member-success">Signed by {record.signed?.typed_signature} on {record.signed?.date}</span>
        </>}
      </div>
      {record && record.status !== "Draft" && <p className="material-meta">Version {record.agreement_version} snapshot is immutable. To change the agreement, edit the material and prepare a new version.</p>}
      {error && <p className="submit-error">{error}</p>}
    </div>
  );
};

const OnboardingApplicant = ({ application }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const [signatures, setSignatures] = useState([]);
  const refreshSignatures = useCallback(async () => {
    const response = await memberApi.get("/workspace/signatures", { params: { application_id: application.application_id } });
    setSignatures(response.data.signatures);
  }, [application.application_id]);
  useEffect(() => { refreshSignatures(); }, [refreshSignatures]);
  return (
    <div className="onboarding-applicant" data-testid={`onboarding-${application.application_id}`}>
      <h3><UserCheck size={17} /> {application.profile_snapshot?.full_name} — {application.profile_snapshot?.email} — {application.profile_snapshot?.profession}</h3>
      {ONBOARDING_TOOLS.map(([type, title, buttonLabel, isAgreement, shareable, description]) => (
        <div key={type}>
          <MaterialCard type={type} title={title} buttonLabel={buttonLabel} description={description} shareable={shareable} applicationId={application.application_id} material={byType[type]} refresh={refresh} />
          {isAgreement && byType[type] && <SignatureControls application={application} agreementType={type} signatures={signatures} refreshSignatures={refreshSignatures} />}
        </div>
      ))}
    </div>
  );
};

const BoardProfilePanel = () => {
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
    <section className="workspace-panel" data-testid="board-profile-panel">
      <h2>Board Member Profile Form</h2>
      <p className="material-description">Collect the information you need from each new board member so the organization has an accurate board profile and understands the skills, relationships and experience each person brings.</p>
      {!form ? (
        <button className="button button-back" onClick={load} data-testid="generate-board-profile-form">Generate My Board Member Profile Form</button>
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
    </section>
  );
};

export const Module6Onboarding = () => {
  const { applications } = useApplications();
  const selected = applications.filter((application) => application.status === "Selected");
  return (
    <div data-testid="module6-workspace">
      <section className="workspace-panel">
        <h2>Prepare Everything Your New Board Members Need to Begin Serving</h2>
        {selected.length === 0 && <p className="workspace-note" data-testid="no-selected">Only applicants whose status is Selected appear here. Mark an applicant as Selected in Module 4 to begin onboarding.</p>}
        {selected.map((application) => <OnboardingApplicant application={application} key={application.application_id} />)}
      </section>
      <BoardProfilePanel />
    </div>
  );
};
