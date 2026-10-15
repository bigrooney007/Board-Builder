import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MemberShell } from "./MemberShell";
import { useMemberAuth } from "./MemberAuthContext";
import { memberApi } from "./api";
import { Module3Launch } from "./workspace/WorkspaceModules";
import "./sgr.css";

// This is the existing materials and launch UI, moved to its own page after scheduling.
export default function RecruitCampaignMaterialsPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [readiness, setReadiness] = useState(null);
  const [preparation, setPreparation] = useState({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const { data } = await memberApi.get("/workspace/opportunity");
    setReadiness(data.readiness || {});
    setPreparation(data.preparation || {});
    if (["Published", "Closed"].includes(data.opportunity?.status)) {
      navigate("/app/board-recruitment#br-section-applicants", { replace: true });
    }
  }, [navigate]);

  useEffect(() => {
    if (loading) return;
    if (!member) {
      navigate("/login?next=/app/board-recruitment/setup/materials", { replace: true });
      return;
    }
    load().catch((err) => setError(err.response?.data?.detail || "Could not load your recruitment materials."));
  }, [member, loading, load, navigate]);

  useEffect(() => {
    if (!readiness || (readiness.profiles_approved && readiness.scheduling_saved)) return;
    navigate("/app/board-recruitment/setup", { replace: true });
  }, [readiness, navigate]);

  if (loading || !member) return null;

  return <MemberShell><main className="member-page sgr sgr-recruitment-machine" data-testid="recruitment-campaign-materials-page">
    <header className="sgr-dashboard-hero">
      <p className="eyebrow">YOUR BOARD RECRUITMENT CAMPAIGN</p>
      <h1>Review Your Resources And Launch Your Campaign</h1>
      <p>Review and approve the application and recruitment materials prepared from your board profiles. When they are ready, launch your campaign below.</p>
    </header>
    {error && <p className="submit-error" role="alert">{error}</p>}
    {readiness?.profiles_approved && readiness?.scheduling_saved && <>
      <section className="member-card" data-testid="recruitment-campaign-review">
        <p className="eyebrow">STEP 3 · REVIEW CAMPAIGN MATERIALS</p>
        <h2>Your Application And Recruitment Copy</h2>
        <p>These drafts use your approved board profiles and application link. Edit and approve each before launch.
          Preparation: {preparation.status || "queued"}{preparation.stage ? ` (${preparation.stage})` : ""}.
        </p>
        <Module3Launch mode="materials" />
      </section>
      <section className="member-card" data-testid="recruitment-campaign-launch">
        <p className="eyebrow">STEP 4 · LAUNCH</p>
        <h2>Publish Your Board Opportunity</h2>
        <p>After approving the required resources, launch the campaign here. The original platform will handle the application form and applicant notifications.</p>
        <Module3Launch mode="launch" onLaunched={() => navigate("/app/board-recruitment#br-section-applicants")} />
      </section>
    </>}
  </main></MemberShell>;
}
