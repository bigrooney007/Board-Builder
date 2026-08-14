import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Download } from "lucide-react";
import { usePageMeta } from "@/seo";
import { fundraisingPortfolioText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function FundraisingPortfolioPage() {
  usePageMeta("Fundraising Portfolio | Nonprofit Board Builder", "Your individual place inside your organization's fundraising strategy.", true);
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    axios.get(`${API}/fundraising-portfolio/${token}`).then((res) => setData(res.data)).catch(() => setInvalid(true));
  }, [token]);

  if (invalid) {
    return <main style={{ maxWidth: 720, margin: "60px auto", padding: 24, fontFamily: "Arial, sans-serif" }} data-testid="fp-invalid"><h1>{fundraisingPortfolioText.h_thisPortfolioLinkIsNot}</h1><p>Please contact the person who sent you this link.</p></main>;
  }
  if (!data) return <main style={{ maxWidth: 720, margin: "60px auto", padding: 24 }} data-testid="fp-loading"><p>Loading…</p></main>;

  return (
    <main style={{ background: "#fff", color: "#000", fontFamily: "Georgia, 'Times New Roman', serif", padding: "34px 16px" }} data-testid="fp-public-page">
      <div style={{ maxWidth: 760, margin: "0 auto", border: "1.5px solid #000", padding: "44px 40px" }}>
        <div style={{ textAlign: "center", padding: "60px 0 40px" }}>
          <h1 style={{ letterSpacing: 3, fontSize: "1.9rem", margin: 0 }} data-testid="fp-title">{fundraisingPortfolioText.h_fundraisingPortfolio}</h1>
          <p style={{ fontSize: "1.2rem", marginTop: 14 }} data-testid="fp-member-name">{data.member_name}</p>
        </div>
        <div style={{ marginBottom: 40 }} data-testid="fp-issuer">
          <p style={{ margin: 0 }}>Issued By: {data.issued_by}</p>
          {data.issuer_title && <p style={{ margin: 0 }}>{data.issuer_title}</p>}
          <p style={{ margin: 0 }}>{data.organization_name}</p>
        </div>
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }} data-testid="fp-text">{data.text.split("\n").slice(2).join("\n").trim()}</div>
        <div style={{ textAlign: "center", marginTop: 40 }}>
          <a href={`${API}/fundraising-portfolio/${token}/pdf`} target="_blank" rel="noreferrer" style={{ background: "#000", color: "#fff", padding: "13px 22px", textDecoration: "none", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 8 }} data-testid="fp-download-pdf"><Download size={16} /> DOWNLOAD PDF</a>
        </div>
      </div>
    </main>
  );
}
