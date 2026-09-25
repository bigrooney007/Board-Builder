import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import TrackedYouTubeVideo from "@/clean/TrackedYouTubeVideo";
import { trackPlatformEvent, usePlatformVideo } from "@/clean/platform";
import DemoOfferCards from "@/components/DemoOfferCards";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import "@/game/game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE = process.env.REACT_APP_BACKEND_URL;

export default function RecruitWalkthroughPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const video = usePlatformVideo("recruitment_demonstration");
  const audioRef = useRef(null);

  useEffect(() => {
    document.title = "Board Recruitment Options | Nonprofit Board Builder";
    const emailedToken = searchParams.get("token") || "";
    if (emailedToken) localStorage.setItem("recruitFreeToken", emailedToken);
    const token = emailedToken || localStorage.getItem("recruitFreeToken");
    if (!token) { navigate("/recruit", { replace: true }); return undefined; }
    axios.post(`${API}/recruit/free/${token}/event`, { event: "video_page_viewed" }).catch(() => {});
    axios.get(`${API}/game/voice/tutorial/recruitment-free`).then((r) => {
      const clip = (r.data.clips || {})["recruitment-free-video-page"];
      if (clip?.ready) {
        const audio = new Audio(`${BASE}${clip.url}`);
        audioRef.current = audio;
        audio.play().catch(() => {});
      }
    }).catch(() => {});
    return () => { if (audioRef.current) audioRef.current.pause(); };
  }, [navigate, searchParams]);

  const buy = async (pathway = "self-guided") => {
    setBusy(pathway); setError("");
    if (audioRef.current) audioRef.current.pause();
    const token = localStorage.getItem("recruitFreeToken");
    try {
      let leadId = "";
      if (token) {
        await axios.post(`${API}/recruit/free/${token}/event`, { event: "checkout_started" }).catch(() => {});
        trackPlatformEvent("recruitment", "checkout_started");
        const assessment = await axios.get(`${API}/recruit/free/${token}`);
        leadId = assessment.data.lead_id || "";
      }
      if (!leadId) { navigate("/recruit"); return; }
      const response = pathway === "supported"
        ? await axios.post(`${API}/payments/supported-checkout`, {
          product: "recruitment", origin_url: window.location.origin, result_token: token || "",
        }, { withCredentials: true })
        : await axios.post(`${API}/payments/checkout`, {
          lead_id: leadId, tier: "497", origin_url: window.location.origin,
        }, { withCredentials: true });
      window.location.href = response.data.checkout_url;
    } catch (err) {
      setError(err.response?.status === 403 ? "Program Access Opening Soon" : "We could not open checkout. Please try again.");
      setBusy("");
    }
  };

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 1120, margin: "0 auto", padding: "40px 20px 90px", textAlign: "center" }} data-testid="recruit-walkthrough-page">
        <h1 style={{ fontSize: "clamp(30px, 6vw, 48px)", lineHeight: 1.08, maxWidth: 680, margin: "0 auto" }} data-testid="recruit-walkthrough-heading">
          See How To Recruit The Board Members Your Organization Needs Yourself
        </h1>
        <p style={{ marginTop: 18, fontWeight: 800, fontSize: 18, color: "#111827" }}>Press Play and Watch The Short Video</p>
        <div style={{ marginTop: 18 }}>
          <TrackedYouTubeVideo video={video} flow="recruitment" testId="recruit-walkthrough-video" title="Board Recruitment Demonstration" placeholder="Demonstration video has not been added yet." />
        </div>

        <DemoOfferCards product="recruitment" busy={busy} onBuy={buy} error={error}
          selfGuided={{
            title:"Recruit The Board Members You Need Using The Platform",
            description:"Get the complete self-guided recruitment system and execute it with confidence.",
            features:["Follow the recruitment process step by step","Use the application, campaign, interview, reference and onboarding tools","Get instructions and real-time support as you execute","Recruit and onboard the Board Members your organization needs"],
            guarantee:"Complete the guided process. If the platform does not help you produce and launch a usable Board recruitment campaign, tell us and we will refund 100% of your purchase.",
            button:"START MY SELF-GUIDED RECRUITMENT — $497",
          }}
          supported={{
            title:"Launch Your Board Recruitment With Rooney",
            description:"Rooney works directly with you to move the recruitment from planning through onboarding.",
            features:["Launch the Board recruitment campaign with you","Support the interview and selection process","Guide reference checks and final decisions","Help you onboard the Board Members you select"],
            price:"$2,997", button:"WORK WITH ROONEY — $2,997",
          }}/>
        <TestimonialCarousel heading="What Nonprofit Leaders We Have Worked With Are Saying" idPrefix="recruitment-demo"/>
      </main>
    </BfgShell>
  );
}
