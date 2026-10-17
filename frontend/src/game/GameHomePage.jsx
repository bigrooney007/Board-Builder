import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { BfgShell, useGameContent } from "./gameShared";
import { useHomepageContent } from "@/clean/platform";
import { useLandingPageMeta } from "@/seo";
import { FREE_START_LABEL, PUBLIC_START_ROUTES } from "@/funnels/publicStartRoutes";
import "./game-landing.css";

export default function GameHomePage() {
  useLandingPageMeta("/board-fundraising-game");
  const navigate = useNavigate();
  const sourceContent = useGameContent();
  const content = useHomepageContent("board-fundraising-game", sourceContent || {});
  const startPath = PUBLIC_START_ROUTES["board-fundraising-game"];
  useEffect(() => {
    if (window.location.hash === "#bfg-goal-form") navigate(startPath, { replace: true });
  }, [navigate, startPath]);
  if (!sourceContent) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  return (
    <BfgShell shellClass="bfg-home-shell">
      <main data-testid="bfg-homepage" className="bfg-home bfg-game-landing">
        <section className="bfg-hero" aria-labelledby="bfg-hero-heading">
          <div className="bfg-hero-inner">
            <h1 id="bfg-hero-heading" data-testid="bfg-hero-headline">{content.headline}</h1>
            <p className="bfg-hero-sub" data-testid="bfg-hero-subheadline">{content.subheadline}</p>
            <Link className="bfg-btn bfg-btn-primary" to={startPath} data-testid="bfg-hero-cta">{FREE_START_LABEL}</Link>
          </div>
        </section>

        <section className="bfg-landing-principle" aria-label="Get your board fundraising">
          <p>{content.hero_explanation}</p>
        </section>

        <div className="bfg-light">
        <section className="bfg-section bfg-intro" data-testid="bfg-intro-section">
          <h2 data-testid="bfg-intro-heading">{content.intro_heading}</h2>
          {(content.intro_paragraphs || []).slice(0, 3).map((paragraph, index) => (
            <p key={index} data-testid={`bfg-intro-paragraph-${index + 1}`}>{paragraph}</p>
          ))}
        </section>

        <section className="bfg-section" data-testid="bfg-stages-section">
          <div className="bfg-section-head">
            <p className="bfg-eyebrow">{content.stages_label}</p>
            <h2>{content.stages_heading}</h2>
          </div>
          <div className="bfg-stages">
            {content.stages.map((stage, index) => (
              <article className="bfg-stage" key={stage.key} data-testid={`bfg-stage-${stage.key}`}>
                <span className="bfg-stage-number">{stage.number || index + 1}</span>
                <h3>{stage.title}</h3>
                <div className="bfg-stage-paras">
                  {stage.items.map((item) => <p key={item}>{item}</p>)}
                </div>
              </article>
            ))}
          </div>
          <div className="bfg-stages-cta">
          <Link className="bfg-btn bfg-btn-primary" to={startPath} data-testid="bfg-stages-cta">{FREE_START_LABEL}</Link>
          </div>
        </section>

        <section className="bfg-section" data-testid="bfg-outcomes-section">
          <div className="bfg-section-head">
            <p className="bfg-eyebrow">{content.outcomes_label}</p>
            <h2>{content.outcomes_heading}</h2>
          </div>
          <div className="bfg-outcomes">
            {(content.outcomes || []).map((outcome) => (
              <article className="bfg-outcome" key={outcome.key} data-testid={`bfg-outcome-${outcome.key}`}>
                <h3>{outcome.heading}</h3>
                {(outcome.paragraphs || []).map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
              </article>
            ))}
          </div>
        </section>

        <TestimonialCarousel heading={content.testimonials_heading} idPrefix="bfg" />

        <section className="bfg-section" data-testid="bfg-faq-section">
          <div className="bfg-section-head">
            <p className="bfg-eyebrow">{content.faqs_label}</p>
            <h2>{content.faqs_heading}</h2>
          </div>
          <div className="bfg-faq">
            {content.faqs.map((faq, index) => (
              <details key={faq.q} data-testid={`bfg-faq-${index + 1}`}>
                <summary>{faq.q}</summary>
                <p>{faq.a}</p>
              </details>
            ))}
          </div>
        </section>

        {content.footer_recruit_label && (
          <section className="bfg-section" style={{ textAlign: "center", paddingTop: 0 }} data-testid="bfg-recruitment-link">
            <p>Need to strengthen your board first?</p>
            <a className="bfg-btn bfg-btn-ghost" href="/recruit">{content.footer_recruit_label}</a>
          </section>
        )}

        <section className="bfg-section bfg-closing" data-testid="bfg-closing-section">
          <h2 data-testid="bfg-closing-heading">{content.closing_heading}</h2>
          <p data-testid="bfg-closing-text">{content.closing_text}</p>
          <Link className="bfg-btn bfg-btn-primary" to={startPath} data-testid="bfg-closing-cta">{FREE_START_LABEL}</Link>
        </section>

        </div>
      </main>
    </BfgShell>
  );
}
