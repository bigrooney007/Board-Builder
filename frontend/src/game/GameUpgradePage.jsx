import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, money } from "./gameShared";
import { trackPlatformEvent } from "@/clean/platform";

const SHARED_AREAS = [
  "Who you believe can help fund your organization.",
  "Where you believe you can find them.",
  "How you believe you can attract them.",
  "What you think you should ask them for and how much you should ask.",
  "How you think you can move them from first discovering your organization to eventually funding it.",
];

export default function GameUpgradePage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [game, setGame] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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
    setBusy(true); setError("");
    try {
      trackPlatformEvent("board-fundraising-game", "checkout_started");
      const response = await memberApi.post("/payments/game-checkout", {
        origin_url: window.location.origin, cancel_path: "/game/upgrade",
      });
      window.location.href = response.data.checkout_url;
    } catch (err) {
      setError(err.response?.data?.detail || "We could not open checkout. Please try again.");
      setBusy(false);
    }
  };

  return <BfgShell><main className="bfg-flow" style={{ maxWidth: 820, margin: "0 auto", padding: "42px 20px 90px", textAlign: "center" }} data-testid="bfg-upgrade-page">
    {!game ? <p>Opening your Board Fundraising Game…</p> : <>
      <p className="bfg-eyebrow">YOUR IDEAS ARE SAVED • {money(game.goal_amount)} FUNDRAISING GOAL</p>
      <h1>YOU'VE SHARED YOUR FUNDRAISING IDEAS. NOW LET'S BRING IN YOUR BOARD.</h1>
      <p style={{ margin: "24px auto 10px", fontSize: 18 }}>You've now told us:</p>
      <ul style={{ maxWidth: 670, margin: "0 auto", textAlign: "left", lineHeight: 1.8, fontSize: 17 }}>
        {SHARED_AREAS.map((area) => <li key={area}>{area}</li>)}
      </ul>
      <p style={{ margin: "24px auto 8px", fontWeight: 700, fontSize: 19 }}>That's your perspective.</p>
      <p style={{ maxWidth: 680, margin: "0 auto", fontSize: 17 }}>Now imagine bringing the thinking of your entire board into the same process. Invite each board member to answer these questions from their own point of view. During your Board Fundraising Game, bring everyone's ideas together, choose the strongest opportunities and build the fundraising strategy your organization will execute together.</p>
      {params.get("checkout") === "cancelled" && <p className="bfg-error" style={{ marginTop: 22 }}>Your checkout was cancelled. You have not been charged.</p>}
      {error && <p className="bfg-error" style={{ marginTop: 22 }}>{error}</p>}
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 28 }} onClick={upgrade} disabled={busy} data-testid="bfg-invite-board-cta">{busy ? "OPENING CHECKOUT…" : "INVITE MY BOARD AND CONTINUE"}</button>
      <p style={{ maxWidth: 590, margin: "15px auto", fontSize: 15 }}>Upgrade to continue your Board Fundraising Game, invite your board members and build your organization's fundraising strategy together.</p>
      <p style={{ fontSize: 14 }}>One-time payment: $497 for your organization and board.</p>
      <Link to="/game/demonstration" style={{ display: "inline-block", marginTop: 10 }}>Watch Product Demonstration</Link>
    </>}
  </main></BfgShell>;
}
