import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "@/funnels/FunnelLayout";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const emptyReference = () => ({ name: "", position: "", organization: "", relationship: "", email: "", phone: "", duration: "" });

const ReferenceFields = ({ index, value, onChange }) => (
  <fieldset className="reference-fieldset" data-testid={`reference-fieldset-${index + 1}`}>
    <legend>Reference {index + 1}</legend>
    <div className="two-col-fields">
      <label className="field"><span>Full Name *</span><input value={value.name} onChange={(event) => onChange({ ...value, name: event.target.value })} data-testid={`ref${index + 1}-name`} /></label>
      <label className="field"><span>Professional Position *</span><input value={value.position} onChange={(event) => onChange({ ...value, position: event.target.value })} data-testid={`ref${index + 1}-position`} /></label>
      <label className="field"><span>Organization *</span><input value={value.organization} onChange={(event) => onChange({ ...value, organization: event.target.value })} data-testid={`ref${index + 1}-organization`} /></label>
      <label className="field"><span>Relationship to You *</span><input value={value.relationship} onChange={(event) => onChange({ ...value, relationship: event.target.value })} data-testid={`ref${index + 1}-relationship`} /></label>
      <label className="field"><span>Email Address *</span><input type="email" value={value.email} onChange={(event) => onChange({ ...value, email: event.target.value })} data-testid={`ref${index + 1}-email`} /></label>
      <label className="field"><span>Phone Number (optional)</span><input value={value.phone} onChange={(event) => onChange({ ...value, phone: event.target.value })} data-testid={`ref${index + 1}-phone`} /></label>
    </div>
    <label className="field"><span>How long have they known or worked with you? *</span><input value={value.duration} onChange={(event) => onChange({ ...value, duration: event.target.value })} data-testid={`ref${index + 1}-duration`} /></label>
  </fieldset>
);

export default function CandidateReferenceFormPage() {
  const { token } = useParams();
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState("");
  const [references, setReferences] = useState([emptyReference(), emptyReference()]);
  const [permission, setPermission] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState("");

  useEffect(() => {
    axios.get(`${API}/public/reference-form/${token}`)
      .then((response) => setMeta(response.data))
      .catch((err) => setError(err.response?.data?.detail || "This form is not available."));
  }, [token]);

  const submit = async () => {
    setError("");
    const incomplete = references.some((r) => !r.name.trim() || !r.position.trim() || !r.organization.trim() || !r.relationship.trim() || !r.email.trim() || !r.duration.trim());
    if (incomplete) { setError("Please complete all required fields for both references."); return; }
    if (!permission) { setError("Please confirm you have permission to share your referees' contact information."); return; }
    setBusy(true);
    try {
      const response = await axios.post(`${API}/public/reference-form/${token}`, { references, permission_confirmed: true });
      setDone(response.data.message);
    } catch (err) { setError(err.response?.data?.detail || "Your references could not be submitted."); }
    setBusy(false);
  };

  return (
    <FunnelLayout>
      <main className="member-page public-form-page" data-testid="candidate-reference-form-page">
        {error && !meta && <div className="member-card"><h2>{error}</h2></div>}
        {meta && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">Board Appointment Reference Process</p>
              <h1 data-testid="reference-form-heading">Provide Your Professional References</h1>
              <p>Hello {meta.candidate_name || "there"}. As part of the board appointment process, please provide two professional references. Each referee will receive a short confidential reference form by email.</p>
            </header>
            {(done || meta.submitted) ? (
              <div className="member-card" data-testid="reference-form-done">
                <CheckCircle2 size={30} />
                <h2>Your References Have Been Recorded</h2>
                <p>{done || "Your references have already been provided. Each referee has received a secure reference form."}</p>
              </div>
            ) : (
              <div className="member-card">
                {references.map((reference, index) => (
                  <ReferenceFields key={index} index={index} value={reference} onChange={(next) => setReferences(references.map((item, i) => (i === index ? next : item)))} />
                ))}
                <label className="checkbox-field" data-testid="reference-permission">
                  <input type="checkbox" checked={permission} onChange={(event) => setPermission(event.target.checked)} />
                  <span>I confirm that I have permission to provide my referees' contact information for this reference process.</span>
                </label>
                {error && <p className="submit-error" data-testid="reference-form-error">{error}</p>}
                <button className="button" disabled={busy} onClick={submit} data-testid="submit-references-button">{busy ? "Submitting…" : "Submit My References"}</button>
              </div>
            )}
          </>
        )}
      </main>
    </FunnelLayout>
  );
}

export function RefereeFormPage() {
  const { token } = useParams();
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState("");
  const [answers, setAnswers] = useState({});
  const [identity, setIdentity] = useState({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState("");

  useEffect(() => {
    axios.get(`${API}/public/referee-form/${token}`)
      .then((response) => { setMeta(response.data); setIdentity(response.data.identity || {}); })
      .catch((err) => setError(err.response?.data?.detail || "This form is not available."));
  }, [token]);

  const IDENTITY_LABELS = { name: "Your Full Name", position: "Professional Position", organization: "Organization", relationship: "Relationship to Candidate", duration: "How long have you known/worked with the candidate?" };

  const submit = async () => {
    setError("");
    if ((meta?.questions || []).some((q) => !String(answers[q.id] || "").trim())) { setError("Please answer every question."); return; }
    if (!answers.recommend) { setError("Please choose Yes, No, or I would need more information to say."); return; }
    if (!String(answers.explanation || "").trim()) { setError("Please explain your response to the final question."); return; }
    if (!answers.declaration_confirmed) { setError("Please confirm the declaration before submitting."); return; }
    setBusy(true);
    try {
      const payload = { ...answers };
      Object.entries(identity).forEach(([key, value]) => { payload[`identity_${key}`] = value; });
      const response = await axios.post(`${API}/public/referee-form/${token}`, payload);
      setDone(response.data.message);
    } catch (err) { setError(err.response?.data?.detail || "Your reference could not be submitted."); }
    setBusy(false);
  };

  return (
    <FunnelLayout>
      <main className="member-page public-form-page" data-testid="referee-form-page">
        {error && !meta && <div className="member-card"><h2>{error}</h2></div>}
        {meta && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">Confidential Reference</p>
              <h1 data-testid="referee-form-heading">Reference for {meta.candidate_name}</h1>
              <p>Thank you for taking the time to provide a reference for {meta.candidate_name} as part of their application to serve on the Board of {meta.organization_name || "the recruiting organization"}. Your response will be shared with the organization reviewing the candidate, which makes its own appointment decision.</p>
            </header>
            {(done || meta.completed) ? (
              <div className="member-card" data-testid="referee-form-done">
                <CheckCircle2 size={30} />
                <h2>Reference Recorded</h2>
                <p>{done || "This reference has already been completed. Thank you."}</p>
              </div>
            ) : (
              <div className="member-card">
                <div className="two-col-fields">
                  {Object.entries(IDENTITY_LABELS).map(([key, label]) => (
                    <label className="field" key={key}><span>{label} *</span>
                      <input value={identity[key] || ""} onChange={(event) => setIdentity({ ...identity, [key]: event.target.value })} data-testid={`referee-identity-${key}`} />
                    </label>
                  ))}
                </div>
                {meta.questions.map((question) => (
                  <label className="field" key={question.id}>
                    <span>{question.label} *</span>
                    <textarea rows="2" value={answers[question.id] || ""} onChange={(event) => setAnswers({ ...answers, [question.id]: event.target.value })} data-testid={`referee-${question.id}`} />
                  </label>
                ))}
                <label className="field"><span>{meta.recommend_question || `Based on your experience, would you feel comfortable recommending ${meta.candidate_name} for board service? Please explain your response.`} *</span>
                  <select value={answers.recommend || ""} onChange={(event) => setAnswers({ ...answers, recommend: event.target.value })} data-testid="referee-recommend">
                    <option value="">Select one</option>
                    {(meta.recommend_options || ["Yes", "No", "I would need more information to say"]).map((option) => <option key={option}>{option}</option>)}
                  </select>
                </label>
                <label className="field"><span>Explanation *</span>
                  <textarea rows="3" value={answers.explanation || ""} onChange={(event) => setAnswers({ ...answers, explanation: event.target.value })} data-testid="referee-explanation" />
                </label>
                <label className="choice" style={{ alignItems: "flex-start" }}>
                  <input type="checkbox" checked={Boolean(answers.declaration_confirmed)} onChange={(event) => setAnswers({ ...answers, declaration_confirmed: event.target.checked })} data-testid="referee-declaration" />
                  <span>I confirm that the information I have provided reflects my own experience and knowledge of the candidate. *</span>
                </label>
                {error && <p className="submit-error" data-testid="referee-form-error">{error}</p>}
                <button className="button" disabled={busy} onClick={submit} data-testid="submit-referee-button">{busy ? "Submitting…" : "Submit Reference"}</button>
              </div>
            )}
          </>
        )}
      </main>
    </FunnelLayout>
  );
}
