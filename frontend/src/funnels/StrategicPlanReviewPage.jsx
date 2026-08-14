import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { spReviewText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicPlanReviewPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [responses, setResponses] = useState({});
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/strategic-plan-review/${token}`).then((r) => {
      setData(r.data); setName(r.data.prefill.full_name);
      if (r.data.submitted) setDone(true);
    }).catch((e) => setError(e.response?.data?.detail || "This link is not valid."));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError("");
    const payload = data.areas.map((a) => ({ area_key: a.area_key, choice: responses[a.area_key]?.choice || "", comment: responses[a.area_key]?.comment || "" })).filter((r) => r.choice);
    if (payload.length !== data.areas.length) { setError("Please choose a response for every strategic area."); setBusy(false); return; }
    try { await axios.post(`${API}/strategic-plan-review/${token}`, { full_name: name, responses: payload }); setDone(true); }
    catch (ex) { setError(ex.response?.data?.detail || "Submission failed. Please try again."); }
    setBusy(false);
  };

  if (error && !data) return <main className="legal-page"><h1>{spReviewText.h_foundationalPlanReview}</h1><p data-testid="sp-review-error">{error}</p></main>;
  if (!data) return <main className="legal-page"><p>Loading…</p></main>;
  if (done) return (
    <main className="legal-page" data-testid="sp-review-thanks">
      <h1>{spReviewText.h_thankYou}</h1>
      <p>Your review has been recorded. Your input will help refine the Foundational Strategic Plan for {data.organization_name} before the detailed area plans are developed.</p>
    </main>
  );
  return (
    <main className="legal-page" data-testid="sp-review-page" style={{ maxWidth: "820px", margin: "0 auto", padding: "32px 16px" }}>
      <p className="eyebrow">{data.organization_name}</p>
      <h1>{spReviewText.h_foundationalStrategicPlanBoardReview}</h1>
      <p>Review the consolidated thinking below. For each strategic area, support it, suggest a change, add an idea, or flag it for Board discussion. This is refinement, not formal adoption.</p>
      <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "16px", borderRadius: "10px", maxHeight: "420px", overflow: "auto" }} data-testid="sp-review-plan-text">{data.display_text}</pre>
      <form onSubmit={submit}>
        <label>Your Name<input required value={name} onChange={(e) => setName(e.target.value)} data-testid="sp-review-name" style={{ display: "block", width: "100%" }} /></label>
        {data.areas.map((area) => (
          <section key={area.area_key} style={{ marginTop: "20px" }} data-testid={`sp-review-area-${area.area_key}`}>
            <h2>{area.area}</h2>
            {data.choices.map((choice) => (
              <label key={choice} style={{ display: "block" }}>
                <input type="radio" name={area.area_key} checked={responses[area.area_key]?.choice === choice}
                  onChange={() => setResponses({ ...responses, [area.area_key]: { ...(responses[area.area_key] || {}), choice } })} /> {choice}
              </label>
            ))}
            <textarea rows="2" style={{ width: "100%" }} placeholder="Comments / details (optional)"
              value={responses[area.area_key]?.comment || ""}
              onChange={(e) => setResponses({ ...responses, [area.area_key]: { ...(responses[area.area_key] || {}), comment: e.target.value } })}
              data-testid={`sp-review-comment-${area.area_key}`} />
          </section>
        ))}
        {error && <p className="submit-error">{error}</p>}
        <button className="button" type="submit" disabled={busy} data-testid="sp-review-submit" style={{ marginTop: "18px" }}>{busy ? "Submitting…" : "SUBMIT MY REVIEW"}</button>
      </form>
    </main>
  );
}
