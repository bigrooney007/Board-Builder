import {SiteBrand} from "@/components/SiteBrand";
import { Link } from "react-router-dom";
import { ArrowRight, Users, Gamepad2, Map, RefreshCw, UserRoundPlus } from "lucide-react";

import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { BlogSlider } from "@/pages/BlogPages";
import { useProfessionalContent, defaults } from "@/professional/content";
import { useLandingPageMeta } from "@/seo";

import "./MainHomePage.css";

const PRODUCT_META = [
  { icon: Users, to: "/recruit", image: "https://images.unsplash.com/photo-1521737711867-e3b97375f902?auto=format&fit=crop&w=1200&q=80", imageAlt: "Professionals working together around a table" },
  { icon: Gamepad2, to: "/board-fundraising", image: "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1200&q=80", imageAlt: "A group collaborating together" },
  { icon: Map, to: "/strategic-planning", image: "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1200&q=80", imageAlt: "A team planning strategy together" },
  { icon: RefreshCw, to: "/board-recommitment", image: "https://images.unsplash.com/photo-1521791055366-0d553872125f?auto=format&fit=crop&w=1200&q=80", imageAlt: "Professionals recommitting through a handshake" },
];
export const MAIN_HOME_DEFAULTS = defaults.home;

export default function MainHomePage() {
  useLandingPageMeta("/");
  const copy = useProfessionalContent("home");

  return (
    <div className="nBB-home nBB-main-directory">
      <header className="nBB-home-nav" style={{gap:12,flexWrap:'wrap'}}>
        <SiteBrand/>
        <Link className="nBB-home-login" to="/meet-rooney">{copy.meetNav}</Link>
        <Link className="nBB-home-login" to="/blog">{copy.blogNav}</Link>
        <Link className="nBB-home-login" to="/join-a-board">{copy.networkNav}</Link>

      </header>
      <main>
        <section className="nBB-home-hero">
          <p className="nBB-home-eyebrow">{copy.heroEyebrow}</p>
          <h1>{copy.heroHeadline}</h1>
          <p className="nBB-home-lead">{copy.heroLead}</p>
          <a href="#choose-path" className="nBB-home-primary">{copy.heroCta} <ArrowRight size={18}/></a>
        </section>

        <section className="nBB-home-problem">
          <p>{copy.problemIntro}</p>
          <h2>{copy.problemHeading}</h2>
          <p>{copy.problemText}</p>
        </section>

        <section id="choose-path" className="nBB-home-paths">
          <div className="nBB-home-section-head">
            <p className="nBB-home-eyebrow">{copy.pathsEyebrow}</p>
            <h2>{copy.pathsHeading}</h2>
          </div>
          <div className="nBB-home-grid">
            {(copy.products || MAIN_HOME_DEFAULTS.products).slice(0,4).map((product, index) => {
              const meta = PRODUCT_META[index] || PRODUCT_META[0];
              const displayed = product;
              const Icon = meta.icon;
              return <article key={meta.to} className="nBB-home-card">
                <img src={meta.image} alt={meta.imageAlt} loading="lazy" />
                <div className="nBB-home-card-body">
                  <Icon size={30}/>
                  <p className="nBB-home-eyebrow">{displayed.eyebrow}</p>
                  <h3>{displayed.title}</h3>
                  <p>{displayed.text}</p>
                  <Link className="nBB-home-card-button" to={meta.to}>{displayed.cta} <ArrowRight size={17}/></Link>
                </div>
              </article>;
            })}
            <article className="nBB-home-card" data-testid="home-board-applicant-network">
              <img
                src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1200&q=80"
                alt="Professionals bringing different skills together around a shared mission"
                loading="lazy"
              />
              <div className="nBB-home-card-body">
                <UserRoundPlus size={30}/>
                <p className="nBB-home-eyebrow">{copy.applicantEyebrow || MAIN_HOME_DEFAULTS.applicantEyebrow}</p>
                <h3>{copy.applicantTitle || MAIN_HOME_DEFAULTS.applicantTitle}</h3>
                <p>{copy.applicantText || MAIN_HOME_DEFAULTS.applicantText}</p>
                <Link className="nBB-home-card-button" to="/join-a-board" data-testid="home-join-board-network-button">
                  {copy.applicantCta || MAIN_HOME_DEFAULTS.applicantCta} <ArrowRight size={17}/>
                </Link>
              </div>
            </article>
          </div>
        </section>

        <section className="nBB-home-problem nBB-home-rooney"><h2>{copy.rooneyHeading}</h2><p>{copy.rooneyText}</p><Link className="nBB-home-primary" to="/meet-rooney">{copy.rooneyCta} <ArrowRight size={18}/></Link></section>
        <section className="nBB-home-proof"><TestimonialCarousel heading={copy.testimonialsHeading} idPrefix="home" /></section>
        <section className="nBB-home-blog"><BlogSlider /></section>

        <section className="nBB-home-closing">
          <h2>{copy.closingHeading}</h2>
          <p>{copy.closingText}</p>
          <div className="nBB-home-closing-actions">
            <a href="#choose-path" className="nBB-home-primary">{copy.closingCta} <ArrowRight size={18}/></a>
            <Link to="/join-a-board" className="nBB-home-primary nBB-home-secondary-cta" data-testid="home-closing-join-board-network">
              {copy.closingApplicantCta || MAIN_HOME_DEFAULTS.closingApplicantCta} <ArrowRight size={18}/>
            </Link>
          </div>
        </section>
      </main>
      <footer className="nBB-home-footer">
        <span>© {new Date().getFullYear()} Nonprofit Board Builder</span>
        <Link to="/privacy-policy">Privacy</Link>
        <Link to="/terms">Terms</Link>
      </footer>
    </div>
  );
}
