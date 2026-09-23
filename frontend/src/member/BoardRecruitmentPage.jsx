import React, { useEffect, useMemo, useState } from "react";
import { ChevronDown, ExternalLink, LifeBuoy, PlayCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { memberApi } from "./api";
import { UnlockPurchaseButton } from "./DashboardPage";
import { SupportBox } from "./CoursePages";
import { Module1Profile } from "./workspace/Module1Profile";
import { RecruitmentCampaignLaunch, RecruitmentMaterials, useMaterials } from "./workspace/WorkspaceModules";
import {
  AutomatedReferenceChecks,
  BackgroundChecksWorkspace,
  InterviewsWorkspace,
  Module4Applicants,
  OnboardingPreparation,
  OnboardingSessionWorkspace,
  RecruitmentPortfoliosWorkspace,
} from "./workspace/ApplicantModules";
import { useRecruitmentSectionVideo } from "@/clean/platform";
import "./sgr.css";

const FLOW_STEPS = [
  ["br-section-questions", "Six Questions"],
  ["br-section-identify", "Board Members Needed"],
  ["br-section-materials", "Application & Materials"],
  ["br-section-campaign", "Launch Campaign"],
  ["br-section-applicants", "Applicants"],
  ["br-section-interviews", "Interviews"],
  ["br-section-references", "References"],
  ["br-section-background", "Background Check"],
  ["br-section-onboarding-prep", "Onboarding Preparation"],
  ["br-section-onboarding-session", "Onboarding Session"],
  ["br-section-portfolios", "Board Member Portfolios"],
];

const SectionVideoButton = ({ videoKey }) => {
  const video = useRecruitmentSectionVideo(videoKey);
  const watchUrl = video?.url?.startsWith("http") ? video.url : video?.youtube_id ? "https://www.youtube.com/watch?v=" + video.youtube_id : "";
  if (!watchUrl) {
    return <button type="button" className="sgr-section-video is-empty" disabled><PlayCircle size={16}/> SECTION VIDEO COMING SOON</button>;
  }
  return (
    <a className="sgr-section-video" href={watchUrl} target="_blank" rel="noreferrer" data-testid={"section-video-" + videoKey}>
      <PlayCircle size={16}/> PLAY SECTION VIDEO <ExternalLink size={13}/>
    </a>
  );
};

const Section = ({ number, title, summary, children, testId, videoKey, status = "", defaultOpen = false }) => {
  const [open,setOpen]=useState(defaultOpen);
  useEffect(() => {
    const syncHash=()=>{if(window.location.hash===`#${testId}`)setOpen(true)};
    syncHash();
    window.addEventListener("hashchange",syncHash);
    return()=>window.removeEventListener("hashchange",syncHash);
  },[testId]);
  return (
    <section id={testId} className={"member-card sgr-flow-section sgr-machine-section " + (open?"is-open":"")} data-testid={testId}>
      <div className="sgr-section-video-row"><SectionVideoButton videoKey={videoKey}/></div>
      <button type="button" className="sgr-section-toggle" onClick={()=>setOpen(!open)} aria-expanded={open}>
        <span className="sgr-step-number">{number}</span>
        <span>
          <strong>{title}</strong>
          {summary&&<small>{summary}</small>}
        </span>
        <span className="sgr-section-right">
          {status&&<em className={"sgr-stage-status " + status.toLowerCase().replaceAll(" ","-")}>{status}</em>}
          <ChevronDown size={18} className={open?"rotate":""}/>
        </span>
      </button>
      {open&&<div className="sgr-section-body">{children}</div>}
    </section>
  );
};

export default function BoardRecruitmentPage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [assessment,setAssessment]=useState(null);\n  const { byType: dashboardMaterials } = useMaterials();

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login?next=/app/board-recruitment"); return; }
    memberApi.post("/recruit/free/member-event/dashboard_entered").catch(()=>{});
  },[loading,member,navigate]);

  useEffect(()=>{
    if(!member)return undefined;
    let active=true;
    let timer;
    const load=()=>{
      memberApi.get("/recruit/free/member-assessment/current").then(response=>{
        if(!active)return;
        setAssessment(response.data);
        const status=response.data?.state?.generation_status;
        if(["queued","generating"].includes(status)) timer=window.setTimeout(load,4000);
      }).catch(()=>{});
    };
    load();
    return()=>{active=false;if(timer)window.clearTimeout(timer)};
  },[member]);

  const allowed=member&&(member.entitlements||[]).some((entitlement)=>
    ["fundraising_board_builder","fbb_recruitment","recruitment_self_guided"].includes(entitlement)
  );
  const answers=assessment?.answers||{};
  const questionKeys=["mission","current_board","desired_board_members","support_needs","board_type","why_join"];
  const answeredCount=questionKeys.filter(key=>String(answers[key]||"").trim()).length;
  const questionsComplete=answeredCount===questionKeys.length;
  const generationStatus=assessment?.state?.generation_status||"not_started";

  const questionStatus=questionsComplete?"Complete":answeredCount?"In Progress":"Start";
  const identifyStatus=assessment?.result?"Ready To Review":questionsComplete&&["queued","generating"].includes(generationStatus)?"Generating":"Locked";

  const boardProfilesApproved=dashboardMaterials.powerhouse_board_blueprint?.status==="Approved";
  const progress=useMemo(()=>{
    if(!questionsComplete)return 0;
    if(!assessment?.result)return 1;
    if(!boardProfilesApproved)return 2;
    return 3;
  },[questionsComplete,assessment?.result,boardProfilesApproved]);

  return (
    <MemberShell>
      <main className="member-page sgr sgr-recruitment-machine" data-testid="fbb-recruitment-page">
        <header className="sgr-dashboard-hero">
          <p className="eyebrow">NONPROFIT BOARD BUILDER</p>
          <h1>SELF-GUIDED BOARD RECRUITMENT</h1>
          <p>Identify the board members your organization needs, launch a professional recruitment campaign and move the right people from applicant to active Board Member through one connected process.</p>
          <div className="sgr-dashboard-promise">
            <span>1. Identify who you need</span>
            <span>2. Launch the campaign</span>
            <span>3. Recruit and onboard your board</span>
          </div>
        </header>

        {member&&!allowed&&(
          <section className="member-card">
            <p><strong>Board Recruitment is not included in your purchase yet.</strong></p>
            <UnlockPurchaseButton product="recruitment" label="UNLOCK BOARD RECRUITMENT — $497"/>
          </section>
        )}

        {allowed&&(
          <>
            <section className="sgr-dashboard-overview member-card">
              <div>
                <p className="eyebrow">YOUR RECRUITMENT PROCESS</p>
                <h2>Everything You Do Here Feeds The Next Step</h2>
                <p>Your information stays connected throughout the process. The platform prepares the next useful resource as soon as it has enough approved information, while you remain in control of every decision.</p>
              </div>
              <div className="sgr-overview-stat">
                <strong>{answeredCount}/6</strong>
                <span>Recruitment questions answered</span>
              </div>
            </section>

            <nav className="sgr-flow-map" aria-label="Board Recruitment Process">
              {FLOW_STEPS.map(([target,label],index)=>(
                <a href={"#"+target} key={target}><span>{index+1}</span>{label}</a>
              ))}
            </nav>

            <Section number={1} title="ANSWER THE SIX RECRUITMENT QUESTIONS"
              summary="Give us the information we need to understand the board you have, the board you want and the people you need."
              testId="br-section-questions" videoKey="questions" status={questionStatus} defaultOpen>
              <p>Answer six focused questions on separate screens. Add your organization logo before you begin if you want it carried into your recruitment materials.</p>
              <button className="button" onClick={()=>navigate("/app/board-recruitment/questions")} data-testid="start-six-questions">
                {questionsComplete?"REVIEW MY SIX ANSWERS":answeredCount?"CONTINUE THE SIX QUESTIONS":"START THE SIX QUESTIONS"}
              </button>
              {questionsComplete&&<p className="member-success">All six answers are saved. The platform has already started identifying the board members your organization needs.</p>}
            </Section>

            <Section number={2} title="IDENTIFY THE BOARD MEMBERS YOUR ORGANIZATION NEEDS"
              summary="Review the exact number of Board Member profiles built from your six answers and recruitment target."
              testId="br-section-identify" videoKey="identify" status={identifyStatus}>
              {!questionsComplete?(
                <p className="workspace-note">Complete all six Recruitment Questions first.</p>
              ):(
                <>
                  {["queued","generating"].includes(generationStatus)&&!assessment?.result&&(
                    <div className="sgr-background-work"><span className="sgr-working-dot"/><div><strong>We are identifying your board members now.</strong><p>You can leave this section and continue using the dashboard. The result will surface here when it is ready.</p></div></div>
                  )}
                  <Module1Profile/>
                </>
              )}
            </Section>

            <Section number={3} title="BUILD YOUR BOARD APPLICATION AND RECRUITMENT MATERIALS"
              summary="Your approved Board Member profiles become the foundation for the application and campaign assets."
              testId="br-section-materials" videoKey="materials" status={progress<2?"Locked":"Prepare"}>
              {progress<2?<p className="workspace-note">Approve the Board Members you need in Section 2 first.</p>:<RecruitmentMaterials/>}
            </Section>

            <Section number={4} title="LAUNCH YOUR RECRUITMENT CAMPAIGN"
              summary="Review what has been prepared, publish the opportunity and begin receiving applicants."
              testId="br-section-campaign" videoKey="launch" status={progress<2?"Locked":"Prepare"}>
              {progress<2?<p className="workspace-note">Approve your Board Member profiles first.</p>:<RecruitmentCampaignLaunch/>}
            </Section>

            <Section number={5} title="APPLICANTS"
              summary="Review everyone who applies, add outside candidates and decide who should receive an interview invitation."
              testId="br-section-applicants" videoKey="applicants">
              <Module4Applicants/>
            </Section>

            <Section number={6} title="INTERVIEWS"
              summary="Interview candidates appear here after you generate their invitation. Create a tailored guide for each person."
              testId="br-section-interviews" videoKey="interviews">
              <InterviewsWorkspace/>
            </Section>

            <Section number={7} title="REFERENCE CHECKS"
              summary="Candidates appear here after their interview guide is generated. Run the existing automated reference workflow."
              testId="br-section-references" videoKey="references">
              <AutomatedReferenceChecks/>
            </Section>

            <Section number={8} title="BACKGROUND CHECK"
              summary="Use a local background-check provider or local sheriff/police option when your organization needs one."
              testId="br-section-background" videoKey="background">
              <BackgroundChecksWorkspace/>
            </Section>

            <Section number={9} title="PREPARE ONBOARDING AND THE APPOINTMENT"
              summary="Set the onboarding session, approve the reusable onboarding materials, then unlock conditional or unconditional appointment emails."
              testId="br-section-onboarding-prep" videoKey="onboarding-prep">
              <OnboardingPreparation/>
            </Section>

            <Section number={10} title="RUN THE BOARD MEMBER ONBOARDING SESSION"
              summary="Use presenter notes and one shared screen to facilitate onboarding cleanly, one section at a time."
              testId="br-section-onboarding-session" videoKey="onboarding-session">
              <OnboardingSessionWorkspace/>
            </Section>

            <Section number={11} title="BOARD MEMBER PORTFOLIOS"
              summary="Review and approve each person's Board role before generating a tailored Portfolio for the people who join."
              testId="br-section-portfolios" videoKey="portfolios">
              <RecruitmentPortfoliosWorkspace/>
            </Section>

            <section id="br-section-support" className="sgr-persistent-support" data-testid="recruitment-support">
              <div className="sgr-support-heading">
                <LifeBuoy size={28}/>
                <div><p className="eyebrow">SUPPORT THROUGHOUT THE PROCESS</p><h2>Need Help With Your Recruitment?</h2><p>Tell us where you are stuck or what you need help executing. Your request stays connected to Board Recruitment.</p></div>
              </div>
              <SupportBox productKey="recruitment_self_guided" moduleNumber={1}
                supportTypes={["I have a question about this step","I need help using the platform","I need help executing this step","I would like someone to help me complete this step"]}/>
            </section>
          </>
        )}
      </main>
    </MemberShell>
  );
}
