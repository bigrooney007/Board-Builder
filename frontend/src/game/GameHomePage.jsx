import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { clearMemberToken, memberApi, storeMemberToken } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, money, useGameContent } from "./gameShared";
import { trackPlatformEvent, useHomepageContent } from "@/clean/platform";
import { useLandingPageMeta } from "@/seo";
import "./game-landing.css";

const PRESETS = [100000, 250000, 500000, 1000000];

export default function GameHomePage() {
  useLandingPageMeta("/board-fundraising-game");
  const navigate = useNavigate();
  const { member, loading: authLoading, setMember } = useMemberAuth();
  const sourceContent = useGameContent();
  const content = useHomepageContent("board-fundraising-game", sourceContent || {});
  const [goal, setGoal] = useState("");
  const [lead, setLead] = useState({ name: "", email: "", org: "" });
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState("");

  useEffect(() => {
    if (sourceContent && window.location.hash === "#bfg-goal-form") {
      document.getElementById("bfg-goal-form")?.scrollIntoView({ block: "start" });
    }
  }, [sourceContent]);

  if (!sourceContent) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const startGame = async () => {
    const digits = String(goal).replace(/[^0-9]/g, "");
    if (digits) sessionStorage.setItem("bfgGoal", digits);
    if (lead.name.trim()) sessionStorage.setItem("bfgName", lead.name.trim());
    if (lead.email.trim()) sessionStorage.setItem("bfgEmail", lead.email.trim());
    if (lead.org.trim()) sessionStorage.setItem("bfgOrg", lead.org.trim());
    if (!lead.name.trim() || !lead.email.trim() || !lead.org.trim() || !digits) {
      setStartError("Enter your name, email, organization name and fundraising goal to continue.");
      document.getElementById("bfg-goal")?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(lead.email.trim()) || Number(digits) < 1) {
      setStartError("Enter a valid email address and a fundraising goal greater than zero.");
      return;
    }
    setStarting(true); setStartError("");
    try {
      if (member) {
        await memberApi.put("/game/profile", {
          organization: { name: lead.org.trim() },
          goal: { amount: Number(digits), purpose: "Reach our fundraising goal" },
          primary_user: { full_name: lead.name.trim(), email: member.email || lead.email.trim() },
          homepage_capture: true,
        });
        trackPlatformEvent("board-fundraising-game", "contact_entered");
        navigate("/game/questions");
        return;
      }
      clearMemberToken();
      localStorage.removeItem("recruitFreeToken");
      sessionStorage.removeItem("operateAsUserId");
      try { await memberApi.post("/members/logout"); } catch { /* no active server session */ }
      const response = await memberApi.post("/members/game-free-start", {
        name: lead.name.trim(), email: lead.email.trim(),
        organization: lead.org.trim(), goal_amount: Number(digits),
      });
      if (response.data.login_required || !response.data.token) {
        navigate("/login?next=" + encodeURIComponent("/game/questions"), { replace: true });
        return;
      }
      trackPlatformEvent("board-fundraising-game", "contact_entered");
      storeMemberToken(response.data.token);
      setMember(response.data.member);
      navigate("/game/questions");
    } catch {
      setStartError("We could not continue. Please check your details and try again.");
      setStarting(false);
    }
  };

  const scrollToForm = () => document.getElementById("bfg-goal-form")?.scrollIntoView({ behavior: "smooth", block: "start" });

  const setAmount = (value) => setGoal(Number(String(value).replace(/[^0-9]/g, "") || 0) ? Number(String(value).replace(/[^0-9]/g, "")).toLocaleString("en-US") : "");

  return (
    <BfgShell shellClass="bfg-home-shell">
      <main data-testid="bfg-homepage" className="bfg-home bfg-game-landing">
        <section className="bfg-hero" aria-labelledby="bfg-hero-heading">
          <div className="bfg-hero-inner">
            <h1 id="bfg-hero-heading" data-testid="bfg-hero-headline">{content.headline}</h1>
            <p className="bfg-hero-sub" data-testid="bfg-hero-subheadline">{content.subheadline}</p>
            <a className="bfg-btn bfg-btn-primary" href="#bfg-goal-form" data-testid="bfg-hero-cta">{content.cta_label}</a>
          </div>
        </section>

        <section className="bfg-landing-principle" aria-label="The Board Fundraising Game">
          <p>{content.hero_explanation}</p>
        </section>

        <div className="bfg-light">
        <section id="bfg-goal-form" className="bfg-goal-section" aria-labelledby="bfg-goal-heading">
            <div className="bfg-goal-box" data-testid="bfg-goal-box">
              <h2 id="bfg-goal-heading" data-testid="bfg-goal-heading">START WITH YOUR FUNDRAISING GOAL</h2>
              <label htmlFor="bfg-goal">{content.goal_label}</label>
              <div className="bfg-goal-input">
                <span>$</span>
                <input id="bfg-goal" inputMode="numeric" placeholder={content.goal_placeholder} aria-required="true"
                  value={goal} onChange={(event) => setAmount(event.target.value)}
                  onKeyDown={(event) => { if (event.key === "Enter") startGame(); }} data-testid="bfg-goal-input" />
              </div>
              <div className="bfg-goal-presets">
                {PRESETS.map((preset) => (
                  <button key={preset} type="button" className={goal === preset.toLocaleString("en-US") ? "active" : ""} onClick={() => setAmount(preset)} data-testid={`bfg-goal-preset-${preset}`}>
                    {money(preset)}
                  </button>
                ))}
              </div>
              <div className="bfg-goal-lead">
                <label className="sr-only" htmlFor="bfg-lead-name">Your name</label>
                <input id="bfg-lead-name" autoComplete="name" placeholder="Your name" value={lead.name} onChange={(event) => setLead({ ...lead, name: event.target.value })} data-testid="bfg-lead-name" />
                <label className="sr-only" htmlFor="bfg-lead-email">Email address</label>
                <input id="bfg-lead-email" autoComplete="email" type="email" placeholder="Email address" value={lead.email} onChange={(event) => setLead({ ...lead, email: event.target.value })} data-testid="bfg-lead-email" />
                <label className="sr-only" htmlFor="bfg-lead-org">Organization name</label>
                <input id="bfg-lead-org" autoComplete="organization" placeholder="Organization name" value={lead.org} onChange={(event) => setLead({ ...lead, org: event.target.value })} data-testid="bfg-lead-org" />
              </div>
              {startError && <p className="bfg-error" data-testid="bfg-start-error">{startError}</p>}
              <button className="bfg-btn bfg-btn-primary" disabled={starting || authLoading} onClick={startGame} data-testid="bfg-form-submit">
                {starting ? "Opening…" : content.cta_label}
              </button>
              <p className="bfg-start-supporting">{content.start_supporting}</p>
            </div>
        </section>
        <section className="bfg-section bfg-agent-intro" aria-labelledby="bfg-agent-intro-heading">
          <h2 id="bfg-agent-intro-heading">How The Game Begins</h2>
          <p>{content.agent_intro}</p>
          <ol>{(content.agent_questions || []).map((question) => <li key={question}>{question}</li>)}</ol>
          <p>{content.agent_followup}</p>
        </section>
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
            <button className="bfg-btn bfg-btn-primary" onClick={scrollToForm} data-testid="bfg-stages-cta">{content.stages_cta_label}</button>
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
          <a className="bfg-btn bfg-btn-primary" href="#bfg-goal-form" data-testid="bfg-closing-cta">{content.closing_cta_label}</a>
        </section>

        </div>
      </main>
    </BfgShell>
  );
}
