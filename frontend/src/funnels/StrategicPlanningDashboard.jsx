import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { CheckCircle2, ClipboardList, Download, ExternalLink, FileText, Mail, PlayCircle, Search, Sparkles, Users } from "lucide-react";
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
 const load=async()=>{try{const r=await axios.get(`${API}/guided/strategic-planning/workspace`,{params:{session_id:sid}});setCtx(r.data);setProject(r.data.project);setCommunity(r.data.community_research||null)}catch(e){setMsg(e.response?.data?.detail||"We could not load your Strategic Planning workspace.")}};
 useEffect(()=>{load()},[]);
 const act=async(key,fn)=>{setBusy(key);setMsg("");try{await fn();await load()}catch(e){setMsg(e.response?.data?.detail||"That action could not be completed yet.")}setBusy("")};
 const respondents=project?.participants?.filter(x=>x.status==="COMPLETED")||[];const areas=project?.areas||[];const submitted=areas.filter(x=>x.plan_submitted_at||x.submitted_plan).length;
 const formLink=project?.generic_form_token?`${window.location.origin}/strategic-planning-form/${project.generic_form_token}`:"";
 const leadFormLink=project?.lead_form_token?`${window.location.origin}/strategic-planning-form/${project.lead_form_token}`:"";
 const researchLink=community?.token?`${window.location.origin}/community-need-research/${community.token}`:"";
 const copy=t=>navigator.clipboard?.writeText(t);
 if(!ctx)return <BfgShell><main className="guided-page"><section className="guided-section"><h1>Strategic Planning</h1><p>{msg||"Preparing your workspace…"}</p></section></main></BfgShell>;
 return <BfgShell><main className="guided-page sp-dashboard">
  <section className="guided-section sp-dash-head"><p className="bfg-eyebrow">STRATEGIC PLANNING WITH YOUR BOARD</p><h1>{ctx.organization_name||"Your Strategic Planning Dashboard"}</h1><p className="guided-intro">Create the roadmap with your board, delegate leadership for the different parts of the organization, and build the structures your mission needs.</p></section>
  <section className="sp-tutorial"><PlayCircle size={44}/><h2>Watch The Strategic Planning Tutorial</h2><p>See the complete process before you begin: optional community research, board planning form, first draft, delegation meeting, detailed area plans, final strategic plan and Board Member Portfolios.</p><div className="guided-video"><PlayCircle size={40}/><strong>Strategic Planning Tutorial</strong><span>Final tutorial video URL will be added before launch.</span></div></section>

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
    {formLink?<><div className="sp-linkbox"><strong>Your Strategic Planning Form</strong><span>{formLink}</span><button onClick={()=>copy(formLink)}>COPY FORM LINK</button></div>{leadFormLink&&<div className="sp-linkbox"><strong>Your Lead User Form</strong><span>{leadFormLink}</span><button onClick={()=>window.location.href=leadFormLink}>COMPLETE MY FORM</button></div>}</>:<A disabled={busy==="form"} onClick={()=>act("form",()=>axios.post(`${API}/guided/strategic-planning/prepare-form`,{session_id:sid}))}><ClipboardList size={15}/> {busy==="form"?"PREPARING…":"PREPARE MY STRATEGIC PLANNING FORM"}</A>}
    {formLink&&<div className="sp-actions"><A onClick={async()=>{const r=await axios.get(`${API}/guided/strategic-planning/form-email`,{params:{session_id:sid}});setEmail(r.data)}}><Mail size={15}/> GENERATE EMAIL TO SEND THE FORM</A></div>}
    {email&&<div className="sp-contentbox"><h3>{email.subject}</h3><p style={{whiteSpace:"pre-wrap"}}>{email.body}</p><A onClick={()=>copy(`Subject: ${email.subject}\n\n${email.body}\n\n${email.form_link||formLink}`)}>COPY EMAIL + LINK</A></div>}
   </Card>

   <Card n="2" title="See Everyone Who Has Completed The Form">
    <p>Each board member appears here as soon as they submit. Open their response online or download a copy for your records.</p>
    {!respondents.length?<p className="sp-empty">No completed board responses yet.</p>:<div className="sp-people">{respondents.map(p=><article key={p.participant_id}><Users size={18}/><div><strong>{p.name}</strong><span>{p.role||"Board Member"}</span></div><a href={`/strategic-planning-response/${p.participant_id}`} target="_blank" rel="noreferrer">VIEW RESPONSE</a></article>)}</div>}
   </Card>

   <Card n="3" title="Generate Your First Strategic Plan Draft">
    <p>Combine everybody's planning responses and, where available, your Community Need Research into the first Strategic Plan Draft. This is the plan your board reviews at the delegation meeting.</p>
    <A disabled={!respondents.length||busy==="draft"} onClick={()=>act("draft",()=>axios.post(`${API}/guided/strategic-planning/generate-draft`,{session_id:sid}))}><Sparkles size={15}/> {busy==="draft"?"BUILDING…":project?.plan?.display_text?"REBUILD STRATEGIC PLAN DRAFT":"GENERATE STRATEGIC PLAN DRAFT"}</A>
    {project?.plan?.display_text&&<div className="sp-contentbox"><h3>Your Strategic Plan Draft Is Ready</h3><p>{project.plan.display_text.slice(0,600)}{project.plan.display_text.length>600?"…":""}</p><div className="sp-actions"><a className="bfg-btn bfg-btn-ghost bfg-btn-sm" href={project.plan.share_url||"#"} target="_blank" rel="noreferrer"><ExternalLink size={15}/> VIEW DRAFT</a><A onClick={()=>act("reviewemail",()=>axios.post(`${API}/guided/strategic-planning/send-draft-email`,{session_id:sid}))}><Mail size={15}/> EMAIL DRAFT TO BOARD</A></div></div>}
   </Card>

   <Card n="4" title="Prepare Your Delegation Meeting">
    <p>Use the facilitation guide to review the draft with your board, decide what stays or changes and delegate every strategic area to the board member best aligned to lead or help build it.</p>
    <A disabled={!project?.plan?.display_text||busy==="guide"} onClick={()=>act("guide",()=>axios.post(`${API}/guided/strategic-planning/facilitation-guide`,{session_id:sid}))}><FileText size={15}/> {busy==="guide"?"PREPARING…":"GENERATE STRATEGIC PLANNING FACILITATION GUIDE"}</A>
    {project?.meeting_guide_text&&<div className="sp-contentbox"><p style={{whiteSpace:"pre-wrap"}}>{project.meeting_guide_text}</p></div>}
   </Card>

   <Card n="5" title="Delegate The Parts Of The Organization">
    <p>Assign every strategic area. When there are fewer board members than areas, aligned areas are grouped so the complete organization is still covered and every participating board member has meaningful responsibility.</p>
    <A disabled={!project?.areas?.length||busy==="delegate"} onClick={()=>act("delegate",()=>axios.post(`${API}/guided/strategic-planning/auto-delegate`,{session_id:sid}))}><Users size={15}/> {busy==="delegate"?"MATCHING…":"MATCH STRATEGIC AREAS TO BOARD MEMBERS"}</A>
    {!!areas.length&&<div className="sp-area-grid">{areas.map(a=><article key={a.area_key}><h3>{a.area}</h3><p><strong>Lead:</strong> {a.owner_name||"Not assigned yet"}</p><p>{a.direction}</p><span>{a.plan_submitted_at||a.submitted_plan?"DETAILED PLAN SUBMITTED":"DETAILED PLAN NOT YET SUBMITTED"}</span>{a.owner_name&&<A onClick={()=>act(`email-${a.area_key}`,()=>axios.post(`${API}/guided/strategic-planning/send-area-assignment`,{session_id:sid,area_key:a.area_key}))}><Mail size={14}/> EMAIL ASSIGNMENT</A>}</article>)}</div>}
   </Card>

   <Card n="6" title="Board Members Build Their Detailed Plans With AI">
    <p>Each assignment email carries the Strategic Plan Draft link. From the plan they select <strong>See My Role</strong>, read their assignment, then select <strong>Start Building My Detailed Plan With AI</strong>. AI writes into an editable document on the page. The board member corrects it, approves it, and only then can download it. The approved copy remains saved here for the Final Strategic Plan.</p>
    <div className="sp-progress"><strong>{submitted} of {areas.length} strategic area plans completed</strong><div><span style={{width:`${areas.length?(submitted/areas.length)*100:0}%`}}/></div></div>
   </Card>

   <Card n="7" title="Build And Download The Final Strategic Plan">
    <p>The Final Strategic Plan combines the approved foundational plan with every detailed strategic area plan submitted by your board members.</p>
    <A disabled={!areas.length||submitted<areas.length||busy==="final"} onClick={()=>act("final",()=>axios.post(`${API}/guided/strategic-planning/final-plan`,{session_id:sid}))}><FileText size={15}/> {busy==="final"?"CONSOLIDATING…":"GENERATE FINAL STRATEGIC PLAN"}</A>
    {submitted<areas.length&&areas.length>0&&<p className="sp-note">{areas.length-submitted} strategic area plan{areas.length-submitted===1?" is":"s are"} still outstanding.</p>}
    {project?.final_plan?.display_text&&<div className="sp-actions"><a className="bfg-btn bfg-btn-primary bfg-btn-sm" href={`${API}/guided/strategic-planning/final-plan/pdf?session_id=${encodeURIComponent(sid)}`}><Download size={15}/> DOWNLOAD FINAL STRATEGIC PLAN</a></div>}
   </Card>

   <Card n="8" title="Create Each Board Member's Leadership Portfolio">
    <p>After the Final Strategic Plan is complete, create a portfolio for each board member showing the strategic areas delegated to them and their responsibility to provide leadership and oversight as the execution structures are built.</p>
    <A disabled={!project?.final_plan?.display_text||busy==="portfolios"} onClick={()=>act("portfolios",()=>axios.post(`${API}/guided/strategic-planning/portfolios`,{session_id:sid}))}><CheckCircle2 size={15}/> {busy==="portfolios"?"CREATING…":"GENERATE BOARD MEMBER PORTFOLIOS"}</A>
    {!!project?.portfolios?.length&&<div className="sp-people">{project.portfolios.map(p=><article key={p.participant_id}><Users size={18}/><div><strong>{p.name}</strong><span>{p.areas?.join(", ")}</span></div><a href={p.url||"#"} target="_blank" rel="noreferrer">VIEW PORTFOLIO</a></article>)}</div>}
   </Card>
   {msg&&<p className="bfg-error">{msg}</p>}
   <section className="sp-support"><h2>Need Support?</h2><p>If you get stuck at any stage of the Strategic Planning process, ask us for help.</p><a className="bfg-btn bfg-btn-ghost" href="mailto:support@nonprofitboardbuilder.com?subject=Strategic%20Planning%20Support">ASK FOR SUPPORT</a></section>
  </div>
 </main></BfgShell>
}
