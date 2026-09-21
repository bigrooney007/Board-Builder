import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MemberShell } from "./MemberShell";
import { useMemberAuth } from "./MemberAuthContext";
import { RecruitmentGameIntake } from "./RecruitmentGameIntake";
import "./sgr.css";

export default function RecruitmentGamePage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  useEffect(() => {
    if (!loading && !member) navigate("/login?next=/app/board-recruitment/game", { replace: true });
  }, [loading, member, navigate]);
  if (loading || !member) return null;
  return <MemberShell><main className="member-page sgr sgr-game-page" data-testid="recruitment-game-page">
    <header className="member-page-heading"><p className="eyebrow">Board Recruitment Game</p><h1>IDENTIFY THE BOARD YOUR ORGANIZATION NEEDS</h1><p>Answer one question at a time. Your complete answers become the verified context used to identify the exact people your organization should recruit.</p></header>
    <section className="member-card sgr-game-card"><RecruitmentGameIntake onComplete={() => navigate("/app/board-recruitment#br-section-identify", { replace: true })} returnOnComplete /></section>
  </main></MemberShell>;
}
