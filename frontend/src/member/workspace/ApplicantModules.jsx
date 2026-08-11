import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, FileText, RefreshCw, Sparkles, UserCheck } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard, SendMaterialButton, currentVersion, printBranded, printText } from "./MaterialCard";
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
      <MaterialCard type="interview_invitation_message" title="Interview Invitation — Short Message" buttonLabel="Generate Short Message Version"
        description="A concise personalized version for LinkedIn, text or another direct-message channel. Use Copy to paste it wherever you message this applicant."
        applicationId={application.application_id} material={byType.interview_invitation_message} refresh={refresh}
        instructions={`Interview details — date: ${invite.date || "to be scheduled"}; time: ${invite.time || "to be scheduled"}; format: ${invite.format}; meeting link/location: ${invite.link || "to be provided"}.`} />
    </div>
  );
};

export const ApplicantDetail = ({ applicationId, statuses, onChanged }) => {
  const [detail, setDetail] = useState(null);
  const [notes, setNotes] = useState("");
  const [showApplication, setShowApplication] = useState(false);
  const { byType: byTypeApp, refresh: refreshApp } = useMaterials(applicationId);
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
        description="A reusable invitation template when you do not need applicant-specific personalization."
        material={byType.general_interview_invitation} refresh={refresh} />
      <MaterialCard type="general_interview_invitation_message" title="Interview Invitation — Short Message" buttonLabel="Generate Short Message Version"
        description="A concise version of the invitation you can send through LinkedIn, text message, Facebook Messenger or another direct-message channel. Use Copy to paste it wherever you message applicants."
        material={byType.general_interview_invitation_message} refresh={refresh} />
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

const REFEREE_LABELS = {
  reliability: "Reliability and follow-through", professionalism: "Professionalism",
  collaboration: "Ability to work collaboratively", leadership: "Leadership abilities",
  strongest_qualities: "Strongest professional qualities", board_service_qualities: "Qualities they could bring to nonprofit board service",
  concerns: "Concerns or considerations", recommend: "Would they recommend this individual for a nonprofit board or leadership role",
  comments: "Additional comments",
};

const RefereeResponse = ({ reference }) => {
  const [open, setOpen] = useState(false);
  if (reference.status !== "Completed") return null;
  return (
    <div className="referee-response">
      <button className="button button-back" onClick={() => setOpen(!open)} data-testid={`view-reference-response-${reference.reference_id}`}>{open ? "Hide Reference" : "View Reference"}</button>
      {open && (
        <dl data-testid={`reference-response-${reference.reference_id}`}>
          <div><dt>Referee</dt><dd>{reference.name} — {reference.position}{reference.organization ? `, ${reference.organization}` : ""}</dd></div>
          <div><dt>Relationship / known for</dt><dd>{reference.relationship} · {reference.duration}</dd></div>
          {reference.completed_at && <div><dt>Submitted</dt><dd>{new Date(reference.completed_at).toLocaleString()}</dd></div>}
          {Object.entries(REFEREE_LABELS).map(([key, label]) => reference.response?.[key] ? <div key={key}><dt>{label}</dt><dd>{reference.response[key]}</dd></div> : null)}
        </dl>
      )}
    </div>
  );
};

const ReferenceProcessPanel = ({ application }) => {
  const [process, setProcess] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [email, setEmail] = useState("");
  const [emailConfirmed, setEmailConfirmed] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const name = application.profile_snapshot?.full_name || "this applicant";
  const isHosted = !(application.source || "").toLowerCase().includes("external");
  const hostedEmail = (application.applicant_email || "").trim();

  const load = useCallback(async () => {
    const response = await memberApi.get(`/workspace/reference-process/${application.application_id}`);
    const record = response.data.process;
    setProcess(record);
    if (record) {
      const known = record.candidate_email || (isHosted ? hostedEmail : "") || "";
      setEmail(known || record.extracted_email || "");
      setEmailConfirmed(Boolean(known));
    }
    setLoaded(true);
  }, [application.application_id, hostedEmail, isHosted]);
  useEffect(() => { load(); }, [load]);

  const defaultEmail = (org = "our organization") => ({
    subject: "Reference Information Requested",
    body: `Hello ${name},\n\nWe are continuing with your board recruitment process. As part of our appointment process, please provide two professional references using the secure form linked below.\n\nThank you for your continued interest in serving with us.`,
  });

  const start = async () => {
    setBusy(true); setError("");
    try {
      const response = await memberApi.post("/workspace/reference-process", { application_id: application.application_id });
      setProcess(response.data);
      const known = response.data.candidate_email || (isHosted ? hostedEmail : "");
      setEmail(known || response.data.extracted_email || "");
      setEmailConfirmed(Boolean(known));
      const template = defaultEmail();
      setSubject(template.subject); setBody(template.body);
    } catch (err) { setError(err.response?.data?.detail || "Could not start the reference check."); }
    setBusy(false);
  };

  const sendToCandidate = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await memberApi.post(`/workspace/reference-process/${application.application_id}/send`,
        { application_id: application.application_id, candidate_email: email, subject, body });
      setMessage(`The Reference Information Form was emailed to ${response.data.sent_to}. The secure form link is included automatically.`);
      setShowPreview(false);
      await load();
    } catch (err) { setError(err.response?.data?.detail || "The form could not be sent."); }
    setBusy(false);
  };

  const resendReferee = async (referenceId) => {
    setBusy(true); setError(""); setMessage("");
    try {
      await memberApi.post(`/workspace/reference-process/${application.application_id}/resend-referee/${referenceId}`);
      setMessage("The reference form has been sent to the referee.");
      await load();
    } catch (err) { setError(err.response?.data?.detail || "The reference form could not be sent."); }
    setBusy(false);
  };

  if (!loaded) return <p>Loading reference check…</p>;
  const waitingForCandidate = process && (!process.references || process.references.length === 0);

  return (
    <div className="detail-section" data-testid="reference-process-panel">
      <h3>Reference Check — {name}</h3>
      <p className="material-description">Collect and verify two professional references for this applicant before making your final board appointment decision. {name} receives a secure form asking for two references; as soon as they submit, each referee is automatically emailed their own confidential reference form. Your organization makes every appointment decision — the platform only records the information.</p>
      {!process && (
        <button className="button" disabled={busy} onClick={start} data-testid="start-reference-check-button">{busy ? "Starting…" : "Start Reference Check"}</button>
      )}
      {process && (
        <>
          <p>Reference Check Status: <strong data-testid="reference-process-status">{process.status}</strong>
            {process.candidate_sent_at && <span className="material-meta"> · Candidate form sent to {process.candidate_sent_to || process.candidate_email} on {new Date(process.candidate_sent_at).toLocaleString()}</span>}
          </p>
          {waitingForCandidate && process.status === "Not Started" && (
            <>
              {isHosted && hostedEmail ? (
                <p className="workspace-note" data-testid="hosted-email-note">Candidate Email: <strong>{hostedEmail}</strong> (from their board application)</p>
              ) : !emailConfirmed && process.extracted_email ? (
                <div className="material-actions" data-testid="extracted-email-confirm">
                  <p className="workspace-note">We found this email address in the applicant's CV — please confirm it before anything is sent:</p>
                  <label className="field" style={{ minWidth: 280 }}><span>Candidate Email</span>
                    <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} data-testid="candidate-email-input" />
                  </label>
                  <button className="button button-back" onClick={() => setEmailConfirmed(true)} data-testid="confirm-email-button">Confirm Email</button>
                </div>
              ) : !emailConfirmed ? (
                <div className="material-actions" data-testid="missing-email-entry">
                  <p className="workspace-note">We could not confidently find an email address for this applicant — we never guess. Enter it below:</p>
                  <label className="field" style={{ minWidth: 280 }}><span>Candidate Email Address</span>
                    <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} data-testid="candidate-email-input" />
                  </label>
                  <button className="button button-back" disabled={!email.trim()} onClick={() => setEmailConfirmed(true)} data-testid="confirm-email-button">Confirm Email</button>
                </div>
              ) : (
                <p className="workspace-note">Candidate Email: <strong>{email}</strong></p>
              )}
              {(emailConfirmed || (isHosted && hostedEmail)) && !showPreview && (
                <button className="button" onClick={() => { const template = defaultEmail(); if (!subject) setSubject(template.subject); if (!body) setBody(template.body); setShowPreview(true); }} data-testid="email-reference-form-button">Email Reference Form to {name}</button>
              )}
              {showPreview && (
                <div className="material-edit" data-testid="candidate-email-preview">
                  <label className="field"><span>Subject</span><input value={subject} onChange={(event) => setSubject(event.target.value)} data-testid="candidate-email-subject" /></label>
                  <label className="field"><span>Email (the secure form link is added automatically below your message)</span>
                    <textarea rows="7" value={body} onChange={(event) => setBody(event.target.value)} data-testid="candidate-email-body" />
                  </label>
                  <div className="material-actions">
                    <button className="button" disabled={busy} onClick={sendToCandidate} data-testid="send-candidate-form-button">{busy ? "Sending…" : "Send"}</button>
                    <button className="button button-back" onClick={() => setShowPreview(false)}>Cancel</button>
                  </div>
                </div>
              )}
            </>
          )}
          {waitingForCandidate && process.status === "Waiting for Candidate" && (
            <>
              {[1, 2].map((index) => (
                <div className="reference-track-row" key={index} data-testid={`reference-track-${index}`}>
                  <div className="reference-track-info"><strong>Reference {index}</strong></div>
                  <span className="blog-status-badge pending" data-testid={`reference-status-${index}`}>Waiting for Candidate</span>
                </div>
              ))}
              <button className="button button-back" disabled={busy} onClick={() => { setShowPreview(true); }} data-testid="resend-candidate-form-button">Resend Candidate Form</button>
              {showPreview && (
                <div className="material-edit">
                  <label className="field"><span>Subject</span><input value={subject} onChange={(event) => setSubject(event.target.value)} /></label>
                  <label className="field"><span>Email</span><textarea rows="7" value={body} onChange={(event) => setBody(event.target.value)} /></label>
                  <div className="material-actions">
                    <button className="button" disabled={busy} onClick={sendToCandidate}>{busy ? "Sending…" : "Send"}</button>
                    <button className="button button-back" onClick={() => setShowPreview(false)}>Cancel</button>
                  </div>
                </div>
              )}
            </>
          )}
          {(process.references || []).map((reference, index) => (
            <div className="reference-track-row" key={reference.reference_id} data-testid={`reference-track-${index + 1}`}>
              <div className="reference-track-info">
                <strong>Reference {index + 1}: {reference.name}</strong>
                <span>{reference.position}{reference.organization ? `, ${reference.organization}` : ""} · {reference.relationship} · Known {reference.duration}</span>
              </div>
              <span className={`blog-status-badge ${reference.status === "Completed" ? "published" : "pending"}`} data-testid={`reference-status-${index + 1}`}>{reference.status}</span>
              {reference.status !== "Completed" && (
                <button className="button button-back" disabled={busy} onClick={() => resendReferee(reference.reference_id)} data-testid={`resend-referee-${index + 1}`}>{reference.status === "Not Sent" ? "Send Reference Request" : "Resend Reference Request"}</button>
              )}
              <RefereeResponse reference={reference} />
            </div>
          ))}
        </>
      )}
      {message && <p className="member-success" data-testid="reference-process-message">{message}</p>}
      {error && <p className="submit-error" data-testid="reference-process-error">{error}</p>}
    </div>
  );
};

const BackgroundCheckPanel = ({ application }) => {
  const [check, setCheck] = useState(application.background_check || { status: "Not started" });
  const [message, setMessage] = useState("");
  const saveCheck = async () => { await memberApi.patch(`/workspace/applications/${application.application_id}`, { background_check: check }); setMessage("Background check record saved."); };
  return (
    <div className="detail-section" data-testid="background-check-panel">
      <h3>Background Check Record</h3>
      <p className="workspace-note">Nonprofit Board Builder does not perform background checks and does not endorse, rank or select any provider. No applicant information is shared. The nonprofit remains responsible for its selection decision.</p>
      <div className="two-col-fields">
        <label className="field"><span>Background check</span><select value={check.status || "Not started"} onChange={(event) => setCheck({ ...check, status: event.target.value })} data-testid="background-status">{["Not Required", "Not started", "Pending", "In progress", "Completed", "Follow-up required"].map((option) => <option key={option}>{option}</option>)}</select></label>
        <label className="field"><span>Requested date</span><input value={check.requested_date || ""} onChange={(event) => setCheck({ ...check, requested_date: event.target.value })} /></label>
        <label className="field"><span>Completed date</span><input value={check.completed_date || ""} onChange={(event) => setCheck({ ...check, completed_date: event.target.value })} /></label>
      </div>
      <label className="field"><span>Notes</span><textarea rows="2" value={check.notes || ""} onChange={(event) => setCheck({ ...check, notes: event.target.value })} /></label>
      <button className="button button-back" onClick={saveCheck} data-testid="save-background-button">Save Background Check Record</button>
      {message && <p className="member-success">{message}</p>}
    </div>
  );
};


// ---------- Module 5: branding, prepare, conditional appointment ----------

const PREPARE_TOOLS = [
  ["organization_overview", "Organization Overview", "Generate Organization Overview", "Create a concise introduction to your organization that gives new board members the information they need to understand the mission, work, priorities and communities you serve."],
  ["board_manual", "Board Manual", "Generate Board Manual", "Create the central guide your board members can use to understand the organization, their responsibilities and how the board will work together."],
  ["board_member_agreement", "Board Member Agreement", "Generate Board Member Agreement", "Set out the responsibilities, expectations and commitments each board member agrees to accept when joining your board."],
  ["confidentiality_agreement", "Confidentiality Agreement", "Generate Confidentiality Agreement", "Set clear expectations for protecting confidential organizational, board, donor, applicant and other sensitive information."],
  ["conflict_of_interest_agreement", "Conflict of Interest Agreement", "Generate Conflict of Interest Agreement", "Create the agreement and disclosure your board members can use to identify and appropriately manage potential conflicts of interest."],
];

export const useBranding = () => {
  const [branding, setBranding] = useState({ logo_data: "", primary_color: "", secondary_color: "" });
  useEffect(() => { memberApi.get("/workspace/branding").then((r) => setBranding((c) => ({ ...c, ...(r.data.branding || {}) }))).catch(() => {}); }, []);
  return [branding, setBranding];
};

const BrandingPanel = ({ branding, setBranding }) => {
  const [message, setMessage] = useState("");
  const onLogo = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 500000) { setMessage("Logo must be under 500KB."); return; }
    const reader = new FileReader();
    reader.onload = () => setBranding({ ...branding, logo_data: reader.result });
    reader.readAsDataURL(file);
  };
  const save = async () => {
    await memberApi.put("/workspace/branding", branding);
    setMessage("Branding saved. Your documents will use these confirmed colors and logo.");
  };
  return (
    <div className="detail-section" data-testid="branding-panel">
      <h3>Document Branding</h3>
      <p className="material-description">Confirm the logo and brand colors used when designing your final documents. If you leave the colors empty, a professional neutral template is used. Nothing is applied without your confirmation here.</p>
      <div className="two-col-fields">
        <label className="field"><span>Organization logo (optional)</span><input type="file" accept="image/*" onChange={onLogo} data-testid="branding-logo-input" /></label>
        <label className="field"><span>Primary color</span><input type="color" value={branding.primary_color || "#1d3a2f"} onChange={(event) => setBranding({ ...branding, primary_color: event.target.value })} data-testid="branding-primary" /></label>
        <label className="field"><span>Secondary color</span><input type="color" value={branding.secondary_color || "#f4f1ea"} onChange={(event) => setBranding({ ...branding, secondary_color: event.target.value })} data-testid="branding-secondary" /></label>
      </div>
      {branding.logo_data && <img src={branding.logo_data} alt="Logo preview" style={{ maxHeight: 48 }} />}
      <div className="material-actions"><button className="button button-back" onClick={save} data-testid="save-branding-button">Confirm Branding</button></div>
      {message && <p className="member-success">{message}</p>}
    </div>
  );
};

export const BoardProfilePanel = () => {
  const [form, setForm] = useState(null);
  const [message, setMessage] = useState("");
  const load = async () => {
    try { const response = await memberApi.get("/workspace/board-profile-form"); setForm(response.data); }
    catch { setMessage("Could not load the profile form."); }
  };
  return (
    <div className="detail-section" data-testid="board-profile-panel">
      <h3>Board Member Profile Form</h3>
      <p className="material-description">Collect the professional information, skills, experience and interests you need to understand how each new board member can contribute. One standard hosted form — candidate-specific secure links with prefilled information are created automatically with each Conditional Appointment.</p>
      {!form ? (
        <button className="button" onClick={load} data-testid="generate-board-profile-form">Create Board Member Profile Form</button>
      ) : (
        <>
          <p className="member-success">Board Member Profile Form is ready.</p>
          <div className="material-actions">
            <code className="app-link-code" data-testid="board-profile-link">{`${window.location.origin}/board-profile/${form.share_token}`}</code>
            <button className="button button-back" onClick={async () => { await navigator.clipboard?.writeText(`${window.location.origin}/board-profile/${form.share_token}`); setMessage("Link copied."); }} data-testid="copy-board-profile-link">Copy Link</button>
          </div>
          <h3>Submitted Profiles ({form.responses.length})</h3>
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

const docStage = (material) => !material ? "Not Started" : material.status === "Approved" ? "Approved" : "Draft";

const OnboardingSessionPanel = ({ session, setSession }) => {
  const [message, setMessage] = useState("");
  const save = async () => {
    await memberApi.put("/workspace/onboarding-session", session);
    setMessage("Onboarding session saved. It is reused for every candidate's Conditional Appointment.");
  };
  return (
    <div className="detail-section" data-testid="onboarding-session-panel">
      <h3>Board Onboarding Session</h3>
      <p className="material-description">The Conditional Appointment email also invites the candidate to your Board Onboarding Session. Save the session once and reuse it for every candidate.</p>
      <div className="two-col-fields">
        <label className="field"><span>Date</span><input value={session.date || ""} onChange={(event) => setSession({ ...session, date: event.target.value })} data-testid="session-date" /></label>
        <label className="field"><span>Time</span><input value={session.time || ""} onChange={(event) => setSession({ ...session, time: event.target.value })} data-testid="session-time" /></label>
        <label className="field"><span>Timezone</span><input value={session.timezone || ""} onChange={(event) => setSession({ ...session, timezone: event.target.value })} data-testid="session-timezone" /></label>
        <label className="field"><span>Format</span><select value={session.format || ""} onChange={(event) => setSession({ ...session, format: event.target.value })} data-testid="session-format"><option value="">Select</option>{["Virtual", "In Person", "Hybrid"].map((option) => <option key={option}>{option}</option>)}</select></label>
        {(session.format === "Virtual" || session.format === "Hybrid") && <label className="field"><span>Meeting link</span><input value={session.link || ""} onChange={(event) => setSession({ ...session, link: event.target.value })} data-testid="session-link" /></label>}
        {(session.format === "In Person" || session.format === "Hybrid") && <label className="field"><span>Location</span><input value={session.location || ""} onChange={(event) => setSession({ ...session, location: event.target.value })} data-testid="session-location" /></label>}
      </div>
      <label className="field"><span>Anything the candidate should prepare (optional)</span><textarea rows="2" value={session.prepare || ""} onChange={(event) => setSession({ ...session, prepare: event.target.value })} /></label>
      <button className="button button-back" onClick={save} data-testid="save-session-button">Save Onboarding Session</button>
      {message && <p className="member-success">{message}</p>}
    </div>
  );
};

const ConditionalPanel = ({ application, orgMaterials, session, onChanged }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const missing = PREPARE_TOOLS.filter(([type]) => docStage(orgMaterials[type]) !== "Approved").map(([, title]) => title);
  return (
    <div className="detail-section" data-testid="conditional-panel">
      <h3>Prepare Conditional Appointment — {application.profile_snapshot?.full_name}</h3>
      <ul className="readiness-list" data-testid="conditional-checklist">
        <li className={["References Submitted", "In Progress", "Completed"].includes(application.reference_check_status) ? "done" : ""}>Reference Check: {application.reference_check_status || "Not Started"}</li>
        <li className={["Completed", "Not Required"].includes(application.background_check?.status) ? "done" : ""}>Background Check: {application.background_check?.status || "Not recorded"}</li>
        {PREPARE_TOOLS.map(([type, title]) => <li key={type} className={docStage(orgMaterials[type]) === "Approved" ? "done" : ""}>{title}: {docStage(orgMaterials[type])}</li>)}
        <li className={session.date ? "done" : ""}>Onboarding Session: {session.date ? `Scheduled — ${session.date} ${session.time || ""}` : "Not scheduled"}</li>
      </ul>
      {missing.length > 0 && <p className="submit-error" data-testid="conditional-missing">Complete the following onboarding materials before preparing this candidate's Conditional Appointment: {missing.join(", ")}</p>}
      <MaterialCard type="conditional_offer" title="Conditional Board Appointment Email" buttonLabel="Generate Conditional Board Appointment Email"
        description="One professional email telling the candidate your organization would like them to join the board (conditional while remaining requirements are completed), inviting them to the Board Onboarding Session, and automatically including their secure candidate-specific links: Organization Overview, Board Manual, the three agreements for signature, their Board Member Profile Form, and the Reference Information Form only if still needed. You never paste links manually."
        applicationId={application.application_id} material={byType.conditional_offer} refresh={refresh} approvable
        extraActions={byType.conditional_offer?.status === "Approved" ? (
          <SendMaterialButton type="conditional_offer" applicationId={application.application_id}
            label={application.emails_sent?.conditional_offer ? "Send Updated Appointment Information" : `Send Conditional Appointment to ${application.applicant_email || "candidate"}`}
            sentAt={application.emails_sent?.conditional_offer} onSent={onChanged} />
        ) : null} />
      <MaterialCard type="after_interview_rejection" title="After-Interview Rejection Email" buttonLabel="Generate After-Interview Rejection Email"
        description="A respectful, concise, professional email for an applicant you interviewed but have decided not to continue with. No onboarding resources are included."
        applicationId={application.application_id} material={byType.after_interview_rejection} refresh={refresh}
        extraActions={<SendMaterialButton type="after_interview_rejection" applicationId={application.application_id} label={application.emails_sent?.after_interview_rejection ? "Send Updated" : "Send"} sentAt={application.emails_sent?.after_interview_rejection} onSent={onChanged} />} />
    </div>
  );
};

const CandidateStatusList = ({ application }) => {
  const [signatures, setSignatures] = useState([]);
  const [profileLink, setProfileLink] = useState(null);
  useEffect(() => {
    memberApi.get("/workspace/signatures", { params: { application_id: application.application_id } }).then((r) => setSignatures(r.data.signatures)).catch(() => {});
    memberApi.get(`/workspace/board-profile-link/${application.application_id}`).then((r) => setProfileLink(r.data)).catch(() => {});
  }, [application.application_id]);
  const signatureStatus = (type) => {
    const record = signatures.find((s) => s.agreement_type === type);
    if (!record) return "Not Sent";
    if (record.status === "Signed") return "Signed";
    return record.status === "Sent" ? "Sent" : "Ready to Send";
  };
  return (
    <ul className="readiness-list" data-testid="candidate-status-list">
      <li className={application.reference_check_status === "Completed" ? "done" : ""}>Reference Check: {application.reference_check_status || "Not Started"}</li>
      <li className={["Completed", "Not Required"].includes(application.background_check?.status) ? "done" : ""}>Background Check: {application.background_check?.status || "Not recorded"}</li>
      {AGREEMENTS.map(([type, title]) => <li key={type} className={signatureStatus(type) === "Signed" ? "done" : ""}>{title}: {signatureStatus(type)}</li>)}
      <li className={profileLink?.response ? "done" : ""}>Board Member Profile: {profileLink?.response ? "Completed" : profileLink?.link ? "Ready" : "Not Sent"}</li>
      <li className={application.emails_sent?.conditional_offer ? "done" : ""}>Conditional Appointment: {application.emails_sent?.conditional_offer ? "Sent" : "Not Prepared"}</li>
    </ul>
  );
};

const CandidateDecisionCard = ({ application, selected, onSelect, onDecision, busyId }) => {
  const snapshot = application.profile_snapshot || {};
  const interviewed = Boolean(application.interview_completed);
  return (
    <div className={`candidate-card ${selected ? "selected" : ""}`} data-testid={`candidate-card-${application.application_id}`}>
      <div className="candidate-card-info">
        <strong>{snapshot.full_name || application.applicant_email}</strong>
        <span>{[snapshot.profession, snapshot.employer].filter(Boolean).join(" · ") || "—"}</span>
        {application.board_role && <span>Role: {application.board_role}</span>}
        <span>Status: <b>{application.status}</b> · Interview: <b data-testid={`interview-status-${application.application_id}`}>{interviewed ? "Completed" : "Not Completed"}</b></span>
      </div>
      <div className="candidate-card-actions">
        <button className="button button-back button-small" onClick={() => onSelect(application.application_id)} data-testid={`review-candidate-${application.application_id}`}>{selected ? "Reviewing" : "Review"}</button>
        {application.status !== "Moving Forward" && !["Selected", "Conditional Appointment"].includes(application.status) && (
          <button className="button button-small" disabled={busyId === application.application_id} onClick={() => onDecision(application.application_id, "move_forward")} data-testid={`move-forward-${application.application_id}`}>Move Forward</button>
        )}
        {!["Not Moving Forward", "Not Selected", "Selected"].includes(application.status) && (
          <button className="button button-back button-small" disabled={busyId === application.application_id} onClick={() => onDecision(application.application_id, "do_not_move_forward")} data-testid={`do-not-move-forward-${application.application_id}`}>Do Not Move Forward</button>
        )}
      </div>
    </div>
  );
};

export const Module5References = () => {
  const { applications, refresh: refreshApps } = useApplications();
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  const [branding, setBranding] = useBranding();
  const [session, setSession] = useState({});
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  const [location, setLocation] = useState("");
  useEffect(() => {
    memberApi.get("/workspace/profile").then((response) => {
      const data = { ...(response.data.prefill || {}), ...(response.data.profile || {}) };
      setLocation([data.city, data.state_region, data.country].filter(Boolean).join(", "));
    }).catch(() => {});
    memberApi.get("/workspace/onboarding-session").then((response) => setSession(response.data.session || {})).catch(() => {});
  }, []);
  const loadDetail = useCallback(() => {
    if (!selectedId) { setDetail(null); return; }
    memberApi.get(`/workspace/applications/${selectedId}`).then((response) => setDetail(response.data.application));
  }, [selectedId]);
  useEffect(() => { loadDetail(); }, [loadDetail]);
  const onChanged = () => { loadDetail(); refreshApps(); };
  const [busyId, setBusyId] = useState("");
  const decide = async (applicationId, decision) => {
    setBusyId(applicationId);
    try {
      await memberApi.post(`/workspace/applications/${applicationId}/decision`, { decision });
      setSelectedId(applicationId);
      await refreshApps();
      if (selectedId === applicationId) loadDetail();
    } catch { window.alert("The decision could not be saved."); }
    setBusyId("");
  };
  const sorted = [...applications].sort((a, b) => Number(Boolean(b.interview_completed)) - Number(Boolean(a.interview_completed)));
  const movingForward = detail && detail.status === "Moving Forward";
  const notMovingForward = detail && ["Not Moving Forward", "Not Selected"].includes(detail.status);

  return (
    <div data-testid="module5-workspace">
      <section className="workspace-panel" data-testid="module5-decide-forward-section">
        <h2>Decide Who Moves Forward</h2>
        <p className="material-description">Review the applicants you interviewed and select the people you would like to move forward in your board recruitment process. Your organization decides — never the AI. Marking a decision sends nothing automatically; it only prepares the right next steps for your review.</p>
        <div className="material-actions">
          <button className="button button-back" onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(`background check providers near ${location || "me"}`)}`, "_blank", "noopener")} data-testid="background-check-search-button">Find Background Check Providers Near Me</button>
        </div>
        {sorted.length === 0 && <p className="workspace-note" data-testid="no-candidates-note">Your applicants from Module 4 appear here automatically once applications arrive.</p>}
        {sorted.map((application) => (
          <CandidateDecisionCard key={application.application_id} application={application} selected={selectedId === application.application_id} onSelect={setSelectedId} onDecision={decide} busyId={busyId} />
        ))}
        {detail && (
          <div className="candidate-progress" data-testid="candidate-progress">
            <h3>{detail.profile_snapshot?.full_name || detail.applicant_email} — <span data-testid="candidate-progress-status">{detail.status}</span></h3>
            {movingForward && <CandidateStatusList application={detail} key={`status-${detail.application_id}-${detail.updated_at}`} />}
            {movingForward && (
              <p className="workspace-note" data-testid="next-step-hint">
                Prepare Next-Step Email: {detail.reference_check_status === "Completed"
                  ? "references are complete — prepare the Conditional Appointment below when your onboarding materials are ready."
                  : "this candidate's next step is the Reference Check below. That email includes only the secure Reference Information Form — onboarding materials are sent later with the Conditional Appointment."}
              </p>
            )}
            {(movingForward || !notMovingForward) && <ReferenceProcessPanel application={detail} key={`ref-${detail.application_id}`} />}
            {(movingForward || !notMovingForward) && <BackgroundCheckPanel application={detail} key={`bg-${detail.application_id}`} />}
          </div>
        )}
      </section>

      <section className="workspace-panel" data-testid="module5-prepare-section">
        <h2>Prepare Your New Board Member Materials</h2>
        <p className="material-description">Prepare the documents and information your selected board members will need before onboarding. Generate each resource, review it, make any changes you want, and approve the final version. These are generated once for your organization — candidate-specific links are created automatically later.</p>
        <ul className="readiness-list" data-testid="prepare-status-list">
          {PREPARE_TOOLS.map(([type, title]) => <li key={type} className={docStage(orgMaterials[type]) === "Approved" ? "done" : ""}>{title}: {docStage(orgMaterials[type])}</li>)}
        </ul>
        <BrandingPanel branding={branding} setBranding={setBranding} />
        {PREPARE_TOOLS.map(([type, title, buttonLabel, description]) => (
          <MaterialCard key={type} type={type} title={title} buttonLabel={buttonLabel} description={description} approvable
            shareable={type === "organization_overview" || type === "board_manual"}
            material={orgMaterials[type]} refresh={refreshOrg}
            extraActions={orgMaterials[type]?.status === "Approved" ? (
              <button className="button button-back" onClick={() => printBranded(title, currentVersion(orgMaterials[type]).display_text, branding)} data-testid={`design-${type}`}><Download size={14} /> {type.includes("agreement") ? "Create Final Agreement PDF" : `Design ${title} PDF`}</button>
            ) : null} />
        ))}
        <BoardProfilePanel />
      </section>

      <section className="workspace-panel" data-testid="module5-decide-section">
        <h2>Communicate Your Decision</h2>
        <p className="material-description">After references and any background checks, communicate your decision. The Conditional Appointment email is also the candidate's onboarding invitation — it automatically includes the candidate's secure links. Nothing is ever pasted manually.</p>
        <OnboardingSessionPanel session={session} setSession={setSession} />
        {!detail && <p className="workspace-note">Choose a candidate above to prepare their decision communication.</p>}
        {detail && <ConditionalPanel application={detail} orgMaterials={orgMaterials} session={session} onChanged={onChanged} key={`dec-${detail.application_id}`} />}
      </section>
    </div>
  );
};

// ---------- Module 6 ----------

const AGREEMENTS = [["board_member_agreement", "Board Member Agreement"], ["confidentiality_agreement", "Confidentiality Agreement"], ["conflict_of_interest_agreement", "Conflict of Interest Agreement"]];

const MemberReadiness = ({ application, onChanged }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const [signatures, setSignatures] = useState([]);
  const [profileLink, setProfileLink] = useState(null);
  const [confirmedReady, setConfirmedReady] = useState(Boolean(application.emails_sent?.formal_appointment_email));
  useEffect(() => {
    memberApi.get("/workspace/signatures", { params: { application_id: application.application_id } }).then((r) => setSignatures(r.data.signatures)).catch(() => {});
    memberApi.get(`/workspace/board-profile-link/${application.application_id}`).then((r) => setProfileLink(r.data)).catch(() => {});
  }, [application.application_id]);
  const signatureStatus = (type) => (signatures.find((s) => s.agreement_type === type) || {}).status || "Not Sent";
  const joined = application.final_outcome === "Joined Board";
  return (
    <div className="onboarding-applicant" data-testid={`onboarding-${application.application_id}`}>
      <h3><UserCheck size={17} /> {application.profile_snapshot?.full_name} {joined && <span className="blog-status-badge published">Board Member</span>}</h3>
      <ul className="readiness-list" data-testid="member-readiness">
        <li className={application.reference_check_status === "Completed" ? "done" : ""}>Reference Check: {application.reference_check_status || "Not Started"}</li>
        <li className={["Completed", "Not Required"].includes(application.background_check?.status) ? "done" : ""}>Background Check: {application.background_check?.status || "Not recorded"}</li>
        {AGREEMENTS.map(([type, title]) => <li key={type} className={signatureStatus(type) === "Signed" ? "done" : ""}>{title}: {signatureStatus(type)}</li>)}
        <li className={profileLink?.response ? "done" : ""}>Board Member Profile: {profileLink?.response ? "Completed" : profileLink?.link ? "Sent" : "Not Sent"}</li>
      </ul>
      {!joined && !confirmedReady && (
        <button className="button" onClick={() => { if (window.confirm(`Confirm that ${application.profile_snapshot?.full_name} is ready for formal appointment? Your organization controls this decision.`)) setConfirmedReady(true); }} data-testid="confirm-ready-button">Confirm Ready for Formal Appointment</button>
      )}
      {(confirmedReady || joined) && (
        <MaterialCard type="formal_appointment_email" title="Formal Board Appointment Email" buttonLabel="Generate Formal Board Appointment Email"
          description="Confirms the appointment is now official, welcomes them to the board using your organization's board type, and covers what happens next. This is different from the Conditional Appointment email."
          applicationId={application.application_id} material={byType.formal_appointment_email} refresh={refresh} approvable
          extraActions={byType.formal_appointment_email?.status === "Approved" ? (
            <SendMaterialButton type="formal_appointment_email" applicationId={application.application_id}
              label={application.emails_sent?.formal_appointment_email ? "Send Updated" : `Send to ${application.applicant_email || "candidate"}`}
              sentAt={application.emails_sent?.formal_appointment_email} onSent={onChanged} />
          ) : null} />
      )}
    </div>
  );
};

const FirstMeetingPanel = ({ orgMaterials, refreshOrg, boardMembers }) => {
  const [meeting, setMeeting] = useState({ date: "", time: "", timezone: "", format: "", link: "", location: "", prepare: "" });
  const [recipients, setRecipients] = useState([]);
  const [message, setMessage] = useState("");
  useEffect(() => { setRecipients(boardMembers.map((m) => m.application_id)); }, [boardMembers]);
  const toggle = (id) => setRecipients((current) => current.includes(id) ? current.filter((x) => x !== id) : [...current, id]);
  const material = orgMaterials.first_board_meeting_invitation;
  const send = async (resend) => {
    const names = boardMembers.filter((m) => recipients.includes(m.application_id)).map((m) => m.profile_snapshot?.full_name).join(", ");
    if (!window.confirm(`Send First Board Meeting Invitation to: ${names}?`)) return;
    setMessage("");
    try {
      const response = await memberApi.post("/workspace/send-first-meeting", { application_ids: recipients, resend });
      setMessage(`Invitation sent to: ${response.data.sent.join(", ") || "no valid recipients"}.${response.data.failures.length ? ` Could not send to: ${response.data.failures.join(", ")}.` : ""}`);
    } catch (err) { setMessage(err.response?.data?.detail || "The invitation could not be sent."); }
  };
  return (
    <section className="workspace-panel" data-testid="first-meeting-panel">
      <h2>Invite Your New Board to Its First Board Meeting</h2>
      <p className="material-description">Invite your newly assembled board to its first official meeting and begin working together. We only need the meeting details — your organization information is already stored.</p>
      <div className="two-col-fields">
        <label className="field"><span>Meeting date</span><input value={meeting.date} onChange={(event) => setMeeting({ ...meeting, date: event.target.value })} data-testid="meeting-date" /></label>
        <label className="field"><span>Meeting time</span><input value={meeting.time} onChange={(event) => setMeeting({ ...meeting, time: event.target.value })} data-testid="meeting-time" /></label>
        <label className="field"><span>Timezone</span><input value={meeting.timezone} onChange={(event) => setMeeting({ ...meeting, timezone: event.target.value })} data-testid="meeting-timezone" /></label>
        <label className="field"><span>Format</span><select value={meeting.format} onChange={(event) => setMeeting({ ...meeting, format: event.target.value })}><option value="">Select</option>{["Virtual", "In Person", "Hybrid"].map((option) => <option key={option}>{option}</option>)}</select></label>
        {(meeting.format === "Virtual" || meeting.format === "Hybrid") && <label className="field"><span>Meeting link</span><input value={meeting.link} onChange={(event) => setMeeting({ ...meeting, link: event.target.value })} data-testid="meeting-link" /></label>}
        {(meeting.format === "In Person" || meeting.format === "Hybrid") && <label className="field"><span>Location</span><input value={meeting.location} onChange={(event) => setMeeting({ ...meeting, location: event.target.value })} data-testid="meeting-location" /></label>}
      </div>
      <label className="field"><span>Anything members should review or prepare (optional)</span><textarea rows="2" value={meeting.prepare} onChange={(event) => setMeeting({ ...meeting, prepare: event.target.value })} data-testid="meeting-prepare" /></label>
      <MaterialCard type="first_board_meeting_invitation" title="First Board Meeting Invitation Email" buttonLabel="Generate First Board Meeting Invitation Email"
        description="One professional editable email to your new board members. Nothing is sent automatically."
        material={material} refresh={refreshOrg} approvable
        instructions={`First board meeting details — date: ${meeting.date || "not supplied"}; time: ${meeting.time || "not supplied"}; timezone: ${meeting.timezone || "not supplied"}; format: ${meeting.format || "not supplied"}; meeting link: ${meeting.link || "not supplied"}; location: ${meeting.location || "not supplied"}; preparation requested: ${meeting.prepare || "none"}. Use these exactly; write '[To be confirmed]' for anything not supplied.`} />
      {material?.status === "Approved" && boardMembers.length > 0 && (
        <div className="detail-section" data-testid="first-meeting-recipients">
          <h3>Recipients (formally appointed board members only)</h3>
          {boardMembers.map((member) => (
            <label className="checkbox-field" key={member.application_id}>
              <input type="checkbox" checked={recipients.includes(member.application_id)} onChange={() => toggle(member.application_id)} data-testid={`recipient-${member.application_id}`} />
              <span>{member.profile_snapshot?.full_name} — {member.applicant_email || "no email on record"}</span>
            </label>
          ))}
          <div className="material-actions">
            <button className="button" disabled={!recipients.length} onClick={() => send(false)} data-testid="send-first-meeting-button">Send First Board Meeting Invitation</button>
            <button className="button button-back" disabled={!recipients.length} onClick={() => send(true)} data-testid="send-updated-meeting-button">Send Updated Meeting Information</button>
          </div>
          {message && <p className="member-success" data-testid="first-meeting-message">{message}</p>}
        </div>
      )}
    </section>
  );
};

const PreparedResource = ({ type, title, material, branding }) => {
  const version = currentVersion(material);
  return (
    <div className="prepared-resource" data-testid={`prepared-${type}`}>
      <div className="material-actions">
        <span className="signature-status"><strong>{title}</strong> — {version ? (material.status === "Approved" ? "Approved" : "Draft") : "Not yet generated — prepare it in Module 5"}</span>
        {version && <button className="button button-back" onClick={() => printBranded(title, version.display_text, branding)} data-testid={`view-prepared-${type}`}><Download size={14} /> Open PDF</button>}
      </div>
    </div>
  );
};

export const Module6Onboarding = () => {
  const { applications, refresh } = useApplications();
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  const [branding] = useBranding();
  const [session, setSession] = useState({});
  useEffect(() => { memberApi.get("/workspace/onboarding-session").then((r) => setSession(r.data.session || {})).catch(() => {}); }, []);
  const candidates = applications.filter((a) => a.status === "Conditional Appointment" || a.status === "Selected");
  const boardMembers = applications.filter((a) => a.final_outcome === "Joined Board" || a.status === "Selected");
  const markSession = async (status) => {
    const next = { ...session, status };
    await memberApi.put("/workspace/onboarding-session", next);
    setSession(next);
  };
  return (
    <div data-testid="module6-workspace">
      <section className="workspace-panel" data-testid="module6-members-section">
        <h2>Onboard Your New Board Members</h2>
        <p className="material-description">Complete the final steps for the people you have selected, formally welcome them to your board, and prepare them to begin serving. Completion of every item never appoints anyone automatically — your organization confirms each appointment.</p>
        {session?.date && (
          <div className="material-actions" data-testid="session-status-controls">
            <span className="signature-status">Onboarding Session: <strong>{session.status || "Scheduled"}</strong> — {session.date} {session.time || ""}</span>
            {session.status !== "Completed" && <button className="button button-back" onClick={() => markSession("Completed")} data-testid="mark-session-completed">Mark Session Completed</button>}
          </div>
        )}
        {candidates.length === 0 && <p className="workspace-note" data-testid="no-conditional">Candidates appear here once you send their Conditional Appointment in Module 5.</p>}
        {candidates.map((application) => <MemberReadiness application={application} onChanged={refresh} key={application.application_id} />)}
      </section>

      <section className="workspace-panel" data-testid="module6-resources-section">
        <h2>Onboarding Resources Prepared in Module 5</h2>
        {[["organization_overview", "Organization Overview"], ["board_manual", "Board Manual"], ...AGREEMENTS].map(([type, title]) => (
          <PreparedResource key={type} type={type} title={title} material={orgMaterials[type]} branding={branding} />
        ))}
      </section>

      <section className="workspace-panel" data-testid="module6-script-section">
        <MaterialCard type="onboarding_script" title="Board Member Onboarding Script" buttonLabel="Generate My Board Member Onboarding Script"
          description="Use this script to guide your onboarding conversation so every new board member understands the organization, their role, expectations and how they can begin contributing."
          material={orgMaterials.onboarding_script} refresh={refreshOrg} approvable />
      </section>

      <FirstMeetingPanel orgMaterials={orgMaterials} refreshOrg={refreshOrg} boardMembers={boardMembers} />

      <section className="workspace-panel" data-testid="complete-recruitment-panel">
        <h2>Complete Recruitment</h2>
        <p className="material-description">You have completed the recruitment process. Continue to see the results of your recruitment campaign and the people who have joined your board.</p>
        <Link className="button" to="/app/recruitment/self-guided/results" data-testid="view-results-button">View My Recruitment Results</Link>
      </section>
    </div>
  );
};
