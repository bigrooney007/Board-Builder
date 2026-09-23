import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, ChevronDown, Copy, Download, ExternalLink, FileText, LifeBuoy, Mail, PlayCircle, Plus, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import { trackPlatformEvent, useStrategicPlanningSectionVideo } from "@/clean/platform";
import "@/game/game.css";
import "./guided-products.css";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

const Button=({children,onClick,disabled=false,secondary=false,testId="",href=""})=>{
  const cls=`bfg-btn ${secondary?"bfg-btn-ghost":"bfg-btn-primary"} bfg-btn-sm`;
  if(href)return <a className={cls} href={href} target="_blank" rel="noreferrer" data-testid={testId||undefined}>{children}</a>;
  return <button type="button" className={cls} disabled={disabled} onClick={onClick} data-testid={testId||undefined}>{children}</button>;
};

const SectionVideo=({videoKey})=>{
  const video=useStrategicPlanningSectionVideo(videoKey);
  const url=video?.url?.startsWith("http")?video.url:video?.youtube_id?`https://www.youtube.com/watch?v=${video.youtube_id}`:"";
  if(!url)return <button className="sp-section-video is-empty" disabled><PlayCircle size={15}/> SECTION VIDEO COMING SOON</button>;
  return <a className="sp-section-video" href={url} target="_blank" rel="noreferrer"><PlayCircle size={15}/> PLAY SECTION VIDEO <ExternalLink size={12}/></a>;
};

const Step=({n,title,summary,status,locked=false,videoKey,children,open,setOpen,testId})=>(
  <section className={`sp-dash-card sp-clean-section ${locked?"sp-locked":""} ${open?"is-open":""}`} id={testId}>
    <div className="sp-video-row"><SectionVideo videoKey={videoKey}/></div>
    <button type="button" className="sp-card-toggle" onClick={()=>!locked&&setOpen(!open)} aria-expanded={open}>
      <span className="sp-step">{n}</span>
      <span><strong>{title}</strong><small>{locked?"Complete the earlier stage first.":summary}</small></span>
      <span className="sp-clean-status">{status&&<em>{status}</em>}<ChevronDown size={18} className={open?"rotate":""}/></span>
    </button>
    {open&&!locked&&<div className="sp-card-body">{children}</div>}
  </section>
);

const fmtMeeting=(meeting)=>{
  if(!meeting?.meeting_date)return "";
  try{
    const d=new Date(`${meeting.meeting_date}T12:00:00`);
    return `${d.toLocaleDateString(undefined,{year:"numeric",month:"long",day:"numeric"})} at ${meeting.start_time||""} ${meeting.timezone_name||""}`;
  }catch{return `${meeting.meeting_date} ${meeting.start_time||""} ${meeting.timezone_name||""}`;}
};

export default function StrategicPlanningDashboard(){
  const sid=new URLSearchParams(window.location.search).get("session_id")||"";
  const navigate=useNavigate();
  const[ctx,setCtx]=useState(null);
  const[session,setSession]=useState(null);
  const[open,setOpen]=useState("1");
  const[busy,setBusy]=useState("");
  const[message,setMessage]=useState("");
  const[invite,setInvite]=useState({name:"",email:""});
  const[meeting,setMeeting]=useState({meeting_date:"",start_time:"",timezone_name:Intl.DateTimeFormat().resolvedOptions().timeZone||""});
  const[finalDraft,setFinalDraft]=useState("");
  const[editingPlan,setEditingPlan]=useState(false);
  const[delegates,setDelegates]=useState([]);
  const[support,setSupport]=useState({support_type:"",message:""});
  const[supportSent,setSupportSent]=useState("");
  const preparingForm=useRef(false);
  const triggeringPlan=useRef(false);

  const load=useCallback(async()=>{
    try{
      const [workspace,live]=await Promise.all([
        axios.get(`${API}/guided/strategic-planning/workspace`,{params:{session_id:sid}}),
        axios.get(`${API}/guided/strategic-planning/session`,{params:{session_id:sid}}).catch(()=>({data:null})),
      ]);
      setCtx(workspace.data);
      setSession(live.data);
      const savedMeeting=workspace.data.project?.planning_meeting||{};
      if(savedMeeting.meeting_date)setMeeting(savedMeeting);
      setFinalDraft(workspace.data.project?.final_plan?.display_text||"");

      const participants=workspace.data.project?.participants||[];
      const active=workspace.data.project?.active_delegation?.delegates||[];
      const byParticipant=new Map(active.filter(x=>x.participant_id).map(x=>[x.participant_id,x]));
      const rows=[...active];
      participants.filter(p=>p.status==="COMPLETED").forEach(person=>{
        if(byParticipant.has(person.participant_id))return;
        rows.push({
          delegation_id:`participant-${person.participant_id}`,participant_id:person.participant_id,
          name:person.name,email:person.email||"",role:person.role==="Lead User"?"":(person.role||""),
          responsibilities:[],areas:[],first_action:"",support_needed:"",reporting_rhythm:"",
          source:"Participated in Strategic Planning",
        });
      });
      setDelegates(rows);
    }catch(error){setMessage(error.response?.data?.detail||"We could not load your Strategic Planning workspace.");}
  },[sid]);

  useEffect(()=>{if(sid)load();},[sid,load]);

  useEffect(()=>{
    if(!ctx||session?.status==="COMPLETED"||p?.final_plan?.display_text)return undefined;
    const timer=window.setInterval(load,15000);
    return()=>window.clearInterval(timer);
  },[ctx,session?.status,p?.final_plan?.display_text,load]);

  const p=ctx?.project||{};
  const answers=ctx?.organization_answers||{};
  const participants=p.participants||[];
  const completed=participants.filter(person=>person.status==="COMPLETED");
  const lead=participants.find(person=>person.role==="Lead User");
  const boardPeople=participants.filter(person=>person.role!=="Lead User");
  const boardResponses=boardPeople.filter(person=>person.status==="COMPLETED");
  const requiredOrg=["mission","goals","objectives","team_building","technology","marketing","partnerships","fundraising","budget","action_planning"];
  const programs=Array.isArray(answers.program_details)?answers.program_details.filter(x=>x?.name?.trim()):String(answers.programs||"").split("\n").filter(Boolean);
  const organizationReady=Boolean(p.organization_details_saved_at&&requiredOrg.every(key=>String(answers[key]||"").trim())&&programs.length);
  const meetingReady=Boolean(p.planning_meeting?.meeting_date&&p.planning_meeting?.start_time&&p.planning_meeting?.timezone_name);
  const formReady=p.form?.status==="Approved";
  const leadDone=lead?.status==="COMPLETED";
  const guideReady=Boolean(p.meeting_guide_text);
  const sessionDone=session?.status==="COMPLETED";
  const finalStatus=p.final_plan?.status||"NONE";
  const finalReady=Boolean(p.final_plan?.display_text);
  const approved=finalStatus==="Approved";
  const finalGenerating=finalStatus==="Generating";
  const finalFailed=finalStatus==="Failed";
  const portfolios=p.portfolios||[];
  const leadLink=p.lead_form_token?`${window.location.origin}/strategic-planning-form/${p.lead_form_token}`:"";
  const formLink=formReady?`${window.location.origin}/strategic-planning-form/${p.generic_form_token}`:"";
  const reviewLink=p.final_plan?.review_url?`${window.location.origin}${p.final_plan.review_url}`:"";

  useEffect(()=>{
    if(!ctx||!organizationReady||!meetingReady||formReady||preparingForm.current)return;
    preparingForm.current=true;
    axios.post(`${API}/guided/strategic-planning/prepare-form`,{session_id:sid})
      .then(()=>load()).catch(e=>setMessage(e.response?.data?.detail||"We could not prepare your Strategic Planning Form."))
      .finally(()=>{preparingForm.current=false;});
  },[ctx,organizationReady,meetingReady,formReady,sid,load]);

  useEffect(()=>{
    if(!sessionDone||finalReady||finalGenerating||triggeringPlan.current)return;
    triggeringPlan.current=true;
    axios.post(`${API}/guided/strategic-planning/session-plan`,{session_id:sid})
      .then(()=>load()).catch(e=>setMessage(e.response?.data?.detail||"We could not start your Strategic Plan generation."))
      .finally(()=>{triggeringPlan.current=false;});
  },[sessionDone,finalReady,finalGenerating,sid,load]);

  useEffect(()=>{
    if(!finalGenerating)return;
    const timer=window.setInterval(load,5000);
    return()=>window.clearInterval(timer);
  },[finalGenerating,load]);

  useEffect(()=>{
    const hash=window.location.hash;
    const map={"#sp-meeting":"2","#sp-founder-form":"3","#sp-board":"4","#sp-guide":"5","#sp-session":"6","#sp-plan":"7","#generate-strategy":"7"};
    if(map[hash]){setOpen(map[hash]);setTimeout(()=>document.querySelector(hash)?.scrollIntoView({behavior:"smooth",block:"start"}),100);}
  },[ctx]);

  const act=async(key,fn)=>{
    setBusy(key);setMessage("");
    try{await fn();await load();}
    catch(error){setMessage(error.response?.data?.detail||"That action could not be completed.");}
    setBusy("");
  };

  const saveMeeting=()=>act("meeting",()=>axios.put(`${API}/guided/strategic-planning/planning-meeting`,{session_id:sid,...meeting}));
  const sendInvite=()=>act("invite",async()=>{
    await axios.post(`${API}/guided/strategic-planning/invite`,{session_id:sid,...invite});
    setInvite({name:"",email:""});
  });
  const generateGuide=()=>act("guide",()=>axios.post(`${API}/guided/strategic-planning/facilitation-guide`,{session_id:sid}));
  const savePlan=()=>act("save-plan",()=>axios.put(`${API}/guided/strategic-planning/final-plan/draft`,{session_id:sid,display_text:finalDraft}));
  const approvePlan=()=>act("approve-plan",async()=>{
    await axios.put(`${API}/guided/strategic-planning/final-plan/draft`,{session_id:sid,display_text:finalDraft});
    await axios.post(`${API}/guided/strategic-planning/final-plan/approve`,{session_id:sid});
    trackPlatformEvent("strategic-planning","platform_completed");
    setEditingPlan(false);
  });
  const copy=text=>navigator.clipboard?.writeText(text);
  const downloadResponse=participantId=>window.open(`${API}/guided/strategic-planning-response/${participantId}/pdf`,"_blank");

  const updateDelegate=(id,field,value)=>setDelegates(rows=>rows.map(x=>x.delegation_id===id?{...x,[field]:value}:x));
  const removeDelegate=id=>setDelegates(rows=>rows.filter(x=>x.delegation_id!==id));
  const addDelegate=()=>setDelegates(rows=>[...rows,{delegation_id:`manual-${Date.now()}`,participant_id:"",name:"",email:"",role:"",responsibilities:[],areas:[],first_action:"",support_needed:"",reporting_rhythm:"",source:"Founder added"}]);
  const confirmedDelegates=useMemo(()=>delegates.filter(x=>x.name?.trim()&&x.role?.trim()&&(x.responsibilities||[]).length),[delegates]);
  const saveDelegates=()=>act("save-delegates",()=>axios.put(`${API}/guided/strategic-planning/active-delegation/people`,{session_id:sid,delegates:confirmedDelegates}));
  const createPortfolios=()=>act("portfolios",async()=>{
    await axios.put(`${API}/guided/strategic-planning/active-delegation/people`,{session_id:sid,delegates:confirmedDelegates});
    await axios.post(`${API}/guided/strategic-planning/portfolios`,{session_id:sid});
  });

  if(!ctx)return <BfgShell><main className="guided-page"><section className="guided-section"><h1>Strategic Planning</h1><p>{message||"Preparing your workspace…"}</p></section></main></BfgShell>;

  return <BfgShell><main className="guided-page sp-dashboard sp-clean-dashboard">
    <section className="sp-clean-hero">
      <p className="bfg-eyebrow">NONPROFIT BOARD BUILDER</p>
      <h1>STRATEGIC PLANNING WITH YOUR BOARD</h1>
      <p>Start with what is true about the organization today. Let every person think independently. Bring those ideas into one Board conversation, make the decisions together, then turn the decisions into a Strategic Plan and confirmed execution roles.</p>
    </section>

    <div className="sp-dash-stack">
      <Step n="1" title="TELL US ABOUT YOUR ORGANIZATION" summary="Capture the organization's present mission, goals, objectives, programs, people, tools, growth functions, budget and action planning." status={organizationReady?"Complete":"Start Here"} videoKey="organization" open={open==="1"} setOpen={v=>setOpen(v?"1":"")} testId="sp-organization">
        <div className="sp-clean-stage">
          <h2>Give The Board A Real Starting Point</h2>
          <p>The organization information is not treated as the final strategy. It gives everyone something real to test, question, protect and improve.</p>
          {p.logo_data_url&&<img src={p.logo_data_url} className="sp-dashboard-logo" alt="Organization logo"/>}
          <Button onClick={()=>navigate(`/strategic-planning/organization?session_id=${encodeURIComponent(sid)}`)}>{organizationReady?"REVIEW ORGANIZATION INFORMATION":"TELL US ABOUT YOUR ORGANIZATION"}</Button>
        </div>
      </Step>

      <Step n="2" title="SET YOUR NEXT STRATEGIC PLANNING MEETING" summary="Save the date, time and timezone for the Board session before the planning form goes out." status={!organizationReady?"Locked":meetingReady?"Scheduled":"Set Meeting"} locked={!organizationReady} videoKey="meeting" open={open==="2"} setOpen={v=>setOpen(v?"2":"")} testId="sp-meeting">
        <div className="sp-clean-stage">
          <h2>When Is Your Next Board Strategic Planning Meeting?</h2>
          <p>That is the meeting everyone is preparing for. The date and time are carried into direct Board invitations.</p>
          <div className="sp-meeting-grid">
            <label>Date<input type="date" value={meeting.meeting_date||""} onChange={e=>setMeeting({...meeting,meeting_date:e.target.value})}/></label>
            <label>Time<input type="time" value={meeting.start_time||""} onChange={e=>setMeeting({...meeting,start_time:e.target.value})}/></label>
            <label>Timezone<input value={meeting.timezone_name||""} onChange={e=>setMeeting({...meeting,timezone_name:e.target.value})}/></label>
          </div>
          <Button disabled={!meeting.meeting_date||!meeting.start_time||!meeting.timezone_name||busy==="meeting"} onClick={saveMeeting}>{busy==="meeting"?"SAVING…":meetingReady?"UPDATE MEETING":"SAVE MEETING"}</Button>
          {meetingReady&&<p className="member-success"><CheckCircle2 size={15}/> {fmtMeeting(p.planning_meeting)}</p>}
        </div>
      </Step>

      <Step n="3" title="COMPLETE YOUR OWN STRATEGIC PLANNING FORM" summary="Critique the organization's starting ideas yourself before asking the rest of the Board to do the same." status={!meetingReady?"Locked":leadDone?"Complete":formReady?"Ready":"Preparing"} locked={!meetingReady} videoKey="founder-form" open={open==="3"} setOpen={v=>setOpen(v?"3":"")} testId="sp-founder-form">
        <div className="sp-clean-stage">
          <h2>Your Thinking Belongs In The Same Pool As Everyone Else's</h2>
          <p>You complete the same Strategic Planning Form the Board will complete. Your ideas stay attributable to you during the session instead of becoming the assumed answer.</p>
          {!formReady?<p className="workspace-note">Preparing your Strategic Planning Form from the organization information you supplied…</p>:leadLink?<Button href={leadLink}>{leadDone?"REVIEW / UPDATE MY STRATEGIC PLANNING FORM":"COMPLETE MY STRATEGIC PLANNING FORM"}</Button>:<p className="workspace-note">Preparing your personal form link…</p>}
          {leadDone&&<p className="member-success"><CheckCircle2 size={15}/> Your response is saved and will enter the live session with everyone else's ideas.</p>}
        </div>
      </Step>

      <Step n="4" title="INVITE YOUR BOARD AND COLLECT THEIR IDEAS" summary="Send the same Strategic Planning Form to each Board Member and see every completed response in one place." status={!leadDone?"Locked":boardResponses.length?`${boardResponses.length} Responded`:"Invite Board"} locked={!leadDone} videoKey="board-forms" open={open==="4"} setOpen={v=>setOpen(v?"4":"")} testId="sp-board">
        <div className="sp-clean-stage">
          <h2>Invite Board Members To Think Before The Meeting</h2>
          <p>Add each Board Member's name and email. They receive their own secure form link and the meeting date. Their original ideas remain traceable to them during the live session.</p>
          <div className="sp-invite-grid">
            <input placeholder="Board Member Name" value={invite.name} onChange={e=>setInvite({...invite,name:e.target.value})}/>
            <input type="email" placeholder="Board Member Email" value={invite.email} onChange={e=>setInvite({...invite,email:e.target.value})}/>
            <Button disabled={!invite.name.trim()||!invite.email.trim()||busy==="invite"} onClick={sendInvite}><Mail size={14}/> {busy==="invite"?"SENDING…":"SEND STRATEGIC PLANNING FORM"}</Button>
          </div>
          {formLink&&<div className="sp-linkbox"><span>{formLink}</span><button onClick={()=>copy(formLink)}><Copy size={14}/> COPY GENERAL FORM LINK</button></div>}
        </div>
        <div className="sp-response-list">
          {!boardPeople.length?<p className="sp-empty">No Board Members added yet.</p>:boardPeople.map(person=><article key={person.participant_id}>
            <Users size={20}/><div><strong>{person.name}</strong><span>{person.email}</span><small>{person.status==="COMPLETED"?"RESPONSE COMPLETED":person.status==="SENT"?"FORM SENT":"WAITING"}</small></div>
            <div className="sp-actions">
              {person.status==="COMPLETED"&&<Button secondary href={`/strategic-planning-response/${person.participant_id}`}>VIEW RESPONSE</Button>}
              {person.status==="COMPLETED"&&<Button secondary onClick={()=>downloadResponse(person.participant_id)}><Download size={14}/> DOWNLOAD</Button>}
              {person.status!=="COMPLETED"&&<Button secondary disabled={busy===`resend-${person.participant_id}`} onClick={()=>act(`resend-${person.participant_id}`,()=>axios.post(`${API}/guided/strategic-planning/invite`,{session_id:sid,name:person.name,email:person.email}))}>RESEND FORM</Button>}
            </div>
          </article>)}
        </div>
      </Step>

      <Step n="5" title="PREPARE FOR THE STRATEGIC PLANNING SESSION" summary="Generate the facilitation guide from the organization context and the ideas submitted before the meeting." status={!boardResponses.length?"Locked":guideReady?"Ready":"Generate Guide"} locked={!boardResponses.length} videoKey="facilitation-guide" open={open==="5"} setOpen={v=>setOpen(v?"5":"")} testId="sp-guide">
        <div className="sp-clean-stage">
          <h2>Your Facilitation Guide</h2>
          <p>The guide prepares you to facilitate Mission, Goals, Objectives, every Program, Team, Technology, Marketing, Partnerships, Fundraising, Budget, Action Planning and execution roles without flattening anybody's thinking.</p>
          <div className="sp-actions">
            <Button disabled={busy==="guide"} onClick={generateGuide}><FileText size={14}/> {busy==="guide"?"PREPARING…":guideReady?"REGENERATE FACILITATION GUIDE":"GENERATE FACILITATION GUIDE"}</Button>
            {guideReady&&<Button secondary href={`${API}/guided/strategic-planning/facilitation-guide/pdf?session_id=${encodeURIComponent(sid)}`}><Download size={14}/> DOWNLOAD GUIDE</Button>}
          </div>
          {guideReady&&<details className="sp-guide"><summary>View Facilitation Guide</summary><pre>{p.meeting_guide_text}</pre></details>}
        </div>
      </Step>

      <Step n="6" title="RUN THE STRATEGIC PLANNING SESSION" summary="Share one Board screen, transcribe the discussion with consent and make one strategic decision at a time." status={!guideReady?"Locked":sessionDone?"Complete":"Ready"} locked={!guideReady} videoKey="live-session" open={open==="6"} setOpen={v=>setOpen(v?"6":"")} testId="sp-session">
        <div className="sp-clean-stage">
          <h2>Bring Everybody's Ideas Into One Board Conversation</h2>
          <p>The existing live session keeps the Lead User in control of the clicks while everyone follows the shared screen. It preserves the option to leave the mission unchanged, captures the Board's selected ideas and keeps the meeting transcript as context for what people actually meant and agreed.</p>
          <Button onClick={()=>navigate(`/strategic-planning/session?session_id=${encodeURIComponent(sid)}`)}>{sessionDone?"VIEW COMPLETED STRATEGIC PLANNING SESSION":"OPEN STRATEGIC PLANNING SESSION"}</Button>
          {sessionDone&&<p className="member-success"><CheckCircle2 size={15}/> The Board decisions and meeting transcript are saved. Your Strategic Plan generation starts automatically.</p>}
        </div>
      </Step>

      <Step n="7" title="REVIEW THE STRATEGIC PLAN, CONFIRM ROLES AND MOVE INTO EXECUTION" summary="Review the generated plan, give the Board a review link, adopt it when ready, then confirm each person's role before creating their Leadership Portfolio." status={!sessionDone?"Locked":approved?"Execution Ready":finalReady?"Review Plan":finalGenerating?"Generating":"Preparing"} locked={!sessionDone} videoKey="plan-execution" open={open==="7"} setOpen={v=>setOpen(v?"7":"")} testId="sp-plan">
        {!finalReady?<div className="sp-clean-stage">
          <h2>{finalFailed?"Strategic Plan Generation Needs Another Attempt":"Building Your Strategic Plan"}</h2>
          <p>{finalFailed?"No Board decisions or responses were lost. Start generation again.":"The plan is being built from the organization's starting information, every original contribution behind the Board's selected ideas and the live meeting discussion. You do not need to start another planning process."}</p>
          {finalFailed&&<Button disabled={busy==="strategy"} onClick={()=>act("strategy",()=>axios.post(`${API}/guided/strategic-planning/session-plan`,{session_id:sid}))}>TRY AGAIN</Button>}
        </div>:<>
          <div className="sp-clean-stage">
            <p className="bfg-eyebrow">YOUR STRATEGIC PLAN</p>
            <h2>{approved?"Strategic Plan Adopted":"Review The Plan Before Adoption"}</h2>
            <p>The plan follows the agreed structure: Executive Summary, Mission, Goals, Objectives, each Program, Team Structure, Technology, Marketing, Partnerships, Fundraising, Budget and Action Planning.</p>
            {!editingPlan?<pre className="sp-plan-preview">{finalDraft}</pre>:<textarea rows={34} value={finalDraft} disabled={approved} onChange={e=>setFinalDraft(e.target.value)}/>}
            <div className="sp-actions">
              {!approved&&!editingPlan&&<Button secondary onClick={()=>setEditingPlan(true)}>EDIT STRATEGIC PLAN</Button>}
              {!approved&&editingPlan&&<Button secondary disabled={busy==="save-plan"} onClick={savePlan}>{busy==="save-plan"?"SAVING…":"SAVE EDITS"}</Button>}
              {reviewLink&&<Button secondary onClick={()=>copy(reviewLink)}><Copy size={14}/> COPY BOARD REVIEW LINK</Button>}
              {reviewLink&&!approved&&<Button secondary disabled={busy==="send-review"} onClick={()=>act("send-review",()=>axios.post(`${API}/guided/strategic-planning/send-draft-email`,{session_id:sid}))}>{busy==="send-review"?"SENDING…":"SEND REVIEW LINK TO PARTICIPANTS"}</Button>}
              {!approved&&<Button disabled={busy==="approve-plan"} onClick={approvePlan}>{busy==="approve-plan"?"ADOPTING…":"APPROVE & ADOPT STRATEGIC PLAN"}</Button>}
              {approved&&<Button href={`${API}/guided/strategic-planning/final-plan/pdf?session_id=${encodeURIComponent(sid)}`}><Download size={14}/> DOWNLOAD STRATEGIC PLAN</Button>}
              {approved&&p.final_plan?.share_url&&<Button secondary onClick={()=>copy(`${window.location.origin}${p.final_plan.share_url}`)}><Copy size={14}/> COPY ADOPTED PLAN LINK</Button>}
            </div>
          </div>

          <div className={`sp-clean-stage sp-role-confirmation ${approved?"":"sp-locked-inner"}`}>
            <p className="bfg-eyebrow">BOARD EXECUTION ROLES</p>
            <h2>Confirm What Each Person Will Carry Forward</h2>
            <p>Everybody who completed the planning process appears here. Anyone explicitly named in the live discussion can also appear through the meeting extraction. The platform can propose from what people volunteered and what the meeting explicitly agreed, but you confirm the actual role and responsibility before any Portfolio is generated.</p>
            {!approved?<p className="workspace-note">Adopt the Strategic Plan before generating Leadership Portfolios.</p>:<>
              <div className="sp-actions"><Button secondary onClick={addDelegate}><Plus size={14}/> ADD SOMEONE ELSE FROM THE SESSION</Button></div>
              <div className="sp-delegation-list">{delegates.map(person=><article className="sp-delegate-card" key={person.delegation_id}>
                <p className="workspace-note"><strong>Starting source:</strong> {person.source||"Strategic Planning participant"}</p>
                <label><strong>Name</strong><input value={person.name||""} onChange={e=>updateDelegate(person.delegation_id,"name",e.target.value)}/></label>
                <label><strong>Email</strong><input type="email" value={person.email||""} onChange={e=>updateDelegate(person.delegation_id,"email",e.target.value)}/></label>
                <label><strong>Confirmed Board / leadership role</strong><input value={person.role||""} onChange={e=>updateDelegate(person.delegation_id,"role",e.target.value)} placeholder="Confirm or edit the role this person will carry"/></label>
                <label><strong>Confirmed responsibilities, one per line</strong><textarea rows={5} value={(person.responsibilities||[]).join("\n")} onChange={e=>updateDelegate(person.delegation_id,"responsibilities",e.target.value.split("\n").map(x=>x.trim()).filter(Boolean))}/></label>
                <label><strong>Strategic areas involved, one per line</strong><textarea rows={3} value={(person.areas||[]).join("\n")} onChange={e=>updateDelegate(person.delegation_id,"areas",e.target.value.split("\n").map(x=>x.trim()).filter(Boolean))}/></label>
                <label><strong>First agreed action</strong><textarea rows={2} value={person.first_action||""} onChange={e=>updateDelegate(person.delegation_id,"first_action",e.target.value)}/></label>
                <Button secondary onClick={()=>removeDelegate(person.delegation_id)}>REMOVE</Button>
              </article>)}</div>
              <div className="sp-actions">
                <Button disabled={!confirmedDelegates.length||busy==="save-delegates"} onClick={saveDelegates}>{busy==="save-delegates"?"SAVING…":"SAVE CONFIRMED ROLES"}</Button>
                <Button disabled={!confirmedDelegates.length||busy==="portfolios"} onClick={createPortfolios}>{busy==="portfolios"?"CREATING…":"CREATE LEADERSHIP PORTFOLIOS & ASSISTANTS"}</Button>
              </div>
              {delegates.some(x=>x.name?.trim()&&(!x.role?.trim()||!(x.responsibilities||[]).length))&&<p className="workspace-note">People without a confirmed role and at least one confirmed responsibility are not included when Portfolios are created.</p>}
            </>}
          </div>

          {approved&&portfolios.length>0&&<div className="sp-clean-stage">
            <h2>Leadership Portfolios & Executive Assistants</h2>
            <p>Each Portfolio is grounded in the adopted Strategic Plan and the role you confirmed. The Executive Assistant is constrained to that approved responsibility.</p>
            {portfolios.map(row=><article className="sp-portfolio-row" key={row.token}>
              <div><strong>{row.name}</strong><p>{row.role||"Confirmed leadership role"}</p><small>{(row.responsibilities||[]).join(" · ")}</small></div>
              <div className="sp-actions">
                <Button secondary href={`/strategic-leadership-portfolio/${row.token}`}>OPEN PORTFOLIO</Button>
                <Button disabled={!row.email||busy===`send-${row.token}`} onClick={()=>act(`send-${row.token}`,()=>axios.post(`${API}/guided/strategic-planning/leadership-portfolio/send`,{session_id:sid,token:row.token}))}>{busy===`send-${row.token}`?"SENDING…":row.sent_at?"RESEND PORTFOLIO":"SEND PORTFOLIO"}</Button>
              </div>
            </article>)}
          </div>}
        </>}
      </Step>
    </div>

    {message&&<p className="bfg-error">{message}</p>}
    <section className="sp-support-card sp-clean-support">
      <div className="sp-support-title"><LifeBuoy size={26}/><div><p className="bfg-eyebrow">SUPPORT THROUGHOUT THE PROCESS</p><h2>Need Help With Strategic Planning?</h2><p>Tell us where you are stuck and what you are trying to accomplish.</p></div></div>
      {supportSent?<p className="member-success">{supportSent}</p>:<div className="sp-support-form">
        <select value={support.support_type} onChange={e=>setSupport({...support,support_type:e.target.value})}>
          <option value="">Choose what you need help with</option>
          <option>Organization setup</option><option>Strategic Planning Form</option><option>Board participation</option><option>Facilitation Guide</option><option>Live Strategic Planning Session</option><option>Strategic Plan review</option><option>Roles and Leadership Portfolios</option><option>Using the platform</option>
        </select>
        <textarea rows={5} value={support.message} onChange={e=>setSupport({...support,message:e.target.value})} placeholder="Tell us what you need help with"/>
        <Button disabled={!support.support_type||!support.message.trim()||busy==="support"} onClick={()=>act("support",async()=>{const r=await axios.post(`${API}/guided/strategic-planning/support`,{session_id:sid,...support});setSupportSent(r.data.message)})}>SEND SUPPORT REQUEST</Button>
      </div>}
    </section>
  </main></BfgShell>;
}
