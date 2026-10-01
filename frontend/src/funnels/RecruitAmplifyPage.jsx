import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RecruitAmplifyPage() {
  const [params] = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [paid, setPaid] = useState(false);
  const [error, setError] = useState("");
  const token = params.get("token") || "";
  const sessionId = params.get("session_id") || "";
  useEffect(() => {
    document.title = "Amplify My Board Recruitment Campaign | Nonprofit Board Builder";
    if (!sessionId) return;
    axios.get(`${API}/payments/status/${encodeURIComponent(sessionId)}`)
      .then(({ data }) => setPaid(data.payment_status === "paid"))
      .catch(() => setError("We could not confirm this payment yet. Please check back shortly."));
  }, [sessionId]);
  const checkout = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await axios.post(`${API}/payments/amplify-checkout`, { token });
      window.location.assign(data.checkout_url);
    } catch (err) { setError(err.response?.data?.detail || "We could not open Stripe checkout. Please try again."); setBusy(false); }
  };
  return <BfgShell><main className="bfg-flow" style={{ maxWidth: 680, margin: "0 auto", padding: "60px 20px" }} data-testid="recruit-amplify-page">
    <h1>{paid ? "Your Campaign Amplification Is Confirmed" : "Amplify My Recruitment Campaign"}</h1>
    {paid ? <p>We have received your payment. Our team has been notified and will handle the additional promotion of your live campaign.</p> : <>
      <p>Reach a larger pool of potential board candidates through additional promotional channels. Your existing Board Applicant Marketplace listing remains live.</p>
      <h2>Amplify My Campaign: $497</h2>
      {token && <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={checkout}>{busy ? "OPENING STRIPE…" : "CONTINUE TO SECURE STRIPE CHECKOUT"}</button>}
      {!token && !sessionId && <p>This campaign link is not available.</p>}
      {params.get("cancelled") && <p>Your checkout was cancelled. You can return whenever you are ready.</p>}
    </>}
    {error && <p className="bfg-error" role="alert">{error}</p>}
    <p><Link to="/app/board-recruitment">Return to my recruitment dashboard</Link></p>
  </main></BfgShell>;
}
