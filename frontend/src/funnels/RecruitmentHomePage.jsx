import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { ArrowRight } from "lucide-react";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { recruitmentHomeContent as defaultCopy } from "@/content/siteContent";
import { useHomepageContent } from "@/clean/platform";
import { useLandingPageMeta } from "@/seo";
import { PUBLIC_START_ROUTES } from "./publicStartRoutes";
import "../game/game.css";
import "./recruitment-home.css";

export default function RecruitmentHomePage() {
  useLandingPageMeta("/recruit");
  const navigate = useNavigate();
  const startPath = PUBLIC_START_ROUTES.recruitment;
  useEffect(() => {
    if (window.location.hash === "#recruit-intake") navigate(startPath, { replace: true });
  }, [navigate, startPath]);
  const savedCopy = useHomepageContent("recruitment", defaultCopy);
  const copy = { ...savedCopy, headline: "Launch Your Board Recruitment Campaign In The Next 30 Minutes",
    subheadline: "Tell us about the board you have and the support you need. Approve your profiles and launch a professional recruitment campaign built for your organization.",
    formHeading: "Start Your Board Recruitment Campaign" };
  const { member, loading, logout } = useMemberAuth();
  const handleLogout = async () => { await logout(); navigate("/login"); };

  return (
    <div className="bfg recruit-home-shell">
      <header className="bfg-nav" style={{ justifyContent: "flex-end" }}>
        <nav className="bfg-nav-actions" aria-label="Lead user account">
          {!loading && (
            member ? (
              <button type="button" className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={handleLogout} data-testid="recruit-home-logout">Log Out</button>
            ) : (
              <Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/login" data-testid="recruit-home-login">{copy.login}</Link>
            )
          )}
        </nav>
      </header>
      <main className="recruit-home" data-testid="recruitment-landing-page">
        <section className="recruit-hero" aria-labelledby="recruit-headline">
          <div className="recruit-hero-copy">
            <h1 id="recruit-headline" data-testid="recruitment-headline">{copy.headline}</h1>
            <p className="recruit-hero-sub">{copy.subheadline}</p>
            <Link to={startPath} className="bfg-btn bfg-btn-primary" data-testid="recruit-home-cta">
              {copy.primaryCta}<ArrowRight size={18} aria-hidden="true" />
            </Link>
          </div>
        </section>

        <section className="recruit-principle" aria-labelledby="recruit-principle-heading">
          <h2 id="recruit-principle-heading">{copy.introHeading}</h2>
          {copy.introParagraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
        </section>

        <section id="recruit-process" className="recruit-section" aria-labelledby="recruit-process-heading">
          <div className="recruit-section-heading">
            <p className="bfg-eyebrow">{copy.processEyebrow}</p>
            <h2 id="recruit-process-heading">{copy.processHeading}</h2>
            <p>{copy.processText}</p>
          </div>
          <ol className="recruit-stage-grid">
            {copy.stages.map((stage, index) => (
              <li className="recruit-stage" key={stage.title}>
                <span className="recruit-stage-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                <h3>{stage.title}</h3><p>{stage.text}</p>
              </li>
            ))}
          </ol>
          <Link to={startPath} className="bfg-btn bfg-btn-primary recruit-section-cta">
            {copy.primaryCta}<ArrowRight size={18} aria-hidden="true" />
          </Link>
        </section>

        <section className="recruit-outcomes-band" aria-labelledby="recruit-outcomes-heading">
          <div className="recruit-section">
            <div className="recruit-section-heading">
              <p className="bfg-eyebrow">{copy.outcomesEyebrow}</p>
              <h2 id="recruit-outcomes-heading">{copy.outcomesHeading}</h2>
            </div>
            <div className="recruit-outcome-grid">
              {copy.outcomes.map((outcome) => <article key={outcome.title}><h3>{outcome.title}</h3><p>{outcome.text}</p></article>)}
            </div>
          </div>
        </section>

        <div className="recruit-testimonials">
          <TestimonialCarousel heading={copy.testimonialsHeading} idPrefix="recruit-home" />
        </div>

        <section className="recruit-section recruit-faq" aria-labelledby="recruit-faq-heading">
          <div className="recruit-section-heading"><h2 id="recruit-faq-heading">{copy.faqHeading}</h2></div>
          {copy.faqs.map((faq) => <details key={faq.q}><summary>{faq.q}</summary><p>{faq.a}</p></details>)}
        </section>

        <section className="recruit-closing" aria-labelledby="recruit-closing-heading">
          <h2 id="recruit-closing-heading">{copy.closingHeading}</h2>
          <p>{copy.closingText}</p>
          <Link to={startPath} className="bfg-btn bfg-btn-primary">{copy.primaryCta}<ArrowRight size={18} aria-hidden="true" /></Link>
        </section>
      </main>
      <footer className="bfg-footer recruit-footer">
        <p>© {new Date().getFullYear()} {copy.footer}</p>
        <Link to="/privacy-policy">{copy.privacy}</Link><Link to="/terms">{copy.terms}</Link>
      </footer>
    </div>
  );
}
