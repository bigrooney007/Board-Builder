import { Link } from "react-router-dom";
import { ArrowDown, ArrowRight } from "lucide-react";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { recruitmentHomeContent as copy } from "@/content/siteContent";
import "../game/game.css";
import "./recruitment-home.css";

export default function RecruitmentHomePage({ form }) {
  return (
    <div className="bfg recruit-home-shell">
      <header className="bfg-nav">
        <Link to="/recruit" className="bfg-logo" data-testid="recruit-home-logo">
          <span className="bfg-logo-mark">{copy.logoMark}</span>
          <span><strong>{copy.brand}</strong><em>{copy.subtitle}</em></span>
        </Link>
        <nav className="bfg-nav-actions" aria-label={copy.subtitle}>
          <a className="recruit-process-link" href="#recruit-process">{copy.howItWorks}</a>
          <Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/login">{copy.login}</Link>
        </nav>
      </header>
      <main className="recruit-home" data-testid="recruitment-landing-page">
        <section className="recruit-hero" aria-labelledby="recruit-headline">
          <div className="recruit-hero-copy">
            <p className="bfg-badge">{copy.eyebrow}</p>
            <h1 id="recruit-headline" data-testid="recruitment-headline">{copy.headline}</h1>
            <p className="recruit-hero-sub">{copy.subheadline}</p>
            <a href="#recruit-intake" className="bfg-btn bfg-btn-primary" data-testid="recruit-home-cta">
              {copy.primaryCta}<ArrowDown size={18} aria-hidden="true" />
            </a>
          </div>
          <div className="recruit-hero-card">
            <span className="recruit-card-mark" aria-hidden="true">01</span>
            <h2>{copy.introHeading}</h2>
            {copy.introParagraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </div>
        </section>

        <section id="recruit-intake" className="recruit-intake-section" aria-labelledby="recruit-form-heading">
          <div className="recruit-section-heading">
            <p className="bfg-eyebrow">{copy.formEyebrow}</p>
            <h2 id="recruit-form-heading">{copy.formHeading}</h2>
            {copy.formText ? <p>{copy.formText}</p> : null}
          </div>
          <div className="recruit-intake-card" data-testid="recruit-embedded-form">{form}</div>
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
          <a href="#recruit-intake" className="bfg-btn bfg-btn-primary recruit-section-cta">
            {copy.primaryCta}<ArrowRight size={18} aria-hidden="true" />
          </a>
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
          <a href="#recruit-intake" className="bfg-btn bfg-btn-primary">{copy.primaryCta}<ArrowDown size={18} aria-hidden="true" /></a>
        </section>
      </main>
      <footer className="bfg-footer recruit-footer">
        <p>© {new Date().getFullYear()} {copy.footer}</p>
        <Link to="/privacy-policy">{copy.privacy}</Link><Link to="/terms">{copy.terms}</Link>
      </footer>
    </div>
  );
}
