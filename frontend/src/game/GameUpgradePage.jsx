import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, formatDate, money, useGameContent } from "./gameShared";

export default function GameUpgradePage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const content = useGameContent();
  const [profile, setProfile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Unlock Your Game | Board Fundraising Game"; }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup", { replace: true }); return; }
    memberApi.get("/game/profile").then((response) => {
      if (response.data.unlocked) {
        navigate(response.data.profile?.situation_completed ? "/game/dashboard" : "/game/welcome", { replace: true });
        return;
      }
      setProfile(response.data.profile || {});
    }).catch(() => setProfile({}));
  }, [loading, member, navigate]);

  const unlock = useCallback(async () => {
    if (busy) return;
    setError(""); setBusy(true);
    try {
      const response = await memberApi.post("/payments/game-checkout", { origin_url: window.location.origin, cancel_path: "/game/upgrade" });
      window.location.href = response.data.checkout_url;
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not start checkout. Please try again.");
      setBusy(false);
    }
  }, [busy]);

  if (loading || !content || !profile) return <div className="bfg" style={{ minHeight: "100vh" }} />;
  const up = content.upgrade_page || {};
  const goalAmount = Number(profile.goal?.amount || 0);

  const PaymentCard = ({ idSuffix }) => (
    <div className="bfg-price-card" style={{ marginTop: 34, textAlign: "center" }} data-testid={`bfg-upgrade-payment-${idSuffix}`}>
      <h2 style={{ fontSize: 22 }}>{up.payment_heading}</h2>
      <p style={{ fontFamily: "Outfit", fontWeight: 800, fontSize: 46, color: "#111827", margin: "12px 0 0" }}>{up.payment_price}</p>
      <p style={{ marginTop: 4, fontWeight: 700, color: "#111827" }}>{up.payment_onetime}</p>
      <p style={{ marginTop: 8 }}>{up.payment_org_line}</p>
      <p style={{ marginTop: 4 }}>{up.payment_subscription_line}</p>
      <p style={{ marginTop: 12, fontSize: 14 }}>{up.payment_includes}</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} onClick={unlock} disabled={busy} data-testid={`bfg-upgrade-cta-${idSuffix}`}>
        {busy ? "Preparing secure checkout…" : up.payment_cta}
      </button>
    </div>
  );

  return (
    <BfgShell>
      <main className="bfg-flow" data-testid="bfg-upgrade-page" style={{ maxWidth: 860, margin: "0 auto", padding: "36px 20px 80px", textAlign: "center" }}>
        <p className="bfg-eyebrow">{up.label}</p>
        <h1 style={{ fontSize: "clamp(28px, 4.6vw, 44px)" }} data-testid="bfg-upgrade-heading">{up.heading}</h1>
        <p style={{ marginTop: 14, maxWidth: 680, marginLeft: "auto", marginRight: "auto" }}>{up.supporting}</p>

        <div className="bfg-goal-highlight" style={{ maxWidth: 480, margin: "26px auto 0" }} data-testid="bfg-upgrade-goal">
          <span>Your Fundraising Goal</span>
          <strong>{goalAmount ? money(goalAmount) : ""}</strong>
          {profile.goal?.deadline && <span>By {formatDate(profile.goal.deadline)}</span>}
        </div>

        <section style={{ marginTop: 44 }} data-testid="bfg-upgrade-intro">
          <h2>{up.intro_heading}</h2>
          {(up.intro_paragraphs || []).map((paragraph, index) => (
            <p key={index} style={{ marginTop: 14, maxWidth: 700, marginLeft: "auto", marginRight: "auto" }}>{paragraph}</p>
          ))}
        </section>

        <section style={{ marginTop: 44 }} data-testid="bfg-upgrade-outcomes">
          <h2>{up.outcomes_heading}</h2>
          {(up.outcomes || []).map((outcome, index) => (
            <div className="bfg-card" key={index} style={{ marginTop: 16, textAlign: "center" }} data-testid={`bfg-upgrade-outcome-${index + 1}`}>
              <h3 style={{ fontSize: 18 }}>{outcome.heading}</h3>
              {(outcome.paragraphs || []).map((paragraph, i) => <p key={i} style={{ marginTop: 10 }}>{paragraph}</p>)}
            </div>
          ))}
        </section>

        <PaymentCard idSuffix="top" />

        <section style={{ marginTop: 44 }} data-testid="bfg-upgrade-features">
          <h2>{up.features_heading}</h2>
          <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", marginTop: 18 }}>
            {(up.features || []).map((feature, index) => (
              <div className="bfg-card" key={index} style={{ textAlign: "center", padding: 22 }} data-testid={`bfg-upgrade-feature-${index + 1}`}>
                <CheckCircle2 size={20} style={{ color: "#059669" }} />
                <h4 style={{ marginTop: 8, fontSize: 16 }}>{feature.heading}</h4>
                <p style={{ marginTop: 8, fontSize: 14 }}>{feature.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section style={{ marginTop: 44 }} data-testid="bfg-upgrade-steps">
          <h2>{up.steps_heading}</h2>
          <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", marginTop: 18 }}>
            {(up.steps || []).map((step, index) => (
              <div className="bfg-card" key={index} style={{ textAlign: "center", padding: 22 }} data-testid={`bfg-upgrade-step-${index + 1}`}>
                <span className="bfg-stage-number">{index + 1}</span>
                <h4 style={{ fontSize: 16 }}>{step.heading}</h4>
                <p style={{ marginTop: 8, fontSize: 14 }}>{step.description}</p>
              </div>
            ))}
          </div>
        </section>

        <PaymentCard idSuffix="bottom" />
        {error && <p className="bfg-error" data-testid="bfg-upgrade-error">{error}</p>}
      </main>
    </BfgShell>
  );
}
