import { useEffect, useState } from "react";
import axios from "axios";
import { BfgShell } from "./gameShared";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function FacilitatedGamePage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { document.title = "Facilitated Board Fundraising Game"; }, []);

  const buy = async () => {
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/payments/facilitated-game-checkout`, {
        origin_url: window.location.origin, cancel_path: "/organize-board-fundraising-game",
      });
      window.location.href = response.data.checkout_url;
    } catch {
      setError("We could not open checkout. Please try again.");
      setBusy(false);
    }
  };

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 760, margin: "0 auto", padding: "40px 20px 90px" }} data-testid="bfg-facilitated-page">
        {/* EXACT LANDING PAGE COPY — provided separately, inserted word for word. */}
        <div data-testid="bfg-facilitated-copy">
          <h1>FACILITATED BOARD FUNDRAISING GAME</h1>
          <p style={{ marginTop: 16, fontFamily: "Outfit", fontWeight: 800, fontSize: 34, color: "#111827" }}>$3,497 ONE-TIME</p>
          <p style={{ marginTop: 14 }}>Do you want us to organize the Board Fundraising Game for your organization?</p>
        </div>
        {error && <p className="bfg-error" style={{ marginTop: 14 }}>{error}</p>}
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26, fontSize: 17 }} disabled={busy}
          onClick={buy} data-testid="bfg-facilitated-cta">
          {busy ? "Opening Checkout…" : "ORGANIZE MY BOARD FUNDRAISING GAME - $3,497"}
        </button>
      </main>
    </BfgShell>
  );
}
