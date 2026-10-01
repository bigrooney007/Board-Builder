import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
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
    else navigate("/recruit", { replace: true });
  }, [token, navigate]);

  return <BfgShell><main className="member-page sgr sgr-questions-page" style={{ maxWidth: 820, margin: "0 auto", padding: "36px 20px 70px" }}>
    <p className="eyebrow">BOARD RECRUITMENT · YOUR ANSWERS SAVE AS YOU GO</p>
    <RecruitmentGameIntake publicToken={token} onComplete={() => navigate(`/recruit/walkthrough?token=${encodeURIComponent(token)}`)} />
    <p style={{ marginTop: 24 }}><Link to="/recruit">Back to Board Recruitment</Link></p>
  </main></BfgShell>;
}
