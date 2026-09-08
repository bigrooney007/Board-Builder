import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { SupportBox } from "./CoursePages";
import { Module1Profile } from "./workspace/Module1Profile";
import { Module3Launch } from "./workspace/WorkspaceModules";
import { Module4Applicants, Module5References, Module6Onboarding, useApplications, useBranding } from "./workspace/ApplicantModules";
import { BoardMemberResultCard } from "./workspace/ResultsPage";
import { useFlowVideo } from "@/hooks/useFlowVideos";

const Section = ({ number, title, children, testId }) => (
  <section className="member-card" data-testid={testId} style={{ marginTop: 26 }}>
    <h2 style={{ marginTop: 0 }}>{number}. {title}</h2>
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
        <BoardMemberResultCard key={application.application_id} application={application} branding={branding} onChanged={refresh} />
      ))}
    </>
  );
};

export default function BoardRecruitmentPage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const video = useFlowVideo("board_recruitment");

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login?next=/app/board-recruitment"); return; }
  }, [loading, member, navigate]);

  const allowed = member && (member.entitlements || []).some((e) => ["fundraising_board_builder", "recruitment_self_guided"].includes(e));

  return (
    <MemberShell>
      <main className="member-page" data-testid="fbb-recruitment-page">
        <header className="member-page-heading">
          <p className="eyebrow">Fundraising Board Builder</p>
          <h1 data-testid="fbb-recruitment-heading">BOARD RECRUITMENT</h1>
          <p><strong>Identify and recruit the professional board members your organization needs to strengthen your board and your ability to raise money.</strong></p>
        </header>
        {member && !allowed && (
          <section className="member-card" data-testid="fbb-recruitment-forbidden"><p>Your account does not include access to this process.</p></section>
        )}
        {allowed && (
          <>
            {video?.youtube_id && (
              <div className="module-video" data-testid="fbb-recruitment-video">
                <iframe src={`https://www.youtube.com/embed/${video.youtube_id}`} title="Board Recruitment" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
              </div>
            )}
            <section className="member-card" data-testid="fbb-recruitment-intro">
              <p>Building the right board starts with knowing exactly who your organization needs.</p>
              <p>Do not recruit people simply because they are available.</p>
              <p>Do not fill seats for the sake of filling seats.</p>
              <p>Build the board around the skills, experience, relationships and expertise your organization needs to succeed.</p>
              <p><strong>Follow the process below.</strong></p>
            </section>

            <Section number={1} title="IDENTIFY THE BOARD MEMBERS YOU NEED" testId="br-section-identify">
              <p>Start by identifying the people your organization should be recruiting.</p>
              <p>We will use the information you provided about your organization to help you determine the skills and experience that could strengthen your board.</p>
              <p>Review the recommendations. Edit them based on what you already know about your present board and your organization's needs. You decide who you want to recruit.</p>
              <Module1Profile />
            </Section>

            <Section number={2} title="CREATE YOUR APPLICATION FORM AND RECRUITMENT CAMPAIGN" testId="br-section-campaign">
              <p>Now create the application potential board members will complete when they are interested in joining your organization, and generate the content you can use to begin attracting potential board members.</p>
              <p>Review your application form before launching your recruitment campaign. Then review and use the campaign content across the channels you believe are appropriate for your organization — your board application link is automatically included in the recruitment materials where appropriate.</p>
              <Module3Launch />
            </Section>

            <Section number={3} title="YOUR BOARD APPLICANTS AND INTERVIEWS" testId="br-section-applicants">
              <p>Everyone who completes your Board Member Application Form will automatically appear below.</p>
              <p>You can also manually add people you discover through referrals, LinkedIn, networking, your existing relationships or any other source — including uploading their CV/resume.</p>
              <p>When you decide you want to interview an applicant, generate an interview guide specifically for that person. It uses their application, their CV or resume if available, what your organization is looking for and the board role being considered. You make the final decision about whether they are right for your board.</p>
              <Module4Applicants />
            </Section>

            <Section number={4} title="REFERENCE CHECKS, AGREEMENTS AND BOARD MEMBER PROFILE" testId="br-section-references">
              <p>If you decide to move an applicant forward, use the resources below to conduct their reference checks. The system does not automatically contact anyone — you decide when and how to use the materials.</p>
              <p>Once you have decided to bring someone onto your board, generate the agreements and documents you want them to review and sign, and send them the Board Member Profile Form so you understand how they want to contribute to the organization.</p>
              <Module5References />
            </Section>

            <Section number={5} title="PREPARE FOR ONBOARDING" testId="br-section-onboarding">
              <p>Before officially bringing the new board member into the organization, generate your onboarding facilitation guide.</p>
              <p>It will help you lead the onboarding conversation and ensure the new board member understands the organization, why they were recruited, their role, the expectations attached to board service, the contribution they have agreed to make and how they can begin supporting the organization.</p>
              <Module6Onboarding />
            </Section>

            <Section number={6} title="CREATE THEIR BOARD MEMBER PORTFOLIO" testId="br-section-portfolio">
              <p>Once the board member has completed the necessary agreements and Board Member Profile Form, you can generate their individual Board Member Portfolio.</p>
              <p>The portfolio brings together the reason they were recruited, the skills and experience they bring, the areas where they want to contribute, their board responsibilities, their agreed commitments, the priorities they can support and the role they can play in strengthening the organization.</p>
              <PortfolioSection />
            </Section>

            <section className="member-card" data-testid="br-closing" style={{ marginTop: 26 }}>
              <h2>YOUR BOARD RECRUITMENT PROCESS CONTINUES</h2>
              <p>Repeat this process for every applicant you want to consider and every new board member you decide to bring into the organization.</p>
              <p>The goal is not simply to fill board seats.</p>
              <p>The goal is to intentionally build the board your organization needs to raise money, grow and accomplish its mission.</p>
            </section>

            <SupportBox productKey="recruitment_self_guided" moduleNumber={1}
              supportTypes={["I have a question about this step", "I need help using the platform", "I need help executing this step", "I would like someone to help me complete this step"]} />
          </>
        )}
      </main>
    </MemberShell>
  );
}
