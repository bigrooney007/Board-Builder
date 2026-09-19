import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { clearMemberToken, memberApi, storeMemberToken } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, money, useGameContent } from "./gameShared";

const PRESETS = [100000, 250000, 500000, 1000000];

export default function GameHomePage() {
  const navigate = useNavigate();
  const { member, loading: authLoading, refresh } = useMemberAuth();
  const content = useGameContent();
  const [goal, setGoal] = useState("");
  const [lead, setLead] = useState({ name: "", email: "", org: "" });
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState("");

  useEffect(() => { document.title = "The Board Fundraising Game | Nonprofit Board Builder"; }, []);

  if (!content) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const startDemonstration = async () => {
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
    setStarting(true); setStartError("");
    try {
      if (member) {
        await memberApi.put("/game/profile", {
          organization: { name: lead.org.trim() },
          goal: { amount: Number(digits), purpose: "Reach our fundraising goal" },
          primary_user: { full_name: lead.name.trim(), email: member.email || lead.email.trim() },
        });
        navigate("/game/demonstration");
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
        navigate("/login?next=" + encodeURIComponent("/game/demonstration"), { replace: true });
        return;
      }
      storeMemberToken(response.data.token);
      await refresh();
      navigate("/game/demonstration");
    } catch {
      setStartError("We could not continue. Please check your details and try again.");
      setStarting(false);
    }
  };

  const launchFromStages = () => {
    const digits = String(goal).replace(/[^0-9]/g, "");
    if (digits || sessionStorage.getItem("bfgGoal")) { startDemonstration(); return; }
    document.getElementById("bfg-goal")?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => document.getElementById("bfg-goal")?.focus({ preventScroll: true }), 500);
  };

  const setAmount = (value) => setGoal(Number(String(value).replace(/[^0-9]/g, "") || 0) ? Number(String(value).replace(/[^0-9]/g, "")).toLocaleString("en-US") : "");

  return (
    <BfgShell shellClass="bfg-home-shell">
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
          {(content.intro_paragraphs || []).slice(0, 3).map((paragraph, index) => (
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
                onKeyDown={(event) => { if (event.key === "Enter") startDemonstration(); }}
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
            <div className="bfg-goal-lead">
              <input placeholder="Your name" value={lead.name} onChange={(event) => setLead({ ...lead, name: event.target.value })} data-testid="bfg-lead-name" />
              <input type="email" placeholder="Email" value={lead.email} onChange={(event) => setLead({ ...lead, email: event.target.value })} data-testid="bfg-lead-email" />
              <input placeholder="Organization name" value={lead.org} onChange={(event) => setLead({ ...lead, org: event.target.value })} data-testid="bfg-lead-org" />
            </div>
            {startError && <p className="bfg-error" data-testid="bfg-start-error">{startError}</p>}
            <button className="bfg-btn bfg-btn-primary" disabled={starting || authLoading} onClick={startDemonstration} data-testid="bfg-hero-cta">
              {starting ? "Opening…" : "WATCH THE PRODUCT DEMONSTRATION"}
            </button>
          </div>
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
          <button className="bfg-btn bfg-btn-primary" disabled={starting || authLoading} onClick={startDemonstration} data-testid="bfg-closing-cta">
            {starting ? "Opening…" : "WATCH THE PRODUCT DEMONSTRATION"}
          </button>
        </section>

        {/* EXACT CTA COPY — provided separately, inserted word for word. */}
        <section className="bfg-section bfg-closing" data-testid="bfg-recruit-cta-section">
          <h2 data-testid="bfg-recruit-cta-heading">Need to recruit board members with fundraising experience?</h2>
          <button className="bfg-btn bfg-btn-primary" onClick={() => { window.location.href = "/recruit"; }} data-testid="bfg-recruit-cta-btn">
            Recruit Board Members
          </button>
        </section>

        <section className="bfg-section bfg-closing" data-testid="bfg-facilitated-cta-section">
          <h2 data-testid="bfg-facilitated-cta-heading">Do you want us to organize the Board Fundraising Game for your organization?</h2>
          <button className="bfg-btn bfg-btn-primary" onClick={() => { window.location.href = "/organize-board-fundraising-game"; }} data-testid="bfg-facilitated-cta-btn">
            Organize My Board Fundraising Game
          </button>
        </section>
        </div>
      </main>
    </BfgShell>
  );
}
