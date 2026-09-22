import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, ClipboardList, Download, FileText, Mail, Plus, Search, Users } from "lucide-react";
import { BfgShell } from "@/game/gameShared";
import "@/game/game.css";
import "./guided-products.css";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

const ORGANIZATION_FIELDS=[
  ["mission","What is your organization's mission? Who do you serve, how do you serve them, and what change are you trying to create?"],
  ["goals","What are your present goals for the next 12 to 24 months? What are you trying to achieve?"],
  ["objectives","What objectives are you presently pursuing to achieve those goals? What results is each objective meant to produce?"],
  ["programs","List each current program or service on its own line so the Board can review every program separately."],
  ["team_building","Who do you presently have available to support the organization? Include staff, Board Members, volunteers, contractors or other people who help you deliver the work."],
  ["operations","What systems or processes presently keep the organization running? Where do you already see operational problems, bottlenecks or gaps?"],
  ["marketing","How do people presently hear about the organization? Who are you trying to reach, and what are you presently doing for marketing, visibility or communications?"],
  ["partnerships","What partnerships or important relationships do you presently have? What kinds of partners do you believe the organization needs?"],
  ["fundraising","How are you presently raising money? What has worked, what has not worked, and what do you believe needs to improve?"],
  ["technology","What technology or tools do you presently use? What work do you need technology to make easier, faster or more reliable?"],
  ["budget","What is your present budget or best current understanding of what it costs to operate and grow the organization? Include only numbers you actually know."],
  ["action_planning","What important actions are already planned or underway? What do you believe needs to happen next?"]
];

const Button=({children,onClick,disabled=false,secondary=false,testId=""})=>(
  <button type="button" className={`bfg-btn ${secondary?"bfg-btn-ghost":"bfg-btn-primary"} bfg-btn-sm`} disabled={disabled} onClick={onClick} data-testid={testId||undefined}>{children}</button>
);

const Step=({n,title,summary,locked=false,children,open,setOpen,testId})=>(
  <section className={`sp-dash-card ${locked?"sp-locked":""}`} id={testId}>
    <button type="button" className="sp-card-toggle" onClick={()=>!locked&&setOpen(!open)}>
      <span className="sp-step">{n}</span>
      <span><strong>{title}</strong><small>{locked?"Complete the earlier step first.":summary}</small></span>
      <span>{locked?"🔒":open?"−":"+"}</span>
    </button>
    {open&&!locked&&<div className="sp-card-body">{children}</div>}
  </section>
);

export default function StrategicPlanningDashboard(){
  const sid=new URLSearchParams(window.location.search).get("session_id")||"";
  const navigate=useNavigate();
  const [ctx,setCtx]=useState(null);
  const [community,setCommunity]=useState(null);
  const [session,setSession]=useState(null);
  const [busy,setBusy]=useState("");
  const [message,setMessage]=useState("");
  const [open,setOpen]=useState("1");
  const [invite,setInvite]=useState({name:"",email:""});
  const [organizationOpen,setOrganizationOpen]=useState(false);
  const [organizationName,setOrganizationName]=useState("");
  const [organizationAnswers,setOrganizationAnswers]=useState({});
  const [organizationLogo,setOrganizationLogo]=useState("");
  const [finalDraft,setFinalDraft]=useState("");
  const [editingPlan,setEditingPlan]=useState(false);
  const [delegates,setDelegates]=useState([]);
  const [support,setSupport]=useState({support_type:"",message:""});
  const [supportSent,setSupportSent]=useState("");

  const load=useCallback(async()=>{
    try{
      const workspace=await axios.get(`${API}/guided/strategic-planning/workspace`,{params:{session_id:sid}});
      setCtx(workspace.data);
      setCommunity(workspace.data.community_research||null);
      setOrganizationName(workspace.data.organization_name||"");
      setOrganizationAnswers(workspace.data.organization_answers||{});
      setOrganizationLogo(workspace.data.project?.logo_data_url||"");
      setFinalDraft(workspace.data.project?.final_plan?.display_text||"");
      setDelegates(workspace.data.project?.active_delegation?.delegates||[]);
      const live=await axios.get(`${API}/guided/strategic-planning/session`,{params:{session_id:sid}});
      setSession(live.data);
    }catch(error){
      setMessage(error.response?.data?.detail||"We could not load your Strategic Planning workspace.");
    }
  },[sid]);

  useEffect(()=>{load();},[load]);
  useEffect(()=>{
    if(ctx?.project?.final_plan?.status!=="Generating")return;
    const timer=window.setInterval(load,10000);
    return()=>window.clearInterval(timer);
  },[ctx?.project?.final_plan?.status,load]);
  useEffect(()=>{
    if(window.location.hash==="#generate-strategy"){
      setOpen("8");
      setTimeout(()=>document.getElementById("generate-strategy")?.scrollIntoView({behavior:"smooth",block:"start"}),150);
    }
  },[ctx]);

  const act=async(key,fn)=>{
    setBusy(key);setMessage("");
    try{await fn();await load();}
    catch(error){setMessage(error.response?.data?.detail||"That action could not be completed yet.");}
    setBusy("");
  };

  if(!ctx)return <BfgShell><main className="guided-page"><section className="guided-section"><h1>Strategic Planning</h1><p>{message||"Preparing your workspace…"}</p></section></main></BfgShell>;

  const p=ctx.project||{};
  const participants=p.participants||[];
  const completed=participants.filter(person=>person.status==="COMPLETED");
  const lead=participants.find(person=>person.role==="Lead User");
  const boardResponses=completed.filter(person=>person.role!=="Lead User");
  const formReady=p.form?.status==="Approved";
  const leadDone=lead?.status==="COMPLETED";
  const organizationReady=Boolean(organizationName.trim()&&String(organizationAnswers.mission||p.mission||"").trim());
  const sessionDone=session?.status==="COMPLETED";
  const guideReady=Boolean(p.meeting_guide_text);
  const finalReady=Boolean(p.final_plan?.display_text);
  const finalGenerating=p.final_plan?.status==="Generating";
  const finalFailed=p.final_plan?.status==="Failed";
  const approved=p.final_plan?.status==="Approved";
  const portfolios=p.portfolios||[];
  const formLink=formReady?`${window.location.origin}/strategic-planning-form/${p.generic_form_token}`:"";
  const leadLink=p.lead_form_token?`${window.location.origin}/strategic-planning-form/${p.lead_form_token}`:"";
  const researchLink=community?.token?`${window.location.origin}/community-need-research/${community.token}`:"";

  const copy=text=>navigator.clipboard?.writeText(text);

  const uploadLogo=file=>{
    if(!file)return;
    const reader=new FileReader();
    reader.onload=()=>setOrganizationLogo(reader.result);
    reader.readAsDataURL(file);
  };

  const saveOrganization=()=>act("organization",async()=>{
    await axios.put(`${API}/guided/strategic-planning/organization`,{
      session_id:sid,organization_name:organizationName,answers:organizationAnswers,logo_data_url:organizationLogo
    });
    setOrganizationOpen(false);
  });

  const sendInvite=()=>act("invite",async()=>{
    await axios.post(`${API}/guided/strategic-planning/invite`,{session_id:sid,...invite});
    setInvite({name:"",email:""});
  });

  const generateGuide=()=>act("guide",()=>axios.post(`${API}/guided/strategic-planning/facilitation-guide`,{session_id:sid}));

  const savePlan=()=>act("save-plan",()=>axios.put(`${API}/guided/strategic-planning/final-plan/draft`,{session_id:sid,display_text:finalDraft}));

  const approvePlan=()=>act("approve-plan",async()=>{
    await axios.put(`${API}/guided/strategic-planning/final-plan/draft`,{session_id:sid,display_text:finalDraft});
    await axios.post(`${API}/guided/strategic-planning/final-plan/approve`,{session_id:sid});
    setEditingPlan(false);
  });

  const updateDelegate=(id,field,value)=>setDelegates(current=>current.map(person=>person.delegation_id===id?{...person,[field]:value}:person));
  const removeDelegate=id=>setDelegates(current=>current.filter(person=>person.delegation_id!==id));
  const addKnownDelegate=person=>setDelegates(current=>{
    if(current.some(item=>item.participant_id===person.participant_id))return current;
    return [...current,{delegation_id:`manual-${person.participant_id}`,participant_id:person.participant_id,name:person.name,email:person.email||"",role:person.role||"",responsibilities:[],areas:[],first_action:"",support_needed:"",reporting_rhythm:""}];
  });
  const addOtherDelegate=()=>setDelegates(current=>[...current,{delegation_id:`manual-${Date.now()}`,participant_id:"",name:"",email:"",role:"",responsibilities:[],areas:[],first_action:"",support_needed:"",reporting_rhythm:""}]);

  const saveDelegates=()=>act("save-delegates",()=>axios.put(`${API}/guided/strategic-planning/active-delegation/people`,{session_id:sid,delegates}));
  const createPortfolios=()=>act("portfolios",async()=>{
    await axios.put(`${API}/guided/strategic-planning/active-delegation/people`,{session_id:sid,delegates});
    await axios.post(`${API}/guided/strategic-planning/portfolios`,{session_id:sid});
  });

  const card=(n,title,summary,unlocked,content,testId="")=>(
    <Step n={n} title={title} summary={summary} locked={!unlocked} open={open===String(n)} setOpen={value=>setOpen(value?String(n):"")} testId={testId}>{content}</Step>
  );

  return <BfgShell><main className="guided-page sp-dashboard">
    <section className="guided-section sp-dash-head">
      <p className="bfg-eyebrow">STRATEGIC PLANNING WITH YOUR BOARD</p>
      <h1>{ctx.organization_name||"Your Strategic Planning Dashboard"}</h1>
      <p className="guided-intro">One simple process: gather the organization's starting information, collect individual ideas, review those ideas together in one live Board session, generate the Strategic Plan, then confirm who will help carry it forward.</p>
      {busy&&["research","form","guide","strategy","portfolios"].includes(busy)&&<p className="bfg-note"><strong>Generating your resource.</strong> This may take a few minutes. If it isn't ready immediately, check back in about 5 minutes.</p>}
    </section>

    <div className="sp-dash-stack">
      {card(1,"Tell Us About Your Organization","Give the Board enough real information to think clearly about the future.",true,<>
        <p>Answer these questions in plain language. Specific information gives your Board something real to react to instead of forcing them to guess what the organization needs.</p>
        <Button onClick={()=>setOrganizationOpen(!organizationOpen)}><ClipboardList size={15}/> {organizationOpen?"CLOSE ORGANIZATION FORM":"OPEN ORGANIZATION FORM"}</Button>
        {organizationOpen&&<div className="sp-contentbox sp-organization-form" data-testid="strategic-organization-form">
          <label><strong>Organization Name</strong><input value={organizationName} onChange={event=>setOrganizationName(event.target.value)}/></label>
          {ORGANIZATION_FIELDS.map(([key,label])=><label key={key}><strong>{label}</strong><textarea rows={key==="programs"?5:4} value={organizationAnswers[key]||""} onChange={event=>setOrganizationAnswers({...organizationAnswers,[key]:event.target.value})}/></label>)}
          <label><strong>Organization Logo</strong><input type="file" accept="image/png,image/jpeg,image/webp" onChange={event=>uploadLogo(event.target.files?.[0])}/></label>
          {organizationLogo&&<img src={organizationLogo} alt={`${organizationName||"Organization"} logo`} style={{maxWidth:180,maxHeight:100,objectFit:"contain"}}/>}
          <Button disabled={!organizationName.trim()||!String(organizationAnswers.mission||"").trim()||busy==="organization"} onClick={saveOrganization}>{busy==="organization"?"SAVING…":"SAVE ORGANIZATION INFORMATION"}</Button>
        </div>}
        {!organizationOpen&&organizationReady&&<div className="sp-contentbox"><strong>Organization information saved.</strong><p>{organizationName}</p><p>{p.mission||organizationAnswers.mission}</p></div>}
      </>)}

      {card(2,"Launch Community Need Research","Listen outside the Board before the Board agrees the organization's direction.",organizationReady,<>
        <p>Use the public research link to hear directly from people who experience, understand or work around the need your organization exists to address.</p>
        {!community?<Button disabled={busy==="research"} onClick={()=>act("research",()=>axios.post(`${API}/guided/strategic-planning/community-research`,{session_id:sid}))}><Search size={15}/> LAUNCH COMMUNITY NEED RESEARCH</Button>:<>
          <div className="sp-linkbox"><span>{researchLink}</span><button onClick={()=>copy(researchLink)}>COPY SURVEY LINK</button></div>
          <div className="sp-contentbox"><h3>Community Research Promotion Kit</h3>{(community.social_posts||[]).map((post,index)=><div className="sp-promotion-post" key={index}><p>{post}</p><button onClick={()=>copy(`${post}\n\n${researchLink}`)}>COPY POST {index+1}</button></div>)}</div>
          <p><strong>{community.response_count||0}</strong> public responses received.</p>
        </>}
      </>)}

      {card(3,"Generate The Strategic Planning Form","Turn the organization information into personal, actionable questions for the Board.",organizationReady,<>
        <p>The form asks people what they personally observe, what they would protect or change, and what they believe the organization should do differently. Every program is reviewed separately.</p>
        {!formReady?<Button disabled={busy==="form"} onClick={()=>act("form",()=>axios.post(`${API}/guided/strategic-planning/prepare-form`,{session_id:sid}))}><ClipboardList size={15}/> GENERATE STRATEGIC PLANNING FORM</Button>:<div className="sp-linkbox"><span>{formLink}</span><button onClick={()=>copy(formLink)}>COPY FORM LINK</button></div>}
      </>)}

      {card(4,"Send The Form To Your Board Members","Collect each person's original thinking before the live session.",formReady,<>
        <p>You can send the general form link yourself or email a person-specific link directly from the platform.</p>
        <div className="sp-linkbox"><span>{formLink}</span><button onClick={()=>copy(formLink)}>COPY GENERAL FORM LINK</button></div>
        <div className="sp-contentbox">
          <input placeholder="Board Member Name" value={invite.name} onChange={event=>setInvite({...invite,name:event.target.value})}/>
          <input type="email" placeholder="Board Member Email" value={invite.email} onChange={event=>setInvite({...invite,email:event.target.value})}/>
          <Button disabled={!invite.name.trim()||!invite.email.trim()||busy==="invite"} onClick={sendInvite}><Mail size={15}/> {busy==="invite"?"SENDING…":"SEND STRATEGIC PLANNING FORM"}</Button>
        </div>
      </>)}

      {card(5,"Complete Your Own Strategic Planning Form","Your own ideas belong in the same pool as the Board's ideas.",formReady,<>
        <p>You are a participant in the planning process too. Complete the same form so your ideas remain attributable to you and can be reviewed alongside everyone else's during the live session.</p>
        {leadLink?<a className="bfg-btn bfg-btn-primary bfg-btn-sm" href={leadLink}>{leadDone?"REVIEW / UPDATE MY FORM":"COMPLETE MY FORM"}</a>:<p className="sp-empty">Your lead-user form link is being prepared.</p>}
        {leadDone&&<p className="member-success"><CheckCircle2 size={16}/> Your response is saved. You can reopen the form and update it before the session.</p>}
      </>)}

      {card(6,"Review Everyone's Responses","See exactly what each person contributed before the meeting.",formReady,<>
        {!completed.length?<p className="sp-empty">No completed responses yet.</p>:<div className="sp-people">{completed.map(person=><article key={person.participant_id}><Users/><div><strong>{person.name}</strong><span>{person.role||"Board Participant"}</span></div><a href={`/strategic-planning-response/${person.participant_id}`} target="_blank" rel="noreferrer">VIEW RESPONSE</a></article>)}</div>}
        <p className="workspace-note">The response page shows the real question wording and the person's full original answer. Internal IDs such as S1 Q1 are never customer-facing labels.</p>
      </>)}

      {card(7,"Run The Strategic Planning Session","Use one live Board session to review ideas, agree direction and discuss execution responsibility.",completed.length>0,<>
        <p>Generate the facilitation guide first. Then open the live session workspace. There you will create the Board's shared screen link, start microphone transcription with consent, and move through Mission, Goals, Objectives, each Program, Team, Operations, Marketing, Partnerships, Fundraising, Technology, Budget and Action Planning one screen at a time.</p>
        <div className="sp-actions">
          <Button disabled={busy==="guide"} onClick={generateGuide}><FileText size={15}/> {guideReady?"REGENERATE FACILITATION GUIDE":"GENERATE FACILITATION GUIDE"}</Button>
          <Button disabled={!guideReady} onClick={()=>navigate(`/strategic-planning/session?session_id=${encodeURIComponent(sid)}`)}>{sessionDone?"VIEW COMPLETED SESSION":"OPEN STRATEGIC PLANNING SESSION"}</Button>
        </div>
        {guideReady&&<details className="sp-guide"><summary>View Facilitation Guide</summary><pre>{p.meeting_guide_text}</pre></details>}
        {!leadDone&&<p className="workspace-note">Your own form is not yet complete. You can still prepare the session, but completing your form first ensures your ideas are reviewed with everyone else's.</p>}
        {sessionDone&&<p className="member-success"><CheckCircle2 size={16}/> The Strategic Planning Session is complete. Board selections and the live transcript are saved.</p>}
      </>)}

      {card(8,"Generate, Review And Approve The Strategic Plan","Turn the Board's agreed direction into one professional organization Strategic Plan.",sessionDone,<>
        <p>The generated plan uses the Board-selected ideas, the full original responses behind those ideas, the organization's starting information, community research as supporting context, and the live meeting transcript. It does not list who said what. It reads as the organization's Strategic Plan.</p>
        {!finalReady?<>
          <Button disabled={busy==="strategy"||finalGenerating} onClick={()=>act("strategy",()=>axios.post(`${API}/guided/strategic-planning/session-plan`,{session_id:sid}))}>{finalGenerating?"GENERATING STRATEGIC PLAN…":busy==="strategy"?"STARTING…":finalFailed?"TRY GENERATING AGAIN":"GENERATE STRATEGIC PLAN"}</Button>
          {finalGenerating&&<p className="workspace-note">Your Strategic Plan is being built in the background. This may take a few minutes. You can leave this page and check back in about 5 minutes.</p>}
          {finalFailed&&<p className="bfg-error">The last generation did not complete. You can try again. No Board responses or session decisions were lost.</p>}
        </>:<>
          <div className="sp-plan-editor">
            {!editingPlan?<pre className="sp-plan-preview">{finalDraft}</pre>:<textarea rows={30} value={finalDraft} disabled={approved} onChange={event=>setFinalDraft(event.target.value)}/>}
          </div>
          <div className="sp-actions">
            {!approved&&!editingPlan&&<Button secondary onClick={()=>setEditingPlan(true)}>EDIT PLAN</Button>}
            {!approved&&editingPlan&&<Button secondary disabled={busy==="save-plan"} onClick={savePlan}>{busy==="save-plan"?"SAVING…":"SAVE EDITS"}</Button>}
            {!approved&&<Button disabled={busy==="approve-plan"} onClick={approvePlan}>{busy==="approve-plan"?"APPROVING…":"APPROVE STRATEGIC PLAN"}</Button>}
            {approved&&<a className="bfg-btn bfg-btn-primary bfg-btn-sm" href={`${API}/guided/strategic-planning/final-plan/pdf?session_id=${encodeURIComponent(sid)}`}><Download size={15}/> DOWNLOAD STRATEGIC PLAN</a>}
            {approved&&p.final_plan?.share_url&&<button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={()=>copy(`${window.location.origin}${p.final_plan.share_url}`)}>COPY STRATEGIC PLAN LINK</button>}
            {approved&&<Button secondary disabled={busy==="send-final"} onClick={()=>act("send-final",()=>axios.post(`${API}/guided/strategic-planning/send-final-plan`,{session_id:sid}))}>{busy==="send-final"?"SENDING…":"SEND STRATEGIC PLAN TO ALL PARTICIPANTS"}</Button>}
          </div>
          {approved&&<p className="member-success"><CheckCircle2 size={16}/> Strategic Plan approved. You can now confirm the responsibilities agreed during the session.</p>}
        </>}
      </>,"generate-strategy")}

      {card(9,"Confirm Delegation And Give Everyone Their Execution Tools","Confirm what was actually agreed in the meeting before anything is sent.",approved,<>
        <p>The platform uses the session transcript to identify people who were explicitly given responsibility. Review every person, correct anything that needs correction, add an email where necessary, and save. The transcript helps; you remain the final authority.</p>

        <div className="sp-actions">
          {completed.filter(person=>!delegates.some(item=>item.participant_id===person.participant_id)).map(person=><Button secondary key={person.participant_id} onClick={()=>addKnownDelegate(person)}><Plus size={14}/> ADD {person.name.toUpperCase()}</Button>)}
          <Button secondary onClick={addOtherDelegate}><Plus size={14}/> ADD SOMEONE ELSE FROM THE SESSION</Button>
        </div>

        {!delegates.length?<div className="sp-empty">No execution responsibility was clearly identified from the transcript yet. Add the people who agreed to carry work forward, or return to the transcript if the discussion needs to be made clearer.</div>:<div className="sp-delegation-list">{delegates.map(person=><article className="sp-delegate-card" key={person.delegation_id}>
          <label><strong>Name</strong><input value={person.name||""} onChange={event=>updateDelegate(person.delegation_id,"name",event.target.value)}/></label>
          <label><strong>Email</strong><input type="email" value={person.email||""} onChange={event=>updateDelegate(person.delegation_id,"email",event.target.value)}/></label>
          <label><strong>Board / leadership role</strong><input value={person.role||""} onChange={event=>updateDelegate(person.delegation_id,"role",event.target.value)}/></label>
          <label><strong>Responsibilities agreed during the session, one per line</strong><textarea rows={6} value={(person.responsibilities||[]).join("\n")} onChange={event=>updateDelegate(person.delegation_id,"responsibilities",event.target.value.split("\n").map(x=>x.trim()).filter(Boolean))}/></label>
          <label><strong>Strategic areas involved, one per line</strong><textarea rows={4} value={(person.areas||[]).join("\n")} onChange={event=>updateDelegate(person.delegation_id,"areas",event.target.value.split("\n").map(x=>x.trim()).filter(Boolean))}/></label>
          <label><strong>First agreed action, if one was stated</strong><textarea rows={3} value={person.first_action||""} onChange={event=>updateDelegate(person.delegation_id,"first_action",event.target.value)}/></label>
          <button type="button" className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={()=>removeDelegate(person.delegation_id)}>REMOVE</button>
        </article>)}</div>}

        <div className="sp-actions">
          <Button disabled={!delegates.length||delegates.some(person=>!person.name?.trim()||!(person.responsibilities||[]).length)||busy==="save-delegates"} onClick={saveDelegates}>{busy==="save-delegates"?"SAVING…":"SAVE CONFIRMED DELEGATION"}</Button>
          <Button disabled={!delegates.length||delegates.some(person=>!person.name?.trim()||!(person.responsibilities||[]).length)||busy==="portfolios"} onClick={createPortfolios}>{busy==="portfolios"?"CREATING…":"CREATE BOARD MEMBER PORTFOLIOS & ASSISTANTS"}</Button>
        </div>

        {portfolios.length>0&&<div className="sp-contentbox"><h3>Board Member Portfolios & Executive Assistants</h3>{portfolios.map(row=><article className="sp-portfolio-row" key={row.token}><div><strong>{row.name}</strong><p>{(row.responsibilities||[]).join(" · ")}</p><small>{row.email||"Add an email in the delegation list before sending."}</small></div><div className="sp-actions"><a className="bfg-btn bfg-btn-ghost bfg-btn-sm" href={`/strategic-leadership-portfolio/${row.token}`} target="_blank" rel="noreferrer">OPEN EXPERIENCE</a><Button disabled={!row.email||Boolean(row.sent_at)||busy===`send-${row.token}`} onClick={()=>act(`send-${row.token}`,()=>axios.post(`${API}/guided/strategic-planning/leadership-portfolio/send`,{session_id:sid,token:row.token}))}>{row.sent_at?"SENT":"SEND STRATEGY + ROLE"}</Button></div></article>)}</div>}
      </>)}

      {message&&<p className="bfg-error">{message}</p>}

      <section className="sp-support-card">
        <h2>Ask For Help</h2>
        <p>If you get stuck anywhere in the process, send the question from here. Tell us what you are trying to do and where you are stuck.</p>
        {supportSent?<p className="member-success">{supportSent}</p>:<div className="sp-support-form">
          <select value={support.support_type} onChange={event=>setSupport({...support,support_type:event.target.value})}>
            <option value="">Choose what you need help with</option>
            <option>Strategic Planning process</option>
            <option>Facilitating the Board session</option>
            <option>Strategic Plan review</option>
            <option>Delegation and Board Member portfolios</option>
            <option>Using the platform</option>
          </select>
          <textarea rows={5} value={support.message} onChange={event=>setSupport({...support,message:event.target.value})} placeholder="Tell us what you need help with"/>
          <Button disabled={!support.support_type||!support.message.trim()||busy==="support"} onClick={()=>act("support",async()=>{const response=await axios.post(`${API}/guided/strategic-planning/support`,{session_id:sid,...support});setSupportSent(response.data.message)})}>SEND SUPPORT REQUEST</Button>
        </div>}
      </section>
    </div>
  </main></BfgShell>;
}
