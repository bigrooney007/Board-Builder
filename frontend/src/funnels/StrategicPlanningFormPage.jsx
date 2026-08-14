import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicPlanningFormPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [identity, setIdentity] = useState({ full_name: "", email: "" });
  const [answers, setAnswers] = useState({});
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/strategic-planning-form/${token}`).then((r) => {
      setData(r.data);
      setIdentity(r.data.prefill);
      if (r.data.submitted) setDone(true);
    }).catch((e) => setError(e.response?.data?.detail || "This link is not valid."));
  }, [token]);

  const setAnswer = (id, value) => setAnswers((a) => ({ ...a, [id]: value }));
  const toggleMulti = (id, option) => setAnswers((a) => {
    const current = a[id] || [];
    return { ...a, [id]: current.includes(option) ? current.filter((o) => o !== option) : [...current, option] };
  });

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError("");
    try {
      await axios.post(`${API}/strategic-planning-form/${token}`, { ...identity, answers });
      setDone(true);
    } catch (ex) { setError(ex.response?.data?.detail || "Submission failed. Please try again."); }
    setBusy(false);
  };

  if (error && !data) return <main className="legal-page"><h1>Strategic Planning Form</h1><p data-testid="sp-public-error">{error}</p></main>;
  if (!data) return <main className="legal-page"><p>Loading…</p></main>;
  if (done) return (
    <main className="legal-page" data-testid="sp-public-thanks">
      <h1>Thank You</h1>
      <p>Your response has been recorded and will be combined with the ideas of the other Board Members as {data.organization_name} builds its strategic plan.</p>
    </main>
  );
  return (
    <main className="legal-page" data-testid="sp-public-form" style={{ maxWidth: "760px", margin: "0 auto", padding: "32px 16px" }}>
      <p className="eyebrow">{data.organization_name}</p>
      <h1>Strategic Planning Form</h1>
      <p style={{ whiteSpace: "pre-wrap" }}>{data.form.introduction}</p>
      <form onSubmit={submit}>
        <label>Your Name<input required value={identity.full_name} onChange={(e) => setIdentity({ ...identity, full_name: e.target.value })} data-testid="sp-public-name" style={{ display: "block", width: "100%" }} /></label>
        <label>Your Email<input type="email" required value={identity.email} onChange={(e) => setIdentity({ ...identity, email: e.target.value })} data-testid="sp-public-email" style={{ display: "block", width: "100%" }} /></label>
        {data.form.sections.map((section) => (
          <section key={section.key} style={{ marginTop: "22px" }}>
            <h2>{section.title}</h2>
            {section.questions.map((q) => (
              <div key={q.id} style={{ marginTop: "10px" }}>
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
        ))}
        {error && <p className="submit-error" data-testid="sp-public-submit-error">{error}</p>}
        <button className="button" type="submit" disabled={busy} data-testid="sp-public-submit" style={{ marginTop: "18px" }}>{busy ? "Submitting…" : "SUBMIT MY STRATEGIC PLANNING RESPONSES"}</button>
      </form>
    </main>
  );
}
