import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { BfgShell } from "@/game/gameShared";
import { memberApi } from "@/member/api";
import "@/game/game.css";

export default function RecruitWelcomePage() {
  const navigate = useNavigate();
  useEffect(() => { document.title = "Welcome | Self-Guided Board Recruitment"; }, []);

  const proceed = async () => {
    try { await memberApi.post("/recruit/free/member-event/welcome_completed"); } catch { /* best effort */ }
    navigate("/app/board-recruitment");
  };

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 720, margin: "0 auto", padding: "40px 20px 90px", textAlign: "center" }} data-testid="recruit-welcome-page">
        <p className="bfg-eyebrow">SELF-GUIDED BOARD RECRUITMENT</p>
        <div style={{ marginTop: 24, aspectRatio: "16 / 9", background: "#0F172A", borderRadius: 16, display: "grid", placeItems: "center" }}
          data-testid="recruit-welcome-video-slot">
          <p style={{ color: "#94A3B8", fontSize: 14 }}>Welcome video coming soon</p>
        </div>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 28 }} onClick={proceed} data-testid="recruit-welcome-continue-btn">
          CONTINUE TO SET UP MY RECRUITMENT
        </button>
      </main>
    </BfgShell>
  );
}
