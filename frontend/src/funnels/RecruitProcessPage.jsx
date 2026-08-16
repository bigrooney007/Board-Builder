import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { PAGE_META, usePageMeta } from "@/seo";
import { recruitProcessText } from "../content/appContent";
import { recruitProcessPageText } from "../content/siteContent";

const STAGES = [
  ["01", "Identify the Board Members Your Organization Needs", "Your organization needs a board with the skills, experience, credibility, relationships and capacity it needs to succeed. The first step is identifying the gap between the board you have today and the powerhouse board your organization needs. That clarity drives the entire recruitment effort."],
  ["02", "Launch Your Recruitment Campaign", "Qualified professionals need a compelling reason to give their time, experience and relationships to your organization. Your recruitment campaign should position board service as a meaningful opportunity and attract people who genuinely want to become part of the mission."],
  ["03", "Select and Interview Your Applicants", "A strong recruitment campaign gives you people to choose from. The next step is identifying the applicants who are truly aligned with your mission, understand what board service requires and have the commitment, experience and capacity your organization needs."],
  ["04", "Complete References and Background Checks", "People do not always turn out to be exactly who they first appear to be. References and, where appropriate or required, background checks help your organization verify the people being considered before bringing them into leadership and build a board it can trust."],
  ["05", "Onboard Your New Board Members", "Once you have selected the people you want, bring them properly into the organization so they understand the mission, expectations, responsibilities and how they will contribute. Your new board members should start knowing what the organization needs from them, what responsibility they own and how they can begin contributing from the start."],
];

export default function RecruitProcessPage() {
  usePageMeta(...PAGE_META.process);
  return (
    <FunnelLayout>
      <main className="recruit-process-page" data-testid="recruit-process-page">
        <section className="process-hero">
          <p className="eyebrow">Board Recruitment</p>
          <h1 data-testid="process-heading">{recruitProcessText.h_yourPathToBuildingThe}</h1>
          <p>{recruitProcessPageText.recruitingTheRightBoardIs}</p>
          <p>{recruitProcessPageText.havingWorkedWithHundredsOf}</p>
        </section>
        <section className="process-steps" data-testid="process-steps">
          {STAGES.map(([number, title, copy]) => (
            <article className="process-step" key={number} data-testid={`process-step-${number}`}>
              <span className="process-step-number">{number}</span>
              <div>
                <h2>{title}</h2>
                <p>{copy}</p>
                {number === "01" && <Link className="button" to="/recruit/checkout" data-testid="process-step-1-cta">{recruitProcessPageText.identifyTheBoardMyNonprofit}<ArrowRight size={16} /></Link>}
              </div>
            </article>
          ))}
        </section>
        <section className="process-final" data-testid="process-final-section">
          <h2>{recruitProcessText.h_buildTheBoardYourMission}</h2>
          <p>{recruitProcessPageText.youDoNotNeedMore}</p>
          <Link className="button process-final-button" to="/recruit/checkout" data-testid="process-final-cta">{recruitProcessPageText.startBuildingMyBoard}<ArrowRight size={18} /></Link>
        </section>
      </main>
    </FunnelLayout>
  );
}
