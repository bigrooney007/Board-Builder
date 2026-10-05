import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, money } from "./gameShared";
import { trackPlatformEvent } from "@/clean/platform";
import { usePlatformVideo } from "@/clean/platform";
import TrackedYouTubeVideo from "@/clean/TrackedYouTubeVideo";
import DemoOfferCards from "@/components/DemoOfferCards";
import "./guided-flow.css";

export default function GameUpgradePage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [game, setGame] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  // Use the same demo the visitor can watch before the game. One Admin setting
  // controls the demonstration on both pages.
  const configuredVideo = usePlatformVideo("game_homepage");
  const video = configuredVideo?.youtube_id ? configuredVideo : { key: "game_homepage", youtube_id: "rsf_QZfEId8", url: "https://youtu.be/rsf_QZfEId8" };

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
      <p className="guided-kicker">YOUR FIVE IDEAS ARE SAVED</p>
      <h1>Now let's bring your board into the strategy.</h1>
      <div className="guided-goal"><span>THE FUNDRAISING GOAL YOU ARE BUILDING TOWARD</span><strong>{money(game.goal_amount)}</strong></div>
      <p className="guided-upgrade-copy">You have shared who you believe can fund your mission, where to find them, how to attract them, what to ask for and how to build the relationship. That is your starting point. Your board brings more ideas and more people to help carry them out.</p>
      <div className="guided-video" data-testid="bfg-upgrade-video">
        <TrackedYouTubeVideo video={video} flow="board-fundraising-game" title="Board Fundraising Game demonstration"
          placeholder="The Board Fundraising Game demonstration will appear here." />
      </div>
      {payButton("bfg-invite-board-cta")}
      <p className="guided-price-note">One payment for your organization and board. Payment is next.</p>
      <p className="guided-upgrade-next">After payment, create your password, tell us about your present individual donors, businesses and grantors, then say how you want to participate. You will confirm the meeting and fundraising deadline before inviting your board.</p>
      <DemoOfferCards product="board-fundraising-game" busy={busy} onBuy={(choice) => choice === "supported" ? supported() : upgrade()} error={error}
        intro="Run the game with your board using the guided platform, or have Rooney help prepare and carry the process with you."
        selfGuided={{ title: "Build The Fundraising Strategy With Your Board", description: "Run the guided process yourselves with the complete platform.",
          features: ["Bring your board's ideas into one fundraising strategy", "Understand existing donors, businesses and grantors", "Agree each board member's role at the group meeting", "Create the strategy and execution portfolios"],
          button: "START THE SELF-GUIDED GAME — $497" }}
        supported={{ title: "Build Your Fundraising System With Rooney", description: "Work directly with Rooney to prepare, guide and turn your board's thinking into a strategy they can execute.",
          features: ["Prepare your board for the fundraising game", "Guide the group discussion and decisions", "Translate decisions into a fundraising strategy", "Support the handoff into board roles and execution"],
          price: "$2,997", button: "WORK WITH ROONEY — $2,997" }} />
      {params.get("checkout") === "cancelled" && <p className="bfg-error" role="alert">Your checkout was cancelled. You have not been charged.</p>}
      {error && <p className="bfg-error" role="alert">{error}</p>}
      {payButton("bfg-invite-board-cta-bottom")}
    </section>}
  </main></BfgShell>;
}
