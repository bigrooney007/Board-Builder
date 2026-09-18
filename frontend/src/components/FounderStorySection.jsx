import { ArrowRight, BriefcaseBusiness, GraduationCap, HeartHandshake, Map, TrendingUp } from "lucide-react";
import { SITE_CONTENT, founderStorySectionText } from "@/content/siteContent";

const founderPhotoUrl = process.env.REACT_APP_ROONEY_HOMEPAGE_PHOTO_URL || "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/ezw4nj2a_InShot_20260413_074422056%20%281%29.webp";

const content = SITE_CONTENT.founderStory;
const credibilityIcons = [HeartHandshake, BriefcaseBusiness, GraduationCap, Map, TrendingUp];

export const FounderStorySection = () => {
  return (
    <>
      <section id="my-story" className="founder-section" data-testid="founder-story-section">
        <div className="founder-photo-panel">
          <div className="founder-photo-frame"><img src={founderPhotoUrl} alt={founderStorySectionText.rooneyAkpesiriTheNonprofitBoard} data-testid="founder-photo" /><span data-testid="founder-photo-caption">{content.photoCaption}</span></div>
        </div>
        <div className="founder-story-copy">
          <p className="eyebrow" data-testid="founder-story-eyebrow">{content.eyebrow}</p>
          <h2 data-testid="founder-story-heading">{content.heading}</h2>
          <div className="founder-identity"><strong data-testid="founder-name">{content.name}</strong><span data-testid="founder-title">{content.title}</span></div>
          <div className="founder-story-text" data-testid="founder-story-text">
            {content.paragraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
          </div>
          <div className="founder-offer-choices" data-testid="founder-offer-choices"><a className="button founder-calendly-button" href="https://calendly.com/boardbuilder/recruitboard" target="_blank" rel="noreferrer" data-testid="founder-book-call-button">{content.bookCallButton} <ArrowRight size={16} /></a></div>
        </div>
      </section>
      <section className="credibility-strip" data-testid="founder-credibility-strip">
        {content.credibility.map((text, index) => {
          const Icon = credibilityIcons[index] || HeartHandshake;
          return <div key={text} data-testid={`credibility-item-${index + 1}`}><Icon size={21} /><span>{text}</span></div>;
        })}
      </section>
    </>
  );
};
