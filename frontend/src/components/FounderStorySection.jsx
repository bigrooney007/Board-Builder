import { useEffect, useState } from "react";
import { ArrowRight, BriefcaseBusiness, GraduationCap, HeartHandshake, ImagePlus, Map, TrendingUp } from "lucide-react";

const founderPhotoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/ezw4nj2a_InShot_20260413_074422056%20%281%29.webp";

const credibility = [
  [HeartHandshake, "Served on nonprofit boards"],
  [BriefcaseBusiness, "Former Vice President of a fundraising consulting firm"],
  [GraduationCap, "Trained hundreds of nonprofit founders and fundraisers"],
  [Map, "Worked with nonprofits across the United States"],
  [TrendingUp, "Contributed to raising more than $5 million"],
];

export const FounderStorySection = ({ onStart }) => {
  const [photo, setPhoto] = useState(founderPhotoUrl);
  const [localPhoto, setLocalPhoto] = useState("");
  useEffect(() => () => localPhoto && URL.revokeObjectURL(localPhoto), [localPhoto]);
  const replacePhoto = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const objectUrl = URL.createObjectURL(file);
    setLocalPhoto(objectUrl);
    setPhoto(objectUrl);
  };

  return (
    <>
      <section id="my-story" className="founder-section" data-testid="founder-story-section">
        <div className="founder-photo-panel">
          <div className="founder-photo-frame"><img src={photo} alt="Rooney Akpesiri, the Nonprofit Board Builder" data-testid="founder-photo" /><span data-testid="founder-photo-caption">Rooney Akpesiri</span></div>
          <label className="founder-photo-control" data-testid="founder-photo-placeholder"><ImagePlus size={17} />Upload Rooney’s Photograph<input type="file" accept="image/*" onChange={replacePhoto} data-testid="founder-photo-upload-input" /></label>
        </div>
        <div className="founder-story-copy">
          <p className="eyebrow" data-testid="founder-story-eyebrow">The story behind the process</p>
          <h2 data-testid="founder-story-heading">I Built This Process From Experience</h2>
          <div className="founder-identity"><strong data-testid="founder-name">Rooney Akpesiri, CNC, CDE, CNE</strong><span data-testid="founder-title">The Nonprofit Board Builder</span></div>
          <div className="founder-story-text" data-testid="founder-story-text">
            <p>I’m Rooney. Known to many as the Nonprofit Board Builder.</p>
            <p>I started as a nonprofit founder many years ago, where I built my first board.</p>
            <p>I made mistakes, damaged relationships, learned from the experience, rebuilt my board, and eventually developed a process that worked.</p>
            <p>Since then, I have served on nonprofit boards, worked as a fundraising consultant, served as Vice President of a fundraising consulting firm working with nonprofits across the United States, trained hundreds of nonprofit founders and fundraisers, helped nonprofits strengthen their boards, and contributed to raising more than $5 million.</p>
            <p>Today, I teach, coach, and work directly with founders and executive directors so they do not make the mistakes I made, damage their relationships, or waste their time.</p>
          </div>
          <button onClick={onStart} className="button" data-testid="founder-start-assessment-button">Tell Me About Your Present Board <ArrowRight size={18} /></button>
        </div>
      </section>
      <section className="credibility-strip" data-testid="founder-credibility-strip">
        {credibility.map(([Icon, text], index) => <div key={text} data-testid={`credibility-item-${index + 1}`}><Icon size={21} /><span>{text}</span></div>)}
      </section>
    </>
  );
};