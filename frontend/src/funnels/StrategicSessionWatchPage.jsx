import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicSessionWatchPage(){
  const {token}=useParams();
  const [data,setData]=useState(null);
  const [error,setError]=useState("");

  const load=useCallback(()=>{
    axios.get(`${API}/guided/strategic-planning/session/watch/${token}`)
      .then(response=>setData(response.data))
      .catch(err=>setError(err.response?.data?.detail||"This Strategic Planning session link is not available."));
  },[token]);

  useEffect(()=>{load();const timer=setInterval(load,2500);return()=>clearInterval(timer);},[load]);

  return <main className="guided-page sp-live-session sp-board-watch" data-testid="strategic-session-board-screen">
    <section className="sp-session-screen">
      <p className="bfg-eyebrow">LIVE STRATEGIC PLANNING SESSION</p>
      {error?<p className="bfg-error">{error}</p>:!data?<p>Joining the session…</p>:<>
        <h1>{data.organization_name}</h1>
        <div className="sp-session-topline"><span>Section {data.current_section_index+1} of {data.total_sections}</span><span>FOLLOWING THE FACILITATOR</span></div>
        {data.section?<>
          <h2 style={{fontSize:"clamp(28px,4vw,46px)",margin:"22px auto"}}>{data.section.title}</h2>
          {data.section.current_context&&<div className="sp-current-context"><span>WHERE THE ORGANIZATION IS STARTING</span><p>{data.section.current_context}</p></div>}
          <div className="sp-idea-grid">
            {data.section.ideas.map(idea=><article className={`sp-idea-card board-view ${idea.selected?"selected":""}`} key={idea.idea_id}>
              <span className="sp-idea-person">{idea.participant_name}</span>
              <p>{idea.idea}</p>
              {idea.selected&&<small>SELECTED BY THE BOARD</small>}
            </article>)}
          </div>
          {data.section.decision_mode==="__keep_current__"&&<div className="sp-board-decision">BOARD DECISION: LEAVE THE MISSION STATEMENT THE WAY IT IS</div>}
          {data.section.decision_mode==="__use_all_ideas__"&&<div className="sp-board-decision">BOARD DECISION: USE ALL IDEAS FROM THIS DISCUSSION</div>}
          {data.section.is_action_planning&&<div className="sp-action-planning-callout"><h2>Action Planning</h2><p>Discuss what happens next and say clearly who is agreeing to lead or support each responsibility. The facilitator will confirm every delegation before anything is sent after the session.</p></div>}
        </>:<p>The facilitator is preparing the first section.</p>}
      </>}
    </section>
  </main>;
}
