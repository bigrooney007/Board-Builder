import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { useFlowVideo } from "@/hooks/useFlowVideos";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, GameVideo, money, useGameContent } from "./gameShared";

const PRESETS = [100000, 250000, 500000, 1000000];

export default function GameHomePage() {
  const navigate = useNavigate();
  const { member } = useMemberAuth();
  const content = useGameContent();
  const video = useFlowVideo("game_homepage");
  const [goal, setGoal] = useState("");

  useEffect(() => { document.title = "The Board Fundraising Game | Nonprofit Board Builder"; }, []);

  if (!content) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const startGame = () => {
    const digits = String(goal).replace(/[^0-9]/g, "");
    if (digits) sessionStorage.setItem("bfgGoal", digits);
    navigate(member ? "/game/start" : "/game/signup");
  };

  const launchFromStages = () => {
    const digits = String(goal).replace(/[^0-9]/g, "");
    if (digits || sessionStorage.getItem("bfgGoal")) { startGame(); return; }
    document.getElementById("bfg-goal")?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => document.getElementById("bfg-goal")?.focus({ preventScroll: true }), 500);
  };

  const setAmount = (value) => setGoal(Number(String(value).replace(/[^0-9]/g, "") || 0) ? Number(String(value).replace(/[^0-9]/g, "")).toLocaleString("en-US") : "");

  return (
    <BfgShell shellClass="bfg-home-shell" nav={member ? (
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/start")} data-testid="bfg-nav-continue-btn">My Game</button>
    ) : (
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/signup?mode=login")} data-testid="bfg-nav-login-btn">Log In</button>
    )}>
      <main data-testid="bfg-homepage" className="bfg-home">
        <section className="bfg-hero">
          <div className="bfg-hero-inner">
            <span className="bfg-badge" data-testid="bfg-hero-badge"><Sparkles size={13} /> {content.hero_badge}</span>
            <h1 data-testid="bfg-hero-headline">{content.headline}</h1>
            <p className="bfg-hero-sub" data-testid="bfg-hero-subheadline">{content.subheadline}</p>
          </div>
        </section>

        <div className="bfg-light">
        <section className="bfg-section bfg-intro" data-testid="bfg-intro-section">
          <h2 data-testid="bfg-intro-heading">{content.intro_heading}</h2>
          {(content.intro_paragraphs || []).map((paragraph, index) => (
            <p key={index} data-testid={`bfg-intro-paragraph-${index + 1}`}>{paragraph}</p>
          ))}
        </section>

        <section className="bfg-section bfg-goal-section" data-testid="bfg-goal-section">
          <h2 data-testid="bfg-goal-heading">{content.goal_label}</h2>
          <div className="bfg-goal-box" data-testid="bfg-goal-box">
            <div className="bfg-goal-input">
              <span>$</span>
              <input
                id="bfg-goal" inputMode="numeric" placeholder={content.goal_placeholder}
                value={goal} onChange={(event) => setAmount(event.target.value)}
                onKeyDown={(event) => { if (event.key === "Enter") startGame(); }}
                data-testid="bfg-goal-input"
              />
            </div>
            <div className="bfg-goal-presets">
              {PRESETS.map((preset) => (
                <button key={preset} type="button" className={goal === preset.toLocaleString("en-US") ? "active" : ""} onClick={() => setAmount(preset)} data-testid={`bfg-goal-preset-${preset}`}>
                  {money(preset)}
                </button>
              ))}
            </div>
            <button className="bfg-btn bfg-btn-primary" onClick={startGame} data-testid="bfg-hero-cta">{content.cta_label}</button>
          </div>
        </section>

        {content.video_enabled && (
          <section className="bfg-section bfg-video-section" data-testid="bfg-video-section">
            <div className="bfg-section-head">
              <p className="bfg-eyebrow">{content.video_label}</p>
              <h2>{content.video_heading}</h2>
              <p style={{ marginTop: 12 }}>{content.video_text}</p>
            </div>
            <GameVideo video={video} testId="bfg-homepage-video" />
          </section>
        )}

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
            <button className="bfg-btn bfg-btn-primary" onClick={launchFromStages} data-testid="bfg-stages-cta">{content.stages_cta_label}</button>
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

        <section className="bfg-section bfg-closing" data-testid="bfg-closing-section">
          <h2 data-testid="bfg-closing-heading">{content.closing_heading}</h2>
          <p data-testid="bfg-closing-text">{content.closing_text}</p>
          <button className="bfg-btn bfg-btn-primary" onClick={startGame} data-testid="bfg-closing-cta">{content.closing_cta_label}</button>
        </section>
        </div>
      </main>
    </BfgShell>
  );
}
