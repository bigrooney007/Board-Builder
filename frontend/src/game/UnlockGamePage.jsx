import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { BfgShell } from "./gameShared";

export default function UnlockGamePage() {
  const navigate = useNavigate();
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
        <div className="bfg-card" style={{ marginTop: 26, padding: 26 }}>
          <p style={{ fontFamily: "Outfit", fontWeight: 800, fontSize: 42, color: "#111827" }}>$497 ONE-TIME</p>
          <p style={{ marginTop: 10 }}>One organization.</p>
          <p>Your entire board.</p>
          <p>No subscription.</p>
        </div>
        {error && <p className="bfg-error" style={{ marginTop: 14 }} data-testid="bfg-unlock-error">{error}</p>}
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26, fontSize: 17 }} disabled={busy}
          onClick={unlock} data-testid="bfg-unlock-cta">
          {busy ? "Opening Checkout…" : "UNLOCK MY BOARD FUNDRAISING GAME - $497"}
        </button>
        <p style={{ marginTop: 18 }}>
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/dashboard")} data-testid="bfg-unlock-later">Not now</button>
        </p>
      </main>
    </BfgShell>
  );
}
