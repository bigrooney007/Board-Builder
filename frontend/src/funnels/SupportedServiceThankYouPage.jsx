import { useEffect } from "react";
import { CheckCircle2 } from "lucide-react";
import { BfgShell } from "@/game/gameShared";
import { memberApi } from "@/member/api";

export default function SupportedServiceThankYouPage(){
  useEffect(()=>{document.title="Thank You | Nonprofit Board Builder";memberApi.post("/members/supported-service/handoff-complete").catch(()=>{});},[]);
  return <BfgShell><main className="bfg-flow" style={{maxWidth:720,margin:"0 auto",padding:"70px 20px 100px",textAlign:"center"}} data-testid="supported-service-thank-you">
    <section className="bfg-card" style={{padding:"38px 28px"}}><CheckCircle2 size={58} color="#087f5b"/><p className="bfg-eyebrow" style={{marginTop:16}}>YOUR INFORMATION IS SAVED</p><h1 style={{fontSize:"clamp(30px,5vw,44px)",lineHeight:1.1}}>Thank You. Rooney Will Take It From Here With You.</h1><p style={{fontSize:18,maxWidth:580,margin:"18px auto 0"}}>We have received the information needed to begin your supported process. Rooney will be in touch within the next 24 hours to confirm the next step and start working with you.</p><p style={{marginTop:18,fontWeight:800}}>You do not need to complete anything else in the platform right now.</p></section>
  </main></BfgShell>;
}
