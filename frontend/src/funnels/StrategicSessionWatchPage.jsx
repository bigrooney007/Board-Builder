import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import { BfgShell } from "@/game/gameShared";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;
export default function StrategicSessionWatchPage(){
 const {token}=useParams();const [data,setData]=useState(null),[error,setError]=useState("");
 const load=useCallback(()=>axios.get(`${API}/guided/strategic-planning/session/watch/${token}`).then(r=>setData(r.data)).catch(e=>setError(e.response?.data?.detail||"This Strategic Planning session link is not available.")),[token]);
 useEffect(()=>{load();const timer=setInterval(load,2500);return()=>clearInterval(timer)},[load]);
 return <BfgShell><main className="guided-page sp-dashboard"><section className="guided-section"><p className="bfg-eyebrow">LIVE STRATEGIC PLANNING SESSION</p>{error?<p className="bfg-error">{error}</p>:!data?<p>Joining the session…</p>:<><h1>{data.organization_name}</h1><p>Section {data.current_section_index+1} of {data.total_sections}. This screen follows the meeting host automatically.</p>{data.section?<div className="sp-contentbox"><h2>{data.section.title}</h2>{data.section.ideas.map((idea,i)=><article className="choice" key={`${idea.participant_name}-${i}`}><strong>{idea.participant_name}</strong><span style={{whiteSpace:"pre-wrap"}}>{idea.idea}</span></article>)}<div className="sp-contentbox"><h3>Nonprofit Board Builder Recommended Ideas</h3><ul>{data.section.recommendations?.map((idea,i)=><li key={i}>{idea}</li>)}</ul></div></div>:<p>The host is preparing the first section.</p>}</>}</section></main></BfgShell>
}
