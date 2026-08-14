import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { areaPackText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AreaPackPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [planText, setPlanText] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/area-pack/${token}`).then((r) => { setData(r.data); if (r.data.submitted) setDone(true); })
      .catch((e) => setError(e.response?.data?.detail || "This link is not valid."));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError("");
    try { await axios.post(`${API}/area-pack/${token}/submit`, { plan_text: planText }); setDone(true); }
    catch (ex) { setError(ex.response?.data?.detail || "Submission failed. Please try again."); }
    setBusy(false);
  };

  if (error && !data) return <main className="legal-page"><h1>{areaPackText.h_strategicAreaDevelopmentPack}</h1><p data-testid="area-pack-error">{error}</p></main>;
  if (!data) return <main className="legal-page"><p>Loading…</p></main>;
  return (
    <main className="legal-page" data-testid="area-pack-page" style={{ maxWidth: "820px", margin: "0 auto", padding: "32px 16px" }}>
      <p className="eyebrow">{data.organization_name}</p>
      <h1>Strategic Area Development Pack — {data.area}</h1>
      {data.owner_name && <p>Prepared for: <strong>{data.owner_name}</strong></p>}
      <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f2", padding: "16px", borderRadius: "10px" }} data-testid="area-pack-text">{data.pack_text}</pre>
      {done ? (
        <div data-testid="area-pack-thanks">
          <h2>{areaPackText.h_detailedPlanSubmitted}</h2>
          <p>Thank you. Your detailed plan for {data.area} has been submitted{data.submitted_at ? ` (${data.submitted_at.slice(0, 10)})` : ""} and will be presented to the Board. You can submit an updated version below at any time before the Board meeting.</p>
          <button className="button button-back button-small" onClick={() => setDone(false)} data-testid="area-pack-resubmit">Submit an Updated Version</button>
        </div>
      ) : (
        <form onSubmit={submit}>
          <h2>Submit Your Detailed Plan for {data.area}</h2>
          <p>Take the agreed foundation above and develop the detailed plan for your area. Paste or write your completed plan below.</p>
          <textarea required rows="14" style={{ width: "100%" }} value={planText} onChange={(e) => setPlanText(e.target.value)} data-testid="area-pack-plan-input" />
          {error && <p className="submit-error">{error}</p>}
          <button className="button" type="submit" disabled={busy} data-testid="area-pack-submit" style={{ marginTop: "14px" }}>{busy ? "Submitting…" : "SUBMIT MY DETAILED AREA PLAN"}</button>
        </form>
      )}
    </main>
  );
}
