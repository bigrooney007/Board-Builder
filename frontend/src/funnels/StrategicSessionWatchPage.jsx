import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicSessionWatchPage(){
  const {token}=useParams();
  const [data,setData]=useState(null);
  const [error,setError]=useState("");
  const [accepted,setAccepted]=useState(false);
  const participantToken=new URLSearchParams(window.location.search).get("participant")||"";

  const load=useCallback(()=>{
    axios.get(`${API}/guided/strategic-planning/session/watch/${token}`,{params:{participant_token:participantToken}})
      .then(response=>setData(response.data))
      .catch(err=>setError(err.response?.data?.detail||"This Strategic Planning session link is not available."));
  },[token,participantToken]);

  useEffect(()=>{load();const timer=setInterval(load,2500);return()=>clearInterval(timer);},[load]);

  return <main className="guided-page sp-live-session sp-board-watch" data-testid="strategic-session-board-screen">
    <section className="sp-session-screen">
      <p className="bfg-eyebrow">LIVE STRATEGIC PLANNING SESSION</p>
      {error?<p className="bfg-error">{error}</p>:!data?<p>Joining the session…</p>:<>
        <h1>{data.organization_name}</h1>
        <div className="sp-session-topline"><span>{data.status==="COMPLETED"?"BOARD REVIEW":`Section ${data.current_section_index+1} of ${data.total_sections}`}</span><span>FOLLOWING THE FACILITATOR</span></div>
        {data.questionnaire_version==="strategic-24-months-15"&&["REVIEW","COMPLETED"].includes(data.status)?<>
          <h2>Our Agreed Direction For The Next 24 Months</h2>{(data.adopted_areas||[]).map(area=><article className="sp-current-context" key={area.area_key}><h3>{area.area}</h3>{area.agreed_ideas.map((idea,i)=><p key={i}><strong>{idea.participant_name}: </strong>{idea.text}</p>)}</article>)}
          {data.participant?(data.participant.acknowledged?<p>You have acknowledged this direction and your agreed responsibilities.</p>:<><label><input type="checkbox" checked={accepted} onChange={e=>setAccepted(e.target.checked)}/> I have reviewed this direction and accept my own agreed responsibilities.</label><button className="bfg-btn bfg-btn-primary" disabled={!accepted} onClick={async()=>{try{await axios.post(`${API}/guided/strategic-planning/session/acknowledge/${participantToken}`,{revision:data.decision_revision,confirmed:true,accept_responsibilities:accepted});load()}catch(e){setError(e.response?.data?.detail||"Could not save your acknowledgement")}}}>I ADOPT THIS AGREED DIRECTION</button></>):<p>Open this session through your personal contribution link to record your own acknowledgement.</p>}
          {data.plan_text&&<pre className="sp-plan-preview">{data.plan_text}</pre>}
        </>:data.status==="COMPLETED"?<><h2>Review The Strategic Plan Together</h2><p>{data.plan_status==="Approved"?"The Board's Strategic Plan has been adopted.":"Discuss the plan with the facilitator. Agreed edits and approval will appear here."}</p>{data.plan_text?<pre className="sp-plan-preview">{data.plan_text}</pre>:<p>Preparing the plan from the decisions you made together…</p>}</>:data.section?<>
          <h2 style={{fontSize:"clamp(28px,4vw,46px)",margin:"22px auto"}}>{data.section.title}</h2>
          {data.section.subtitle&&<p className="guided-preflow-help">{data.section.subtitle}</p>}
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
