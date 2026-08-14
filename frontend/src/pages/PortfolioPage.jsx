import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Download } from "lucide-react";
import { usePageMeta } from "@/seo";
import { portfolioPageText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PortfolioPage() {
  usePageMeta("Board Member Portfolio | Nonprofit Board Builder", "Your Board Member Portfolio.", true);
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [gate, setGate] = useState("loading");

  useEffect(() => {
    axios.get(`${API}/portfolio/${token}`).then((res) => { setData(res.data); setGate("ready"); }).catch(() => setGate("invalid"));
  }, [token]);

  if (gate === "loading") return <main style={{ padding: 60, textAlign: "center", fontFamily: "Georgia, serif" }}><p>Loading…</p></main>;
  if (gate === "invalid") {
    return (
      <main style={{ padding: 60, textAlign: "center", fontFamily: "Georgia, serif" }} data-testid="portfolio-invalid">
        <h1>{portfolioPageText.h_thisPortfolioIsNotAvailable}</h1>
        <p>Please contact the organization that sent you this link.</p>
      </main>
    );
  }

  const bodyLines = data.display_text.split("\n");
  return (
    <main style={{ background: "#f2f2f2", minHeight: "100vh", padding: "34px 12px", fontFamily: "Georgia, 'Times New Roman', serif", color: "#000" }} data-testid="portfolio-page">
      <div style={{ maxWidth: 780, margin: "0 auto 18px", textAlign: "right" }}>
        <a href={`${API}/portfolio/${token}/pdf`} style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "#000", color: "#fff", padding: "11px 18px", textDecoration: "none", fontWeight: 700 }} data-testid="portfolio-download-pdf"><Download size={15} /> DOWNLOAD PDF</a>
      </div>
      <section style={{ maxWidth: 780, margin: "0 auto 26px", background: "#fff", border: "1.5px solid #000", outline: "1px solid #000", outlineOffset: -10, padding: "120px 56px", textAlign: "center", minHeight: 640 }} data-testid="portfolio-cover">
        <h1 style={{ fontSize: "2rem", letterSpacing: 2, margin: 0 }} data-testid="portfolio-title">{data.title.toUpperCase()}</h1>
        {data.member_name && <p style={{ fontSize: "1.2rem", marginTop: 16 }} data-testid="portfolio-member-name">{data.member_name}</p>}
        <div style={{ textAlign: "left", marginTop: 200, fontSize: "0.98rem", lineHeight: 1.7 }} data-testid="portfolio-issuer">
          <p style={{ margin: 0 }}>Issued By: {data.issued_by}</p>
          {data.issuer_title && <p style={{ margin: 0 }}>Title: {data.issuer_title}</p>}
          <p style={{ margin: 0 }}>Organization: {data.organization}</p>
          <p style={{ margin: 0 }}>Date: {data.issue_date}</p>
        </div>
      </section>
      <section style={{ maxWidth: 780, margin: "0 auto", background: "#fff", border: "1.5px solid #000", outline: "1px solid #000", outlineOffset: -10, padding: "56px" }} data-testid="portfolio-content">
        {bodyLines.map((line, index) => {
          const stripped = line.trim();
          if (!stripped) return <div key={index} style={{ height: 8 }} />;
          if (index < 3 && (stripped.toUpperCase() === data.title.toUpperCase() || stripped === data.member_name)) return null;
          if (stripped.startsWith("- ")) return <p key={index} style={{ margin: "0 0 6px 18px" }}>• {stripped.slice(2)}</p>;
          if (stripped === stripped.toUpperCase() && stripped.length < 90 && /[A-Za-z]/.test(stripped)) {
            return <h2 key={index} style={{ fontSize: "1.25rem", margin: "26px 0 8px", letterSpacing: 0.5 }}>{stripped}</h2>;
          }
          return <p key={index} style={{ margin: "0 0 10px", lineHeight: 1.65 }}>{stripped}</p>;
        })}
      </section>
    </main>
  );
}
