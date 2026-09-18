import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import "@/game/game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE = process.env.REACT_APP_BACKEND_URL;

export default function RecruitWalkthroughPage() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const audioRef = useRef(null);

  useEffect(() => {
    document.title = "Self-Guided Board Recruitment | Nonprofit Board Builder";
    const token = localStorage.getItem("recruitFreeToken");
    if (!token) { navigate("/recruit", { replace: true }); return undefined; }
    axios.post(`${API}/recruit/free/${token}/event`, { event: "video_page_viewed" }).catch(() => {});
    axios.get(`${API}/game/voice/tutorial/recruitment-free`).then((r) => {
      const clip = (r.data.clips || {})["recruitment-free-video-page"];
      if (clip?.ready) {
        const audio = new Audio(`${BASE}${clip.url}`);
        audioRef.current = audio;
        audio.play().catch(() => {});
      }
    }).catch(() => {});
    return () => { if (audioRef.current) audioRef.current.pause(); };
  }, []);

  const buy = async () => {
    setBusy(true); setError("");
    if (audioRef.current) audioRef.current.pause();
    const token = localStorage.getItem("recruitFreeToken");
    try {
      let leadId = "";
      if (token) {
        await axios.post(`${API}/recruit/free/${token}/event`, { event: "checkout_started" }).catch(() => {});
        const assessment = await axios.get(`${API}/recruit/free/${token}`);
        leadId = assessment.data.lead_id || "";
      }
      if (!leadId) { navigate("/recruit"); return; }
      const response = await axios.post(`${API}/payments/checkout`, {
        lead_id: leadId, tier: "497", origin_url: window.location.origin,
      }, { withCredentials: true });
      window.location.href = response.data.checkout_url;
    } catch (err) {
      setError(err.response?.status === 403 ? "Program Access Opening Soon" : "We could not open checkout. Please try again.");
      setBusy(false);
    }
  };

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 720, margin: "0 auto", padding: "40px 20px 90px", textAlign: "center" }} data-testid="recruit-walkthrough-page">
        <h1 style={{ fontSize: "clamp(30px, 6vw, 48px)", lineHeight: 1.08, maxWidth: 680, margin: "0 auto" }} data-testid="recruit-walkthrough-heading">
          See How To Recruit The Board Members Your Organization Needs Yourself
        </h1>
        <p style={{ marginTop: 18, fontWeight: 800, fontSize: 18, color: "#111827" }}>Press Play and Watch The Short Video</p>
        <div style={{ marginTop: 18, aspectRatio: "16 / 9", background: "#0F172A", borderRadius: 16, display: "grid", placeItems: "center", overflow: "hidden" }}
          data-testid="recruit-walkthrough-video-slot">
          <p style={{ color: "#94A3B8", fontSize: 14 }}>Walkthrough video coming soon</p>
        </div>

        <h2 style={{ marginTop: 36, fontSize: "clamp(24px, 4vw, 32px)" }}>Start Recruiting The Board Members Your Organization Needs</h2>
        <div className="bfg-card" style={{ marginTop: 20, padding: "26px 22px", textAlign: "left" }}>
          <p style={{ fontWeight: 800, fontSize: 18, color: "#111827", textAlign: "center" }}>Your Self-Guided Board Recruitment System</p>
          <p style={{ marginTop: 18 }}><strong>See the process executed step by step.</strong> Know exactly what to do from recruitment campaign to selection and onboarding.</p>
          <p style={{ marginTop: 14 }}><strong>Use the materials we provide to execute it yourself.</strong> Get the forms, campaign materials, interview tools, reference process and onboarding materials you need at each stage.</p>
          <p style={{ marginTop: 14 }}><strong>Get support throughout the entire process.</strong> When you need help, request support without handing the whole process over to someone else.</p>
          <p style={{ marginTop: 24, textAlign: "center", fontFamily: "Outfit", fontWeight: 800, fontSize: 38, color: "#111827" }} data-testid="recruit-walkthrough-price">$497 One Time</p>
          <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16, width: "100%", minHeight: 58, fontSize: 16 }} disabled={busy} onClick={buy} data-testid="recruit-walkthrough-buy-btn">
            {busy ? "Opening Secure Checkout…" : "START MY BOARD RECRUITMENT — $497"}
          </button>
          <p style={{ marginTop: 12, textAlign: "center", fontSize: 13 }}>One payment. Follow the complete recruitment process inside your dashboard.</p>
        </div>
        {error && <p className="bfg-error" data-testid="recruit-walkthrough-error">{error}</p>}
      </main>
    </BfgShell>
  );
}
