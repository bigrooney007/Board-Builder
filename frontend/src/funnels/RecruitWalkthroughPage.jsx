import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import TrackedYouTubeVideo from "@/clean/TrackedYouTubeVideo";
import { trackPlatformEvent, usePlatformVideo } from "@/clean/platform";
import "@/game/game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const QUESTION_KEYS = ["mission", "current_board", "desired_board_members", "board_type", "support_needs", "why_join"];

export default function RecruitWalkthroughPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [assessment, setAssessment] = useState(null);
  const [showVideo, setShowVideo] = useState(false);
  const video = usePlatformVideo("recruitment_demonstration");

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

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 850, margin: "0 auto", padding: "40px 20px 90px" }} data-testid="recruit-walkthrough-page">
        <p className="eyebrow">YOUR SIX ANSWERS ARE SAVED</p>
        <h1 data-testid="recruit-walkthrough-heading">Your Board Recruitment Assessment Is Complete</h1>
        <p>We now have the context to identify the board members {assessment?.organization || "your organization"} needs. Unlock your campaign to see the exact recommended profiles, review materials built for your organization and launch your recruitment campaign in the next 30 minutes.</p>
        <h2>What happens after you unlock</h2>
        <ol>
          <li>See why each recommended board profile matters to your organization and approve or edit your list.</li>
          <li>Review your board application, opportunity, outreach emails, social posts, overview, manual and onboarding resources.</li>
          <li>Launch to the Board Applicant Marketplace and Applicant Network. Use the same materials on LinkedIn and your own channels.</li>
          <li>Manage applicants, candidate-specific interviews, checks, offers and onboarding from your dashboard.</li>
        </ol>
        {error && <p className="bfg-error" role="alert">{error}</p>}
        <button type="button" className="bfg-btn bfg-btn-primary" disabled={busy || !assessment} onClick={buy} data-testid="recruit-checkout-button">{busy ? "OPENING CHECKOUT…" : "UNLOCK MY RECRUITMENT CAMPAIGN — $497"}</button>
        <p><button type="button" className="bfg-btn bfg-btn-ghost" onClick={() => navigate(`/recruit/questions?token=${encodeURIComponent(assessment?.token || "")}`)}>Review my saved answers</button></p>
        <section style={{ marginTop: 35 }}><button type="button" className="bfg-btn bfg-btn-ghost" onClick={() => setShowVideo(!showVideo)}>{showVideo ? "Hide" : "Watch"} the optional recruitment demonstration</button>
          {showVideo && <TrackedYouTubeVideo video={video} flow="recruitment" testId="recruit-walkthrough-video" title="Board Recruitment Demonstration" placeholder="Demonstration video has not been added yet." />}
        </section>
      </main>
    </BfgShell>
  );
}
