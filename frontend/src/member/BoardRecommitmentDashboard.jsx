import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { MemberShell } from "./MemberShell";
import { SupportBox } from "./CoursePages";
import { memberApi } from "./api";
import ReactivationStep2, { ResponseView } from "./ReactivationStep2";
import ReactivationUnderstand from "./ReactivationUnderstand";
import ReactivationStep3 from "./ReactivationStep3";
import ReactivationStep5 from "./ReactivationStep5";
import FounderBoardAudit from "./FounderBoardAudit";
import "./sgr.css";

const MemberResponse = ({ row }) => {
  const requested=new URLSearchParams(window.location.search).get("member");
  const [open,setOpen]=useState(requested===row.member_record_id); const [response,setResponse]=useState(null); const [error,setError]=useState("");
  useEffect(()=>{if(open&&row.status==="COMPLETED"&&!response)memberApi.get(`/reactivation/board-members/${row.member_record_id}/response`).then(r=>setResponse(r.data)).catch(()=>setError("We could not load this response."))},[open,response,row.member_record_id,row.status]);
  const toggle=()=>setOpen(!open);
  return <article className="member-card" style={{marginTop:12}} data-testid={`recommitment-person-${row.member_record_id}`}>
    <button type="button" onClick={toggle} style={{width:"100%",border:0,background:"transparent",display:"flex",justifyContent:"space-between",alignItems:"center",cursor:"pointer",padding:0,textAlign:"left"}}>
      <div><h3 style={{margin:0}}>{row.name}</h3><p style={{margin:"5px 0 0"}}>{row.role||"Board Member"} · <strong>{row.status==="COMPLETED"?"Response received":"Waiting for response"}</strong></p></div>{open?<ChevronUp/>:<ChevronDown/>}
    </button>
    {open&&<div style={{marginTop:18}}>
      {row.status!=="COMPLETED"?<p>Once this board member completes the Recommitment Form, their response and next actions will appear here.</p>:<>
        {response?<ResponseView data={response} testPrefix={`recommitment-dashboard-${row.member_record_id}`}/>:<p>Loading response…</p>}
        {error&&<p className="submit-error">{error}</p>}
        <p style={{marginTop:18}}><strong>Next:</strong> use the tools below to interpret this response, prepare the one-on-one conversation, save what you agreed, and create the Board Member Portfolio.</p>
      </>}
    </div>}
  </article>
};

export default function BoardRecommitmentDashboard(){
 const [roster,setRoster]=useState(null);
 const [open,setOpen]=useState("1");
 const load=useCallback(()=>memberApi.get("/reactivation/roster").then(r=>setRoster(r.data)).catch(()=>setRoster({members:[]})),[]);
 useEffect(()=>{load()},[load]);
 useEffect(()=>{const requested=new URLSearchParams(window.location.search).get("member");if(requested)setTimeout(()=>document.querySelector(`[data-testid="recommitment-person-${requested}"]`)?.scrollIntoView({behavior:"smooth",block:"center"}),150)},[roster]);
 return <MemberShell><main className="member-page sgr" data-testid="board-recommitment-dashboard">
   <header className="member-page-heading"><p className="eyebrow">Nonprofit Board Builder</p><h1>BOARD RECOMMITMENT</h1><p><strong>Get clear answers from disengaged board members, have the right one-on-one conversation, and move forward with people who are ready to serve.</strong></p></header>

   <CompactSection n="1" title="Generate The Recommitment Form And Email" open={open==="1"} onOpen={()=>setOpen(open==="1"?"":"1")}><p>Generate the form first, then generate the matching email and send its link to each Board Member.</p><ReactivationStep2/></CompactSection>
   <CompactSection n="2" title="Complete The Founder / Executive Director Audit" open={open==="2"} onOpen={()=>setOpen(open==="2"?"":"2")}><FounderBoardAudit/></CompactSection>

   <CompactSection n="3" title="See Everyone Who Has Completed The Form" open={open==="3"} onOpen={()=>setOpen(open==="3"?"":"3")}><div id="recommitment-responses" data-testid="recommitment-responses">
    <p className="eyebrow">2. BOARD MEMBER RESPONSES</p><h2>Everyone Who Completes The Form Appears Here</h2><p>Click a person's name to see their response. Then use the workflow immediately below to interpret what they told you and prepare the conversation.</p>
    {!roster?<p>Loading board members…</p>:roster.members.length===0?<p>No board members have been added yet. Your completed generic Recommitment Form responses will appear here.</p>:roster.members.map(row=><MemberResponse key={row.member_record_id} row={row}/>)}
   </div></CompactSection>

   <CompactSection n="4" title="Interpret Each Response And Prepare The Conversation" open={open==="4"} onOpen={()=>setOpen(open==="4"?"":"4")}><div data-testid="recommitment-interpret-conversation"><p>For each person, use their response and organization information to interpret what they said, generate the one-on-one script, then record what was actually agreed.</p>
    <ReactivationUnderstand/>
    <ReactivationStep3/>
   </div></CompactSection>

   <CompactSection n="5" title="Summarize The Board And Create The Correct Next-Step Resources" open={open==="5"} onOpen={()=>setOpen(open==="5"?"":"5")}><div data-testid="recommitment-portfolios"><p>The summary shows who is stepping up, stepping down or moving to an advisory role. Each person then receives only the email or portfolio appropriate to the confirmed outcome.</p>
    <ReactivationStep5/>
   </div></CompactSection>

   <div id="recommitment-support" style={{marginTop:26}} data-testid="recommitment-support">
    <SupportBox productKey="reactivation_self_guided" moduleNumber={1} supportTypes={["I have a question about Board Recommitment","I need help interpreting a board member response","I need help preparing for a conversation","I need help using the platform"]}/>
   </div>
 </main></MemberShell>
}

const CompactSection=({n,title,open,onOpen,children})=><section className="member-card compact-flow-section"><button type="button" className="compact-flow-toggle" onClick={onOpen}><span>{n}</span><strong>{title}</strong>{open?<ChevronUp/>:<ChevronDown/>}</button>{open&&<div className="compact-flow-body">{children}</div>}</section>;
