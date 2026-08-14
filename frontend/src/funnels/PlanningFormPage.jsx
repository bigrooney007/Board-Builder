import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PlanningFormPage() {
  usePageMeta("Board Fundraising Planning Form | Nonprofit Board Builder", "Share your ideas as your organization builds its fundraising plan with the Board.", true);
  const { token } = useParams();
  const [context, setContext] = useState(null);
  const [state, setState] = useState("loading");
  const [identity, setIdentity] = useState({ full_name: "", email: "", role: "" });
  const [answers, setAnswers] = useState({});
  const [confirmation, setConfirmation] = useState(false);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    axios.get(`${API}/planning-form/${token}`).then((res) => {
      setContext(res.data);
      setIdentity({ ...res.data.prefill });
      setState(res.data.submitted ? "done" : "ready");
    }).catch(() => setState("invalid"));
  }, [token]);

  const allQuestions = useMemo(() => (context ? context.form.sections.flatMap((s) => s.questions) : []), [context]);

  const setAnswer = (id, value) => setAnswers((current) => ({ ...current, [id]: value }));
  const toggleOption = (id, option) => setAnswers((current) => {
    const list = current[id] || [];
    return { ...current, [id]: list.includes(option) ? list.filter((item) => item !== option) : [...list, option] };
  });

  const validate = () => {
    const found = {};
    if (!identity.full_name.trim()) found.full_name = "Required.";
    if (!/^\S+@\S+\.\S+$/.test(identity.email.trim())) found.email = "Enter a valid email address.";
    allQuestions.forEach((question) => {
      if (!question.required) return;
      const value = answers[question.id];
      if (question.type === "multi" ? !(value || []).length : !String(value || "").trim()) found[question.id] = "This question is required.";
    });
    if (!confirmation) found.confirmation = "This confirmation is required.";
    setErrors(found);
    if (Object.keys(found).length) window.scrollTo(0, 0);
    return !Object.keys(found).length;
  };

  const submit = async () => {
    if (!validate()) return;
    setBusy(true);
    setSubmitError("");
    try {
      await axios.post(`${API}/planning-form/${token}`, { ...identity, ...answers, confirmation });
      setState("done");
      window.scrollTo(0, 0);
    } catch (err) {
      setSubmitError(err.response?.data?.detail || "We could not submit your response. Please try again.");
      setBusy(false);
    }
  };

  if (state === "loading") {
    return <FunnelLayout restrained><main><div className="intake-card" data-testid="pf-loading"><h2>Loading…</h2></div></main></FunnelLayout>;
  }
  if (state === "invalid") {
    return (
      <FunnelLayout restrained>
        <main><div className="intake-card" data-testid="pf-invalid"><h2>This Form Link Is Not Valid</h2><p>Please contact the person who sent you this link and ask them to resend your personal form link.</p></div></main>
      </FunnelLayout>
    );
  }
  if (state === "done") {
    return (
      <FunnelLayout restrained>
        <main>
          <div className="intake-card" data-testid="pf-thank-you">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Response submitted</p>
            <h2>Thank You</h2>
            <p data-testid="pf-thank-you-copy">Your fundraising planning response has been submitted to {context.organization_name}.</p>
            <p>Your ideas will be considered alongside the responses of the other Board Members as the organization's Fundraising Strategy Plan is developed.</p>
          </div>
        </main>
      </FunnelLayout>
    );
  }

  const form = context.form;
  return (
    <FunnelLayout restrained>
      <main data-testid="pf-page">
        <section className="funnel-hero-banner brp-hero intake-hero" data-testid="pf-hero">
          <h1 data-testid="pf-title">{form.title}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="pf-organization">{context.organization_name}</p>
          <i aria-hidden="true" />
        </section>

        <section className="intake-shell" data-testid="pf-form">
          <div className="member-card" style={{ marginBottom: 18 }} data-testid="pf-introduction">
            <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{form.introduction}</p>
            {form.goal_context && <p style={{ whiteSpace: "pre-wrap", marginTop: 12 }} data-testid="pf-goal-context"><strong>{form.goal_context}</strong></p>}
          </div>

          <h2 className="intake-step-title">About You</h2>
          <div className="two-col-fields">
            <label className="field"><span>Full Name <b>*</b></span><input value={identity.full_name} onChange={(e) => setIdentity({ ...identity, full_name: e.target.value })} data-testid="pf-full-name" />{errors.full_name && <p className="field-error">{errors.full_name}</p>}</label>
            <label className="field"><span>Email <b>*</b></span><input type="email" value={identity.email} onChange={(e) => setIdentity({ ...identity, email: e.target.value })} data-testid="pf-email" />{errors.email && <p className="field-error">{errors.email}</p>}</label>
          </div>
          <label className="field"><span>Current Board Role</span><input value={identity.role} onChange={(e) => setIdentity({ ...identity, role: e.target.value })} data-testid="pf-role" /></label>

          {form.sections.map((section) => (
            <div key={section.key} data-testid={`pf-section-${section.key}`}>
              <h2 className="intake-step-title">{section.title}</h2>
              {section.key === "relationships" && <p className="eyebrow" data-testid="pf-relationship-note">{form.relationship_note}</p>}
              {section.questions.map((question) => (
                <div key={question.id}>
                  {question.type === "multi" ? (
                    <fieldset className="field choice-field">
                      <legend>{question.prompt} {question.required && <b>*</b>}</legend>
                      <div className="choice-grid">
                        {question.options.map((option) => (
                          <label className={`choice ${(answers[question.id] || []).includes(option) ? "selected" : ""}`} key={option}>
                            <input type="checkbox" checked={(answers[question.id] || []).includes(option)} onChange={() => toggleOption(question.id, option)} data-testid={`pf-${question.id}-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
                            <span>{option}</span>
                          </label>
                        ))}
                      </div>
                      {errors[question.id] && <p className="field-error">{errors[question.id]}</p>}
                    </fieldset>
                  ) : (
                    <label className="field"><span>{question.prompt} {question.required ? <b>*</b> : "(optional)"}</span>
                      {question.id === "ownership" && <span style={{ display: "block", fontSize: "0.85rem", color: "#555", marginBottom: 4 }} data-testid="pf-ownership-examples">{form.ownership_examples}</span>}
                      <textarea rows={4} value={answers[question.id] || ""} onChange={(e) => setAnswer(question.id, e.target.value)} data-testid={`pf-${question.id.replace(/_/g, "-")}`} />
                      {errors[question.id] && <p className="field-error">{errors[question.id]}</p>}
                    </label>
                  )}
                </div>
              ))}
            </div>
          ))}

          <fieldset className="field choice-field" data-testid="pf-confirmation-field">
            <label className={`choice ${confirmation ? "selected" : ""}`}>
              <input type="checkbox" checked={confirmation} onChange={() => setConfirmation(!confirmation)} data-testid="pf-confirmation" />
              <span>{form.confirmation_text} <b>*</b></span>
            </label>
            {errors.confirmation && <p className="field-error">{errors.confirmation}</p>}
          </fieldset>

          {submitError && <p className="submit-error" data-testid="pf-submit-error">{submitError}</p>}
          <div className="intake-nav">
            <span />
            <button type="button" className="button" onClick={submit} disabled={busy} data-testid="pf-submit-button">{busy ? "Submitting…" : "SUBMIT MY FUNDRAISING PLANNING RESPONSE"}</button>
          </div>
        </section>
      </main>
    </FunnelLayout>
  );
}
