import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useFlowVideo } from "@/hooks/useFlowVideos";
import { BfgShell, GameVideo } from "./gameShared";

export default function GameDemonstrationPage() {
  const navigate = useNavigate();
  const video = useFlowVideo("game_homepage");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "See How The Board Fundraising Game Works"; }, []);

  const buy = async () => {
    setBusy(true); setError("");
    try {
      const response = await memberApi.post("/payments/game-checkout", {
        origin_url: window.location.origin,
        cancel_path: "/game/demonstration",
      });
      window.location.href = response.data.checkout_url;
    } catch {
      setError("We could not open checkout. Please try again.");
      setBusy(false);
    }
  };

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 820, margin: "0 auto", padding: "40px 20px 90px", textAlign: "center" }} data-testid="bfg-demonstration-page">
        <p className="bfg-eyebrow">SEE THE BOARD FUNDRAISING GAME IN ACTION</p>
        <h1 style={{ fontSize: "clamp(30px, 6vw, 48px)", lineHeight: 1.08 }}>See Exactly How You And Your Board Will Use The Platform</h1>
        <p style={{ margin: "16px auto 0", maxWidth: 650, fontSize: 17 }}>
          Watch Rooney take you through the Board Fundraising Game and show you how your board moves from a fundraising goal to a clear fundraising strategy, individual board roles and the tools needed to execute.
        </p>
        <div style={{ marginTop: 26 }}><GameVideo video={video} testId="bfg-demonstration-video" /></div>
        <div className="bfg-card" style={{ marginTop: 28, padding: 26 }}>
          <h2>Bring Your Board Into The Game</h2>
          <p style={{ marginTop: 12 }}>One organization. Your entire board. One-time payment.</p>
          <p style={{ marginTop: 18, fontFamily: "Outfit", fontWeight: 800, fontSize: 42, color: "#111827" }}>$497</p>
          {error && <p className="bfg-error" style={{ marginTop: 14 }}>{error}</p>}
          <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20, width: "100%", minHeight: 58, fontSize: 16 }}
            disabled={busy} onClick={buy} data-testid="bfg-demonstration-buy">
            {busy ? "Opening Secure Checkout…" : "START MY BOARD FUNDRAISING GAME — $497"}
          </button>
        </div>
      </main>
    </BfgShell>
  );
}
