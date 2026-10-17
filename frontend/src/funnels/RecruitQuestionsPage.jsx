import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PUBLIC_START_ROUTES } from "./publicStartRoutes";
import { BfgShell } from "@/game/gameShared";
import { RecruitmentGameIntake } from "@/member/RecruitmentGameIntake";
import "@/member/sgr.css";

export default function RecruitQuestionsPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || localStorage.getItem("recruitFreeToken") || "";
  useEffect(() => {
    document.title = "Your Board Recruitment Assessment | Nonprofit Board Builder";
    if (token) localStorage.setItem("recruitFreeToken", token);
    else navigate(PUBLIC_START_ROUTES.recruitment, { replace: true });
  }, [token, navigate]);

  return <BfgShell><main className="member-page sgr sgr-questions-page" style={{ maxWidth: 820, margin: "0 auto", padding: "36px 20px 70px" }}>
    <RecruitmentGameIntake publicToken={token} onComplete={() => navigate(`/recruit/walkthrough?token=${encodeURIComponent(token)}`)} />
  </main></BfgShell>;
}
