import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import TrackedYouTubeVideo from "@/clean/TrackedYouTubeVideo";
import { usePlatformVideo } from "@/clean/platform";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import "@/game/game.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RecruitWelcomePage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const sessionId = new URLSearchParams(useLocation().search).get("session_id") || "";
  const [allowed,setAllowed]=useState(null);
  const video=usePlatformVideo("recruitment_welcome");
  const internalRecruitTest=Boolean(
    member?.internal_client_test
    && member?.client_test_product==="recruitment"
    && member?.entitlements?.some((key)=>["recruitment_self_guided","recruitment_selection_onboarding"].includes(key))
  );
  useEffect(() => {
    document.title = "Welcome | Self-Guided Board Recruitment";
    if(loading)return;
    if(internalRecruitTest){setAllowed(true);return}
    if(!sessionId){setAllowed(false);return}
    axios.get(`${API}/payments/flow-status/${sessionId}`,{params:{flow:"recruitment"}})
      .then(r=>setAllowed(r.data.payment_status==="paid")).catch(()=>setAllowed(false));
  }, [sessionId,loading,internalRecruitTest]);

  const proceed = async () => {
    try { await memberApi.post("/recruit/free/member-event/welcome_completed"); } catch { /* best effort */ }
    navigate("/app/board-recruitment");
  };
  if(loading||allowed===null)return <BfgShell><main className="bfg-flow" style={{maxWidth:720,margin:"0 auto",padding:"60px 20px",textAlign:"center"}}><p>Confirming your Board Recruitment access…</p></main></BfgShell>;
  if(!allowed)return <BfgShell><main className="bfg-flow" style={{maxWidth:720,margin:"0 auto",padding:"60px 20px",textAlign:"center"}}><h1>This Link Does Not Belong To The Board Recruitment Flow.</h1><button className="bfg-btn bfg-btn-primary" onClick={()=>navigate("/recruit")}>RETURN TO BOARD RECRUITMENT</button></main></BfgShell>;

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 720, margin: "0 auto", padding: "40px 20px 90px", textAlign: "center" }} data-testid="recruit-welcome-page">
        <p className="bfg-eyebrow">SELF-GUIDED BOARD RECRUITMENT</p>
        <h1 style={{fontSize:"clamp(30px,6vw,46px)",lineHeight:1.08,margin:"8px auto 0"}}>Welcome To Your Board Recruitment Platform</h1>
        <p style={{maxWidth:620,margin:"16px auto 0",fontSize:17}}>Watch this short onboarding to see how your dashboard guides you from the six recruitment questions through campaign launch, selection and onboarding.</p>
        <div style={{ marginTop: 24 }}>
          <TrackedYouTubeVideo video={video} flow="recruitment" testId="recruit-welcome-video" title="Board Recruitment Onboarding" placeholder="Onboarding video has not been added yet." />
        </div>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 28 }} onClick={proceed} data-testid="recruit-welcome-continue-btn">GO TO MY DASHBOARD</button>
      </main>
    </BfgShell>
  );
}
