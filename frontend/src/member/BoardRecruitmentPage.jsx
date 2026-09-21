import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { memberApi } from "./api";
import { UnlockPurchaseButton } from "./DashboardPage";
import { SupportBox } from "./CoursePages";
import { Module1Profile } from "./workspace/Module1Profile";
import { RecruitmentCampaignLaunch, RecruitmentMaterials } from "./workspace/WorkspaceModules";
import { AppointmentOffersWorkspace, AutomatedReferenceChecks, BackgroundChecksWorkspace, FormalAppointmentWorkspace, Module4Applicants, OnboardingFacilitationGuide, OnboardingPreparation, useApplications, useBranding } from "./workspace/ApplicantModules";
import { BoardMemberResultCard } from "./workspace/ResultsPage";
import "./sgr.css";

const FLOW_STEPS = [
  ["br-section-intake", "Play Recruitment Game"],
  ["br-section-identify", "Identify Board Members"],
  ["br-section-materials", "Application & Campaign Materials"],
  ["br-section-campaign", "Launch Campaign"],
  ["br-section-applicants", "Applicants & Interviews"],
  ["br-section-references", "Reference Checks"],
  ["br-section-background", "Background Checks"],
  ["br-section-offers", "Appointment Offers"],
  ["br-section-onboarding", "Onboarding"],
  ["br-section-final-appointment", "Final Appointment"],
  ["br-section-team", "My Team"],
  ["br-section-support", "Ask For Help"],
];

const Section = ({ number, title, summary, children, testId, defaultOpen = false }) => {
  const [open,setOpen]=useState(defaultOpen);
  useEffect(() => {
    const syncHash = () => { if (window.location.hash === `#${testId}`) setOpen(true); };
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, [testId]);
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
  const gameAnswers = assessment?.answers || {};
  const gameCompleted = ["mission", "current_board", "important_areas", "support_needs"].every((key) => String(gameAnswers[key] || "").trim());

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
              <button className="button" onClick={()=>navigate("/app/board-recruitment/game")} data-testid="start-recruitment-game">{gameCompleted?"REVIEW MY BOARD RECRUITMENT GAME":"START THE GAME"}</button>
              {gameCompleted&&<p className="member-success" style={{marginTop:14}}>Recruitment Game completed. Your four answers are saved. Continue to Step 2 to identify the exact Board Members your organization needs.</p>}
            </Section>

            <Section number={2} title="IDENTIFY THE EXACT TYPE OF BOARD MEMBERS NEEDED" summary="Generate the profiles directly from your Recruitment Game." testId="br-section-identify">
              <p>Generate the exact Board Member profiles from your organization information, recruitment target, present Board, priority gaps and all four Recruitment Game answers.</p>
              <Module1Profile />
            </Section>

            <Section number={3} title="GENERATE THE BOARD APPLICATION AND RECRUITMENT MATERIALS" summary="Create the branded application first, then the job post, emails and campaign content." testId="br-section-materials">
              <p>Create your Board Member Application Form and the finished materials you will use to attract the exact type of people your organization needs.</p>
              <RecruitmentMaterials />
            </Section>

            <Section number={4} title="LAUNCH THE RECRUITMENT CAMPAIGN" summary="Publish your approved application and materials." testId="br-section-campaign">
              <p>Review the application and approved recruitment materials, then launch the campaign when you are ready to begin receiving applicants.</p>
              <RecruitmentCampaignLaunch />
            </Section>

            <Section number={5} title="VIEW APPLICANTS AND RUN INTERVIEWS" summary="Review applications, add external candidates and create the interview tools for each person." testId="br-section-applicants">
              <p>Everyone who completes your Board Member Application Form will automatically appear below.</p>
              <p>You can also add people you discover through referrals, LinkedIn, networking, your existing relationships or another source, including uploading their CV or résumé.</p>
              <p>When you decide you want to interview an applicant, generate an interview guide specifically for that person. It uses their application, their CV or resume if available, what your organization is looking for and the board role being considered. You make the final decision about whether they are right for your board.</p>
              <Module4Applicants />
            </Section>

            <Section number={6} title="COMPLETE REFERENCE CHECKS" summary="Start the automated reference process for any applicant." testId="br-section-references">
              <p>Every applicant appears here automatically. Start a reference check and the platform first checks the candidate's CV for explicit referee details. If no usable references are found, ask the applicant to provide them through the secure form.</p>
              <AutomatedReferenceChecks />
            </Section>

            <Section number={7} title="COMPLETE BACKGROUND CHECKS" summary="Decide whether each applicant needs a background check and record the result." testId="br-section-background">
              <p>Every applicant appears here. Choose whether a background check is required for that person. If it is, use the local search tools to find an appropriate provider or local sheriff/police background-check option.</p>
              <BackgroundChecksWorkspace />
            </Section>

            <Section number={8} title="SEND THE APPOINTMENT OFFER" summary="Choose a conditional or unconditional Board appointment offer." testId="br-section-offers">
              <p>You decide how to appoint each person. Use a Conditional Appointment when you want an outstanding reference or required background check to remain a condition. Use an Unconditional Appointment Offer when you have decided those checks will not be conditions of the offer.</p>
              <AppointmentOffersWorkspace />
            </Section>

            <Section number={9} title="ONBOARD THE NEW BOARD MEMBER" summary="Set the onboarding session, send the onboarding pack and record what was agreed." testId="br-section-onboarding">
              <p>Set the onboarding date, prepare the Organization Overview, Board Manual, agreements and Board Member Profile Form, then send the onboarding email with the secure links.</p>
              <OnboardingPreparation />
              <div style={{ marginTop: 18 }}>
                <h3>Prepare To Facilitate The Onboarding Conversation</h3>
                <p>Use the facilitation guide during the session to clarify expectations and agree exactly how this person will contribute.</p>
                <OnboardingFacilitationGuide />
              </div>
            </Section>

            <Section number={10} title="CONFIRM THE FINAL BOARD APPOINTMENT" summary="After onboarding, formally confirm the appointment and send the final appointment documents." testId="br-section-final-appointment">
              <p>After the onboarding conversation is complete and you have saved the Onboarding Conclusion / Role Agreement, confirm the person's final Board appointment. Reference and background-check statuses remain visible to you but do not make the decision for you.</p>
              <FormalAppointmentWorkspace />
            </Section>

            <Section number={11} title="MY TEAM" summary="Create and manage the individual Board Member Portfolios for the people who joined your Board." testId="br-section-team">
              <p>Each formally appointed Board Member appears here. Their Portfolio is built from their application, experience, Board Member Profile and, most importantly, what you actually agreed together during onboarding.</p>
              <PortfolioSection />
            </Section>

            <Section number={12} title="ASK FOR HELP" summary="Request support inside the platform." testId="br-section-support">
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
