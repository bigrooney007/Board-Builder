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
            <header className="member-page-heading apply-header">
              {data.logo_data && <img className="apply-logo" src={data.logo_data} alt={`${data.organization_name} logo`} />}
              <p className="eyebrow">Nonprofit board opportunity</p>
              <h1 data-testid="public-org-name">{data.organization_name}</h1>
              <p className="apply-intro" data-testid="public-apply-intro">{(data.intro_sentences || []).join(" ")}</p>
            </header>
            {data.status === "Closed" ? (
              <div className="member-card" data-testid="applications-closed"><h2>Applications Closed</h2><p>This recruitment campaign is no longer accepting applications.</p></div>
            ) : (
              <section className="workspace-panel">
                <h2>Apply to Join the Board</h2>
                <ApplicationForm questions={[...data.core_questions, ...data.custom_questions.map((question) => ({ ...question, required: false }))]} submitLabel="Submit My Board Application" onSubmit={submit} />
              </section>
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

const SignatureCanvas = ({ onChange }) => {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const point = (event) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const source = event.touches ? event.touches[0] : event;
    return { x: source.clientX - rect.left, y: source.clientY - rect.top };
  };
  const start = (event) => { drawing.current = true; const ctx = canvasRef.current.getContext("2d"); const p = point(event); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const move = (event) => {
    if (!drawing.current) return;
    event.preventDefault();
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineWidth = 2; ctx.lineCap = "round"; ctx.strokeStyle = "#1b1b1b";
    const p = point(event); ctx.lineTo(p.x, p.y); ctx.stroke();
  };
  const end = () => { if (drawing.current) { drawing.current = false; onChange(canvasRef.current.toDataURL("image/png")); } };
  const clear = () => { const canvas = canvasRef.current; canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height); onChange(""); };
  return (
    <div className="signature-canvas-wrap" data-testid="signature-canvas-wrap">
      <canvas ref={canvasRef} width={420} height={140} className="signature-canvas" data-testid="signature-canvas"
        onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
        onTouchStart={start} onTouchMove={move} onTouchEnd={end} />
      <button type="button" className="link-button" onClick={clear} data-testid="signature-clear">Clear signature</button>
    </div>
  );
};

export const SignAgreementPage = () => {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ agreed: false, typed_signature: "", email: "", date: new Date().toISOString().slice(0, 10) });
  const [method, setMethod] = useState("typed");
  const [drawnImage, setDrawnImage] = useState("");
  const [done, setDone] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots"; meta.content = "noindex, nofollow";
    document.head.appendChild(meta);
    return () => document.head.removeChild(meta);
  }, []);
  const load = () => axios.get(`${API}/public/sign/${token}`).then((response) => setData(response.data)).catch(() => setError("This signature link is not valid."));
  useEffect(() => { load(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps
  const sign = async () => {
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/public/sign/${token}`, { ...form, signature_method: method, signature_image: method === "drawn" ? drawnImage : "" });
      setDone(response.data.message);
      await load();
    } catch (err) { setError(err.response?.data?.detail || "Your signature could not be recorded."); }
    setBusy(false);
  };
  const primary = data?.primary_color || "#1d3a2f";
  const signed = Boolean(done || data?.signed);
  return (
    <main className="hosted-agreement-page" data-testid="sign-agreement-page">
      {error && !data && <div className="member-card" style={{ margin: "60px auto", maxWidth: 480 }}><h2>{error}</h2></div>}
      {data && (
        <article className="hosted-agreement" style={{ "--agreement-primary": primary }}>
          <header className="hosted-agreement-head">
            {data.logo_data && <img src={data.logo_data} alt={`${data.organization_name} logo`} className="hosted-agreement-logo" />}
            <p className="hosted-agreement-org" data-testid="sign-org-name">{data.organization_name}</p>
            <h1 data-testid="sign-heading">{data.agreement_title}</h1>
            <p className="hosted-agreement-meta">Prepared for {data.board_member_name}{data.agreement_version ? ` · Version ${data.agreement_version}` : ""}</p>
          </header>
          <div className="hosted-agreement-body" data-testid="sign-document">{data.document}</div>
          {signed ? (
            <section className="hosted-agreement-signed" data-testid="sign-success">
              <h2>Agreement Signed</h2>
              <p>Thank you. Your signed agreement has been submitted to {data.organization_name}.</p>
              {data.signed_record && (
                <div className="signed-record" data-testid="signed-record">
                  <p><strong>Signed by:</strong> {data.signed_record.name}</p>
                  {data.signed_record.signature_image && <img src={data.signed_record.signature_image} alt="Signature" className="signed-signature-image" />}
                  {!data.signed_record.signature_image && <p className="typed-signature-display">{data.signed_record.name}</p>}
                  <p><strong>Date signed:</strong> {data.signed_record.date}{data.signed_record.signed_at ? ` (${new Date(data.signed_record.signed_at).toLocaleString()})` : ""} · Method: {data.signed_record.method === "drawn" ? "Drawn signature" : "Typed signature"}</p>
                </div>
              )}
              <button className="button" onClick={() => window.print()} data-testid="download-signed-copy">Download Copy</button>
            </section>
          ) : (
            <section className="hosted-agreement-sign" data-testid="sign-form">
              <h2>Sign Agreement</h2>
              <label className="choice"><input type="checkbox" checked={form.agreed} onChange={(event) => setForm({ ...form, agreed: event.target.checked })} data-testid="sign-agree-checkbox" /><span>I have read and agree to the terms of this agreement.</span></label>
              <div className="two-col-fields">
                <label className="field"><span>Full legal name <b>*</b></span><input value={form.typed_signature} onChange={(event) => setForm({ ...form, typed_signature: event.target.value })} data-testid="sign-name-input" /></label>
                <label className="field"><span>Confirm your email <b>*</b></span><input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} data-testid="sign-email-input" /></label>
                <label className="field"><span>Date <b>*</b></span><input value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} data-testid="sign-date-input" /></label>
              </div>
              <div className="signature-method-toggle" data-testid="signature-method-toggle">
                <button type="button" className={`button button-small ${method === "typed" ? "" : "button-back"}`} onClick={() => setMethod("typed")} data-testid="method-typed">Type My Signature</button>
                <button type="button" className={`button button-small ${method === "drawn" ? "" : "button-back"}`} onClick={() => setMethod("drawn")} data-testid="method-drawn">Draw My Signature</button>
              </div>
              {method === "typed" ? (
                form.typed_signature && <p className="typed-signature-display" data-testid="typed-signature-preview">{form.typed_signature}</p>
              ) : (
                <SignatureCanvas onChange={setDrawnImage} />
              )}
              {error && <p className="submit-error" data-testid="sign-error">{error}</p>}
              <button className="button" disabled={busy || !form.agreed || !form.typed_signature || !form.email || (method === "drawn" && !drawnImage)} onClick={sign} data-testid="sign-agreement-button">{busy ? "Recording…" : "Sign Agreement"}</button>
              <p className="material-meta">This electronic signature process does not constitute legal advice. The organization remains responsible for determining whether its document and signature process meets its legal requirements.</p>
            </section>
          )}
        </article>
      )}
    </main>
  );
};
