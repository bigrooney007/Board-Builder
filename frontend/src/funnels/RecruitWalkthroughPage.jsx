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
      <main className="bfg-flow" style={{ maxWidth: 720, margin: "0 auto", padding: "40px 20px 90px" }} data-testid="recruit-walkthrough-page">
        <h1 data-testid="recruit-walkthrough-heading">See How To Recruit The Board Members Your Organization Needs Yourself</h1>
        <p style={{ marginTop: 16 }}>You already know who you need.</p>
        <p style={{ marginTop: 8 }}>Now see the exact system you can use to find them, launch your recruitment campaign, review applicants and bring the right people successfully onto your board.</p>
        <div style={{ marginTop: 26, aspectRatio: "16 / 9", background: "#0F172A", borderRadius: 16, display: "grid", placeItems: "center" }}
          data-testid="recruit-walkthrough-video-slot">
          <p style={{ color: "#94A3B8", fontSize: 14 }}>Walkthrough video coming soon</p>
        </div>
        <h2 style={{ marginTop: 34 }}>Start Recruiting The Board Members Your Organization Needs</h2>
        <p style={{ marginTop: 12 }}>Use the complete Self-Guided Board Recruitment System to move from knowing who you need to successfully bringing them onto your board.</p>
        <p style={{ marginTop: 18, fontFamily: "Outfit", fontWeight: 800, fontSize: 34, color: "#111827" }} data-testid="recruit-walkthrough-price">$497 One Time</p>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 14 }} disabled={busy} onClick={buy} data-testid="recruit-walkthrough-buy-btn">
          {busy ? "Opening Checkout…" : "START MY BOARD RECRUITMENT — $497"}
        </button>
        <p style={{ marginTop: 12, fontSize: 14 }}>Follow the process step by step. Get the tools and materials you need at every stage. Request help whenever you need it.</p>
        {error && <p className="bfg-error" data-testid="recruit-walkthrough-error">{error}</p>}
      </main>
    </BfgShell>
  );
}
