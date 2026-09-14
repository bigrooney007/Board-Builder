import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Sparkles } from "lucide-react";
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

  const setAmount = (value) => setGoal(Number(String(value).replace(/[^0-9]/g, "") || 0) ? Number(String(value).replace(/[^0-9]/g, "")).toLocaleString("en-US") : "");

  return (
    <BfgShell nav={member ? (
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
            <div className="bfg-goal-box" data-testid="bfg-goal-box">
              <label htmlFor="bfg-goal">{content.goal_label}</label>
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
          </div>
        </section>

        <div className="bfg-light">
        {content.video_enabled && (
          <section className="bfg-section bfg-video-section" data-testid="bfg-video-section">
            <div className="bfg-section-head">
              <p className="bfg-eyebrow">Watch</p>
              <h2>{content.video_heading}</h2>
              <p style={{ marginTop: 12 }}>{content.video_text}</p>
            </div>
            <GameVideo video={video} testId="bfg-homepage-video" />
          </section>
        )}

        <section className="bfg-section" data-testid="bfg-stages-section">
          <div className="bfg-section-head">
            <p className="bfg-eyebrow">How it works</p>
            <h2>{content.stages_heading}</h2>
          </div>
          <div className="bfg-stages">
            {content.stages.map((stage, index) => (
              <article className="bfg-stage" key={stage.key} data-testid={`bfg-stage-${stage.key}`}>
                <span className="bfg-stage-number">{index + 1}</span>
                <h3>{stage.title}</h3>
                <ul>{stage.items.map((item) => <li key={item}>{item}</li>)}</ul>
              </article>
            ))}
          </div>
        </section>

        <section className="bfg-section" data-testid="bfg-benefits-section">
          <div className="bfg-section-head">
            <p className="bfg-eyebrow">Outcomes</p>
            <h2>{content.benefits_heading}</h2>
          </div>
          <div className="bfg-benefits">
            {content.benefits.map((benefit) => (
              <div className="bfg-benefit" key={benefit}><CheckCircle2 size={18} /> {benefit}</div>
            ))}
          </div>
        </section>

        <TestimonialCarousel heading={content.testimonials_heading} idPrefix="bfg" />

        <section className="bfg-section" data-testid="bfg-faq-section">
          <div className="bfg-section-head">
            <p className="bfg-eyebrow">Questions</p>
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
          <h2>Ready to Bring Your Board Together?</h2>
          <button className="bfg-btn bfg-btn-primary" onClick={startGame} data-testid="bfg-closing-cta">{content.cta_label}</button>
        </section>
        </div>
      </main>
    </BfgShell>
  );
}
