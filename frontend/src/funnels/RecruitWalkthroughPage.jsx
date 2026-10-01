import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import TrackedYouTubeVideo from "@/clean/TrackedYouTubeVideo";
import DemoOfferCards from "@/components/DemoOfferCards";
import { trackPlatformEvent, usePlatformVideo } from "@/clean/platform";
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
  const video = usePlatformVideo("recruitment_upgrade");

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
      <p className="guided-kicker">YOUR SIX ANSWERS ARE SAVED</p>
      <h1 data-testid="recruit-walkthrough-heading">Now let's recruit the board members your organization needs.</h1>
      <p className="guided-upgrade-copy">You told us about {assessment.organization || "your organization"}, the board you have and where you need stronger support. Those answers will guide the board member profiles and campaign materials we build with you.</p>
      <div className="guided-video" data-testid="recruit-upgrade-video">
        <TrackedYouTubeVideo video={video} flow="recruitment" testId="recruit-walkthrough-video"
          title="A message from Rooney before you launch your recruitment campaign"
          placeholder="A short message from Rooney will appear here." />
      </div>
      {payButton("recruit-checkout-button")}
      <p className="guided-price-note">One-time payment. Payment is next.</p>
      <div className="guided-outcomes">
        <p><strong>First,</strong> review and approve the board profiles your organization needs.</p>
        <p><strong>Then,</strong> use your application, outreach and social posts to launch your campaign.</p>
        <p><strong>As people apply,</strong> manage interviews, checks, offers and onboarding in your existing dashboard.</p>
      </div>
      <DemoOfferCards product="recruitment" busy={busy} onBuy={(choice) => choice === "supported" ? supported() : buy()} error={error}
        intro="Launch the campaign with the complete platform, or work directly with Rooney to identify, attract and onboard the board members you need."
        selfGuided={{ title: "Launch Your Board Recruitment Campaign", description: "Use the complete platform to recruit and onboard the board members your organization needs.",
          features: ["Identify and approve the board member profiles", "Create your application and recruitment messages", "Launch the campaign and manage applicants", "Interview, make offers and onboard new members"],
          button: "START MY CAMPAIGN — $497" }}
        supported={{ title: "Recruit Your Board With Rooney", description: "Work directly with Rooney to shape the campaign and move the right people through recruitment.",
          features: ["Identify the board capability you need", "Prepare your recruitment campaign together", "Guide selection and onboarding decisions", "Get direct support through the process"],
          price: "$2,997", button: "WORK WITH ROONEY — $2,997" }} />
      {error && <p className="bfg-error" role="alert">{error}</p>}
      {payButton("recruit-checkout-button-bottom")}
      <p><button type="button" className="bfg-btn bfg-btn-ghost" onClick={() => navigate(`/recruit/questions?token=${encodeURIComponent(assessment.token)}`)}>Review my six answers</button></p>
    </section>}
  </main></BfgShell>;
}
