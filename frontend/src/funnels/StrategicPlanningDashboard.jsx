import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { CheckCircle2, ClipboardList, Download, FileText, Mail, PlayCircle, Search, Users } from "lucide-react";
import { BfgShell } from "@/game/gameShared";
import "@/game/game.css";
import "./guided-products.css";
import "./strategic-planning-dashboard.css";
const API=`${process.env.REACT_APP_BACKEND_URL}/api`;
const A=({children,onClick,disabled=false})=><button className="bfg-btn bfg-btn-primary bfg-btn-sm" disabled={disabled} onClick={onClick}>{children}</button>;
const Card=({n,title,children})=><section className="sp-dash-card"><div className="sp-step">{n}</div><h2>{title}</h2>{children}</section>;

export default function StrategicPlanningDashboard(){
 const sid=new URLSearchParams(window.location.search).get("session_id")||"";const [ctx,setCtx]=useState(null),[busy,setBusy]=useState(""),[msg,setMsg]=useState("");
 const [project,setProject]=useState(null),[community,setCommunity]=useState(null),[email,setEmail]=useState(null);
 const [invite,setInvite]=useState({name:"",email:""}),[session,setSession]=useState(null),[sessionStep,setSessionStep]=useState(0),[decisions,setDecisions]=useState({}),[transcript,setTranscript]=useState(""),[listening,setListening]=useState(false);const recognition=useRef(null);
 const load=useCallback(async()=>{try{const r=await axios.get(`${API}/guided/strategic-planning/workspace`,{params:{session_id:sid}});setCtx(r.data);setProject(r.data.project);setCommunity(r.data.community_research||null);const s=await axios.get(`${API}/guided/strategic-planning/session`,{params:{session_id:sid}});setSession(s.data);setDecisions(Object.fromEntries((s.data.sections||[]).map(x=>[x.key,x.selected_participant_id]).filter(x=>x[1])));setTranscript(s.data.transcript||"")}catch(e){setMsg(e.response?.data?.detail||"We could not load your Strategic Planning workspace.")}},[sid]);
 useEffect(()=>{load()},[load]);
 const act=async(key,fn)=>{setBusy(key);setMsg("");try{await fn();await load()}catch(e){setMsg(e.response?.data?.detail||"That action could not be completed yet.")}setBusy("")};
 const respondents=project?.participants?.filter(x=>x.status==="COMPLETED")||[];const areas=project?.areas||[];const submitted=areas.filter(x=>x.plan_submitted_at||x.submitted_plan).length;
 const delegations=respondents.map(person=>({...person,assigned:areas.filter(area=>area.owner_participant_id===person.participant_id)})).filter(person=>person.assigned.length);
 const formLink=project?.generic_form_token?`${window.location.origin}/strategic-planning-form/${project.generic_form_token}`:"";
 const leadFormLink=project?.lead_form_token?`${window.location.origin}/strategic-planning-form/${project.lead_form_token}`:"";
 const researchLink=community?.token?`${window.location.origin}/community-need-research/${community.token}`:"";
 const copy=t=>navigator.clipboard?.writeText(t);
 const uploadLogo=(file)=>{if(!file)return;const reader=new FileReader();reader.onload=()=>act("logo",()=>axios.post(`${API}/guided/strategic-planning/branding`,{session_id:sid,logo_data_url:reader.result}));reader.readAsDataURL(file)};
 const startListening=()=>{const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){setMsg("Live transcription is not supported in this browser. Use the transcript box to paste or type the meeting discussion.");return}const r=new SpeechRecognition();r.continuous=true;r.interimResults=true;r.onresult=e=>{let text="";for(let i=e.resultIndex;i<e.results.length;i++)if(e.results[i].isFinal)text+=e.results[i][0].transcript+" ";if(text)setTranscript(current=>(current+" "+text).trim())};r.onend=()=>setListening(false);r.start();recognition.current=r;setListening(true)};
 const stopListening=()=>{recognition.current?.stop();setListening(false)};
 if(!ctx)return <BfgShell><main className="guided-page"><section className="guided-section"><h1>Strategic Planning</h1><p>{msg||"Preparing your workspace…"}</p></section></main></BfgShell>;
 return <BfgShell><main className="guided-page sp-dashboard">
  <section className="guided-section sp-dash-head"><p className="bfg-eyebrow">STRATEGIC PLANNING WITH YOUR BOARD</p><h1>{ctx.organization_name||"Your Strategic Planning Dashboard"}</h1><p className="guided-intro">Create the roadmap with your board, delegate leadership for the different parts of the organization, and build the structures your mission needs.</p></section>
  <section className="sp-tutorial"><PlayCircle size={44}/><h2>Watch The Strategic Planning Tutorial</h2><p>See the complete process before you begin: organization intake, optional community research, Board review form, live planning session, delegation, detailed plans, final Strategic Plan and Board Member Portfolios.</p><div className="guided-video"><PlayCircle size={40}/><strong>Strategic Planning Tutorial</strong><span>Final tutorial video URL will be added before launch.</span></div></section>

  <div className="sp-dash-stack">
   <Card n="OPTIONAL" title="Launch Community Need Research">
    <p>Survey the public before your board plans. The survey asks about the need your mission addresses, the best approaches to solving it and how respondents could help.</p>
    {!community?<A disabled={busy==="research"} onClick={()=>act("research",()=>axios.post(`${API}/guided/strategic-planning/community-research`,{session_id:sid}))}><Search size={15}/> {busy==="research"?"CREATING…":"CREATE COMMUNITY NEED SURVEY + PROMOTION KIT"}</A>:<>
      <div className="sp-linkbox"><strong>Your public survey</strong><span>{researchLink}</span><button onClick={()=>copy(researchLink)}>COPY LINK</button></div>
      <div className="sp-contentbox"><h3>5 Social Media Posts To Promote The Survey</h3>{community.social_posts?.map((p,i)=><p key={i}><strong>Post {i+1}:</strong> {p}</p>)}</div>
      <p>{community.response_count||0} public responses received.</p>
    </>}
    <p className="sp-note">Don't need public research? Skip this and go directly to your Board Strategic Planning Form.</p>
   </Card>

   <Card n="1" title="Send Your Strategic Planning Form To The Board">
    <p>Your form is built from the information you gave us after payment. It reviews your mission, goals, objectives, programs, team building, operations, marketing, partnerships, fundraising, technology, budget, organizational priorities and action planning.</p>
    <label className="sp-contentbox"><strong>Upload Your Organization Logo</strong><p>The logo appears centrally above the organization name on your Strategic Planning Form.</p><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>uploadLogo(e.target.files?.[0])}/></label>
    {formLink?<><div className="sp-linkbox"><strong>Your Strategic Planning Form</strong><span>{formLink}</span><button onClick={()=>copy(formLink)}>COPY FORM LINK</button></div>{leadFormLink&&<div className="sp-linkbox"><strong>Your Lead User Form</strong><span>{leadFormLink}</span><button onClick={()=>window.location.href=leadFormLink}>COMPLETE MY FORM</button></div>}<div className="sp-contentbox"><h3>Send The Form To A Board Member</h3><input placeholder="Board Member Name" value={invite.name} onChange={e=>setInvite({...invite,name:e.target.value})}/><input type="email" placeholder="Board Member Email" value={invite.email} onChange={e=>setInvite({...invite,email:e.target.value})}/><A disabled={!invite.name||!invite.email||busy==="invite"} onClick={()=>act("invite",async()=>{await axios.post(`${API}/guided/strategic-planning/invite`,{session_id:sid,...invite});setInvite({name:"",email:""})})}><Mail size={15}/> {busy==="invite"?"SENDING…":"SEND STRATEGIC PLANNING FORM"}</A></div></>:<A disabled={busy==="form"} onClick={()=>act("form",()=>axios.post(`${API}/guided/strategic-planning/prepare-form`,{session_id:sid}))}><ClipboardList size={15}/> {busy==="form"?"PREPARING…":"GENERATE MY STRATEGIC PLANNING FORM"}</A>}
    {formLink&&<div className="sp-actions"><A onClick={async()=>{const r=await axios.get(`${API}/guided/strategic-planning/form-email`,{params:{session_id:sid}});setEmail(r.data)}}><Mail size={15}/> GENERATE EMAIL TO SEND THE FORM</A></div>}
    {email&&<div className="sp-contentbox"><h3>{email.subject}</h3><p style={{whiteSpace:"pre-wrap"}}>{email.body}</p><A onClick={()=>copy(`Subject: ${email.subject}\n\n${email.body}\n\n${email.form_link||formLink}`)}>COPY EMAIL + LINK</A></div>}
   </Card>

   <Card n="2" title="See Everyone Who Has Completed The Form">
    <p>Each board member appears here as soon as they submit. Open their response online or download a copy for your records.</p>
    {!respondents.length?<p className="sp-empty">No completed board responses yet.</p>:<div className="sp-people">{respondents.map(p=><article key={p.participant_id}><Users size={18}/><div><strong>{p.name}</strong><span>{p.role||"Board Member"}</span></div><div className="sp-actions"><a href={`/strategic-planning-response/${p.participant_id}`} target="_blank" rel="noreferrer">VIEW RESPONSE</a><a href={`${API}/strategic-planning-response/${p.participant_id}/pdf`}>DOWNLOAD</a></div></article>)}</div>}
   </Card>

   <Card n="3" title="Start The Strategic Planning Session">
    <p>Review every section with the board. Choose the idea the board agrees will become the direction. The contributor whose idea is selected becomes the person delegated to build that section.</p>
    {!session?.sections?.length?<p className="sp-note">Generate the form and receive at least one completed response before starting the session.</p>:<>{session.status!=="COMPLETED"&&<div className="sp-contentbox"><h3>{session.sections[sessionStep]?.title}</h3>{session.sections[sessionStep]?.ideas.map(idea=><label className={`choice ${decisions[session.sections[sessionStep].key]===idea.participant_id?"selected":""}`} key={idea.participant_id}><input type="radio" name={session.sections[sessionStep].key} checked={decisions[session.sections[sessionStep].key]===idea.participant_id} onChange={()=>setDecisions({...decisions,[session.sections[sessionStep].key]:idea.participant_id})}/><strong>{idea.participant_name}</strong><span style={{whiteSpace:"pre-wrap"}}>{idea.idea}</span></label>)}<div className="sp-actions">{sessionStep>0&&<button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={()=>setSessionStep(sessionStep-1)}>BACK</button>}{sessionStep<session.sections.length-1&&<A disabled={!decisions[session.sections[sessionStep].key]} onClick={()=>setSessionStep(sessionStep+1)}>AGREE AND NEXT</A>}</div></div>}<div className="sp-contentbox"><h3>Meeting Transcript</h3><p>Allow microphone access so the discussion can become context when AI helps each delegated person build their detailed plan.</p><A onClick={listening?stopListening:startListening}>{listening?"STOP LISTENING":"START MICROPHONE TRANSCRIPTION"}</A><textarea rows={8} value={transcript} onChange={e=>setTranscript(e.target.value)} placeholder="The live transcript appears here. You can also paste a transcript."/></div>{session.status!=="COMPLETED"&&<A disabled={Object.keys(decisions).length<session.sections.length||busy==="session"} onClick={()=>act("session",()=>axios.post(`${API}/guided/strategic-planning/session/complete`,{session_id:sid,decisions,transcript}))}>{busy==="session"?"SAVING SESSION…":"END SESSION AND START DELEGATION"}</A>}</>}
   </Card>

   <Card n="4" title="Generate The Strategic Planning Facilitation Guide">
    <p>Use the guide to run the session, discuss every contribution, select the agreed direction and explain what happens after delegation.</p>
    <A disabled={!respondents.length||busy==="guide"} onClick={()=>act("guide",()=>axios.post(`${API}/guided/strategic-planning/facilitation-guide`,{session_id:sid}))}><FileText size={15}/> {busy==="guide"?"PREPARING…":"GENERATE STRATEGIC PLANNING FACILITATION GUIDE"}</A>
    {project?.meeting_guide_text&&<div className="sp-contentbox"><p style={{whiteSpace:"pre-wrap"}}>{project.meeting_guide_text}</p></div>}
   </Card>

   <Card n="5" title="Start Delegation">
    <p>Each selected contributor receives one delegation email containing every section assigned to them. Each section includes the agreed direction, all other ideas, the session transcript and instructions for building the detailed plan they will present at the next meeting.</p>
    {!delegations.length?<p className="sp-note">Complete the Strategic Planning Session to create the delegations.</p>:<div className="sp-area-grid">{delegations.map(person=><article key={person.participant_id}><h3>{person.name}</h3><p><strong>Delegated sections:</strong> {person.assigned.map(a=>a.area).join(", ")}</p><p>{person.assigned.filter(a=>a.plan_submitted_at||a.submitted_plan).length} of {person.assigned.length} detailed plans submitted.</p><A disabled={busy===`delegate-${person.participant_id}`} onClick={()=>act(`delegate-${person.participant_id}`,()=>axios.post(`${API}/guided/strategic-planning/send-delegation`,{session_id:sid,participant_id:person.participant_id}))}><Mail size={14}/> {busy===`delegate-${person.participant_id}`?"SENDING…":"SEND DELEGATION"}</A></article>)}</div>}
   </Card>

   <Card n="6" title="Board Members Build Their Detailed Plans With AI">
    <p>Each delegation email carries the links for that person's assigned sections. Every link includes the agreed direction, everybody's ideas and the meeting context. The Board Member selects <strong>Start Building My Detailed Plan With AI</strong>, corrects the editable draft, approves it and can then download it. The approved copy remains saved here for the Final Strategic Plan.</p>
    <div className="sp-progress"><strong>{submitted} of {areas.length} strategic area plans completed</strong><div><span style={{width:`${areas.length?(submitted/areas.length)*100:0}%`}}/></div></div>
   </Card>

   <Card n="7" title="Build And Download The Final Strategic Plan">
    <p>The Final Strategic Plan combines the approved foundational plan with every detailed strategic area plan submitted by your board members.</p>
    <A disabled={!areas.length||submitted<areas.length||busy==="final"} onClick={()=>act("final",()=>axios.post(`${API}/guided/strategic-planning/final-plan`,{session_id:sid}))}><FileText size={15}/> {busy==="final"?"CONSOLIDATING…":"GENERATE FINAL STRATEGIC PLAN"}</A>
    {submitted<areas.length&&areas.length>0&&<p className="sp-note">{areas.length-submitted} strategic area plan{areas.length-submitted===1?" is":"s are"} still outstanding.</p>}
    {project?.final_plan?.display_text&&<div className="sp-actions"><a className="bfg-btn bfg-btn-primary bfg-btn-sm" href={`${API}/guided/strategic-planning/final-plan/pdf?session_id=${encodeURIComponent(sid)}`}><Download size={15}/> DOWNLOAD FINAL STRATEGIC PLAN</a></div>}
   </Card>

   <Card n="8" title="Send The Present Strategic Plan To The Board">
    <p>Everyone who completed the Strategic Planning Form appears here. Send the complete present plan to all participants when it is ready.</p>
    <div className="sp-people">{respondents.map(p=><article key={p.participant_id}><Users size={18}/><div><strong>{p.name}</strong><span>{p.email}</span></div></article>)}</div>
    <A disabled={!project?.final_plan?.display_text||busy==="send-final"} onClick={()=>act("send-final",()=>axios.post(`${API}/guided/strategic-planning/send-final-plan`,{session_id:sid}))}><Mail size={15}/> {busy==="send-final"?"SENDING…":"SEND PRESENT STRATEGIC PLAN"}</A>
   </Card>

   <Card n="9" title="Create Each Board Member's Leadership Portfolio">
    <p>After the Final Strategic Plan is complete, create a portfolio for each board member showing the strategic areas delegated to them and their responsibility to provide leadership and oversight as the execution structures are built.</p>
    <A disabled={!project?.final_plan?.display_text||busy==="portfolios"} onClick={()=>act("portfolios",()=>axios.post(`${API}/guided/strategic-planning/portfolios`,{session_id:sid}))}><CheckCircle2 size={15}/> {busy==="portfolios"?"CREATING…":"GENERATE BOARD MEMBER PORTFOLIOS"}</A>
    {!!project?.portfolios?.length&&<div className="sp-people">{project.portfolios.map(p=><article key={p.participant_id}><Users size={18}/><div><strong>{p.name}</strong><span>{p.areas?.join(", ")}</span></div><a href={p.url||"#"} target="_blank" rel="noreferrer">VIEW PORTFOLIO</a></article>)}</div>}
   </Card>
   {msg&&<p className="bfg-error">{msg}</p>}
   <section className="sp-support"><h2>Need Support?</h2><p>If you get stuck at any stage of the Strategic Planning process, ask us for help.</p><a className="bfg-btn bfg-btn-ghost" href="mailto:support@nonprofitboardbuilder.com?subject=Strategic%20Planning%20Support">ASK FOR SUPPORT</a></section>
  </div>
 </main></BfgShell>
}
