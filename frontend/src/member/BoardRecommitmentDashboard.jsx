import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ExternalLink, LifeBuoy, PlayCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { MemberShell } from "./MemberShell";
import { SupportBox } from "./CoursePages";
import { memberApi } from "./api";
import RecommitmentFormsSection from "./RecommitmentFormsSection";
import ReactivationUnderstand from "./ReactivationUnderstand";
import RecommitmentFinalStage from "./RecommitmentFinalStage";
import { trackPlatformEvent, useRecommitmentSectionVideo } from "@/clean/platform";
import "./sgr.css";

const SectionVideoButton=({videoKey})=>{
  const video=useRecommitmentSectionVideo(videoKey);
  const url=video?.url?.startsWith("http")?video.url:video?.youtube_id?`https://www.youtube.com/watch?v=${video.youtube_id}`:"";
  if(!url)return <button type="button" className="sgr-section-video is-empty" disabled><PlayCircle size={16}/> SECTION VIDEO COMING SOON</button>;
  return <a className="sgr-section-video" href={url} target="_blank" rel="noreferrer"><PlayCircle size={16}/> PLAY SECTION VIDEO <ExternalLink size={13}/></a>;
};

const Section=({number,title,summary,status,videoKey,testId,children,defaultOpen=false})=>{
  const[open,setOpen]=useState(defaultOpen);
  useEffect(()=>{
    const sync=()=>{if(window.location.hash===`#${testId}`)setOpen(true)};
    sync();window.addEventListener("hashchange",sync);return()=>window.removeEventListener("hashchange",sync);
  },[testId]);
  return <section id={testId} className={`member-card sgr-flow-section sgr-machine-section ${open?"is-open":""}`}>
    <div className="sgr-section-video-row"><SectionVideoButton videoKey={videoKey}/></div>
    <button type="button" className="sgr-section-toggle" onClick={()=>setOpen(!open)} aria-expanded={open}>
      <span className="sgr-step-number">{number}</span>
      <span><strong>{title}</strong><small>{summary}</small></span>
      <span className="sgr-section-right">{status&&<em className="sgr-stage-status">{status}</em>}<ChevronDown size={18} className={open?"rotate":""}/></span>
    </button>
    {open&&<div className="sgr-section-body">{children}</div>}
  </section>;
};

export default function BoardRecommitmentDashboard(){
  const navigate=useNavigate();
  const[setup,setSetup]=useState(null);
  const[form,setForm]=useState(null);
  const[board,setBoard]=useState(null);
  const[refreshKey,setRefreshKey]=useState(0);

  const load=useCallback(async()=>{
    const [setupResponse,formResponse,boardResponse]=await Promise.all([
      memberApi.get("/reactivation/setup").catch(()=>({data:null})),
      memberApi.get("/reactivation/recommitment-form").catch(()=>({data:null})),
      memberApi.get("/reactivation/my-board").catch(()=>({data:null})),
    ]);
    setSetup(setupResponse.data);
    setForm(formResponse.data);
    setBoard(boardResponse.data);
  },[]);

  useEffect(()=>{load()},[load,refreshKey]);
  useEffect(()=>{
    const rows=board?Object.values(board.groups||{}).flat():[];
    const respondents=rows.filter(row=>row.status==="COMPLETED");
    const resolved=respondents.filter(row=>row.conversation_outcome&&String(row.conversation_conclusion||"").trim());
    if(respondents.length&&resolved.length===respondents.length)trackPlatformEvent("board-recommitment","platform_completed");
  },[board]);

  const changed=()=>{setRefreshKey(value=>value+1);load()};
  const rows=board?Object.values(board.groups||{}).flat():[];
  const responded=rows.filter(row=>row.status==="COMPLETED").length;
  const resolved=rows.filter(row=>row.status==="COMPLETED"&&row.conversation_outcome&&String(row.conversation_conclusion||"").trim()).length;
  const setupComplete=Boolean(setup?.complete);
  const formApproved=form?.status==="Approved";

  return <MemberShell><main className="member-page sgr recommitment-clean-dashboard" data-testid="board-recommitment-dashboard">
    <header className="sgr-dashboard-hero">
      <p className="eyebrow">NONPROFIT BOARD BUILDER</p>
      <h1>BOARD RECOMMITMENT</h1>
      <p>Give each Board Member a clear opportunity to recommit, move into an Advisory Board role or step down gracefully, then turn the final agreement into a role they can actually execute.</p>
      <div className="sgr-dashboard-promise">
        <span>1. Give the process context</span><span>2. Send the right form</span><span>3. Have the right conversation</span><span>4. Confirm the way forward</span>
      </div>
    </header>

    <Section number="1" title="ANSWER FOUR IMPORTANT QUESTIONS"
      summary="Tell us your mission, why recommitment matters, what you need the Board to help accomplish and when you need the new commitment in place."
      status={setupComplete?"Complete":"Start Here"} videoKey="questions" testId="recommitment-questions" defaultOpen>
      <div className="sgr-clean-stage">
        <h2>Give The Process The Context It Needs</h2>
        <p>These four answers become the organization context used by the Recommitment Forms, response interpretation, call scripts and final Board Member Portfolios.</p>
        {setup?.answers?.logo_data_url&&<img src={setup.answers.logo_data_url} alt="Organization logo" className="recommitment-dashboard-logo"/>}
        <button className="button" onClick={()=>navigate("/board-recommitment/questions")}>{setupComplete?"REVIEW MY FOUR ANSWERS":"ANSWER THE FOUR QUESTIONS"}</button>
      </div>
    </Section>

    <Section number="2" title="PREPARE AND SEND THE RECOMMITMENT FORMS"
      summary="Create both form versions, approve the outreach email, copy what you need or send a personal form directly from the platform."
      status={!setupComplete?"Locked":formApproved?"Ready":"Prepare"} videoKey="forms" testId="recommitment-forms">
      {!setupComplete?<p className="workspace-note">Complete the four questions in Section 1 first.</p>:<RecommitmentFormsSection onChanged={changed}/>}
    </Section>

    <Section number="3" title="REVIEW RESPONSES AND PREPARE THE CONVERSATION"
      summary="Every submitted form appears automatically. View or download the response, interpret what it means and generate the one-on-one call script for that person's chosen path."
      status={!formApproved?"Locked":responded?`${responded} Responded`:"Waiting For Responses"} videoKey="responses" testId="recommitment-responses">
      {!formApproved?<p className="workspace-note">Approve the Recommitment Forms first.</p>:<ReactivationUnderstand key={refreshKey}/>}
    </Section>

    <Section number="4" title="CONFIRM THE FINAL OUTCOME AND MOVE EACH PERSON FORWARD"
      summary="After the conversation, record what was actually agreed. Confirm Active Board, Advisory Board or Step Down, then create the correct Portfolio or transition email."
      status={!responded?"Waiting For Responses":resolved===responded?"Complete":`${resolved}/${responded} Resolved`} videoKey="decisions" testId="recommitment-decisions">
      {!responded?<p className="workspace-note">Board Members appear here automatically after submitting their Recommitment Form.</p>:<RecommitmentFinalStage key={refreshKey}/>}
    </Section>

    <section className="sgr-persistent-support" data-testid="recommitment-support">
      <div className="sgr-support-heading"><LifeBuoy size={28}/><div><p className="eyebrow">SUPPORT THROUGHOUT THE PROCESS</p><h2>Need Help With Board Recommitment?</h2><p>Tell us where you are stuck, which response you are trying to understand or which conversation you need help preparing for.</p></div></div>
      <SupportBox productKey="reactivation_self_guided" moduleNumber={1} supportTypes={["I have a question about this step","I need help understanding a Board Member response","I need help preparing for a conversation","I need help deciding the correct next step","I need help using the platform"]}/>
    </section>
  </main></MemberShell>;
}
