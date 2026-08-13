import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { PAGE_META, usePageMeta } from "@/seo";

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
          <h1 data-testid="process-heading">Your Path to Building the Board Your Nonprofit Needs</h1>
          <p>Recruiting the right board is not just about bringing in the right people. It is also about bringing them in the right way so they understand the mission, commit to the organization and participate fully in building it.</p>
          <p>Having worked with hundreds of nonprofits to strengthen their boards over the last decade, here are the 5 steps we recommend to build the board your organization needs.</p>
        </section>
        <section className="process-steps" data-testid="process-steps">
          {STAGES.map(([number, title, copy]) => (
            <article className="process-step" key={number} data-testid={`process-step-${number}`}>
              <span className="process-step-number">{number}</span>
              <div>
                <h2>{title}</h2>
                <p>{copy}</p>
                {number === "01" && <Link className="button" to="/recruit/checkout" data-testid="process-step-1-cta">Identify the Board My Nonprofit Needs <ArrowRight size={16} /></Link>}
              </div>
            </article>
          ))}
        </section>
        <section className="process-final" data-testid="process-final-section">
          <h2>Build the Board Your Mission Deserves</h2>
          <p>You do not need more names on your board. You need committed people with the capacity to help your nonprofit grow, raise money, build relationships and move the mission forward.</p>
          <Link className="button process-final-button" to="/recruit/checkout" data-testid="process-final-cta">Start Building My Board <ArrowRight size={18} /></Link>
        </section>
      </main>
    </FunnelLayout>
  );
}
