import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "@/game/game.css";
import "./guided-products.css";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicSessionWatchPage(){
 const {token}=useParams();
 const [data,setData]=useState(null),[error,setError]=useState("");
 const load=useCallback(()=>axios.get(`${API}/guided/strategic-planning/session/watch/${token}`).then(r=>setData(r.data)).catch(e=>setError(e.response?.data?.detail||"This Strategic Planning session link is not available.")),[token]);
 useEffect(()=>{load();const timer=setInterval(load,2000);return()=>clearInterval(timer)},[load]);

 return <div className="bfg guided-page sp-live-session sp-board-watch"><main className="sp-session-screen">
  {error?<p className="bfg-error">{error}</p>:!data?<p>Joining the Strategic Planning Session…</p>:<>
   <div className="sp-session-topline"><span>LIVE BOARD SCREEN</span><span>Section {data.current_section_index+1} of {data.total_sections}</span></div>
   <p className="bfg-eyebrow">{data.organization_name}</p>
   {data.status!=="IN PROGRESS"?<div className="sp-session-finished"><h1>The host is preparing the session.</h1><p>Keep this screen open. It will update automatically when the Strategic Planning Session starts.</p></div>:data.section?<>
    <h1>{data.section.title}</h1>
    {data.section.current_context&&<div className="sp-current-context"><span>WHERE THE ORGANIZATION IS STARTING</span><p>{data.section.current_context}</p></div>}
    <div className="sp-idea-grid">{data.section.ideas.map(idea=><article className={`sp-idea-card board-view ${idea.selected?"selected":""}`} key={idea.idea_id}><span className="sp-idea-person">{idea.participant_name}</span><p>{idea.idea}</p>{idea.selected&&<small>SELECTED BY THE BOARD</small>}</article>)}</div>
    {data.section.decision_mode==="__keep_current__"&&<div className="sp-board-decision">BOARD DECISION: Keep the present Mission Statement.</div>}
    {data.section.decision_mode==="__use_all_ideas__"&&<div className="sp-board-decision">BOARD DECISION: Use all ideas from this discussion.</div>}
    {data.section.is_action_planning&&<div className="sp-action-planning-callout"><h2>Action Planning</h2><p>Discuss what happens next and say clearly who is agreeing to help lead or support each responsibility.</p></div>}
   </>:<p>The host is preparing the first section.</p>}
  </>}
 </main></div>;
}
