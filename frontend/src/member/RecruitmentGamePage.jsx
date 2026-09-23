import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, ImagePlus, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { MemberShell } from "./MemberShell";
import { useMemberAuth } from "./MemberAuthContext";
import { memberApi } from "./api";
import { RecruitmentGameIntake } from "./RecruitmentGameIntake";
import "./sgr.css";

export default function RecruitmentGamePage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [stage, setStage] = useState("intro");
  const [branding, setBranding] = useState({ logo_data: "", primary_color: "", secondary_color: "" });
  const [assessment, setAssessment] = useState(null);
  const [brandingMessage, setBrandingMessage] = useState("");
  const [brandingBusy, setBrandingBusy] = useState(false);

  useEffect(() => {
    if (!loading && !member) navigate("/login?next=/app/board-recruitment/questions", { replace: true });
  }, [loading, member, navigate]);

  useEffect(() => {
    if (!member) return;
    memberApi.get("/workspace/branding")
      .then((response) => setBranding((current) => ({ ...current, ...(response.data.branding || {}) })))
      .catch(() => {});
    memberApi.get("/recruit/free/member-assessment/current")
      .then((response) => setAssessment(response.data))
      .catch(() => {});
  }, [member]);

  const completedCount = useMemo(() => {
    const answers = assessment?.answers || {};
    return ["mission","current_board","desired_board_members","support_needs","board_type","why_join"]
      .filter((key) => String(answers[key] || "").trim()).length;
  }, [assessment]);

  const chooseLogo = (event) => {
    const file = event.target.files?.[0];
    setBrandingMessage("");
    if (!file) return;
    if (!file.type.startsWith("image/")) { setBrandingMessage("Please choose an image file for your logo."); return; }
    if (file.size > 500000) { setBrandingMessage("Logo must be under 500KB."); return; }
    const reader = new FileReader();
    reader.onload = () => setBranding((current) => ({ ...current, logo_data: reader.result }));
    reader.readAsDataURL(file);
  };

  const saveLogo = async () => {
    setBrandingBusy(true); setBrandingMessage("");
    try {
      await memberApi.put("/workspace/branding", branding);
      setBrandingMessage("Organization logo saved.");
    } catch (error) {
      setBrandingMessage(error.response?.data?.detail || "We could not save your logo.");
    }
    setBrandingBusy(false);
  };

  const finish = () => navigate("/app/board-recruitment#br-section-identify", { replace: true });

  if (loading || !member) return null;

  return (
    <MemberShell>
      <main className="member-page sgr sgr-questions-page" data-testid="recruitment-questions-page">
        {stage === "intro" ? (
          <>
            <header className="sgr-questions-intro">
              <p className="eyebrow">SELF-GUIDED BOARD RECRUITMENT</p>
              <h1>Answer The Six Recruitment Questions</h1>
              <p>These six questions give us the context we need to understand the board you have, the board you want to build and the exact people your organization should recruit.</p>
            </header>

            <section className="member-card sgr-question-intro-card">
              <div className="sgr-question-intro-icon"><ShieldCheck size={28}/></div>
              <h2>Before We Identify Who You Need</h2>
              <p>We already know your organization name, your contact information and how many new board members you want to recruit. These questions help us understand the thinking behind that goal.</p>
              <div className="sgr-intro-points">
                <div><CheckCircle2 size={18}/><span>Your answers stay connected to this recruitment process.</span></div>
                <div><CheckCircle2 size={18}/><span>You can review and edit the board-member recommendations before approving them.</span></div>
                <div><CheckCircle2 size={18}/><span>Once the six questions are complete, the platform starts preparing the next stage underneath while you return to the dashboard.</span></div>
              </div>
            </section>

            <section className="member-card sgr-logo-card" data-testid="recruitment-questions-branding">
              <div className="sgr-logo-copy">
                <p className="eyebrow">YOUR ORGANIZATION</p>
                <h2>{assessment?.organization || "Add Your Organization Logo"}</h2>
                <p>Add your logo once. We will carry it into the Board Application and the branded recruitment resources that follow.</p>
              </div>
              <div className="sgr-logo-control">
                {branding.logo_data ? (
                  <img src={branding.logo_data} alt={`${assessment?.organization || "Organization"} logo`} />
                ) : (
                  <div className="sgr-logo-placeholder"><ImagePlus size={28}/><span>No logo added yet</span></div>
                )}
                <label className="button button-outline">
                  CHOOSE LOGO
                  <input type="file" accept="image/*" onChange={chooseLogo} hidden data-testid="recruitment-questions-logo-input"/>
                </label>
                {branding.logo_data && (
                  <button className="button button-outline" disabled={brandingBusy} onClick={saveLogo}>
                    {brandingBusy ? "SAVING…" : "SAVE LOGO"}
                  </button>
                )}
              </div>
              {brandingMessage && <p className="member-success">{brandingMessage}</p>}
            </section>

            <section className="sgr-question-start">
              <p>{completedCount ? `${completedCount} of 6 answers are already saved.` : "You will answer one question at a time."}</p>
              <button className="button" onClick={() => setStage("questions")} data-testid="start-six-recruitment-questions">
                {completedCount ? "CONTINUE MY SIX QUESTIONS" : "START THE SIX QUESTIONS"} <ArrowRight size={17}/>
              </button>
              <button className="button button-outline" onClick={() => navigate("/app/board-recruitment")}>RETURN TO DASHBOARD</button>
            </section>
          </>
        ) : (
          <section className="member-card sgr-question-stage">
            <RecruitmentGameIntake onComplete={finish}/>
          </section>
        )}
      </main>
    </MemberShell>
  );
}
