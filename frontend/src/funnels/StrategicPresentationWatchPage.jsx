import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import { BfgShell } from "@/game/gameShared";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;
export default function StrategicPresentationWatchPage(){
 const {token}=useParams(),[data,setData]=useState(null),[error,setError]=useState("");
 const load=useCallback(()=>axios.get(`${API}/guided/strategic-planning/presentation-meeting/watch/${token}`).then(r=>setData(r.data)).catch(e=>setError(e.response?.data?.detail||"This presentation meeting link is not available.")),[token]);
 useEffect(()=>{load();const timer=setInterval(load,2500);return()=>clearInterval(timer)},[load]);
 return <BfgShell><main className="guided-page sp-dashboard"><section className="guided-section"><p className="bfg-eyebrow">LIVE BOARD STRATEGIC PLANNING SESSION</p>{error?<p className="bfg-error">{error}</p>:!data?<p>Joining the session…</p>:<><h1>{data.organization_name}</h1><p>Section {data.current_area_index+1} of {data.total_areas}. This screen follows the Lead User automatically while the Board presents, discusses, adopts and delegates.</p>{data.area?<div className="sp-contentbox"><h2>{data.area.area}</h2>{data.area.owner_name&&<p><strong>First plan builder / presenter:</strong> {data.area.owner_name}</p>}<p style={{whiteSpace:"pre-wrap"}}>{data.area.submitted_plan||data.area.direction}</p>{(data.approved_area_keys||[]).includes(data.area.area_key)&&<p className="member-success"><strong>BOARD ADOPTED THIS SECTION</strong></p>}</div>:<p>The facilitator is preparing the first section.</p>}</>}</section></main></BfgShell>;
}
