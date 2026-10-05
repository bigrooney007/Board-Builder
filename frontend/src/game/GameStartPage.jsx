import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { clearMemberToken, memberApi, storeMemberToken } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { money, useGameContent } from "./gameShared";
import { trackPlatformEvent, useHomepageContent } from "@/clean/platform";
import { usePageMeta } from "@/seo";
import PublicStartLayout from "@/funnels/PublicStartLayout";

const PRESETS = [100000, 250000, 500000, 1000000];

export default function GameStartPage() {
  usePageMeta("Start Your Board Fundraising | Nonprofit Board Builder", "Enter your fundraising goal and answer the five questions to get your board fundraising.", true);
  const navigate = useNavigate();
  const { member, loading: authLoading, setMember } = useMemberAuth();
  const sourceContent = useGameContent();
  const content = useHomepageContent("board-fundraising-game", sourceContent || {});
  const [goal, setGoal] = useState("");
  const [lead, setLead] = useState({ name: "", email: "", org: "" });
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState("");

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
        window.scrollTo({ top: 0 });
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
        window.scrollTo({ top: 0 });
        navigate("/login?next=" + encodeURIComponent("/game/questions"), { replace: true });
        return;
      }
      trackPlatformEvent("board-fundraising-game", "contact_entered");
      storeMemberToken(response.data.token);
      setMember(response.data.member);
      window.scrollTo({ top: 0 });
      navigate("/game/questions");
    } catch {
      setStartError("We could not continue. Please check your details and try again.");
      setStarting(false);
    }
  };

  const setAmount = (value) => setGoal(Number(String(value).replace(/[^0-9]/g, "") || 0) ? Number(String(value).replace(/[^0-9]/g, "")).toLocaleString("en-US") : "");

  return (
    <PublicStartLayout backTo="/board-fundraising-game" backLabel="Read about getting your Board fundraising" testId="bfg-start-page">
      <form className="public-start-card bfg-goal-box" data-testid="bfg-goal-box" onSubmit={(event) => { event.preventDefault(); startGame(); }}>
        <h1 id="bfg-goal-heading" data-testid="bfg-goal-heading">START WITH YOUR FUNDRAISING GOAL</h1>
        <label htmlFor="bfg-goal">{content.goal_label}</label>
        <div className="bfg-goal-input">
          <span>$</span>
          <input id="bfg-goal" inputMode="numeric" placeholder={content.goal_placeholder} aria-required="true"
            value={goal} onChange={(event) => setAmount(event.target.value)}
            required data-testid="bfg-goal-input" />
        </div>
        <div className="bfg-goal-presets">
          {PRESETS.map((preset) => (
            <button type="button" key={preset} className={goal === preset.toLocaleString("en-US") ? "active" : ""} onClick={() => setAmount(preset)} data-testid={`bfg-goal-preset-${preset}`}>
              {money(preset)}
            </button>
          ))}
        </div>
        <div className="bfg-goal-lead">
          <label className="sr-only" htmlFor="bfg-lead-name">Your name</label>
          <input id="bfg-lead-name" autoComplete="name" required placeholder="Your name" value={lead.name} onChange={(event) => setLead({ ...lead, name: event.target.value })} data-testid="bfg-lead-name" />
          <label className="sr-only" htmlFor="bfg-lead-email">Email address</label>
          <input id="bfg-lead-email" autoComplete="email" type="email" required placeholder="Email address" value={lead.email} onChange={(event) => setLead({ ...lead, email: event.target.value })} data-testid="bfg-lead-email" />
          <label className="sr-only" htmlFor="bfg-lead-org">Organization name</label>
          <input id="bfg-lead-org" autoComplete="organization" required placeholder="Organization name" value={lead.org} onChange={(event) => setLead({ ...lead, org: event.target.value })} data-testid="bfg-lead-org" />
        </div>
        {startError && <p className="bfg-error" data-testid="bfg-start-error">{startError}</p>}
        <button type="submit" className="bfg-btn bfg-btn-primary" disabled={starting || authLoading} data-testid="bfg-form-submit">
          {starting ? "Opening…" : content.cta_label}
        </button>
        <p className="bfg-start-supporting">{content.start_supporting}</p>
      </form>
    </PublicStartLayout>
  );
}
