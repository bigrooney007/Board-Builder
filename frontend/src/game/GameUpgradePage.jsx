import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, money } from "./gameShared";
import { trackPlatformEvent, useHomepageContent } from "@/clean/platform";
import { OFFER_TEXT_DEFAULTS } from "@/content/offerTextDefaults";
import OfferTextRoadmap from "@/funnels/OfferTextRoadmap";
import DemoOfferCards from "@/components/DemoOfferCards";
import "./guided-flow.css";

export default function GameUpgradePage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [game, setGame] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const copy = useHomepageContent("offer-board-fundraising-game", OFFER_TEXT_DEFAULTS["offer-board-fundraising-game"]);

  useEffect(() => { document.title = "Bring In Your Board | Board Fundraising Game"; }, []);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent("/game/upgrade")}`, { replace: true }); return; }
    memberApi.get("/game/free").then(({ data }) => {
      if (!data.complete) navigate("/game/questions", { replace: true });
      else if (data.unlocked) navigate("/game/setup", { replace: true });
      else setGame(data);
    }).catch(() => navigate("/board-fundraising-game", { replace: true }));
  }, [loading, member, navigate]);

  const upgrade = async () => {
    setBusy("self-guided"); setError("");
    try {
      trackPlatformEvent("board-fundraising-game", "checkout_started");
      const response = await memberApi.post("/payments/game-checkout", {
        origin_url: window.location.origin, cancel_path: "/game/upgrade",
      });
      window.location.href = response.data.checkout_url;
    } catch (err) {
      setError(err.response?.data?.detail || "We could not open checkout. Please try again.");
      setBusy("");
    }
  };

  const supported = async () => {
    setBusy("supported"); setError("");
    try {
      trackPlatformEvent("board-fundraising-game", "checkout_started");
      const response = await memberApi.post("/payments/supported-checkout", {
        origin_url: window.location.origin, product: "board-fundraising-game",
      });
      window.location.href = response.data.checkout_url;
    } catch (err) { setError(err.response?.data?.detail || "We could not open checkout. Please try again."); setBusy(""); }
  };

  const payButton = (testId) => <button type="button" className="bfg-btn bfg-btn-primary guided-action" onClick={upgrade} disabled={busy}
    data-testid={testId}>{busy === "self-guided" ? "OPENING SECURE CHECKOUT…" : "BRING MY BOARD INTO THE GAME — $497"}</button>;

  return <BfgShell><main className="guided-flow" data-testid="bfg-upgrade-page">
    {!game ? <p className="guided-loading">Opening your Board Fundraising Game…</p> : <section className="guided-upgrade">
      <p className="guided-kicker">{copy.eyebrow}</p>
      <h1>{copy.heading}</h1>
      <div className="guided-goal"><span>THE FUNDRAISING GOAL YOU ARE BUILDING TOWARD</span><strong>{money(game.goal_amount)}</strong></div>
      <OfferTextRoadmap copy={copy} />
      {payButton("bfg-invite-board-cta")}
      <p className="guided-price-note">One payment for your organization and board. Payment is next.</p>
      <DemoOfferCards product="board-fundraising-game" busy={busy} onBuy={(choice) => choice === "supported" ? supported() : upgrade()} error={error}
        intro={copy.cardIntro} offerEyebrow={copy.offerEyebrow} offerHeading={copy.offerHeading}
        selfGuided={{ title: copy.selfGuidedTitle, description: copy.selfGuidedDescription,
          features: copy.selfGuidedFeatures,
          button: "START THE SELF-GUIDED GAME — $497" }}
        supported={{ title: copy.supportedTitle, description: copy.supportedDescription,
          features: copy.supportedFeatures,
          price: "$2,997", button: "WORK WITH ROONEY — $2,997" }} />
      {params.get("checkout") === "cancelled" && <p className="bfg-error" role="alert">Your checkout was cancelled. You have not been charged.</p>}
      {error && <p className="bfg-error" role="alert">{error}</p>}
      {payButton("bfg-invite-board-cta-bottom")}
    </section>}
  </main></BfgShell>;
}
