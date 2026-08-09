import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "@/funnels/FunnelLayout";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const chunkQuestions = (questions, size = 6) => {
  const steps = [];
  for (let index = 0; index < questions.length; index += size) steps.push(questions.slice(index, index + size));
  return steps;
};

export const ApplicationForm = ({ questions, initialAnswers = {}, submitLabel, onSubmit, requireCv = true }) => {
  const steps = useMemo(() => chunkQuestions(questions), [questions]);
  const totalSteps = steps.length + (requireCv ? 1 : 0);
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState(() => {
    const initial = {};
    questions.forEach((question) => { initial[question.id] = initialAnswers[question.id] || ""; });
    return initial;
  });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const cvRef = useRef(null);

  const validate = () => {
    const found = {};
    if (stepIndex < steps.length) {
      steps[stepIndex].forEach((question) => {
        if (question.required !== false && !String(answers[question.id] || "").trim()) found[question.id] = "This field is required.";
      });
    } else if (requireCv && !cvRef.current?.files?.length) {
      found.cv = "Please upload your résumé/CV (PDF, DOC or DOCX).";
    }
    setErrors(found);
    return !Object.keys(found).length;
  };

  const next = async () => {
    if (!validate()) return;
    if (stepIndex < totalSteps - 1) { setStepIndex(stepIndex + 1); window.scrollTo({ top: 0, behavior: "smooth" }); return; }
    setBusy(true); setSubmitError("");
    try { await onSubmit(answers, cvRef.current?.files?.[0] || null); }
    catch (error) { setSubmitError(error.response?.data?.detail || "We could not submit your application. Please try again."); setBusy(false); }
  };

  return (
    <div className="funnel-lead-form step-form public-application-form">
      <div className="step-progress">
        <span className="step-count" data-testid="application-step-count">Step {stepIndex + 1} of {totalSteps}</span>
        <div className="step-progress-bar"><i style={{ width: `${((stepIndex + 1) / totalSteps) * 100}%` }} /></div>
      </div>
      {stepIndex < steps.length ? (
        <div className="step-fields" key={stepIndex}>
          {steps[stepIndex].map((question) => (
            <label className="field" key={question.id} data-testid={`application-${question.id}`}>
              <span>{question.label}{question.required !== false && <b> *</b>}</span>
              {question.type === "textarea" && <textarea rows="3" value={answers[question.id]} onChange={(event) => setAnswers({ ...answers, [question.id]: event.target.value })} />}
              {question.type === "yes_no" && <select value={answers[question.id]} onChange={(event) => setAnswers({ ...answers, [question.id]: event.target.value })}><option value="">Select one</option><option>Yes</option><option>No</option></select>}
              {(question.type === "text" || question.type === "email" || !["textarea", "yes_no"].includes(question.type)) && ["text", "email"].includes(question.type) && <input type={question.type} value={answers[question.id]} onChange={(event) => setAnswers({ ...answers, [question.id]: event.target.value })} />}
              {errors[question.id] && <p className="field-error">{errors[question.id]}</p>}
            </label>
          ))}
        </div>
      ) : (
        <div className="step-fields">
          <label className="field" data-testid="application-cv">
            <span>Upload résumé/CV <b>*</b></span>
            <input type="file" ref={cvRef} accept=".pdf,.doc,.docx" />
            {errors.cv && <p className="field-error">{errors.cv}</p>}
          </label>
        </div>
      )}
      {submitError && <p className="submit-error" data-testid="application-submit-error">{submitError}</p>}
      <div className="step-actions">
        {stepIndex > 0 ? <button type="button" className="button button-back" onClick={() => setStepIndex(stepIndex - 1)} data-testid="application-back"><ArrowLeft size={15} /> Back</button> : <span />}
        <button type="button" className="button funnel-submit" disabled={busy} onClick={next} data-testid={stepIndex === totalSteps - 1 ? "application-submit" : "application-continue"}>
          {busy ? "Submitting…" : stepIndex === totalSteps - 1 ? submitLabel : <>Continue <ArrowRight size={15} /></>}
        </button>
      </div>
    </div>
  );
};

const SubmittedScreen = ({ organizationName, supporting }) => (
  <section className="workspace-panel application-submitted" data-testid="application-submitted">
    <CheckCircle2 size={34} />
    <h1>Your Application Has Been Submitted</h1>
    <p>{supporting || `Your application has been submitted to ${organizationName} for consideration. Completing an application does not guarantee an interview or board appointment.`}</p>
    <p className="workspace-note">Would you like to create a Board Applicant profile so we can notify you about future nonprofit board opportunities? <a href="/join-a-board">Join the Board Applicant Network</a></p>
  </section>
);

export const OpportunityApplyPage = () => {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  useEffect(() => {
    axios.get(`${API}/public/board-opportunities/${slug}`).then((response) => setData(response.data)).catch((err) => setError(err.response?.status === 410 ? "Applications Closed" : "This board opportunity could not be found."));
  }, [slug]);
  const submit = async (answers, cv) => {
    const form = new FormData();
    form.append("payload", JSON.stringify(answers));
    if (cv) form.append("cv", cv);
    await axios.post(`${API}/public/board-opportunities/${slug}/apply`, form);
    setSubmitted(true);
  };
  return (
    <FunnelLayout>
      <main className="member-page public-opportunity-page" data-testid="public-opportunity-page">
        {error && <div className="member-card"><h2 data-testid="opportunity-error">{error}</h2></div>}
        {data && !submitted && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">Nonprofit board opportunity</p>
              <h1 data-testid="public-org-name">{data.organization_name} Is Recruiting New Board Members</h1>
              {data.mission && <p><strong>Mission:</strong> {data.mission}</p>}
            </header>
            {data.status === "Closed" ? (
              <div className="member-card" data-testid="applications-closed"><h2>Applications Closed</h2><p>This recruitment campaign is no longer accepting applications.</p></div>
            ) : (
              <>
                <section className="workspace-panel">
                  <h2>The Board Opportunity</h2>
                  <pre className="material-display" data-testid="public-opportunity-display">{data.opportunity_display}</pre>
                  <dl className="opportunity-facts">
                    {data.candidate_profiles?.length > 0 && <div><dt>Especially looking for</dt><dd>{data.candidate_profiles.join("; ")}</dd></div>}
                    <div><dt>Time commitment</dt><dd>{data.time_commitment || "—"} {data.meeting_structure ? `· ${data.meeting_structure}` : ""}</dd></div>
                    <div><dt>Location</dt><dd>{data.geographic_requirements || "—"}</dd></div>
                    <div><dt>Application deadline</dt><dd data-testid="public-deadline">{data.application_deadline || "Open until positions are filled"}</dd></div>
                  </dl>
                </section>
                <section className="workspace-panel">
                  <h2>Apply to Join the Board</h2>
                  <ApplicationForm questions={[...data.core_questions, ...data.custom_questions.map((question) => ({ ...question, required: false }))]} submitLabel="Submit My Board Application" onSubmit={submit} />
                </section>
              </>
            )}
          </>
        )}
        {submitted && <SubmittedScreen organizationName={data?.organization_name} />}
      </main>
    </FunnelLayout>
  );
};

export const SavedProfileApplyPage = () => {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [mode, setMode] = useState("confirm");
  const [updateProfile, setUpdateProfile] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    axios.get(`${API}/public/apply/${token}`).then((response) => setData(response.data)).catch((err) => setError(err.response?.status === 410 ? "Applications Closed" : "This application link is not valid."));
  }, [token]);
  const confirm = async () => {
    setBusy(true); setError("");
    try { const response = await axios.post(`${API}/public/apply/${token}/confirm`); setResult(response.data); }
    catch (err) { setError(err.response?.data?.detail || "We could not submit your application."); }
    setBusy(false);
  };
  const submitUpdated = async (answers, cv) => {
    const form = new FormData();
    form.append("payload", JSON.stringify({ answers, update_profile: updateProfile }));
    if (cv) form.append("cv", cv);
    const response = await axios.post(`${API}/public/apply/${token}/apply-updated`, form);
    setResult(response.data);
  };
  const profile = data?.profile || {};
  return (
    <FunnelLayout>
      <main className="member-page public-opportunity-page" data-testid="saved-profile-apply-page">
        {error && !result && <div className="member-card"><h2 data-testid="apply-token-error">{error}</h2></div>}
        {result && <SubmittedScreen organizationName={data?.opportunity?.organization_name} supporting={result.supporting} />}
        {data && !result && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">Board Applicant Network</p>
              <h1 data-testid="apply-heading">Apply to Join the Board of {data.opportunity.organization_name}</h1>
            </header>
            {data.already_applied && <div className="member-card" data-testid="already-applied"><h2>You Have Already Applied</h2><p>An application from your profile has already been submitted for this opportunity.</p></div>}
            {!data.already_applied && mode === "confirm" && (
              <section className="workspace-panel">
                <h2>Your Professional Profile</h2>
                <dl className="opportunity-facts" data-testid="saved-profile-summary">
                  {[["Name", profile.name], ["Profession", profile.profession], ["Current organization", profile.employer], ["Professional summary", profile.professional_summary], ["Skills", (profile.skills || []).join(", ")], ["Board experience", profile.board_experience], ["Fundraising interests", (profile.fundraising_interests || []).join(", ")], ["Causes", (profile.causes || []).join(", ")], ["Location", profile.location], ["Availability", profile.availability], ["CV on file", profile.cv_filename || "None"]].map(([label, value]) => (
                    <div key={label}><dt>{label}</dt><dd>{value || "—"}</dd></div>
                  ))}
                </dl>
                {error && <p className="submit-error">{error}</p>}
                <div className="material-actions">
                  <button className="button" disabled={busy} onClick={confirm} data-testid="confirm-application-button">Confirm My Application</button>
                  <button className="button button-back" onClick={() => setMode("update")} data-testid="apply-updated-button">Apply With Updated Information</button>
                </div>
              </section>
            )}
            {!data.already_applied && mode === "update" && (
              <section className="workspace-panel">
                <h2>Apply With Updated Information</h2>
                <p className="workspace-note">Update anything that has changed for this opportunity. Fields you leave blank keep your saved profile information. A new CV upload is optional — your saved CV is used otherwise.</p>
                <ApplicationForm
                  questions={[...data.opportunity.core_questions.map((question) => ({ ...question, required: false })), ...data.opportunity.custom_questions.map((question) => ({ ...question, required: false }))]}
                  submitLabel="Submit My Updated Application" onSubmit={submitUpdated} requireCv={false} />
                <label className="choice update-profile-choice">
                  <input type="checkbox" checked={updateProfile} onChange={(event) => setUpdateProfile(event.target.checked)} data-testid="update-profile-checkbox" />
                  <span>Also update my Board Applicant profile with these changes</span>
                </label>
              </section>
            )}
          </>
        )}
      </main>
    </FunnelLayout>
  );
};

export const SignAgreementPage = () => {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ agreed: false, typed_signature: "", email: "", date: new Date().toISOString().slice(0, 10) });
  const [done, setDone] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { axios.get(`${API}/public/sign/${token}`).then((response) => setData(response.data)).catch(() => setError("This signature link is not valid.")); }, [token]);
  const sign = async () => {
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/public/sign/${token}`, form);
      setDone(response.data.message);
    } catch (err) { setError(err.response?.data?.detail || "Your signature could not be recorded."); }
    setBusy(false);
  };
  return (
    <FunnelLayout>
      <main className="member-page public-opportunity-page" data-testid="sign-agreement-page">
        {error && !data && <div className="member-card"><h2>{error}</h2></div>}
        {data && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">{data.organization_name}</p>
              <h1 data-testid="sign-heading">{data.agreement_title}</h1>
              <p>Prepared for {data.board_member_name}</p>
            </header>
            <section className="workspace-panel">
              <pre className="material-display sign-document" data-testid="sign-document">{data.document}</pre>
              {done || data.signed ? (
                <p className="member-success" data-testid="sign-success">{done || "This agreement has already been signed."}</p>
              ) : (
                <div className="sign-form">
                  <label className="choice"><input type="checkbox" checked={form.agreed} onChange={(event) => setForm({ ...form, agreed: event.target.checked })} data-testid="sign-agree-checkbox" /><span>I have read and agree to the document above.</span></label>
                  <div className="two-col-fields">
                    <label className="field"><span>Type your full name <b>*</b></span><input value={form.typed_signature} onChange={(event) => setForm({ ...form, typed_signature: event.target.value })} data-testid="sign-name-input" /></label>
                    <label className="field"><span>Confirm your email <b>*</b></span><input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} data-testid="sign-email-input" /></label>
                    <label className="field"><span>Date <b>*</b></span><input value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} data-testid="sign-date-input" /></label>
                  </div>
                  {error && <p className="submit-error" data-testid="sign-error">{error}</p>}
                  <button className="button" disabled={busy || !form.agreed || !form.typed_signature || !form.email} onClick={sign} data-testid="sign-agreement-button">Sign Agreement</button>
                  <p className="material-meta">This electronic signature process does not constitute legal advice. The organization remains responsible for determining whether its document and signature process meets its legal requirements.</p>
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </FunnelLayout>
  );
};
