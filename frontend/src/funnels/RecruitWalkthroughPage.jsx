import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import TrackedYouTubeVideo from "@/clean/TrackedYouTubeVideo";
import { trackPlatformEvent, usePlatformVideo } from "@/clean/platform";
import "@/game/game.css";
import "@/game/guided-flow.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const QUESTION_KEYS = ["mission", "current_board", "desired_board_members", "board_type", "support_needs", "why_join"];

export default function RecruitWalkthroughPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [busy, setBusy] = useState(false);
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
    setBusy(true); setError("");
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
      setBusy(false);
    }
  };

  const payButton = (id) => <button type="button" className="bfg-btn bfg-btn-primary guided-action" disabled={busy || !assessment}
    onClick={buy} data-testid={id}>{busy ? "OPENING SECURE CHECKOUT…" : "BUILD MY BOARD RECRUITMENT CAMPAIGN — $497"}</button>;

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
      {error && <p className="bfg-error" role="alert">{error}</p>}
      {payButton("recruit-checkout-button-bottom")}
      <p><button type="button" className="bfg-btn bfg-btn-ghost" onClick={() => navigate(`/recruit/questions?token=${encodeURIComponent(assessment.token)}`)}>Review my six answers</button></p>
    </section>}
  </main></BfgShell>;
}
