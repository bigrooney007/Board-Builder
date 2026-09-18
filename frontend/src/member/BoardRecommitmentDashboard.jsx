import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Copy, Mail, PlayCircle } from "lucide-react";
import { MemberShell } from "./MemberShell";
import { SupportBox } from "./CoursePages";
import { memberApi } from "./api";
import ReactivationStep2, { ResponseView } from "./ReactivationStep2";
import ReactivationUnderstand from "./ReactivationUnderstand";
import ReactivationStep3 from "./ReactivationStep3";
import ReactivationStep5 from "./ReactivationStep5";
import "./sgr.css";

const MemberResponse = ({ row }) => {
  const [open,setOpen]=useState(false); const [response,setResponse]=useState(null); const [error,setError]=useState("");
  const toggle=async()=>{const next=!open;setOpen(next);if(next&&row.status==="COMPLETED"&&!response){try{setResponse((await memberApi.get(`/reactivation/board-members/${row.member_record_id}/response`)).data)}catch{setError("We could not load this response.")}}};
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
 const [roster,setRoster]=useState(null),[email,setEmail]=useState(null),[copied,setCopied]=useState("");
 const load=useCallback(()=>memberApi.get("/reactivation/roster").then(r=>setRoster(r.data)).catch(()=>setRoster({members:[]})),[]);
 useEffect(()=>{load()},[load]);
 const copy=async(text,tag)=>{try{await navigator.clipboard.writeText(text)}catch{window.prompt("Copy:",text)}setCopied(tag);setTimeout(()=>setCopied(""),2000)};
 const loadEmail=()=>memberApi.get("/reactivation/recommitment-email").then(r=>setEmail(r.data)).catch(e=>window.alert(e.response?.data?.detail||"Approve the Recommitment Form first."));
 return <MemberShell><main className="member-page sgr" data-testid="board-recommitment-dashboard">
   <header className="member-page-heading"><p className="eyebrow">Nonprofit Board Builder</p><h1>BOARD RECOMMITMENT</h1><p><strong>Get clear answers from disengaged board members, have the right one-on-one conversation, and move forward with people who are ready to serve.</strong></p></header>

   <section className="member-card" data-testid="recommitment-tutorial">
    <p className="eyebrow">START HERE</p><h2><PlayCircle size={20}/> Watch The Board Recommitment Tutorial</h2>
    <p>Watch this first. It shows you how to send the form, review each response, prepare the conversation, record the conclusion and create the Board Member Portfolio.</p>
    <div style={{aspectRatio:"16/9",background:"#0f172a",color:"#fff",borderRadius:12,display:"grid",placeItems:"center",marginTop:16}}><div style={{textAlign:"center"}}><PlayCircle size={42}/><p style={{color:"#cbd5e1"}}>Tutorial video will appear here when the final video URL is added.</p></div></div>
   </section>

   <section style={{marginTop:26}} data-testid="recommitment-form-email">
    <div className="member-card"><p className="eyebrow">1. SEND THE RECOMMITMENT FORM</p><h2>Your Recommitment Form & Email</h2><p>Your form is the first thing you need. Send the same form link to each board member you need to recommit. Their completed responses will automatically appear below.</p></div>
    <ReactivationStep2/>
    <section className="member-card" style={{marginTop:12}}>
      <h2>Your Ready-To-Send Email</h2><p>Generate the email containing your Recommitment Form link, review it and copy it into your email.</p>
      {!email?<button className="button" onClick={loadEmail}><Mail size={15}/> SHOW MY RECOMMITMENT EMAIL</button>:<>
       <p><strong>Subject:</strong> {email.subject}</p><div style={{whiteSpace:"pre-wrap",border:"1px solid #ddd",padding:16,borderRadius:8}}>{email.body}</div>
       <p><strong>Form link:</strong> <span style={{wordBreak:"break-all"}}>{email.form_link}</span></p>
       <button className="button" onClick={()=>copy(`Subject: ${email.subject}\n\n${email.body.replace(/\[[^\]]+\]/,email.form_link)}`,"email")}><Copy size={15}/>{copied==="email"?" COPIED":" COPY EMAIL + FORM LINK"}</button>
      </>}
    </section>
   </section>

   <section className="member-card" style={{marginTop:26}} data-testid="recommitment-responses">
    <p className="eyebrow">2. BOARD MEMBER RESPONSES</p><h2>Everyone Who Completes The Form Appears Here</h2><p>Click a person's name to see their response. Then use the workflow immediately below to interpret what they told you and prepare the conversation.</p>
    {!roster?<p>Loading board members…</p>:roster.members.length===0?<p>No board members have been added yet. Your completed generic Recommitment Form responses will appear here.</p>:roster.members.map(row=><MemberResponse key={row.member_record_id} row={row}/>)}
   </section>

   <section style={{marginTop:26}} data-testid="recommitment-interpret-conversation">
    <div className="member-card"><p className="eyebrow">3. INTERPRET & HAVE THE CONVERSATION</p><h2>Understand Their Response. Prepare The Call. Record What You Agreed.</h2><p>For each person who responded, interpret their answers, generate the one-on-one call script, have the conversation, then save the conclusion and final outcome. Saving what was actually agreed becomes the authoritative basis for their portfolio.</p></div>
    <ReactivationUnderstand/>
    <ReactivationStep3/>
   </section>

   <section style={{marginTop:26}} data-testid="recommitment-portfolios">
    <div className="member-card"><p className="eyebrow">4. CREATE THEIR BOARD MEMBER PORTFOLIO</p><h2>Turn The Recommitment Conversation Into Clear Responsibility</h2><p>Once the conversation conclusion and outcome are saved, generate the Board Member Portfolio for anyone continuing in an active or eligible support role. Review it, approve it, then prepare and send the portfolio email.</p></div>
    <ReactivationStep5/>
   </section>

   <div id="recommitment-support" style={{marginTop:26}} data-testid="recommitment-support">
    <SupportBox productKey="reactivation_self_guided" moduleNumber={1} supportTypes={["I have a question about Board Recommitment","I need help interpreting a board member response","I need help preparing for a conversation","I need help using the platform"]}/>
   </div>
 </main></MemberShell>
}
