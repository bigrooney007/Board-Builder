import { useEffect, useState } from "react";
import { memberApi } from "@/member/api";
import { BfgShell } from "./gameShared";

export default function UnlockGamePage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { document.title = "Unlock Your Board Fundraising Game"; }, []);

  const unlock = async () => {
    setBusy(true); setError("");
    try {
      const response = await memberApi.post("/payments/game-checkout", {
        origin_url: window.location.origin, cancel_path: "/game/unlock",
      });
      window.location.href = response.data.checkout_url;
    } catch {
      setError("We could not open checkout. Please try again.");
      setBusy(false);
    }
  };

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 620, margin: "0 auto", padding: "40px 20px 80px", textAlign: "center" }} data-testid="bfg-unlock-page">
        <h1 data-testid="bfg-unlock-heading">UNLOCK YOUR BOARD FUNDRAISING GAME</h1>
        <p style={{ marginTop: 16, fontSize: 17 }}>Watch how the complete Board Fundraising Game works, then unlock it for your organization.</p>
        <div style={{ marginTop: 26, aspectRatio: "16 / 9", background: "#0F172A", borderRadius: 16, display: "grid", placeItems: "center" }} data-testid="bfg-unlock-video-slot"><p style={{ color: "#94A3B8", fontSize: 14 }}>Board Fundraising Game video</p></div>
        <div className="bfg-card" style={{ marginTop: 26, padding: 26, textAlign: "left" }}>
          <h2 style={{ textAlign: "center" }}>Turn The Ideas You Just Created Into Your Board's Fundraising System</h2>
          <p style={{ marginTop: 18 }}>✓ <strong>Bring your entire board into the game</strong> so fundraising is no longer sitting with one person.</p>
          <p style={{ marginTop: 12 }}>✓ <strong>Capture and combine everyone's fundraising ideas</strong> into one working strategy for your organization.</p>
          <p style={{ marginTop: 12 }}>✓ <strong>Build the strategy together during Game Night</strong> so your board understands it, helps decide it and is ready to execute it.</p>
          <p style={{ marginTop: 12 }}>✓ <strong>Give every board member a clear fundraising role</strong> based on how they said they can contribute.</p>
          <p style={{ marginTop: 12 }}>✓ <strong>Leave with the strategy, tools and execution system</strong> your board needs to start raising money together.</p>
          <p style={{ marginTop: 24, textAlign: "center", fontFamily: "Outfit", fontWeight: 800, fontSize: 42, color: "#111827" }}>$497 ONE-TIME</p>
          <p style={{ marginTop: 8, textAlign: "center" }}>One organization. Your entire board. No subscription.</p>
        </div>
        {error && <p className="bfg-error" style={{ marginTop: 14 }} data-testid="bfg-unlock-error">{error}</p>}
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26, fontSize: 17 }} disabled={busy}
          onClick={unlock} data-testid="bfg-unlock-cta">
          {busy ? "Opening Checkout…" : "UNLOCK MY BOARD FUNDRAISING GAME - $497"}
        </button>
      </main>
    </BfgShell>
  );
}
