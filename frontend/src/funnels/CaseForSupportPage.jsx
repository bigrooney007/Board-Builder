import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Download } from "lucide-react";
import { usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CaseForSupportPage() {
  usePageMeta("Case for Support | Nonprofit Board Builder", "Why this organization's work matters and how you can help.", true);
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    axios.get(`${API}/case-for-support/${token}`).then((res) => setData(res.data)).catch(() => setInvalid(true));
  }, [token]);

  if (invalid) {
    return <main style={{ maxWidth: 720, margin: "60px auto", padding: 24, fontFamily: "Arial, sans-serif" }} data-testid="cfs-invalid"><h1>This link is not valid</h1><p>Please contact the person who shared this document with you.</p></main>;
  }
  if (!data) return <main style={{ maxWidth: 720, margin: "60px auto", padding: 24 }} data-testid="cfs-loading"><p>Loading…</p></main>;

  return (
    <main style={{ background: "#fff", color: "#000", fontFamily: "Georgia, 'Times New Roman', serif", padding: "34px 16px" }} data-testid="cfs-public-page">
      <div style={{ maxWidth: 760, margin: "0 auto", border: "1.5px solid #000", padding: "44px 40px" }}>
        <div style={{ textAlign: "center", padding: "60px 0 40px" }}>
          <h1 style={{ letterSpacing: 3, fontSize: "1.9rem", margin: 0 }} data-testid="cfs-title">THE CASE FOR SUPPORT</h1>
          <p style={{ fontSize: "1.2rem", marginTop: 14 }} data-testid="cfs-organization">{data.organization_name}</p>
        </div>
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }} data-testid="cfs-text">{data.text.split("\n").slice(2).join("\n").trim()}</div>
        <div style={{ textAlign: "center", marginTop: 40 }}>
          <a href={`${API}/case-for-support/${token}/pdf`} target="_blank" rel="noreferrer" style={{ background: "#000", color: "#fff", padding: "13px 22px", textDecoration: "none", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 8 }} data-testid="cfs-download-pdf"><Download size={16} /> DOWNLOAD PDF</a>
        </div>
      </div>
    </main>
  );
}
