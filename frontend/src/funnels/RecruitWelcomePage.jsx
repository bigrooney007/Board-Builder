import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import { memberApi } from "@/member/api";
import "@/game/game.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RecruitWelcomePage() {
  const navigate = useNavigate();
  const sessionId = new URLSearchParams(useLocation().search).get("session_id") || "";
  const [allowed,setAllowed]=useState(null);
  const [videoId,setVideoId]=useState("");
  useEffect(() => {
    document.title = "Welcome | Self-Guided Board Recruitment";
    if(!sessionId){setAllowed(false);return}
    axios.get(`${API}/payments/flow-status/${sessionId}`,{params:{flow:"recruitment"}})
      .then(r=>setAllowed(r.data.payment_status==="paid")).catch(()=>setAllowed(false));
    axios.get(`${API}/flow-videos`).then((r)=>{
      const video=(r.data.videos||[]).find((item)=>item.key==="recruitment_welcome");
      setVideoId(video?.youtube_id||"");
    }).catch(()=>{});
  }, [sessionId]);

  const proceed = async () => {
    try { await memberApi.post("/recruit/free/member-event/welcome_completed"); } catch { /* best effort */ }
    navigate("/app/board-recruitment");
  };
  if(allowed===null)return <BfgShell><main className="bfg-flow" style={{maxWidth:720,margin:"0 auto",padding:"60px 20px",textAlign:"center"}}><p>Confirming your Board Recruitment access…</p></main></BfgShell>;
  if(!allowed)return <BfgShell><main className="bfg-flow" style={{maxWidth:720,margin:"0 auto",padding:"60px 20px",textAlign:"center"}}><h1>This Link Does Not Belong To The Board Recruitment Flow.</h1><button className="bfg-btn bfg-btn-primary" onClick={()=>navigate("/recruit")}>RETURN TO BOARD RECRUITMENT</button></main></BfgShell>;

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 720, margin: "0 auto", padding: "40px 20px 90px", textAlign: "center" }} data-testid="recruit-welcome-page">
        <p className="bfg-eyebrow">SELF-GUIDED BOARD RECRUITMENT</p>
        <div style={{ marginTop: 24, aspectRatio: "16 / 9", background: "#0F172A", borderRadius: 16, display: "grid", placeItems: "center", overflow: "hidden" }} data-testid="recruit-welcome-video-slot">
          {videoId ? (
            <iframe
              src={`https://www.youtube.com/embed/${videoId}?rel=0`}
              title="Board Recruitment Onboarding"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              style={{ width: "100%", height: "100%", border: 0 }}
              data-testid="recruit-welcome-video"
            />
          ) : (
            <p style={{ color: "#94A3B8", fontSize: 14 }}>Onboarding video has not been added yet.</p>
          )}
        </div>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 28 }} onClick={proceed} data-testid="recruit-welcome-continue-btn">OPEN MY BOARD RECRUITMENT DASHBOARD</button>
      </main>
    </BfgShell>
  );
}