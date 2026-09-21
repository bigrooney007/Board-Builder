import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MemberShell } from "./MemberShell";
import { useMemberAuth } from "./MemberAuthContext";
import { memberApi } from "./api";
import { RecruitmentGameIntake } from "./RecruitmentGameIntake";
import "./sgr.css";

export default function RecruitmentGamePage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [branding, setBranding] = useState({ logo_data: "", primary_color: "", secondary_color: "" });
  const [organizationName, setOrganizationName] = useState("");
  const [brandingMessage, setBrandingMessage] = useState("");
  const [brandingBusy, setBrandingBusy] = useState(false);

  useEffect(() => {
    if (!loading && !member) navigate("/login?next=/app/board-recruitment/game", { replace: true });
  }, [loading, member, navigate]);

  useEffect(() => {
    if (!member) return;
    memberApi.get("/workspace/branding").then((response) => setBranding((current) => ({ ...current, ...(response.data.branding || {}) }))).catch(() => {});
    memberApi.get("/recruit/free/member-assessment/current").then((response) => setOrganizationName(response.data.organization || "")).catch(() => {});
  }, [member]);

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
      setBrandingMessage("Logo saved. It will be used on your Board Application and branded recruitment resources.");
    } catch (error) {
      setBrandingMessage(error.response?.data?.detail || "We could not save your logo.");
    }
    setBrandingBusy(false);
  };

  if (loading || !member) return null;
  return <MemberShell><main className="member-page sgr sgr-game-page" data-testid="recruitment-game-page">
    <header className="member-page-heading">
      <p className="eyebrow">Board Recruitment Game</p>
      <h1>IDENTIFY THE BOARD YOUR ORGANIZATION NEEDS</h1>
      <p>Answer one question at a time. Your complete answers become the verified context used to identify the exact people your organization should recruit.</p>
    </header>

    <section className="member-card sgr-game-card" data-testid="recruitment-game-branding">
      <p className="eyebrow">YOUR ORGANIZATION</p>
      <h2>{organizationName || "Add Your Organization Logo"}</h2>
      <p>Your organization name is already saved from the Recruitment homepage. Add your logo here so the Board Application and branded recruitment resources can carry your identity.</p>
      <label className="field">
        <span>Organization Logo <small>(optional if you do not have one)</small></span>
        <input type="file" accept="image/*" onChange={chooseLogo} data-testid="recruitment-game-logo-input" />
      </label>
      {branding.logo_data && <img src={branding.logo_data} alt={`${organizationName || "Organization"} logo`} style={{ maxHeight: 72, maxWidth: 220, objectFit: "contain", marginTop: 10 }} />}
      <div className="sgr-row-actions">
        <button className="button button-small button-outline" disabled={brandingBusy || !branding.logo_data} onClick={saveLogo} data-testid="recruitment-game-save-logo">
          {brandingBusy ? "SAVING…" : "SAVE ORGANIZATION LOGO"}
        </button>
      </div>
      {brandingMessage && <p className="member-success">{brandingMessage}</p>}
    </section>

    <section className="member-card sgr-game-card">
      <RecruitmentGameIntake onComplete={() => navigate("/app/board-recruitment#br-section-identify", { replace: true })} returnOnComplete />
    </section>
  </main></MemberShell>;
}
