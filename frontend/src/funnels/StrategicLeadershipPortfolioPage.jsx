import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Download } from "lucide-react";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicLeadershipPortfolioPage(){
  const {token}=useParams();
  const [data,setData]=useState(null);
  const [error,setError]=useState("");
  const [showRole,setShowRole]=useState(false);
  const roleRef=useRef(null);

  useEffect(()=>{
    axios.get(`${API}/guided/strategic-planning/leadership-portfolio/${token}`)
      .then(response=>setData(response.data))
      .catch(err=>setError(err.response?.data?.detail||"This portfolio is not available."));
  },[token]);

  const revealRole=()=>{
    setShowRole(true);
    window.setTimeout(()=>roleRef.current?.scrollIntoView({behavior:"smooth",block:"start"}),50);
  };

  if(error)return <main className="legal-page"><h1>Strategic Plan</h1><p>{error}</p></main>;
  if(!data)return <main className="legal-page"><p>Loading…</p></main>;

  return <main className="legal-page" style={{maxWidth:900,margin:"0 auto",padding:"40px 18px 80px"}}>
    <p className="eyebrow">{data.organization_name}</p>
    <h1>Our Strategic Plan</h1>
    <p>This is the Strategic Plan your Board reviewed and your organization approved. Read the plan first so you can see where the organization is going and how the different parts fit together.</p>

    <article className="standard-document" style={{margin:"28px 0",padding:"30px",border:"1px solid #e5e7eb",borderRadius:18,background:"#fff"}}>
      <pre style={{whiteSpace:"pre-wrap",fontFamily:"Georgia, serif",lineHeight:1.75,margin:0,textAlign:"left"}}>{data.strategic_plan_text}</pre>
    </article>

    <div style={{display:"flex",gap:12,justifyContent:"center",flexWrap:"wrap"}}>
      {data.strategic_plan_url&&<a className="button button-back" href={data.strategic_plan_url} target="_blank" rel="noreferrer">OPEN / PRINT STRATEGIC PLAN</a>}
      <button className="button" onClick={revealRole}>HOW I CAN GET INVOLVED</button>
    </div>

    {showRole&&<section ref={roleRef} style={{scrollMarginTop:30,marginTop:55,paddingTop:35,borderTop:"1px solid #e5e7eb"}}>
      <p className="eyebrow">YOUR ROLE IN THE PLAN</p>
      <h1>{data.member_name}'s Board Leadership Portfolio</h1>
      <p>This reflects the responsibility agreed during the Strategic Planning Session and confirmed by the organization leader.</p>
      <article className="standard-document" style={{margin:"26px 0",padding:"30px",border:"1px solid #e5e7eb",borderRadius:18,background:"#fff"}}>
        <pre style={{whiteSpace:"pre-wrap",fontFamily:"Georgia, serif",lineHeight:1.75,margin:0,textAlign:"left"}}>{data.display_text}</pre>
      </article>
      <div style={{display:"flex",gap:12,justifyContent:"center",flexWrap:"wrap"}}>
        <a className="button" href={`${API}/guided/strategic-planning/leadership-portfolio/${token}/pdf`}><Download size={16}/> DOWNLOAD MY PORTFOLIO</a>
        <a className="button" href={data.assistant_url||`/strategic-leadership-assistant/${token}`}>OPEN MY EXECUTIVE ASSISTANT</a>
      </div>
    </section>}
  </main>;
}
