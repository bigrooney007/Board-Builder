import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Globe } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard } from "./MaterialCard";
import { recruitmentModulesText, workspaceModulesText } from "../../content/appContent";

export const useMaterials = (applicationId = "") => {
  const [byType, setByType] = useState({});
  const [loaded, setLoaded] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const response = await memberApi.get("/workspace/materials", { params: applicationId ? { application_id: applicationId } : {} });
      const map = {};
      response.data.materials.forEach((material) => { if ((material.application_id || "") === applicationId) map[material.type] = material; });
      setByType(map);
    } catch { /* ignore */ }
    setLoaded(true);
  }, [applicationId]);
  useEffect(() => { refresh(); }, [refresh]);
  return { byType, refresh, loaded };
};

const CAMPAIGN_TOOLS = [
  ["board_recruitment_job_post", "Recruitment Job Post", "Generate My Recruitment Job Post", "Your primary professional board opportunity, ready for professional platforms such as LinkedIn Jobs, BoardSource, Idealist and VolunteerMatch. Your application link is inserted automatically."],
  ["recruitment_emails", "Recruitment Email", "Generate My Recruitment Email", "A professional email to send to your network, supporters, colleagues and community contacts inviting qualified people to consider the board opportunity."],
  ["social_posts", "Social Media Recruitment Post", "Generate My Social Media Recruitment Post", "A shareable recruitment post written as a real nonprofit recruitment announcement for your social channels, with your application call to action and link."],
  ["referral_request_email", "Referral Email", "Generate My Referral Email", "A ready-to-forward message your board members, supporters, partners and colleagues can send to people who may be a strong fit — with your application link included."],
];

const ApplicationPanel = ({ opportunity, coreQuestions, applicationSaved, onGenerate, busy }) => {
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState(false);
  const publicUrl = opportunity ? `/board-opportunities/${opportunity.slug}/apply` : "";

  return (
    <section className="workspace-panel" data-testid="application-editor">
      <h2>{recruitmentModulesText.h_yourBoardApplication}</h2>
      <p className="material-description">{recruitmentModulesText.d_yourHostedBoardApplicationIs}</p>
      {!applicationSaved && (
        <div className="material-actions">
          <button className="button" disabled={busy} onClick={onGenerate} data-testid="generate-board-application">
            {busy ? "GENERATING…" : "GENERATE MY BOARD APPLICATION FORM"}
          </button>
          {busy && <p className="workspace-note" data-testid="application-generation-wait">This may take a few minutes. If it isn't ready immediately, check back in about 5 minutes.</p>}
          <p className="workspace-note">Your saved organization name and logo are applied automatically to the public application.</p>
        </div>
      )}
      {applicationSaved && (
        <>
          {publicUrl && (
            <div className="material-actions">
              <code className="app-link-code" data-testid="application-link">{`${window.location.origin}${publicUrl}`}</code>
              <button className="button button-back" onClick={() => { navigator.clipboard?.writeText(`${window.location.origin}${publicUrl}`); setMessage("Application link copied."); }} data-testid="copy-application-link">Copy Application Link</button>
              <button className="button button-back" onClick={() => setPreview(!preview)} data-testid="preview-application-button">{preview ? "Hide Application" : "View Application"}</button>
            </div>
          )}
          {preview && (
            <div className="application-preview" data-testid="application-preview">
              <h3>Application Preview — {opportunity?.organization_name}</h3>
              {[...coreQuestions.map((q) => q.label + (q.required ? " *" : "")), "Upload résumé/CV *"].map((label) => (
                <div className="preview-question" key={label}><span>{label}</span><i /></div>
              ))}
            </div>
          )}
          <p className="material-meta">{workspaceModulesText.useThisLinkInYour}</p>
        </>
      )}
      {message && <p className="member-success">{message}</p>}
    </section>
  );
};

export const Module3Launch = ({ mode = "all" }) => {
  const { byType, refresh } = useMaterials();
  const [opportunity, setOpportunity] = useState(null);
  const [coreQuestions, setCoreQuestions] = useState([]);
  const [readiness, setReadiness] = useState({});
  const [preparation, setPreparation] = useState({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadOpportunity = useCallback(async () => {
    try {
      const response = await memberApi.get("/workspace/opportunity");
      setOpportunity(response.data.opportunity);
      setCoreQuestions(response.data.core_questions);
      setReadiness(response.data.readiness);
      setPreparation(response.data.preparation || {});
    } catch { /* ignore */ }
  }, []);
  useEffect(() => { loadOpportunity(); }, [loadOpportunity]);

  const refreshAll = async () => { await refresh(); await loadOpportunity(); };
  useEffect(() => {
    if (!["queued", "generating"].includes(preparation.status)) return undefined;
    const timer = window.setInterval(() => { refreshAll(); }, 4000);
    return () => window.clearInterval(timer);
  }, [preparation.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const generateApplication = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      await memberApi.post("/workspace/opportunity/application/generate");
      setMessage("Your Board Application is ready. Review the public form, then generate the four recruitment campaign materials below.");
      await loadOpportunity();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not generate the Board Application.");
    }
    setBusy(false);
  };

  const publish = async () => {
    if (!window.confirm("Launching will make your Board Application public and notify eligible professionals in the Nonprofit Board Builder Applicant Network about this opportunity.\n\nLaunch My Recruitment Campaign?")) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await memberApi.post("/workspace/opportunity/publish");
      setMessage("Your recruitment campaign is live.");
      await loadOpportunity();
    } catch (err) { setError(err.response?.data?.detail || "Could not launch the campaign."); }
    setBusy(false);
  };

  const closeCampaign = async () => {
    if (!window.confirm("Close this recruitment campaign? The application page will show Applications Closed. Existing applications and materials remain.")) return;
    try { await memberApi.post("/workspace/opportunity/close"); await loadOpportunity(); } catch (err) { setError(err.response?.data?.detail || "Could not close the campaign."); }
  };

  const publicUrl = opportunity ? `/board-opportunities/${opportunity.slug}/apply` : "";
  const launched = opportunity?.status === "Published";

  return (
    <div data-testid="module3-workspace">
      {mode !== "launch" && (
        <>
          <ApplicationPanel opportunity={opportunity} coreQuestions={coreQuestions} applicationSaved={!!readiness.application_saved} onGenerate={generateApplication} busy={busy} />
          {readiness.application_saved ? (
            <>
              <section className="workspace-panel" data-testid="campaign-materials">
                <h2>{recruitmentModulesText.h_yourRecruitmentCampaignMaterials}</h2>
                <p className="material-description">{recruitmentModulesText.d_eachResourceIsCreatedFrom}</p>
              </section>
              {CAMPAIGN_TOOLS.map(([type, title, buttonLabel, description]) => (
                <MaterialCard key={type} type={type} title={title} buttonLabel={buttonLabel} description={description} material={byType[type]} refresh={refreshAll} approvable />
              ))}
            </>
          ) : (
            <section className="workspace-panel">
              <p className="workspace-note">Generate your Board Application first. Your job post, recruitment email, social media post and referral email will then use the same application link.</p>
            </section>
          )}
        </>
      )}

      {mode !== "materials" && <section className="workspace-panel publish-panel" data-testid="publish-panel">
        <h2>{recruitmentModulesText.h_launchMyRecruitmentCampaign}</h2>
        <p className="material-description">{recruitmentModulesText.d_launchingIsTheOnlyAction}</p>
        <p>Status: <strong className={`opportunity-status status-${(opportunity?.status || "Draft").replace(/\s/g, "-").toLowerCase()}`} data-testid="opportunity-status">{launched ? "Live" : opportunity?.status || "Draft"}</strong></p>
        <ul className="readiness-list">
          <li className={readiness.application_saved ? "done" : ""} data-testid="readiness-application">Board Application created</li>
          <li className={readiness.materials_generated ? "done" : ""} data-testid="readiness-materials">Campaign materials prepared ({readiness.materials_count || 0} of {readiness.materials_total || 4})</li>
          <li className={readiness.materials_approved ? "done" : ""} data-testid="readiness-materials-approved">Campaign materials approved ({readiness.materials_approved_count || 0} of {readiness.materials_total || 4})</li>
        </ul>
        {launched && (
          <div className="member-success" data-testid="published-info">
            <h3>{recruitmentModulesText.h_yourRecruitmentCampaignIsLive}</h3>
            <p>{workspaceModulesText.yourBoardApplicationIsReady}</p>
            <p>Launched {opportunity.published_at && new Date(opportunity.published_at).toLocaleString()}. Network announcement {opportunity.broadcast_status || "Initiated"} ({opportunity.broadcast_mode === "test" ? "delivered as an internal preview to the program owner" : "delivered to eligible Applicant Network members"}).
              <br /><a href={publicUrl} target="_blank" rel="noreferrer"><Globe size={13} /> {publicUrl} <ExternalLink size={12} /></a></p>
            <Link className="button" to="/app/board-recruitment#br-section-applicants" data-testid="continue-to-applicants">CONTINUE TO APPLICANTS</Link>
          </div>
        )}
        {message && <p className="member-success">{message}</p>}
        {error && <p className="submit-error" data-testid="publish-error">{error}</p>}
        <div className="material-actions">
          {!launched && opportunity?.status !== "Closed" && (
            <button className="button" disabled={busy || !(readiness.application_saved && readiness.materials_approved)} onClick={publish} data-testid="publish-button">{workspaceModulesText.launchMyRecruitmentCampaign}</button>
          )}
          {launched && <button className="button button-back" onClick={closeCampaign} data-testid="close-campaign-button">Close Recruitment Campaign</button>}
          {opportunity?.status === "Closed" && <p className="workspace-note">{recruitmentModulesText.n_thisCampaignIsClosedApplications}</p>}
        </div>
        <p className="material-meta">{workspaceModulesText.launchingMakesTheApplicationPublic}<Link to={publicUrl}>{publicUrl || "…"}</Link>{workspaceModulesText.launchAnnouncementNote}</p>
      </section>}
    </div>
  );
};

export const RecruitmentMaterials = () => <Module3Launch mode="materials" />;
export const RecruitmentCampaignLaunch = () => <Module3Launch mode="launch" />;
