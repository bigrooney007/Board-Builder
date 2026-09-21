import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, FileText, UserCheck } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard, SendMaterialButton, currentVersion, downloadMaterialPdf, printBranded } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";
import { recruitmentWorkspaceText, applicantModulesText } from "../../content/appContent";

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

const CandidateActions = ({ application, refresh, branding }) => {
  const { byType, refresh: refreshMaterials } = useMaterials(application.application_id);
  const name = application.profile_snapshot?.full_name || "this applicant";
  const email = application.applicant_email || application.profile_snapshot?.email || "";
  const interviewed = Boolean(application.interview_completed);
  const refreshAll = async () => { await refreshMaterials(); await refresh(); };

  const markInterviewComplete = async () => {
    if (!window.confirm(`Mark the interview with ${name} as complete? You control this — nothing is inferred automatically.`)) return;
    await memberApi.patch(`/workspace/applications/${application.application_id}`, { interview_completed: true });
    await refreshAll();
  };

  return (
    <>
      <div className="detail-section" data-testid="interview-invitation-section">
        <MaterialCard type="interview_invitation" title={`Interview Invitation — ${name}`} buttonLabel="Generate Interview Invitation"
          description="A finished, candidate-specific invitation to the interview stage. If no scheduling link is stored, the email says your organization will coordinate the interview time directly — you can edit anything before sending. Nothing is sent automatically."
          applicationId={application.application_id} material={byType.interview_invitation} refresh={refreshAll} approvable
          extraActions={byType.interview_invitation ? (
            <SendMaterialButton type="interview_invitation" applicationId={application.application_id} recipientEmail={email}
              label={application.emails_sent?.interview_invitation ? "Send Again" : `Send Interview Invitation${email ? ` to ${email}` : ""}`}
              sentAt={application.emails_sent?.interview_invitation} onSent={refreshAll} />
          ) : null} />
      </div>

      <div className="detail-section" data-testid="before-interview-rejection-section">
        <MaterialCard type="before_interview_rejection" title={`Before-Interview Rejection — ${name}`} buttonLabel="Generate Before-Interview Rejection"
          description="Use this only when YOU have decided not to invite this applicant to interview. A respectful, relationship-preserving email with no invented rejection reason. Sending it marks the applicant Not Moving to Interview — their record is always preserved."
          applicationId={application.application_id} material={byType.before_interview_rejection} refresh={refreshAll} approvable
          extraActions={byType.before_interview_rejection ? (
            <SendMaterialButton type="before_interview_rejection" applicationId={application.application_id} recipientEmail={email}
              label={application.emails_sent?.before_interview_rejection ? "Send Again" : "Send Before-Interview Rejection"}
              sentAt={application.emails_sent?.before_interview_rejection} onSent={refreshAll} />
          ) : null} />
      </div>

      <div className="detail-section" data-testid="interview-guide-section">
        <MaterialCard type="interview_guide" title={`Interview Guide — ${name}`} buttonLabel="Generate Interview Guide"
          description="A candidate-specific interview guide built from this person's actual application and CV, your organization's mission and needs, and the approved board-member profiles from Step 2. It prepares you to run the conversation — it never scores or selects candidates. You make every decision."
          applicationId={application.application_id} material={byType.interview_guide} refresh={refreshAll} approvable
          extraActions={byType.interview_guide ? (
            <button className="button button-back" onClick={() => printBranded(`Board Candidate Interview Guide — ${name}`, currentVersion(byType.interview_guide).display_text + "\n\nPOST-INTERVIEW NOTES\n\nMost Relevant Strengths:\n\n\nConcerns / Areas to Clarify:\n\n\nPotential Areas of Contribution:\n\n\nCommitment / Availability:\n\n\nFollow-Up Questions:\n\n\nOverall Notes:\n\n", branding || {})} data-testid="download-branded-interview-guide"><Download size={14} /> Download Branded Copy</button>
          ) : null} />
      </div>

      <div className="detail-section" data-testid="interview-completion-section">
        <h3>Interview Status: <span data-testid="interview-status">{interviewed ? `Completed${application.interview_completed_at ? ` — ${new Date(application.interview_completed_at).toLocaleDateString()}` : ""}` : "Not Completed"}</span></h3>
        {!interviewed && (
          <button className="button button-back" onClick={markInterviewComplete} data-testid="mark-interview-complete-button">Mark Interview Complete</button>
        )}
        {interviewed && (
          <MaterialCard type="after_interview_thank_you" title={`After-Interview Thank-You — ${name}`} buttonLabel="Generate After-Interview Thank-You"
            description="A decision-neutral thank-you for everyone who attended their interview. It never accepts, rejects or conditionally appoints — it simply thanks the candidate and says you will follow up once the review process is complete."
            applicationId={application.application_id} material={byType.after_interview_thank_you} refresh={refreshAll} approvable
            extraActions={byType.after_interview_thank_you ? (
              <SendMaterialButton type="after_interview_thank_you" applicationId={application.application_id} recipientEmail={email}
                label={application.emails_sent?.after_interview_thank_you ? "Send Again" : "Send After-Interview Thank-You"}
                sentAt={application.emails_sent?.after_interview_thank_you} onSent={refreshAll} />
            ) : null} />
        )}
        {interviewed && (
          <MaterialCard type="after_interview_email" title={`Move Forward After Interview — ${name}`} buttonLabel="Generate Move Forward Email"
            description="Use this ONLY after you have decided this candidate should move forward to References / Background Checks. It tells them they are proceeding to the next stage of the recruitment process — it is not a Board appointment. If you selected 'Further Conversation or Clarification Needed' or 'Do Not Move Forward', do not use this email."
            applicationId={application.application_id} material={byType.after_interview_email} refresh={refreshAll} approvable
            extraActions={byType.after_interview_email ? (
              <SendMaterialButton type="after_interview_email" applicationId={application.application_id} recipientEmail={email}
                label={application.emails_sent?.after_interview_email ? "Send Again" : "Send Move Forward Email"}
                sentAt={application.emails_sent?.after_interview_email} onSent={refreshAll} />
            ) : null} />
        )}
      </div>
    </>
  );
};

export const ApplicantDetail = ({ applicationId, statuses, onChanged, branding }) => {
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
        <h3>{recruitmentWorkspaceText.h_applicantProfile}</h3>
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
          <h3>{recruitmentWorkspaceText.h_applicationAnswers}</h3>
          <dl>{Object.entries(application.answers || {}).map(([key, value]) => key === "custom" ? null : <div key={key}><dt>{key.replace(/_/g, " ")}</dt><dd>{String(value) || "—"}</dd></div>)}</dl>
          {application.answers?.custom && Object.keys(application.answers.custom).length > 0 && <dl>{Object.entries(application.answers.custom).map(([key, value]) => <div key={key}><dt>Custom question</dt><dd>{String(value) || "—"}</dd></div>)}</dl>}
        </div>
      )}
      <CandidateActions application={application} refresh={async () => { await refresh(); if (onChanged) onChanged(); }} branding={branding} />
      <div className="detail-section">
        <h3>{recruitmentWorkspaceText.h_privateNotesNeverShownTo}</h3>
        <textarea rows="4" value={notes} onChange={(event) => setNotes(event.target.value)} data-testid="applicant-notes" />
        <button className="button button-back" onClick={saveNotes} data-testid="save-notes-button">Save Notes</button>
      </div>
    </div>
  );
};

const ExternalApplicantForm = ({ refresh }) => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [cvFile, setCvFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const submit = async () => {
    setMessage("");
    if (!name.trim()) { setMessage("Applicant name is required."); return; }
    if (!cvFile) { setMessage("Please upload the applicant's CV / résumé."); return; }
    setBusy(true);
    try {
      const payload = new FormData();
      payload.append("name", name);
      payload.append("email", email.trim());
      payload.append("cv", cvFile);
      await memberApi.post("/workspace/applications/external", payload);
      setName(""); setEmail(""); setCvFile(null);
      setMessage("Applicant added. They now use the exact same interview actions as your hosted applicants.");
      refresh();
    } catch (err) { setMessage(err.response?.data?.detail || "Could not add the applicant."); }
    setBusy(false);
  };
  return (
    <section className="workspace-panel" data-testid="external-applicant-form">
      <h2>{recruitmentWorkspaceText.h_addExternalApplicant}</h2>
      <p className="material-description">{recruitmentWorkspaceText.d_applicantsMayAlsoComeTo}</p>
      <div className="two-col-fields">
        <label className="field"><span>Applicant Name <b>*</b></span><input value={name} onChange={(event) => setName(event.target.value)} data-testid="external-applicant-name" /></label>
        <label className="field"><span>Applicant Email</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} data-testid="external-applicant-email" /></label>
        <label className="field"><span>CV / Résumé <b>*</b></span><input type="file" accept=".pdf,.doc,.docx" onChange={(event) => setCvFile(event.target.files?.[0] || null)} data-testid="external-applicant-cv" /></label>
      </div>
      <button className="button" disabled={busy} onClick={submit} data-testid="add-external-applicant-button">{busy ? "Adding…" : "Add Applicant"}</button>
      {message && <p className="member-success" data-testid="external-applicant-message">{message}</p>}
    </section>
  );
};

export const Module4Applicants = () => {
  const { applications, statuses, refresh } = useApplications();
  const [branding] = useBranding();
  const [openId, setOpenId] = useState("");
  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("application_id") || "";
    if (requested && applications.some((application) => application.application_id === requested)) setOpenId(requested);
  }, [applications]);
  const interviewLabel = (application) => application.interview_completed ? "Interview Completed"
    : application.emails_sent?.interview_invitation ? "Interview Invited"
    : application.status === "Not Moving to Interview" ? "Not Moving to Interview" : "New";
  return (
    <div data-testid="module4-workspace">
      <ExternalApplicantForm refresh={refresh} />
      <section className="workspace-panel">
        <h2>{recruitmentWorkspaceText.h_yourBoardApplicants}</h2>
        <p className="material-description">{recruitmentWorkspaceText.d_everyoneWhoAppliesThroughYour}</p>
        {applications.length === 0 && <p className="workspace-note" data-testid="no-applicants">{applicantModulesText.noApplicationsYetWhenYour}</p>}
        {applications.map((application) => (
          <div className={`applicant-row ${openId === application.application_id ? "open" : ""}`} key={application.application_id} data-testid={`applicant-row-${application.application_id}`}>
            <button className="applicant-row-head" onClick={() => setOpenId(openId === application.application_id ? "" : application.application_id)}>
              <strong>{application.profile_snapshot?.full_name || application.applicant_email}</strong>
              <span>{[application.profile_snapshot?.profession, application.profile_snapshot?.employer].filter(Boolean).join(" · ") || "—"}</span>
              <span>{application.profile_snapshot?.location || application.profile_snapshot?.city || ""}</span>
              <span className="source-tag">{application.source}</span>
              <span>CV: {application.cv_filename ? "Yes" : "No"}</span>
              <span data-testid={`interview-label-${application.application_id}`}>{interviewLabel(application)}</span>
              <span className={`status-pill status-${application.status.replace(/\s/g, "-").toLowerCase()}`}>{application.status}</span>
            </button>
            {openId === application.application_id && <ApplicantDetail applicationId={application.application_id} statuses={statuses} onChanged={refresh} branding={branding} />}
          </div>
        ))}
      </section>
    </div>
  );
};

// ---------- Module 5 ----------

const REFEREE_LABELS = {
  capacity: "Capacity and length of relationship", strengths: "Strengths, skills or qualities for board service",
  teamwork: "Working with others, responsibility and team contribution", explanation: "Explanation",
  reliability: "Reliability, professionalism and follow-through", professionalism: "Professionalism",
  collaboration: "Ability to work collaboratively", leadership: "Leadership abilities",
  strongest_qualities: "Strongest professional qualities", board_service_qualities: "Qualities they could bring to nonprofit board service",
  concerns: "Concerns or considerations", recommend: "Would they feel comfortable recommending this candidate for board service",
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
      <p className="material-description">Collect and verify two professional references for this candidate before making your final board appointment decision. {name} receives a secure form asking for two references. When they submit, you are notified and the references appear below marked Ready to Contact — no reference is emailed until you click Email Reference for Confirmation. Each reference then receives their own secure five-question form, and you are notified as each response comes in. You make every decision — the platform only records the information.</p>
      {!process && (
        <button className="button" disabled={busy} onClick={start} data-testid="start-reference-check-button">{busy ? "Starting…" : "START REFERENCING"}</button>
      )}
      {process && (
        <>
          <p>Reference Check Status: <strong data-testid="reference-process-status">{process.status}</strong>
            {process.candidate_sent_at && <span className="material-meta"> · Candidate form sent to {process.candidate_sent_to || process.candidate_email} on {new Date(process.candidate_sent_at).toLocaleString()}</span>}
          </p>
          {waitingForCandidate && process.status === "Not Started" && (
            <>
              {isHosted && hostedEmail ? (
                <p className="workspace-note" data-testid="hosted-email-note">Candidate Email: <strong>{hostedEmail}</strong>{applicantModulesText.fromTheirBoardApplication}</p>
              ) : !emailConfirmed && process.extracted_email ? (
                <div className="material-actions" data-testid="extracted-email-confirm">
                  <p className="workspace-note">{recruitmentWorkspaceText.n_weFoundThisEmailAddress}</p>
                  <label className="field" style={{ minWidth: 280 }}><span>Candidate Email</span>
                    <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} data-testid="candidate-email-input" />
                  </label>
                  <button className="button button-back" onClick={() => setEmailConfirmed(true)} data-testid="confirm-email-button">Confirm Email</button>
                </div>
              ) : !emailConfirmed ? (
                <div className="material-actions" data-testid="missing-email-entry">
                  <p className="workspace-note">{recruitmentWorkspaceText.n_weCouldNotConfidentlyFind}</p>
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
                  <label className="field"><span>{applicantModulesText.emailTheSecureFormLink}</span>
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
                <button className="button button-back" disabled={busy} onClick={() => resendReferee(reference.reference_id)} data-testid={`resend-referee-${index + 1}`}>{["Not Sent", "Ready to Contact"].includes(reference.status) ? "Email Reference for Confirmation" : "Resend Reference Request"}</button>
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
      <h3>{recruitmentWorkspaceText.h_backgroundCheckRecord}</h3>
      <p style={{ fontSize: 14, color: "#555" }}>Your organization decides whether a background check or specific clearance is required and carries out its own process. This record simply tracks the status of that process — nothing here performs a check, and no status is ever interpreted as a pass or fail. "References Submitted" means referee details were provided, not that reference checks are complete.</p>
      <p className="workspace-note">{recruitmentWorkspaceText.n_nonprofitBoardBuilderDoesNot}</p>
      <div className="two-col-fields">
        <label className="field"><span>Background check</span><select value={check.status || "Not started"} onChange={(event) => setCheck({ ...check, status: event.target.value })} data-testid="background-status">{["Not Required", "Not started", "Pending", "In progress", "Completed", "Follow-up required"].map((option) => <option key={option}>{option}</option>)}</select></label>
        <label className="field"><span>Requested date</span><input value={check.requested_date || ""} onChange={(event) => setCheck({ ...check, requested_date: event.target.value })} /></label>
        <label className="field"><span>Completed date</span><input value={check.completed_date || ""} onChange={(event) => setCheck({ ...check, completed_date: event.target.value })} /></label>
      </div>
      <label className="field"><span>Notes</span><textarea rows="2" value={check.notes || ""} onChange={(event) => setCheck({ ...check, notes: event.target.value })} /></label>
      <button className="button button-back" onClick={saveCheck} data-testid="save-background-button">{applicantModulesText.saveBackgroundCheckRecord}</button>
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

export const BrandingPanel = ({ branding, setBranding, heading = "Document Branding", description = "Confirm the logo and brand colors used when designing your final documents. If you leave the colors empty, a professional neutral template is used. Nothing is applied without your confirmation here." }) => {
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
      <h3>{heading}</h3>
      <p className="material-description">{description}</p>
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
      <h3>{recruitmentWorkspaceText.h_boardMemberProfileForm}</h3>
      <p className="material-description">{recruitmentWorkspaceText.d_collectTheProfessionalInformationSkills}</p>
      {!form ? (
        <button className="button" onClick={load} data-testid="generate-board-profile-form">{applicantModulesText.createBoardMemberProfileForm}</button>
      ) : (
        <>
          <p className="member-success">{applicantModulesText.boardMemberProfileFormIs}</p>
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

const TIMEZONES = ["Eastern Time (ET)", "Central Time (CT)", "Mountain Time (MT)", "Pacific Time (PT)", "Alaska Time", "Hawaii Time", "UTC", "Other"];

const OnboardingSessionPanel = ({ session, setSession }) => {
  const [message, setMessage] = useState("");
  const save = async () => {
    await memberApi.put("/workspace/onboarding-session", session);
    setMessage("Onboarding session saved. It is reused automatically for every candidate joining this session.");
  };
  return (
    <div className="detail-section" data-testid="onboarding-session-panel">
      <div className="two-col-fields">
        <label className="field"><span>{applicantModulesText.whatDateWouldYouLike}</span><input type="date" value={session.date || ""} onChange={(event) => setSession({ ...session, date: event.target.value })} data-testid="session-date" /></label>
        <label className="field"><span>{applicantModulesText.whatTimeWouldYouLike}</span><input type="time" value={session.time || ""} onChange={(event) => setSession({ ...session, time: event.target.value })} data-testid="session-time" /></label>
        <label className="field"><span>{applicantModulesText.whatTimezoneShouldWeUse}</span>
          <select value={TIMEZONES.includes(session.timezone) ? session.timezone : (session.timezone ? "Other" : "")} onChange={(event) => setSession({ ...session, timezone: event.target.value === "Other" ? (TIMEZONES.includes(session.timezone) ? "" : session.timezone || "") || "Other" : event.target.value })} data-testid="session-timezone">
            <option value="">Select timezone</option>{TIMEZONES.map((zone) => <option key={zone}>{zone}</option>)}
          </select>
        </label>
        <label className="field"><span>{applicantModulesText.howWillTheOnboardingSession}</span><select value={session.format || ""} onChange={(event) => setSession({ ...session, format: event.target.value })} data-testid="session-format"><option value="">Select</option>{["Virtual", "In Person", "Hybrid"].map((option) => <option key={option}>{option}</option>)}</select></label>
        {(session.format === "Virtual" || session.format === "Hybrid") && <label className="field"><span>{applicantModulesText.whatMeetingLinkShouldWe}</span><input value={session.link || ""} onChange={(event) => setSession({ ...session, link: event.target.value })} data-testid="session-link" /></label>}
        {(session.format === "In Person" || session.format === "Hybrid") && <label className="field"><span>{applicantModulesText.whereWillTheOnboardingSession}</span><input value={session.location || ""} onChange={(event) => setSession({ ...session, location: event.target.value })} data-testid="session-location" /></label>}
      </div>
      <label className="field"><span>{applicantModulesText.isThereAnythingYouWould}</span><textarea rows="2" value={session.prepare || ""} onChange={(event) => setSession({ ...session, prepare: event.target.value })} data-testid="session-prepare" /></label>
      <button className="button button-back" onClick={save} data-testid="save-session-button">Save Onboarding Session</button>
      {message && <p className="member-success">{message}</p>}
    </div>
  );
};

const ConditionalPanel = ({ application, orgMaterials, session, onChanged, profileReady }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  return (
    <div className="detail-section" data-testid="conditional-panel">
      <h3>Prepare Conditional Appointment — {application.profile_snapshot?.full_name}</h3>
      <MaterialCard type="conditional_offer" title={applicantModulesText.conditionalBoardAppointmentEmail} buttonLabel="Generate Conditional Board Appointment Email"
        description="One professional conditional appointment email containing the onboarding date, Organization Overview, Board Manual, three secure agreement links and the Board Member Profile Form link. The reference check must be complete and every onboarding resource must be approved before this email can be generated."
        applicationId={application.application_id} material={byType.conditional_offer} refresh={refresh} approvable
        extraActions={byType.conditional_offer?.status === "Approved" ? (
          <SendMaterialButton type="conditional_offer" applicationId={application.application_id}
            label={application.emails_sent?.conditional_offer ? "Send Updated Appointment Information" : `Send Conditional Appointment to ${application.applicant_email || "candidate"}`}
            sentAt={application.emails_sent?.conditional_offer} onSent={onChanged} />
        ) : null} />
      <MaterialCard type="after_interview_rejection" title={applicantModulesText.afterInterviewRejectionEmail} buttonLabel="Generate After-Interview Rejection Email"
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
  const signatureRecord = (type) => signatures.find((s) => s.agreement_type === type);
  const signatureStatus = (type) => {
    const record = signatureRecord(type);
    if (!record) return "Not Sent";
    if (record.status === "Signed") return "Signed";
    return record.status === "Sent" ? "Sent" : "Ready to Send";
  };
  const copyLink = async (token) => {
    await navigator.clipboard?.writeText(`${window.location.origin}/sign/${token}`);
  };
  return (
    <ul className="readiness-list" data-testid="candidate-status-list">
      <li className={application.reference_check_status === "Completed" ? "done" : ""}>Reference Check: {application.reference_check_status || "Not Started"}</li>
      <li className={["Completed", "Not Required"].includes(application.background_check?.status) ? "done" : ""}>Background Check: {application.background_check?.status || "Not recorded"}</li>
      {AGREEMENTS.map(([type, title]) => {
        const record = signatureRecord(type);
        return (
          <li key={type} className={signatureStatus(type) === "Signed" ? "done" : ""}>
            {title}: {signatureStatus(type)}
            {record && record.status !== "Signed" && record.token && (
              <button className="link-button" onClick={() => copyLink(record.token)} data-testid={`copy-sign-link-${type}`} style={{ marginLeft: 8 }}>{applicantModulesText.copyReviewAmpSignLink}</button>
            )}
          </li>
        );
      })}
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
          <button className="button button-back button-small" disabled={busyId === application.application_id} onClick={() => onDecision(application.application_id, "do_not_move_forward")} data-testid={`do-not-move-forward-${application.application_id}`}>{applicantModulesText.doNotMoveForward}</button>
        )}
      </div>
    </div>
  );
};

export const Module5References = () => {
  const { applications, refresh: refreshApps } = useApplications();
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  const [branding] = useBranding();
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
  const [profileReady, setProfileReady] = useState(false);
  useEffect(() => {
    if (!detail?.application_id) { setProfileReady(false); return; }
    memberApi.get(`/workspace/board-profile-link/${detail.application_id}`)
      .then((r) => setProfileReady(Boolean(r.data?.link)))
      .catch(() => setProfileReady(false));
  }, [detail?.application_id, detail?.updated_at]);

  return (
    <div data-testid="module5-workspace">
      <section className="workspace-panel" data-testid="module5-background-check-section">
        <h2>{recruitmentWorkspaceText.h_backgroundCheck}</h2>
        <p className="material-description">{recruitmentWorkspaceText.d_nonprofitBoardBuilderDoesNot}</p>
        <div className="material-actions">
          <button className="button" onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(`background check providers near ${location || "me"}`)}`, "_blank", "noopener")} data-testid="background-check-search-button">{applicantModulesText.findBackgroundCheckProvidersNear}</button>
        </div>
      </section>
      <section className="workspace-panel" data-testid="module5-decide-forward-section">
        <h2>{recruitmentWorkspaceText.h_decideWhoMovesForward}</h2>
        <p className="material-description">{recruitmentWorkspaceText.d_reviewTheApplicantsYouInterviewed}</p>
        {sorted.length === 0 && <p className="workspace-note" data-testid="no-candidates-note">{applicantModulesText.yourApplicantsFromStep4}</p>}
        {sorted.map((application) => (
          <CandidateDecisionCard key={application.application_id} application={application} selected={selectedId === application.application_id} onSelect={setSelectedId} onDecision={decide} busyId={busyId} />
        ))}
        {detail && (
          <div className="candidate-progress" data-testid="candidate-progress">
            <h3>{detail.profile_snapshot?.full_name || detail.applicant_email} — <span data-testid="candidate-progress-status">{detail.status}</span></h3>
            {(movingForward || !notMovingForward) && <ReferenceProcessPanel application={detail} key={`ref-${detail.application_id}`} />}
          </div>
        )}
      </section>

      <section className="workspace-panel" data-testid="module5-prepare-section">
        <h2>{recruitmentWorkspaceText.h_prepareYourNewBoardMember}</h2>
        <p className="material-description">{recruitmentWorkspaceText.d_prepareTheDocumentsAndInformation}</p>
        <ul className="readiness-list" data-testid="prepare-status-list">
          {PREPARE_TOOLS.map(([type, title]) => <li key={type} className={docStage(orgMaterials[type]) === "Approved" ? "done" : ""}>{title}: {docStage(orgMaterials[type])}</li>)}
        </ul>
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
        <h2>{recruitmentWorkspaceText.h_scheduleTheBoardOnboardingSession}</h2>
        <p className="material-description">{recruitmentWorkspaceText.d_chooseWhenYouWouldLike}</p>
        <OnboardingSessionPanel session={session} setSession={setSession} />
        {!detail && <p className="workspace-note">{recruitmentWorkspaceText.n_chooseACandidateAboveTo}</p>}
        {detail && <ConditionalPanel application={detail} orgMaterials={orgMaterials} session={session} onChanged={onChanged} profileReady={profileReady} key={`dec-${detail.application_id}`} />}
      </section>
    </div>
  );
};

export const AutomatedReferenceChecks = () => {
  const { applications, refresh: refreshApps } = useApplications();
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  const [busyId, setBusyId] = useState("");
  const loadDetail = useCallback(() => {
    if (!selectedId) { setDetail(null); return; }
    memberApi.get(`/workspace/applications/${selectedId}`).then((response) => setDetail(response.data.application));
  }, [selectedId]);
  useEffect(() => { loadDetail(); }, [loadDetail]);
  const decide = async (applicationId, decision) => {
    setBusyId(applicationId);
    try {
      await memberApi.post(`/workspace/applications/${applicationId}/decision`, { decision });
      setSelectedId(applicationId);
      await refreshApps();
      loadDetail();
    } catch { window.alert("The decision could not be saved."); }
    setBusyId("");
  };
  const sorted = [...applications].sort((a, b) => Number(Boolean(b.interview_completed)) - Number(Boolean(a.interview_completed)));
  const eligible = detail && !["Not Moving Forward", "Not Selected"].includes(detail.status);
  return (
    <div data-testid="automated-reference-workspace">
      <section className="workspace-panel">
        <h2>Automated Reference Check</h2>
        <p className="material-description">Choose the applicant you want to move forward. The platform emails the secure reference form, collects two professional referees, sends each referee the confirmation form when you instruct it to and records every response here.</p>
        {sorted.length === 0 && <p className="workspace-note" data-testid="no-reference-candidates">Applicants appear here after they enter your recruitment process.</p>}
        {sorted.map((application) => (
          <CandidateDecisionCard key={application.application_id} application={application} selected={selectedId === application.application_id} onSelect={setSelectedId} onDecision={decide} busyId={busyId} />
        ))}
        {detail && eligible && <ReferenceProcessPanel application={detail} key={`automated-ref-${detail.application_id}`} />}
        {detail && !eligible && <p className="workspace-note">This applicant is not moving forward, so a reference check is not required.</p>}
      </section>
    </div>
  );
};

export const OnboardingPreparation = () => {
  const { applications } = useApplications();
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  const [branding] = useBranding();
  const [session, setSession] = useState({});
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  useEffect(() => {
    memberApi.get("/workspace/onboarding-session").then((response) => setSession(response.data.session || {})).catch(() => {});
  }, []);
  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    memberApi.get(`/workspace/applications/${selectedId}`).then((response) => setDetail(response.data.application));
  }, [selectedId]);
  const candidates = applications.filter((application) => application.reference_check_status === "Completed"
    || ["Conditional Appointment", "Selected"].includes(application.status)
    || application.final_outcome === "Joined Board");
  const onChanged = () => memberApi.get(`/workspace/applications/${selectedId}`).then((response) => setDetail(response.data.application));
  return (
    <div data-testid="onboarding-preparation-workspace">
      <section className="workspace-panel" data-testid="onboarding-date-section">
        <h2>Set The Onboarding Date</h2>
        <p className="material-description">Save the date and delivery details once. These details are inserted into the conditional appointment email automatically.</p>
        <OnboardingSessionPanel session={session} setSession={setSession} />
      </section>
      <section className="workspace-panel" data-testid="onboarding-materials-section">
        <h2>Generate The Onboarding Materials</h2>
        <p className="material-description">Generate and approve the Organization Overview, Board Manual, three agreements and Board Member Profile Form before preparing the conditional appointment email.</p>
        <ul className="readiness-list" data-testid="prepare-status-list">
          {PREPARE_TOOLS.map(([type, title]) => <li key={type} className={docStage(orgMaterials[type]) === "Approved" ? "done" : ""}>{title}: {docStage(orgMaterials[type])}</li>)}
        </ul>
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
      <section className="workspace-panel" data-testid="conditional-offer-section">
        <h2>Send The Conditional Appointment Email</h2>
        <p className="material-description">Select a candidate whose automated reference check is complete. Their email will carry every approved onboarding link and the saved onboarding date.</p>
        {candidates.length === 0 && <p className="workspace-note">Candidates appear here when their automated reference check is complete.</p>}
        {candidates.map((application) => (
          <button className={`button ${selectedId === application.application_id ? "" : "button-back"}`} style={{ marginRight: 8, marginBottom: 8 }} key={application.application_id} onClick={() => setSelectedId(application.application_id)} data-testid={`select-onboarding-candidate-${application.application_id}`}>
            {application.profile_snapshot?.full_name || application.applicant_email}
          </button>
        ))}
        {detail && <ConditionalPanel application={detail} orgMaterials={orgMaterials} session={session} onChanged={onChanged} profileReady key={`conditional-${detail.application_id}`} />}
      </section>
    </div>
  );
};

export const OnboardingFacilitationGuide = () => {
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  return (
    <div data-testid="onboarding-guide-workspace">
      <MaterialCard type="onboarding_script" title={applicantModulesText.boardMemberOnboardingFacilitatorGuide} buttonLabel="Generate Onboarding Facilitation Guide"
        description="A complete read-through guide for leading the onboarding session, reviewing expectations, discussing how each new board member will contribute and recording the responsibilities agreed during the conversation."
        material={orgMaterials.onboarding_script} refresh={refreshOrg} approvable />
    </div>
  );
};

// ---------- Module 6 ----------

const AGREEMENTS = [["board_member_agreement", "Board Member Agreement"], ["confidentiality_agreement", "Confidentiality Agreement"], ["conflict_of_interest_agreement", "Conflict of Interest Agreement"]];

const OnboardingConclusionPanel = ({ application }) => {
  const empty = { board_role: "", agreed_primary_contribution_area: "", agreed_responsibility: "", agreed_leadership: "", how_their_experience_will_be_used: "", organization_support_agreed: "", immediate_next_steps: "", private_notes: "" };
  const [form, setForm] = useState(empty);
  const [savedAt, setSavedAt] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    memberApi.get(`/workspace/applications/${application.application_id}/onboarding-conclusion`).then((response) => {
      setForm({ ...empty, ...(response.data.conclusion || {}), board_role: response.data.board_role || "" });
      setSavedAt(response.data.saved_at || "");
    }).catch(() => {});
  }, [application.application_id]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async () => {
    try {
      const response = await memberApi.put(`/workspace/applications/${application.application_id}/onboarding-conclusion`, form);
      setSavedAt(response.data.saved_at || new Date().toISOString());
      setMessage("Onboarding conclusion saved. The Board Member Portfolio can now use the responsibilities you agreed together.");
    } catch (error) { setMessage(error.response?.data?.detail || "The onboarding conclusion could not be saved."); }
  };
  const field = (name, label) => (
    <label className="field"><span>{label}</span><textarea rows="2" value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} data-testid={`onboarding-conclusion-${name}`} /></label>
  );
  return (
    <div className="detail-section" data-testid={`onboarding-conclusion-${application.application_id}`}>
      <h3>Record The Onboarding Conclusion</h3>
      <p className="material-description">Save what you and this board member agreed during onboarding. This becomes the authoritative basis for their Board Member Portfolio.</p>
      <label className="field"><span>Board Role</span><input value={form.board_role} onChange={(event) => setForm({ ...form, board_role: event.target.value })} data-testid="onboarding-conclusion-board-role" /></label>
      {field("agreed_primary_contribution_area", "Primary Contribution Area")}
      {field("agreed_responsibility", "Responsibility Agreed")}
      {field("agreed_leadership", "Leadership Agreed")}
      {field("how_their_experience_will_be_used", "How Their Experience Will Be Used")}
      {field("organization_support_agreed", "Support The Organization Agreed To Provide")}
      {field("immediate_next_steps", "Immediate Next Steps")}
      <button className="button button-back" onClick={save} data-testid="save-onboarding-conclusion">Save Onboarding Conclusion</button>
      {savedAt && <p className="material-meta">Saved {new Date(savedAt).toLocaleString()}</p>}
      {message && <p className="member-success">{message}</p>}
    </div>
  );
};

const MemberReadiness = ({ application, onChanged }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const [signatures, setSignatures] = useState([]);
  const [profileLink, setProfileLink] = useState(null);
  useEffect(() => {
    memberApi.get("/workspace/signatures", { params: { application_id: application.application_id } }).then((r) => setSignatures(r.data.signatures)).catch(() => {});
    memberApi.get(`/workspace/board-profile-link/${application.application_id}`).then((r) => setProfileLink(r.data)).catch(() => {});
  }, [application.application_id]);
  const signatureStatus = (type) => (signatures.find((s) => s.agreement_type === type) || {}).status || "Not Sent";
  const joined = application.final_outcome === "Joined Board";
  const confirmed = joined || application.status === "Selected";
  const refsDone = application.reference_check_status === "Completed";
  const agreementsSigned = AGREEMENTS.every(([type]) => signatureStatus(type) === "Signed");
  const profileDone = Boolean(profileLink?.response);
  const readyForAppointment = refsDone && agreementsSigned && profileDone;
  const confirmFormal = async () => {
    if (!window.confirm(`Formally confirm ${application.profile_snapshot?.full_name}'s appointment to the Board? You control this decision — it is never automatic.`)) return;
    try {
      await memberApi.patch(`/workspace/applications/${application.application_id}`, { status: "Selected" });
      if (onChanged) onChanged();
    } catch { window.alert("The confirmation could not be saved. Please try again."); }
  };
  return (
    <div className="onboarding-applicant" data-testid={`onboarding-${application.application_id}`}>
      <h3><UserCheck size={17} /> {application.profile_snapshot?.full_name} {joined && <span className="blog-status-badge published">Board Member</span>}{!joined && confirmed && <span className="blog-status-badge published">Formal Appointment Confirmed</span>}</h3>
      <ul className="readiness-list" data-testid="member-readiness">
        <li className={refsDone ? "done" : ""}>Reference Process: {application.reference_check_status || "Not Started"}{application.reference_check_status === "References Submitted" ? " (submitted is not completed — finish the reference process)" : ""}</li>
        {AGREEMENTS.map(([type, title]) => <li key={type} className={signatureStatus(type) === "Signed" ? "done" : ""}>{title}: {signatureStatus(type)}</li>)}
        <li className={profileLink?.response ? "done" : ""}>Board Member Profile: {profileLink?.response ? "Completed" : profileLink?.link ? "Sent" : "Not Sent"}</li>
      </ul>
      {!confirmed && (
        <>
          <button className="button" disabled={!readyForAppointment} onClick={confirmFormal} data-testid="confirm-ready-button">Confirm Formal Appointment</button>
          {!readyForAppointment && <p className="workspace-note" data-testid="formal-appointment-blocked-note">Formal Appointment becomes available after the automated reference check is complete, all three agreements are signed and the Board Member Profile Form is completed.</p>}
        </>
      )}
      {confirmed && (
        <>
          <OnboardingConclusionPanel application={application} />
          <MaterialCard type="formal_appointment_letter" title="Formal Board Appointment Letter" buttonLabel="Generate Formal Appointment Letter"
            description="The organization's formal written confirmation of this appointment — a professional letter with your organization details, the issue date, the member's details and an authorized signatory block. Approve it and its secure view link is included in the Final Appointment Email."
            applicationId={application.application_id} material={byType.formal_appointment_letter} refresh={refresh} approvable
            extraActions={byType.formal_appointment_letter ? (
              <button className="button button-back" onClick={() => downloadMaterialPdf(byType.formal_appointment_letter)} data-testid={`letter-pdf-${application.application_id}`}><Download size={14} /> Download PDF</button>
            ) : null} />
          <MaterialCard type="formal_appointment_email" title={applicantModulesText.formalBoardAppointmentEmail} buttonLabel="Generate Final Board Appointment Email"
            description="Formally confirms the appointment, welcomes them to the board and delivers the approved onboarding resources — the Formal Appointment Letter link, documents to review and agreements to sign. Only APPROVED documents are linked; unapproved ones are omitted until you approve them."
            applicationId={application.application_id} material={byType.formal_appointment_email} refresh={refresh} approvable
            extraActions={byType.formal_appointment_email?.status === "Approved" ? (
              <SendMaterialButton type="formal_appointment_email" applicationId={application.application_id}
                label={application.emails_sent?.formal_appointment_email ? "Send Updated" : `Send to ${application.applicant_email || "candidate"}`}
                sentAt={application.emails_sent?.formal_appointment_email} onSent={onChanged} />
            ) : null} />
        </>
      )}
    </div>
  );
};

const FirstMeetingPanel = ({ orgMaterials, refreshOrg, boardMembers }) => {
  const [meeting, setMeeting] = useState({ date: "", time: "", timezone: "", format: "", link: "", location: "", meeting_id: "", passcode: "", chat_link: "", instructions: "" });
  const [recipients, setRecipients] = useState([]);
  const [message, setMessage] = useState("");
  useEffect(() => { memberApi.get("/workspace/first-meeting").then((r) => { if (r.data.first_meeting?.date) setMeeting((c) => ({ ...c, ...r.data.first_meeting })); }).catch(() => {}); }, []);
  useEffect(() => { setRecipients(boardMembers.map((m) => m.application_id)); }, [boardMembers]);
  const toggle = (id) => setRecipients((current) => current.includes(id) ? current.filter((x) => x !== id) : [...current, id]);
  const material = orgMaterials.first_board_meeting_invitation;
  const saveMeeting = async () => {
    if (!meeting.date.trim() || !meeting.time.trim() || !meeting.timezone.trim()) { setMessage("Meeting date, time and timezone are required."); return false; }
    await memberApi.put("/workspace/first-meeting", meeting);
    setMessage("");
    return true;
  };
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
      <h2>{recruitmentWorkspaceText.h_yourFirstBoardMeeting}</h2>
      <p className="material-description">{recruitmentWorkspaceText.d_thisMeetingIsTheTransition}</p>
      <div className="two-col-fields">
        <label className="field"><span>Meeting Date <b>*</b></span><input value={meeting.date} onChange={(event) => setMeeting({ ...meeting, date: event.target.value })} data-testid="meeting-date" /></label>
        <label className="field"><span>Meeting Time <b>*</b></span><input value={meeting.time} onChange={(event) => setMeeting({ ...meeting, time: event.target.value })} data-testid="meeting-time" /></label>
        <label className="field"><span>Timezone <b>*</b></span><input value={meeting.timezone} onChange={(event) => setMeeting({ ...meeting, timezone: event.target.value })} data-testid="meeting-timezone" /></label>
        <label className="field"><span>Format</span><select value={meeting.format} onChange={(event) => setMeeting({ ...meeting, format: event.target.value })}><option value="">Select</option>{["Virtual", "In Person", "Hybrid"].map((option) => <option key={option}>{option}</option>)}</select></label>
        {(meeting.format === "Virtual" || meeting.format === "Hybrid") && <label className="field"><span>Meeting Link (optional)</span><input value={meeting.link} onChange={(event) => setMeeting({ ...meeting, link: event.target.value })} data-testid="meeting-link" /></label>}
        {(meeting.format === "In Person" || meeting.format === "Hybrid") && <label className="field"><span>Location</span><input value={meeting.location} onChange={(event) => setMeeting({ ...meeting, location: event.target.value })} data-testid="meeting-location" /></label>}
        <label className="field"><span>Meeting ID (optional)</span><input value={meeting.meeting_id} onChange={(event) => setMeeting({ ...meeting, meeting_id: event.target.value })} data-testid="meeting-id" /></label>
        <label className="field"><span>Passcode (optional)</span><input value={meeting.passcode} onChange={(event) => setMeeting({ ...meeting, passcode: event.target.value })} data-testid="meeting-passcode" /></label>
        <label className="field"><span>{applicantModulesText.meetingChatLinkOptional}</span><input value={meeting.chat_link} onChange={(event) => setMeeting({ ...meeting, chat_link: event.target.value })} data-testid="meeting-chat" /></label>
      </div>
      <label className="field"><span>Additional Instructions (optional)</span><textarea rows="2" value={meeting.instructions} onChange={(event) => setMeeting({ ...meeting, instructions: event.target.value })} data-testid="meeting-prepare" /></label>
      <MaterialCard type="first_board_meeting_invitation" title={applicantModulesText.firstBoardMeetingInvitationEmail} buttonLabel="Generate First Board Meeting Invitation"
        description="One professional email inviting your new board members to their first Board Meeting — the moment recruitment becomes active board participation. Meeting details are saved once and inserted automatically; a Board Member Profile reminder appears only for members who have not completed theirs. Nothing is sent automatically."
        material={material} refresh={refreshOrg} approvable beforeGenerate={saveMeeting} />
      {material?.status === "Approved" && boardMembers.length > 0 && (
        <div className="detail-section" data-testid="first-meeting-recipients">
          <h3>{recruitmentWorkspaceText.h_recipientsFormallyAppointedBoardMembers}</h3>
          {boardMembers.map((member) => (
            <label className="checkbox-field" key={member.application_id}>
              <input type="checkbox" checked={recipients.includes(member.application_id)} onChange={() => toggle(member.application_id)} data-testid={`recipient-${member.application_id}`} />
              <span>{member.profile_snapshot?.full_name} — {member.applicant_email || "no email on record"}</span>
            </label>
          ))}
          <div className="material-actions">
            <button className="button" disabled={!recipients.length} onClick={() => send(false)} data-testid="send-first-meeting-button">{applicantModulesText.sendFirstBoardMeetingInvitation}</button>
            <button className="button button-back" disabled={!recipients.length} onClick={() => send(true)} data-testid="send-updated-meeting-button">{applicantModulesText.sendUpdatedMeetingInformation}</button>
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
        <span className="signature-status"><strong>{title}</strong> — {version ? (material.status === "Approved" ? "Approved" : "Draft") : "Not yet generated — prepare it in Step 5"}</span>
        {version && <button className="button button-back" onClick={() => printBranded(title, version.display_text, branding)} data-testid={`view-prepared-${type}`}><Download size={14} /> Open PDF</button>}
      </div>
    </div>
  );
};

export const Module6Onboarding = () => {
  const { applications, refresh } = useApplications();
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  const boardMembers = applications.filter((a) => a.final_outcome === "Joined Board");
  const appointmentStage = applications.filter((a) => a.final_outcome === "Joined Board"
    || ["Moving Forward", "Conditional Appointment", "Selected"].includes(a.status));
  return (
    <div data-testid="module6-workspace">
      {appointmentStage.length > 0 && (
        <section className="workspace-panel" data-testid="module6-formal-appointment-section">
          <h2>Formal Appointment</h2>
          <p className="material-description">Once the applicable reference process is Completed (submitted referee details are not enough) and any required background check is complete, you — never the system — confirm each candidate's Formal Appointment. That unlocks their Formal Board Appointment Letter and Final Board Appointment Email.</p>
          {appointmentStage.map((application) => (
            <MemberReadiness application={application} onChanged={refresh} key={application.application_id} />
          ))}
        </section>
      )}
      <section className="workspace-panel" data-testid="module6-script-section">
        <h2>{recruitmentWorkspaceText.h_prepareForYourBoardOnboarding}</h2>
        <MaterialCard type="onboarding_script" title={applicantModulesText.boardMemberOnboardingFacilitatorGuide} buttonLabel="Generate Onboarding Facilitation Guide"
          description="A complete read-through facilitation guide you can have open during the onboarding session — with the actual words to say for the welcome, the organization story, the role of the Board, the strengths-and-contribution discussion, the documents review and closing, plus after-session actions including recording each member's Onboarding Conclusion / Role Agreement."
          material={orgMaterials.onboarding_script} refresh={refreshOrg} approvable />
      </section>

      <FirstMeetingPanel orgMaterials={orgMaterials} refreshOrg={refreshOrg} boardMembers={boardMembers} />
    </div>
  );
};

export const FormalAppointmentWorkspace = () => {
  const { applications, refresh } = useApplications();
  const candidates = applications.filter((application) => application.reference_check_status === "Completed"
    || ["Conditional Appointment", "Selected"].includes(application.status)
    || application.final_outcome === "Joined Board");
  return (
    <div data-testid="formal-appointment-workspace">
      {candidates.length === 0 && <p className="workspace-note">Candidates appear here after their automated reference check is complete.</p>}
      {candidates.map((application) => <MemberReadiness application={application} onChanged={refresh} key={application.application_id} />)}
    </div>
  );
};

export const FirstBoardMeetingWorkspace = () => {
  const { applications } = useApplications();
  const { byType: orgMaterials, refresh: refreshOrg } = useMaterials();
  const boardMembers = applications.filter((application) => application.final_outcome === "Joined Board" || application.status === "Selected");
  return <FirstMeetingPanel orgMaterials={orgMaterials} refreshOrg={refreshOrg} boardMembers={boardMembers} />;
};
