import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import DemoOfferCards from "@/components/DemoOfferCards";
import { trackPlatformEvent, useHomepageContent } from "@/clean/platform";
import { OFFER_TEXT_DEFAULTS } from "@/content/offerTextDefaults";
import OfferTextRoadmap from "./OfferTextRoadmap";
import "@/game/game.css";
import "@/game/guided-flow.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const QUESTION_KEYS = ["mission", "current_board", "desired_board_members", "board_type", "support_needs", "why_join"];

export default function RecruitWalkthroughPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [assessment, setAssessment] = useState(null);
  const copy = useHomepageContent("offer-recruitment", OFFER_TEXT_DEFAULTS["offer-recruitment"]);

  useEffect(() => {
    document.title = "Unlock Your Board Recruitment Campaign | Nonprofit Board Builder";
    const emailedToken = searchParams.get("token") || "";
    if (emailedToken) localStorage.setItem("recruitFreeToken", emailedToken);
    const token = emailedToken || localStorage.getItem("recruitFreeToken");
    if (!token) { navigate("/recruit", { replace: true }); return undefined; }
    axios.get(`${API}/recruit/free/${token}`).then(({ data }) => {
      setAssessment(data);
      if (QUESTION_KEYS.some((key) => !String(data.answers?.[key] || "").trim())) {
        navigate(`/recruit/questions?token=${encodeURIComponent(token)}`, { replace: true });
      }
    }).catch(() => navigate("/recruit", { replace: true }));
  }, [navigate, searchParams]);

  const buy = async () => {
    setBusy("self-guided"); setError("");
    const token = localStorage.getItem("recruitFreeToken");
    try {
      await axios.post(`${API}/recruit/free/${token}/event`, { event: "checkout_started" }).catch(() => {});
      trackPlatformEvent("recruitment", "checkout_started");
      const response = await axios.post(`${API}/payments/checkout`, {
        lead_id: assessment.lead_id, tier: "497", origin_url: window.location.origin,
      }, { withCredentials: true });
      window.location.href = response.data.checkout_url;
    } catch (err) {
      setError(err.response?.data?.detail || "We could not open checkout. Please try again.");
      setBusy("");
    }
  };

  const supported = async () => {
    setBusy("supported"); setError("");
    try {
      trackPlatformEvent("recruitment", "checkout_started");
      const response = await axios.post(`${API}/payments/supported-checkout`, {
        origin_url: window.location.origin, product: "recruitment", result_token: assessment.token,
      });
      window.location.href = response.data.checkout_url;
    } catch (err) { setError(err.response?.data?.detail || "We could not open checkout. Please try again."); setBusy(""); }
  };

  const payButton = (id) => <button type="button" className="bfg-btn bfg-btn-primary guided-action" disabled={busy || !assessment}
    onClick={buy} data-testid={id}>{busy === "self-guided" ? "OPENING SECURE CHECKOUT…" : "BUILD MY BOARD RECRUITMENT CAMPAIGN — $497"}</button>;

  return <BfgShell><main className="guided-flow" data-testid="recruit-walkthrough-page">
    {!assessment ? <p className="guided-loading">Opening your recruitment campaign…</p> : <section className="guided-recruit-upgrade">
      <p className="guided-kicker">{copy.eyebrow}</p>
      <h1 data-testid="recruit-walkthrough-heading">{copy.heading}</h1>
      <OfferTextRoadmap copy={copy} />
      {payButton("recruit-checkout-button")}
      <p className="guided-price-note">One-time payment. Payment is next.</p>

      <DemoOfferCards product="recruitment" busy={busy} onBuy={(choice) => choice === "supported" ? supported() : buy()} error={error}
        intro={copy.cardIntro}
        selfGuided={{ title: copy.selfGuidedTitle, description: copy.selfGuidedDescription,
          features: copy.selfGuidedFeatures,
          button: "START MY CAMPAIGN — $497" }}
        supported={{ title: copy.supportedTitle, description: copy.supportedDescription,
          features: copy.supportedFeatures,
          price: "$2,997", button: "WORK WITH ROONEY — $2,997" }} />
      {error && <p className="bfg-error" role="alert">{error}</p>}
      {payButton("recruit-checkout-button-bottom")}
      <p><button type="button" className="bfg-btn bfg-btn-ghost" onClick={() => navigate(`/recruit/questions?token=${encodeURIComponent(assessment.token)}`)}>Review my six answers</button></p>
    </section>}
  </main></BfgShell>;
}
