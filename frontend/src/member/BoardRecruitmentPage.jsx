import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { memberApi } from "./api";
import { UnlockPurchaseButton } from "./DashboardPage";
import { SupportBox } from "./CoursePages";
import { Module1Profile } from "./workspace/Module1Profile";
import { RecruitmentCampaignLaunch, RecruitmentMaterials } from "./workspace/WorkspaceModules";
import { AutomatedReferenceChecks, FirstBoardMeetingWorkspace, FormalAppointmentWorkspace, Module4Applicants, OnboardingFacilitationGuide, OnboardingPreparation, useApplications, useBranding } from "./workspace/ApplicantModules";
import { BoardMemberResultCard } from "./workspace/ResultsPage";
import "./sgr.css";

const FLOW_STEPS = [
  ["br-section-intake", "Play Recruitment Game"], ["br-section-identify", "Identify Board Members"],
  ["br-section-materials", "Generate Materials"], ["br-section-campaign", "Launch Campaign"],
  ["br-section-applicants", "Manage Applicants"], ["br-section-references", "Reference Check"],
  ["br-section-onboarding", "Prepare Onboarding"], ["br-section-facilitation", "Facilitate Onboarding"],
  ["br-section-portfolio", "Appointment & Portfolio"], ["br-section-first-meeting", "First Board Meeting"],
  ["br-section-support", "Ask For Help"],
];

const Section = ({ number, title, summary, children, testId, defaultOpen = false }) => {
  const [open,setOpen]=useState(defaultOpen);
  return <section id={testId} className={`member-card sgr-flow-section ${open?"is-open":""}`} data-testid={testId} style={{ marginTop: 18 }}>
    <button type="button" className="sgr-section-toggle" onClick={()=>setOpen(!open)} aria-expanded={open}>
      <span className="sgr-step-number">{number}</span><span><strong>{title}</strong>{summary&&<small>{summary}</small>}</span><b>{open?"CLOSE":"OPEN"}</b>
    </button>
    {open&&<div className="sgr-section-body">{children}</div>}
  </section>;
};

const PortfolioSection = () => {
  const { applications, refresh } = useApplications();
  const [branding] = useBranding();
  const joined = (applications || []).filter((a) => a.final_outcome === "Joined Board" || a.status === "Selected");
  return (
    <>
      {joined.length === 0 && <p data-testid="br-no-board-members"><em>Board members who complete their agreements and Board Member Profile Form will appear here.</em></p>}
      {joined.map((application) => (
        <BoardMemberResultCard key={application.application_id} application={application} branding={branding} onChanged={refresh} portfolioOnly />
      ))}
    </>
  );
};

export default function BoardRecruitmentPage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [assessment,setAssessment]=useState(null);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login?next=/app/board-recruitment"); return; }
    memberApi.post("/recruit/free/member-event/dashboard_entered").catch(() => {});
    memberApi.get("/recruit/free/member-assessment/current").then(r=>setAssessment(r.data)).catch(()=>{});
  }, [loading, member, navigate]);

  const allowed = member && (member.entitlements || []).some((e) => ["fundraising_board_builder", "fbb_recruitment", "recruitment_self_guided"].includes(e));

  return (
    <MemberShell>
      <main className="member-page sgr" data-testid="fbb-recruitment-page">
        <header className="member-page-heading">
          <p className="eyebrow">Nonprofit Board Builder</p>
          <h1 data-testid="fbb-recruitment-heading">SELF-GUIDED BOARD RECRUITMENT</h1>
          <p><strong>Identify and recruit the professional board members your organization needs to strengthen your board and your ability to raise money.</strong></p>
        </header>
        {member && !allowed && (
          <section className="member-card" data-testid="fbb-recruitment-forbidden">
            <p><strong>Board Recruitment is not included in your purchase yet. Unlock it to get started.</strong></p>
            <UnlockPurchaseButton product="recruitment" label="UNLOCK BOARD RECRUITMENT — $497" testId="fbb-recruitment-unlock-button" />
          </section>
        )}
        {allowed && (
          <>
            <section className="member-card" data-testid="fbb-recruitment-intro">
              <p>Building the right board starts with knowing exactly who your organization needs.</p>
              <p>Do not recruit people simply because they are available.</p>
              <p>Do not fill seats for the sake of filling seats.</p>
              <p>Build the board around the skills, experience, relationships and expertise your organization needs to succeed.</p>
              <p><strong>Follow the process below.</strong></p>
            </section>

            <nav className="sgr-flow-map" aria-label="Board Recruitment Process" data-testid="br-flow-map">
              {FLOW_STEPS.map(([target, label], index) => (
                <a href={`#${target}`} key={target}><span>{index + 1}</span>{label}</a>
              ))}
            </nav>

            <Section number={1} title="PLAY THE BOARD RECRUITMENT GAME" summary="Answer four questions in one clean step-by-step game." testId="br-section-intake" defaultOpen>
              <p>Click Start Game to open Question 1. You will answer Questions 1 to 4 on separate game screens and return here when the game is complete.</p>
              <button className="button" onClick={()=>navigate("/app/board-recruitment/game")} data-testid="start-recruitment-game">{assessment?.result?"REVIEW MY BOARD RECRUITMENT GAME":"START THE GAME"}</button>
              {assessment?.result&&<p className="member-success" style={{marginTop:14}}>Game completed. Your answers are ready to identify the exact Board Members your organization needs.</p>}
            </Section>

            <Section number={2} title="IDENTIFY THE EXACT TYPE OF BOARD MEMBERS NEEDED" summary="Generate the profiles directly from your Recruitment Game." testId="br-section-identify">
              <p>Generate the exact Board Member profiles from your organization information, recruitment target, present Board, priority gaps and all four Recruitment Game answers.</p>
              <Module1Profile />
            </Section>

            <Section number={3} title="GENERATE THE RECRUITMENT MATERIALS" summary="Application form, job post, emails and campaign content." testId="br-section-materials">
              <p>Create your Board Member Application Form and the finished materials you will use to attract the exact type of people your organization needs.</p>
              <RecruitmentMaterials />
            </Section>

            <Section number={4} title="LAUNCH THE RECRUITMENT CAMPAIGN" summary="Publish your approved application and materials." testId="br-section-campaign">
              <p>Review the application and approved recruitment materials, then launch the campaign when you are ready to begin receiving applicants.</p>
              <RecruitmentCampaignLaunch />
            </Section>

            <Section number={5} title="VIEW AND ADD APPLICANTS" summary="Review applications and create individual interview guides." testId="br-section-applicants">
              <p>Everyone who completes your Board Member Application Form will automatically appear below.</p>
              <p>You can also add people you discover through referrals, LinkedIn, networking, your existing relationships or another source, including uploading their CV or résumé.</p>
              <p>When you decide you want to interview an applicant, generate an interview guide specifically for that person. It uses their application, their CV or resume if available, what your organization is looking for and the board role being considered. You make the final decision about whether they are right for your board.</p>
              <Module4Applicants />
            </Section>

            <Section number={6} title="COMPLETE THE AUTOMATED REFERENCE CHECK" summary="Run the secure automated reference process." testId="br-section-references">
              <p>Move the right applicant forward and run the complete reference process through the automated reference-check system.</p>
              <AutomatedReferenceChecks />
            </Section>

            <Section number={7} title="PREPARE THE ONBOARDING AND SEND THE CONDITIONAL APPOINTMENT" summary="Set the meeting, generate onboarding materials and send every secure link." testId="br-section-onboarding">
              <p>Set the onboarding date, prepare the Organization Overview and Board Manual, generate all three agreements, create the Board Member Profile Form and send one conditional appointment email carrying every secure link.</p>
              <OnboardingPreparation />
            </Section>

            <Section number={8} title="GENERATE THE ONBOARDING FACILITATION GUIDE" summary="Open the tools for facilitating the onboarding meeting." testId="br-section-facilitation">
              <p>Use the guide to lead the onboarding conversation, clarify expectations and record exactly what the new board member has agreed to contribute.</p>
              <OnboardingFacilitationGuide />
            </Section>

            <Section number={9} title="GENERATE THE FINAL APPOINTMENT LETTER AND BOARD MEMBER PORTFOLIO" summary="Confirm the appointment and create the individual portfolio." testId="br-section-portfolio">
              <p>Confirm the final appointment after the reference check, agreements and Board Member Profile are complete. Record the onboarding conclusion, generate the formal appointment letter and create the individual Board Member Portfolio.</p>
              <FormalAppointmentWorkspace />
              <p>The portfolio brings together the reason they were recruited, the skills and experience they bring, the areas where they want to contribute, their board responsibilities, their agreed commitments, the priorities they can support and the role they can play in strengthening the organization.</p>
              <PortfolioSection />
            </Section>

            <Section number={10} title="ORGANIZE THE FIRST BOARD MEETING" summary="Enter the meeting details and send the invitation." testId="br-section-first-meeting">
              <p>Set the meeting details, generate the invitation and send it to the board members who have completed the recruitment and appointment process.</p>
              <FirstBoardMeetingWorkspace />
            </Section>

            <Section number={11} title="ASK FOR HELP" summary="Request support inside the platform." testId="br-section-support">
              <p>Request support whenever you need help using the platform or executing the recruitment process.</p>
              <div id="sgr-support"><SupportBox productKey="recruitment_self_guided" moduleNumber={1}
                supportTypes={["I have a question about this step", "I need help using the platform", "I need help executing this step", "I would like someone to help me complete this step"]} /></div>
            </Section>
          </>
        )}
      </main>
    </MemberShell>
  );
}
