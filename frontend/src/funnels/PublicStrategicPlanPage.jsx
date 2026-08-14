import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PlanView = ({ endpoint, testid }) => {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots"; meta.content = "noindex, nofollow";
    document.head.appendChild(meta);
    return () => document.head.removeChild(meta);
  }, []);
  useEffect(() => {
    axios.get(`${API}/${endpoint}/${token}`).then((r) => setData(r.data)).catch((e) => setError(e.response?.data?.detail || "This link is not valid."));
  }, [endpoint, token]);
  if (error) return <main className="legal-page"><h1>Not Available</h1><p data-testid={`${testid}-error`}>{error}</p></main>;
  if (!data) return <main className="legal-page"><p>Loading…</p></main>;
  return (
    <main className="legal-page" data-testid={testid} style={{ maxWidth: "780px", margin: "0 auto", padding: "40px 18px" }}>
      <p className="eyebrow">{data.organization_name}</p>
      <h1>{data.title}</h1>
      <div className="material-actions" style={{ margin: "14px 0" }}>
        <button className="button button-back" onClick={() => window.print()} data-testid={`${testid}-print`}>Download / Print PDF</button>
      </div>
      <pre style={{ whiteSpace: "pre-wrap", fontFamily: "Georgia, serif", lineHeight: 1.7 }} data-testid={`${testid}-text`}>{data.display_text}</pre>
      <p style={{ marginTop: "26px", color: "#5c5c56" }}>Prepared with {data.issued_by} · The Nonprofit Board Builder</p>
    </main>
  );
};

export default function PublicStrategicPlanPage() {
  return <PlanView endpoint="strategic-plan" testid="public-strategic-plan" />;
}

export function PublicActionPlanPage() {
  return <PlanView endpoint="strategic-action-plan" testid="public-action-plan" />;
}
