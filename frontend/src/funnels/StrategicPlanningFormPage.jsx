import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { strategicPlanningPublicContent } from "../content/appContent";

const F = strategicPlanningPublicContent.form;

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicPlanningFormPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [identity, setIdentity] = useState({ full_name: "", email: "" });
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(0);
  const [stepError, setStepError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/strategic-planning-form/${token}`).then((r) => {
      setData(r.data);
      setIdentity(r.data.prefill);
      setAnswers(r.data.existing_answers || {});
      if (r.data.submitted) setDone(true);
    }).catch((e) => setError(e.response?.data?.detail || F.invalidLink));
  }, [token]);

  const setAnswer = (id, value) => setAnswers((a) => ({ ...a, [id]: value }));
  const toggleMulti = (id, option) => setAnswers((a) => {
    const current = a[id] || [];
    return { ...a, [id]: current.includes(option) ? current.filter((o) => o !== option) : [...current, option] };
  });

  if (error && !data) return <main className="legal-page"><h1>{F.title}</h1><p data-testid="sp-public-error">{error}</p></main>;
  if (!data) return <main className="legal-page"><p>{F.loading}</p></main>;
  if (done) return (
    <main className="legal-page" data-testid="sp-public-thanks">
      <h1>{F.thanksHeading}</h1>
      <p>{F.thanks(data.organization_name)}</p>
    </main>
  );

  const sections = data.form.sections || [];
  const totalSteps = sections.length + 1;
  const section = step > 0 ? sections[step - 1] : null;

  const validateStep = () => {
    if (step === 0) {
      if (!identity.full_name.trim()) return F.nameRequired;
      if (!identity.email.trim()) return F.emailRequired;
      return "";
    }
    for (const q of section.questions) {
      const value = answers[q.id];
      if (q.required && (q.type === "multi" ? !(value || []).length : !(value || "").trim())) return F.answerRequired(q.prompt);
    }
    return "";
  };

  const next = () => {
    const problem = validateStep();
    setStepError(problem);
    if (!problem) { setStep(step + 1); window.scrollTo(0, 0); }
  };

  const submit = async () => {
    const problem = validateStep();
    setStepError(problem);
    if (problem) return;
    setBusy(true);
    try {
      await axios.post(`${API}/strategic-planning-form/${token}`, { ...identity, answers });
      setDone(true);
    } catch (ex) { setStepError(ex.response?.data?.detail || F.submitFailed); }
    setBusy(false);
  };

  return (
    <main className="legal-page" data-testid="sp-public-form" style={{ maxWidth: "760px", margin: "0 auto", padding: "32px 16px" }}>
      {data.logo_data_url && <img src={data.logo_data_url} alt={`${data.organization_name} logo`} style={{display:"block",maxWidth:180,maxHeight:120,objectFit:"contain",margin:"0 auto 18px"}}/>}
      <p className="eyebrow" style={{textAlign:"center"}}>{data.organization_name}</p>
      <h1 style={{textAlign:"center"}}>{data.is_lead_user ? "Complete Your Own Strategic Planning Form" : F.title}</h1>
      <div className="progress-copy" style={{ marginTop: "10px" }}>
        <span data-testid="sp-public-progress">{F.stepLabel(step + 1, totalSteps)}{section ? ` — ${section.title}` : ""}</span>
        <span>{Math.round(((step + 1) / totalSteps) * 100)}%</span>
      </div>
      <div className="progress-track"><div style={{ width: `${((step + 1) / totalSteps) * 100}%` }} /></div>

      {step === 0 && (
        <section style={{ marginTop: "18px" }} data-testid="sp-public-step-identity">
          <p style={{ whiteSpace: "pre-wrap" }}>{data.form.introduction}</p>
          <label>{F.nameLabel} *<input required value={identity.full_name} onChange={(e) => setIdentity({ ...identity, full_name: e.target.value })} data-testid="sp-public-name" style={{ display: "block", width: "100%" }} /></label>
          <label>{F.emailLabel} *<input type="email" required value={identity.email} onChange={(e) => setIdentity({ ...identity, email: e.target.value })} data-testid="sp-public-email" style={{ display: "block", width: "100%" }} /></label>
        </section>
      )}

      {section && (
        <section style={{ marginTop: "18px" }} data-testid={`sp-public-step-${section.key}`}>
          <h2>{section.title}</h2>
          {section.questions.map((q) => (
            <div key={q.id} style={{ marginTop: "12px" }}>
              <label style={{ fontWeight: 600 }}>{q.prompt}{q.required ? " *" : ""}</label>
              {q.type === "multi" ? (
                <div>{q.options.map((option) => (
                  <label key={option} style={{ display: "block" }}>
                    <input type="checkbox" checked={(answers[q.id] || []).includes(option)} onChange={() => toggleMulti(q.id, option)} /> {option}
                  </label>))}
                </div>
              ) : q.type === "short" ? (
                <input style={{ width: "100%" }} value={answers[q.id] || ""} onChange={(e) => setAnswer(q.id, e.target.value)} data-testid={`sp-q-${q.id}`} />
              ) : (
                <textarea rows="4" style={{ width: "100%" }} value={answers[q.id] || ""} onChange={(e) => setAnswer(q.id, e.target.value)} data-testid={`sp-q-${q.id}`} />
              )}
            </div>
          ))}
        </section>
      )}

      {stepError && <p className="submit-error" data-testid="sp-public-submit-error">{stepError}</p>}
      <div className="material-actions" style={{ marginTop: "20px" }}>
        {step > 0 && <button className="button button-back" onClick={() => { setStep(step - 1); setStepError(""); window.scrollTo(0, 0); }} data-testid="sp-public-back">{F.back}</button>}
        {step < totalSteps - 1 && <button className="button" onClick={next} data-testid="sp-public-next">{F.next}</button>}
        {step === totalSteps - 1 && <button className="button" disabled={busy} onClick={submit} data-testid="sp-public-submit">{busy ? F.submitting : F.submit}</button>}
      </div>
    </main>
  );
}
