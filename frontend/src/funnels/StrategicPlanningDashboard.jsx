import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, ClipboardList, Copy, Download, FileText, Lock, Mail, Search, Users } from "lucide-react";
import { BfgShell } from "@/game/gameShared";
import "@/game/game.css";
import "./guided-products.css";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;
const GENERATION_ACTIONS=new Set(["research","form","guide","strategy","portfolios"]);

const ORGANIZATION_FIELDS=[
 ["mission","What is your organization's mission? Who do you serve, how do you serve them, and what change are you trying to create?"],
 ["goals","What are your present goals for the next 12 to 24 months? What are you looking to achieve?"],
 ["objectives","What objectives are you using to achieve those goals? What specific results are you working toward?"],
 ["programs","What programs or services do you currently run? Put one program or service on each line."],
 ["team_building","Who do you presently have available to support the work? Include staff, Board Members, volunteers, contractors or other key people."],
 ["operations","What systems and processes presently help you run the organization? What operational challenges should the Board understand?"],
 ["marketing","How do people presently hear about your organization? Who are you trying to reach, and what visibility or communication needs improvement?"],
 ["partnerships","What partnerships or important relationships do you already have? What kinds of partners do you believe you still need?"],
 ["fundraising","How do you presently raise money? What is working, what is difficult, and what needs to improve?"],
 ["technology","What technology or tools do you presently use? What work do you need technology to make easier or more reliable?"],
 ["budget","What should the Board understand about the present budget, major costs, funding available, or resources needed to execute the plan?"],
 ["action_planning","What major actions are already planned or underway? What do you believe needs to happen next?"],
];

const Button=({children,onClick,disabled=false,className=""})=><button type="button" className={`bfg-btn bfg-btn-primary bfg-btn-sm ${className}`.trim()} disabled={disabled} onClick={onClick}>{disabled&&<Lock size={14}/>} {children}</button>;
const Step=({n,title,open,setOpen,locked=false,children,id})=><section id={id} className={`sp-dash-card ${locked?"sp-locked":""}`}><button type="button" className="sp-card-toggle" onClick={()=>!locked&&setOpen(!open)}><span className="sp-step">{n}</span><span><strong>{title}</strong><small>{locked?"Complete the earlier steps to unlock this section.":open?"Close section":"Open section"}</small></span>{locked?<Lock size={20}/>:<span>{open?"−":"+"}</span>}</button>{open&&!locked&&<div className="sp-card-body">{children}</div>}</section>;

export default function StrategicPlanningDashboard(){
 const sid=new URLSearchParams(window.location.search).get("session_id")||"";
 const navigate=useNavigate();
 const [ctx,setCtx]=useState(null),[community,setCommunity]=useState(null),[session,setSession]=useState(null),[busy,setBusy]=useState(""),[msg,setMsg]=useState("");
 const [open,setOpen]=useState("1"),[invite,setInvite]=useState({name:"",email:""}),[finalDraft,setFinalDraft]=useState(""),[delegates,setDelegates]=useState([]),[support,setSupport]=useState({support_type:"",message:""}),[supportSent,setSupportSent]=useState("");
 const [organizationOpen,setOrganizationOpen]=useState(false),[organizationName,setOrganizationName]=useState(""),[organizationAnswers,setOrganizationAnswers]=useState({}),[organizationLogo,setOrganizationLogo]=useState("");

 const load=useCallback(async()=>{
  try{
   const w=await axios.get(`${API}/guided/strategic-planning/workspace`,{params:{session_id:sid}});
   setCtx(w.data);setCommunity(w.data.community_research||null);setOrganizationName(w.data.organization_name||"");setOrganizationAnswers(w.data.organization_answers||{});setOrganizationLogo(w.data.project?.logo_data_url||"");setFinalDraft(w.data.project?.final_plan?.display_text||"");setDelegates(w.data.project?.active_delegation?.delegates||[]);
   const sr=await axios.get(`${API}/guided/strategic-planning/session`,{params:{session_id:sid}});setSession(sr.data);
  }catch(e){setMsg(e.response?.data?.detail||"We could not load your Strategic Planning workspace.");}
 },[sid]);

 useEffect(()=>{load();},[load]);
 useEffect(()=>{if(window.location.hash==="#generate-strategy"){setOpen("8");setTimeout(()=>document.getElementById("generate-strategy")?.scrollIntoView({behavior:"smooth",block:"start"}),250)}},[ctx]);

 const act=async(key,fn)=>{setBusy(key);setMsg("");try{await fn();await load()}catch(e){setMsg(e.response?.data?.detail||"That action could not be completed yet.")}setBusy("")};
 const copy=text=>navigator.clipboard?.writeText(text);
 const p=ctx?.project||{},respondents=(p.participants||[]).filter(x=>x.status==="COMPLETED");
 const formReady=p.form?.status==="Approved",leadDone=respondents.some(x=>x.role==="Lead User"),organizationReady=Boolean(organizationName.trim()&&String(organizationAnswers.mission||p.mission||"").trim()),sessionDone=session?.status==="COMPLETED",planReady=Boolean(p.final_plan?.display_text),approved=p.final_plan?.status==="Approved";
 const formLink=formReady?`${window.location.origin}/strategic-planning-form/${p.generic_form_token}`:"",leadLink=p.lead_form_token?`${window.location.origin}/strategic-planning-form/${p.lead_form_token}`:"",researchLink=community?.token?`${window.location.origin}/community-need-research/${community.token}`:"",planLink=p.final_plan?.share_token?`${window.location.origin}/strategic-plan/${p.final_plan.share_token}`:"";

 const uploadLogo=file=>{if(!file)return;const reader=new FileReader();reader.onload=()=>setOrganizationLogo(reader.result);reader.readAsDataURL(file)};
 const saveOrganization=()=>act("organization",async()=>{await axios.put(`${API}/guided/strategic-planning/organization`,{session_id:sid,organization_name:organizationName,answers:organizationAnswers,logo_data_url:organizationLogo});setOrganizationOpen(false)});
 const updateDelegate=(id,field,value)=>setDelegates(rows=>rows.map(row=>row.delegation_id===id?{...row,[field]:value}:row));
 const removeDelegate=id=>setDelegates(rows=>rows.filter(row=>row.delegation_id!==id));
 const addKnown=person=>setDelegates(rows=>rows.some(row=>row.participant_id===person.participant_id)?rows:[...rows,{delegation_id:`manual-${person.participant_id}`,participant_id:person.participant_id,name:person.name,email:person.email||"",role:person.role||"",responsibilities:[],areas:[],first_action:"",support_needed:"",reporting_rhythm:""}]);
 const addOther=()=>setDelegates(rows=>[...rows,{delegation_id:`manual-${Date.now()}`,participant_id:"",name:"",email:"",role:"",responsibilities:[],areas:[],first_action:"",support_needed:"",reporting_rhythm:""}]);
 const saveDelegates=()=>act("save-delegates",()=>axios.put(`${API}/guided/strategic-planning/active-delegation/people`,{session_id:sid,delegates}));

 if(!ctx)return <BfgShell><main className="guided-page"><section className="guided-section"><h1>Strategic Planning</h1><p>{msg||"Preparing your workspace…"}</p></section></main></BfgShell>;
 const card=(n,title,unlocked,content,id="")=><Step n={n} title={title} locked={!unlocked} open={open===String(n)} setOpen={v=>setOpen(v?String(n):"")} id={id}>{content}</Step>;

 return <BfgShell><main className="guided-page sp-dashboard">
  <section className="guided-section sp-dash-head"><p className="bfg-eyebrow">STRATEGIC PLANNING WITH YOUR BOARD</p><h1>{ctx.organization_name||"Your Strategic Planning Dashboard"}</h1><p className="guided-intro">Collect honest thinking before the meeting, review it together in one live Strategic Planning Session, then generate, approve and delegate one professional Strategic Plan.</p>{GENERATION_ACTIONS.has(busy)&&<p className="bfg-note" data-testid="strategic-generation-wait"><strong>Generating your resource.</strong> This may take a few minutes. If it isn't ready immediately, check back in about 5 minutes.</p>}</section>

  <div className="sp-dash-stack">
   {card(1,"Tell Us About Your Organization",true,<>
    <p>Give the platform enough specific context to understand where the organization is now. These answers are the starting reality the Board will review, not automatic final decisions.</p>
    <Button onClick={()=>setOrganizationOpen(!organizationOpen)}><ClipboardList size={15}/> {organizationOpen?"CLOSE ORGANIZATION FORM":"TELL US ABOUT YOUR ORGANIZATION"}</Button>
    {organizationOpen&&<div className="sp-contentbox sp-organization-form"><label><strong>Organization Name</strong><input value={organizationName} onChange={e=>setOrganizationName(e.target.value)}/></label>{ORGANIZATION_FIELDS.map(([key,label])=><label key={key}><strong>{label}</strong><textarea rows={key==="programs"?6:4} value={organizationAnswers[key]||""} onChange={e=>setOrganizationAnswers({...organizationAnswers,[key]:e.target.value})}/></label>)}<label><strong>Organization Logo</strong><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>uploadLogo(e.target.files?.[0])}/></label>{organizationLogo&&<img src={organizationLogo} alt="" style={{maxWidth:180,maxHeight:100,objectFit:"contain"}}/>}<Button disabled={!organizationName.trim()||!String(organizationAnswers.mission||"").trim()||busy==="organization"} onClick={saveOrganization}>{busy==="organization"?"SAVING…":"SAVE ORGANIZATION INFORMATION"}</Button></div>}
    {!organizationOpen&&organizationReady&&<div className="sp-contentbox"><strong>Organization information saved</strong><p>{organizationName}</p><p>{organizationAnswers.mission||p.mission}</p></div>}
   </>)}

   {card(2,"Launch Community Need Research",organizationReady,<>
    <p>Listen outside the Board before agreeing the strategy. The survey asks people to speak from what they have personally observed or experienced. The promotion content below is ready to share.</p>
    {!community?<Button disabled={busy==="research"} onClick={()=>act("research",()=>axios.post(`${API}/guided/strategic-planning/community-research`,{session_id:sid}))}><Search size={15}/> LAUNCH COMMUNITY NEED RESEARCH</Button>:<>
     <div className="sp-linkbox"><span>{researchLink}</span><button onClick={()=>copy(researchLink)}>COPY SURVEY LINK</button></div>
     <div className="sp-contentbox"><h3>Community Research Promotion Kit</h3>{(community.social_posts||[]).map((post,index)=><article className="sp-promotion-post" key={index}><p>{post}</p><button onClick={()=>copy(`${post}\n\n${researchLink}`)}>COPY POST {index+1}</button></article>)}</div>
     <p>{community.response_count||0} community responses received.</p>
    </>}
   </>)}

   {card(3,"Generate The Strategic Planning Form",organizationReady,<>
    <p>Create the form Board Members will use to contribute their own ideas before the live session. Each program is reviewed separately, and the questions ask people to speak from their own observation and experience.</p>
    {!formReady?<Button disabled={busy==="form"} onClick={()=>act("form",()=>axios.post(`${API}/guided/strategic-planning/prepare-form`,{session_id:sid}))}><ClipboardList size={15}/> GENERATE STRATEGIC PLANNING FORM</Button>:<div className="sp-linkbox"><span>{formLink}</span><button onClick={()=>copy(formLink)}>COPY FORM LINK</button></div>}
   </>)}

   {card(4,"Send The Form To Your Board Members",formReady,<>
    <p>Send each Board Member their own planning link. Their responses remain attributable to them when the Board reviews the ideas together.</p>
    <div className="sp-contentbox"><input placeholder="Board Member Name" value={invite.name} onChange={e=>setInvite({...invite,name:e.target.value})}/><input type="email" placeholder="Board Member Email" value={invite.email} onChange={e=>setInvite({...invite,email:e.target.value})}/><Button disabled={!invite.name||!invite.email||busy==="invite"} onClick={()=>act("invite",async()=>{await axios.post(`${API}/guided/strategic-planning/invite`,{session_id:sid,...invite});setInvite({name:"",email:""})})}><Mail size={15}/> SEND STRATEGIC PLANNING FORM</Button></div>
   </>)}

   {card(5,"Complete Your Own Strategic Planning Form",formReady,<>
    <p>Your own ideas belong in the process too. Complete the same form so your thinking can be reviewed alongside the Board Members' ideas during the session.</p>
    <a className="bfg-btn bfg-btn-primary bfg-btn-sm" href={leadLink}>OPEN MY STRATEGIC PLANNING FORM</a>
    {leadDone&&<p className="member-success"><CheckCircle2 size={16}/> Your response has been saved. You can reopen the form to review or update it before the session.</p>}
   </>)}

   {card(6,"Review Everyone Who Has Completed The Form",formReady,<>
    <p>See exactly what each person submitted before the meeting. The real question text is shown with each answer.</p>
    {!respondents.length?<p className="sp-empty">No completed responses yet.</p>:<div className="sp-people">{respondents.map(person=><article key={person.participant_id}><Users/><div><strong>{person.name}</strong><span>{person.role||"Board Member"}</span></div><a href={`/strategic-planning-response/${person.participant_id}`} target="_blank" rel="noreferrer">VIEW RESPONSE</a></article>)}</div>}
   </>)}

   {card(7,"Run The Strategic Planning Session",respondents.length>0,<>
    <p>Generate your facilitation guide first. Then open the live session page, create the shared Board screen, start microphone transcription with consent, and review the strategy one section at a time.</p>
    <div className="sp-actions">
     <Button disabled={busy==="guide"} onClick={()=>act("guide",()=>axios.post(`${API}/guided/strategic-planning/facilitation-guide`,{session_id:sid}))}><FileText size={15}/> {p.meeting_guide_text?"REGENERATE FACILITATION GUIDE":"GENERATE FACILITATION GUIDE"}</Button>
     {p.meeting_guide_text&&<Button onClick={()=>navigate(`/strategic-planning/session?session_id=${encodeURIComponent(sid)}`)}>PREPARE / START STRATEGIC PLANNING SESSION</Button>}
    </div>
    {p.meeting_guide_text&&<details className="sp-guide"><summary>View Facilitation Guide</summary><pre>{p.meeting_guide_text}</pre></details>}
    {session?.status==="IN PROGRESS"&&<p className="member-success">Your Strategic Planning Session is currently in progress.</p>}
    {sessionDone&&<p className="member-success"><CheckCircle2 size={16}/> Strategic Planning Session completed. The Board decisions and transcript are ready for the Strategic Plan.</p>}
   </>)}

   {card(8,"Generate, Review And Approve The Strategic Plan",sessionDone,<>
    <p>Generate one professional Strategic Plan from the Board-selected ideas, the preserved original responses, your organization context, community research and the live session transcript. The finished document will not read like a transcript or list who said what.</p>
    {!planReady&&<Button disabled={busy==="strategy"} onClick={()=>act("strategy",()=>axios.post(`${API}/guided/strategic-planning/session-plan`,{session_id:sid}))}>GENERATE MY STRATEGIC PLAN</Button>}
    {planReady&&<>
     <div className="sp-plan-editor"><textarea rows={30} value={finalDraft} disabled={approved} onChange={e=>setFinalDraft(e.target.value)}/></div>
     <div className="sp-actions">
      {!approved&&<Button disabled={busy==="save-plan"} onClick={()=>act("save-plan",()=>axios.put(`${API}/guided/strategic-planning/final-plan/draft`,{session_id:sid,display_text:finalDraft}))}>SAVE EDITS</Button>}
      {!approved&&<Button disabled={busy==="approve-plan"} onClick={()=>act("approve-plan",async()=>{await axios.put(`${API}/guided/strategic-planning/final-plan/draft`,{session_id:sid,display_text:finalDraft});await axios.post(`${API}/guided/strategic-planning/final-plan/approve`,{session_id:sid})})}>APPROVE STRATEGIC PLAN</Button>}
      <a className="bfg-btn bfg-btn-primary bfg-btn-sm" href={`${API}/guided/strategic-planning/final-plan/pdf?session_id=${encodeURIComponent(sid)}`}><Download size={15}/> DOWNLOAD STRATEGIC PLAN</a>
      {approved&&planLink&&<button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={()=>copy(planLink)}><Copy size={15}/> COPY STRATEGIC PLAN LINK</button>}
     </div>
     {approved&&<p className="member-success"><CheckCircle2 size={16}/> Strategic Plan approved. You can now confirm delegation and send execution access.</p>}
    </>}
   </>,"generate-strategy")}

   {card(9,"Confirm Delegation And Start Execution",approved,<>
    <p>The platform has pulled only the responsibilities it could identify from the Action Planning discussion. Review every person and responsibility. Edit, remove or add people before anything is sent.</p>
    <div className="sp-contentbox"><h3>Everyone Who Contributed Before The Session</h3><p>Add somebody only when the live session actually gave them an execution responsibility.</p><div className="sp-people">{respondents.map(person=>{const added=delegates.some(row=>row.participant_id===person.participant_id);return <article key={person.participant_id}><Users/><div><strong>{person.name}</strong><span>{person.role||"Board Member"}</span></div><button type="button" disabled={added} onClick={()=>addKnown(person)}>{added?"IN DELEGATION":"ADD TO DELEGATION"}</button></article>})}</div><Button onClick={addOther}>ADD SOMEONE MENTIONED IN THE SESSION</Button></div>

    <div className="sp-delegation-list">
     {delegates.map(person=><article className="sp-delegate-card" key={person.delegation_id}>
      <label><strong>Name</strong><input value={person.name||""} onChange={e=>updateDelegate(person.delegation_id,"name",e.target.value)}/></label>
      <label><strong>Email</strong><input type="email" value={person.email||""} onChange={e=>updateDelegate(person.delegation_id,"email",e.target.value)} placeholder="Add email before sending"/></label>
      <label><strong>Role / relationship to the organization</strong><input value={person.role||""} onChange={e=>updateDelegate(person.delegation_id,"role",e.target.value)}/></label>
      <label><strong>Responsibilities agreed during the session</strong><textarea rows={5} value={(person.responsibilities||[]).join("\n")} onChange={e=>updateDelegate(person.delegation_id,"responsibilities",e.target.value.split("\n").map(x=>x.trim()).filter(Boolean))}/></label>
      <label><strong>Strategic areas</strong><textarea rows={3} value={(person.areas||[]).join("\n")} onChange={e=>updateDelegate(person.delegation_id,"areas",e.target.value.split("\n").map(x=>x.trim()).filter(Boolean))}/></label>
      <label><strong>First action</strong><textarea rows={2} value={person.first_action||""} onChange={e=>updateDelegate(person.delegation_id,"first_action",e.target.value)}/></label>
      <button type="button" className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={()=>removeDelegate(person.delegation_id)}>REMOVE</button>
     </article>)}
    </div>

    <div className="sp-actions">
     <Button disabled={!delegates.length||delegates.some(person=>!person.name.trim()||!(person.responsibilities||[]).length)||busy==="save-delegates"} onClick={saveDelegates}>{busy==="save-delegates"?"SAVING…":"CONFIRM & SAVE DELEGATION"}</Button>
     <Button disabled={!delegates.length||busy==="portfolios"} onClick={()=>act("portfolios",()=>axios.post(`${API}/guided/strategic-planning/portfolios`,{session_id:sid}))}>CREATE BOARD MEMBER PORTFOLIOS & EXECUTIVE ASSISTANTS</Button>
     <Button disabled={busy==="send-final"} onClick={()=>act("send-final",()=>axios.post(`${API}/guided/strategic-planning/send-final-plan`,{session_id:sid}))}><Mail size={15}/> SEND STRATEGIC PLAN TO PARTICIPANTS</Button>
    </div>

    {(p.portfolios||[]).length>0&&<div className="sp-contentbox"><h3>Board Execution Portfolios</h3>{p.portfolios.map(row=><article className="sp-portfolio-row" key={row.token}><div><strong>{row.name}</strong><p>{(row.responsibilities||[]).join(" · ")}</p><small>{row.email||"Add this person's email in the delegation list before sending."}</small></div><div className="sp-actions"><a className="bfg-btn bfg-btn-ghost bfg-btn-sm" href={`/strategic-leadership-portfolio/${row.token}`} target="_blank" rel="noreferrer">VIEW PORTFOLIO</a><a className="bfg-btn bfg-btn-ghost bfg-btn-sm" href={`/strategic-leadership-assistant/${row.token}`} target="_blank" rel="noreferrer">OPEN EXECUTIVE ASSISTANT</a><Button disabled={!row.email||Boolean(row.sent_at)} onClick={()=>act(`send-${row.token}`,()=>axios.post(`${API}/guided/strategic-planning/leadership-portfolio/send`,{session_id:sid,token:row.token}))}>{row.sent_at?"SENT":"SEND PLAN + PORTFOLIO"}</Button></div></article>)}</div>}
   </>)}

   {msg&&<p className="bfg-error">{msg}</p>}

   <section className="sp-support-card"><h2>Ask For Help</h2><p>Tell us what you need help with. Your question is sent from inside your Strategic Planning workspace.</p>{supportSent?<p className="member-success">{supportSent}</p>:<div className="sp-support-form"><select value={support.support_type} onChange={e=>setSupport({...support,support_type:e.target.value})}><option value="">Choose what you need help with</option><option>Strategic Planning process</option><option>Facilitating the Board session</option><option>Strategic Plan</option><option>Delegation and execution</option><option>Using the platform</option></select><textarea rows={5} value={support.message} onChange={e=>setSupport({...support,message:e.target.value)} placeholder="Tell us what you need help with"/><Button disabled={!support.support_type||!support.message.trim()||busy==="support"} onClick={()=>act("support",async()=>{const r=await axios.post(`${API}/guided/strategic-planning/support`,{session_id:sid,...support});setSupportSent(r.data.message)})}>SEND SUPPORT REQUEST</Button></div>}</section>
  </div>
 </main></BfgShell>;
}
