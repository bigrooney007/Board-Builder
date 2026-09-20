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
import { RecruitmentTutorial } from "./RecruitmentTutorial";
import { RecruitmentGameIntake } from "./RecruitmentGameIntake";
import "./sgr.css";

const FLOW_STEPS = [
  ["br-section-intake", "Play Recruitment Game"], ["br-section-identify", "Identify Board Members"],
  ["br-section-materials", "Generate Materials"], ["br-section-campaign", "Launch Campaign"],
  ["br-section-applicants", "Manage Applicants"], ["br-section-references", "Reference Check"],
  ["br-section-onboarding", "Prepare Onboarding"], ["br-section-facilitation", "Facilitate Onboarding"],
  ["br-section-portfolio", "Appointment & Portfolio"], ["br-section-support", "Ask For Help"],
  ["br-section-first-meeting", "First Board Meeting"],
];

const Section = ({ number, title, children, testId }) => (
  <section id={testId} className="member-card sgr-flow-section" data-testid={testId} style={{ marginTop: 26 }}>
    <div className="sgr-step-heading"><span>{number}</span><h2>{title}</h2></div>
    {children}
  </section>
);

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

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login?next=/app/board-recruitment"); return; }
    memberApi.post("/recruit/free/member-event/dashboard_entered").catch(() => {});
  }, [loading, member, navigate]);

  const allowed = member && (member.entitlements || []).some((e) => ["fundraising_board_builder", "fbb_recruitment", "recruitment_self_guided"].includes(e));

  return (
    <MemberShell>
      <main className="member-page sgr" data-testid="fbb-recruitment-page">
        <header className="member-page-heading">
          <p className="eyebrow">Nonprofit Board Builder</p>
          <h1 data-testid="fbb-recruitment-heading">SELF-GUIDED BOARD RECRUITMENT</h1>
          <p><strong>Identify and recruit the professional board members your organization needs to strengthen your board and your ability to raise money.</strong></p>
          {allowed && <div style={{ marginTop: 14 }}><RecruitmentTutorial /></div>}
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

            <Section number={1} title="PLAY THE BOARD RECRUITMENT GAME" testId="br-section-intake">
              <p>Answer four questions about your mission, present board and the needs of your entire organization. Your answers become the intake used throughout the recruitment process.</p>
              <RecruitmentGameIntake />
            </Section>

            <Section number={2} title="IDENTIFY THE EXACT TYPE OF BOARD MEMBERS NEEDED" testId="br-section-identify">
              <p>Start by identifying the people your organization should be recruiting.</p>
              <p>We will use the information you provided about your organization to help you determine the skills and experience that could strengthen your board.</p>
              <p>Review the recommendations. Edit them based on what you already know about your present board and your organization's needs. You decide who you want to recruit.</p>
              <Module1Profile />
            </Section>

            <Section number={3} title="GENERATE THE RECRUITMENT MATERIALS" testId="br-section-materials">
              <p>Create your Board Member Application Form and the finished materials you will use to attract the exact type of people your organization needs.</p>
              <RecruitmentMaterials />
            </Section>

            <Section number={4} title="LAUNCH THE RECRUITMENT CAMPAIGN" testId="br-section-campaign">
              <p>Review the application and approved recruitment materials, then launch the campaign when you are ready to begin receiving applicants.</p>
              <RecruitmentCampaignLaunch />
            </Section>

            <Section number={5} title="VIEW AND ADD APPLICANTS" testId="br-section-applicants">
              <p>Everyone who completes your Board Member Application Form will automatically appear below.</p>
              <p>You can also add people you discover through referrals, LinkedIn, networking, your existing relationships or another source, including uploading their CV or résumé.</p>
              <p>When you decide you want to interview an applicant, generate an interview guide specifically for that person. It uses their application, their CV or resume if available, what your organization is looking for and the board role being considered. You make the final decision about whether they are right for your board.</p>
              <Module4Applicants />
            </Section>

            <Section number={6} title="COMPLETE THE AUTOMATED REFERENCE CHECK" testId="br-section-references">
              <p>Move the right applicant forward and run the complete reference process through the automated reference-check system.</p>
              <AutomatedReferenceChecks />
            </Section>

            <Section number={7} title="PREPARE THE ONBOARDING AND SEND THE CONDITIONAL APPOINTMENT" testId="br-section-onboarding">
              <p>Set the onboarding date, prepare the Organization Overview and Board Manual, generate all three agreements, create the Board Member Profile Form and send one conditional appointment email carrying every secure link.</p>
              <OnboardingPreparation />
            </Section>

            <Section number={8} title="GENERATE THE ONBOARDING FACILITATION GUIDE" testId="br-section-facilitation">
              <p>Use the guide to lead the onboarding conversation, clarify expectations and record exactly what the new board member has agreed to contribute.</p>
              <OnboardingFacilitationGuide />
            </Section>

            <Section number={9} title="GENERATE THE FINAL APPOINTMENT LETTER AND BOARD MEMBER PORTFOLIO" testId="br-section-portfolio">
              <p>Confirm the final appointment after the reference check, agreements and Board Member Profile are complete. Record the onboarding conclusion, generate the formal appointment letter and create the individual Board Member Portfolio.</p>
              <FormalAppointmentWorkspace />
              <p>The portfolio brings together the reason they were recruited, the skills and experience they bring, the areas where they want to contribute, their board responsibilities, their agreed commitments, the priorities they can support and the role they can play in strengthening the organization.</p>
              <PortfolioSection />
            </Section>

            <Section number={10} title="ASK FOR HELP" testId="br-section-support">
              <p>Request support whenever you need help using the platform or executing the recruitment process.</p>
              <div id="sgr-support">
              <SupportBox productKey="recruitment_self_guided" moduleNumber={1}
                supportTypes={["I have a question about this step", "I need help using the platform", "I need help executing this step", "I would like someone to help me complete this step"]} />
              </div>
            </Section>

            <Section number={11} title="ORGANIZE THE FIRST BOARD MEETING" testId="br-section-first-meeting">
              <p>Set the meeting details, generate the invitation and send it to the board members who have completed the recruitment and appointment process.</p>
              <FirstBoardMeetingWorkspace />
            </Section>
          </>
        )}
      </main>
    </MemberShell>
  );
}
