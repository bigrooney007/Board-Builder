import { useEffect,useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Download } from "lucide-react";
const API=`${process.env.REACT_APP_BACKEND_URL}/api`;
export default function StrategicLeadershipPortfolioPage(){
 const {token}=useParams();const [data,setData]=useState(null),[error,setError]=useState("");
 useEffect(()=>{axios.get(`${API}/guided/strategic-planning/leadership-portfolio/${token}`).then(r=>setData(r.data)).catch(e=>setError(e.response?.data?.detail||"This portfolio is not available."))},[token]);
 if(error)return <main className="legal-page"><h1>Board Member Leadership Portfolio</h1><p>{error}</p></main>;
 if(!data)return <main className="legal-page"><p>Loading…</p></main>;
 return <main className="legal-page" style={{maxWidth:820,margin:"0 auto",padding:"40px 18px"}}><p className="eyebrow">{data.organization_name}</p><h1>{data.title}</h1><p><strong>{data.member_name}</strong></p><pre style={{whiteSpace:"pre-wrap",fontFamily:"Georgia, serif",lineHeight:1.7}}>{data.display_text}</pre><div style={{display:"flex",gap:12,flexWrap:"wrap"}}><a className="button" href={`${API}/guided/strategic-planning/leadership-portfolio/${token}/pdf`}><Download size={16}/> DOWNLOAD PORTFOLIO</a><a className="button" href={`/strategic-leadership-assistant/${token}`}>LET'S HELP YOU EXECUTE</a></div></main>
}
