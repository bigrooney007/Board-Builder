import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Globe, PlayCircle } from "lucide-react";
import { useRecruitmentSectionVideo } from "@/clean/platform";
import { memberApi } from "../api";
import { MaterialCard } from "./MaterialCard";
import { recruitmentModulesText, workspaceModulesText } from "../../content/appContent";

export const useMaterials = (applicationId = "") => {
  const [byType, setByType] = useState({});
  const [loaded, setLoaded] = useState(false);
  const load = useCallback(async () => {
    try {
      const response = await memberApi.get("/workspace/materials", { params: applicationId ? { application_id: applicationId } : {} });
      const map = {};
      response.data.materials.forEach((material) => { if ((material.application_id || "") === applicationId) map[material.type] = material; });
      setByType(map);
    } catch { /* ignore */ }
    setLoaded(true);
  }, [applicationId]);
  const refresh = useCallback(async () => {
    await load();
    window.dispatchEvent(new CustomEvent("recruitment-materials-changed", { detail: { applicationId } }));
  }, [load, applicationId]);
  useEffect(() => {
    load();
    const onChanged = (event) => { if (event.detail?.applicationId === applicationId) load(); };
    window.addEventListener("recruitment-materials-changed", onChanged);
    return () => window.removeEventListener("recruitment-materials-changed", onChanged);
  }, [load, applicationId]);
  return { byType, refresh, loaded };
};

const CAMPAIGN_TOOLS = [
  ["board_opportunity", "Board Opportunity", "Generate My Board Opportunity", "The professional opportunity shown in the Board Applicant Marketplace. Review its mission, roles and expectations before publishing."],
  ["board_recruitment_job_post", "Recruitment Job Post", "Generate My Recruitment Job Post", "Your primary professional board opportunity, ready for professional platforms such as LinkedIn Jobs, BoardSource, Idealist and VolunteerMatch. Your application link is inserted automatically."],
  ["recruitment_emails", "Recruitment Email", "Generate My Recruitment Email", "A professional email to send to your network, supporters, colleagues and community contacts inviting qualified people to consider the board opportunity."],
  ["social_posts", "Social Media Recruitment Posts", "Generate My Social Media Recruitment Posts", "Three tailored posts for your social channels. Each introduces the Board opportunity from a different angle and includes your application link."],
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
              {[...coreQuestions.map((q) => q.label + (q.required ? " *" : "")), "Upload résumé/CV (optional)"].map((label) => (
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

export const Module3Launch = ({ mode = "all", onLaunched }) => {
  const launchVideo = useRecruitmentSectionVideo("launch");
  const { byType, refresh } = useMaterials();
  const [opportunity, setOpportunity] = useState(null);
  const [coreQuestions, setCoreQuestions] = useState([]);
  const [readiness, setReadiness] = useState({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadOpportunity = useCallback(async () => {
    try {
      const response = await memberApi.get("/workspace/opportunity");
      setOpportunity(response.data.opportunity);
      setCoreQuestions(response.data.core_questions);
      setReadiness(response.data.readiness);
    } catch { /* ignore */ }
  }, []);
  useEffect(() => { loadOpportunity(); }, [loadOpportunity]);

  const refreshAll = async () => { await refresh(); await loadOpportunity(); };
  useEffect(() => {
    if (["Published", "Closed"].includes(opportunity?.status)) return undefined;
    const timer = window.setInterval(() => { refreshAll(); }, 6000);
    return () => window.clearInterval(timer);
  }, [opportunity?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const generateApplication = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      await memberApi.post("/workspace/opportunity/application/generate");
      setMessage("Your Board Application is ready. Review the public form and your campaign materials below.");
      await loadOpportunity();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not generate the Board Application.");
    }
    setBusy(false);
  };

  const publish = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      await memberApi.post("/workspace/opportunity/publish");
      setMessage("Your recruitment campaign is live.");
      await loadOpportunity();
      onLaunched?.();
    } catch (err) { setError(err.response?.data?.detail || "Could not launch the campaign."); }
    setBusy(false);
  };

  const closeCampaign = async () => {
    if (!window.confirm("Close this recruitment campaign? The application page will show Applications Closed. Existing applications and materials remain.")) return;
    try { await memberApi.post("/workspace/opportunity/close"); await loadOpportunity(); } catch (err) { setError(err.response?.data?.detail || "Could not close the campaign."); }
  };

  const retryNetwork = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await memberApi.post("/workspace/opportunity/broadcast/retry");
      setMessage(response.data.mode === "test" ? "The Applicant Network announcement preview was resent to the program owner." : "The Applicant Network announcement was initiated.");
      await loadOpportunity();
    } catch (err) { setError(err.response?.data?.detail || "Could not retry the Applicant Network announcement."); }
    setBusy(false);
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
                <MaterialCard key={type} type={type} title={title} buttonLabel={buttonLabel} description={description} material={byType[type]} refresh={refreshAll} approvable readOnly={["Published", "Closed"].includes(opportunity?.status)} />
              ))}
              <section className="workspace-panel"><h2>Interview, Check And Offer Communications</h2>
                <p className="material-description">Your approved organization-level drafts are available here. Candidate-specific emails and secure onboarding links are prepared when you choose a person.</p></section>
              {[["general_interview_invitation", "Reusable Interview Invitation"], ["recruitment_communications", "Decision, Check And Offer Communications"]].map(([type, title]) => (
                <MaterialCard key={type} type={type} title={title} buttonLabel={`Generate ${title}`} material={byType[type]}
                  refresh={refreshAll} approvable readOnly={["Published", "Closed"].includes(opportunity?.status)} />
              ))}
            </>
          ) : (
            <section className="workspace-panel">
              <p className="workspace-note">Generate your Board Application first. Your opportunity, job post, recruitment email, social posts and referral email then use the same application link.</p>
            </section>
          )}
        </>
      )}

      {mode !== "materials" && <section className="workspace-panel publish-panel" data-testid="publish-panel">
        <h2>{recruitmentModulesText.h_launchMyRecruitmentCampaign}</h2>
        {launchVideo?.youtube_id && (
          <a className="button button-back" href={`https://www.youtube.com/watch?v=${launchVideo.youtube_id}`} target="_blank" rel="noreferrer" data-testid="launch-recruitment-video">
            <PlayCircle size={18} /> WATCH: LAUNCH YOUR RECRUITMENT CAMPAIGN IN THE NEXT 30 MINUTES
          </a>
        )}
        <p className="material-description">{recruitmentModulesText.d_launchingIsTheOnlyAction}</p>
        <p>Status: <strong className={`opportunity-status status-${(opportunity?.status || "Draft").replace(/\s/g, "-").toLowerCase()}`} data-testid="opportunity-status">{launched ? "Live" : opportunity?.status || "Draft"}</strong></p>
        <ul className="readiness-list">
          <li className={readiness.application_saved ? "done" : ""} data-testid="readiness-application">Board Application created</li>
          <li className={readiness.materials_generated ? "done" : ""} data-testid="readiness-materials">Campaign materials prepared ({readiness.materials_count || 0} of {readiness.materials_total || 4})</li>
          <li className={readiness.materials_approved ? "done" : ""} data-testid="readiness-materials-approved">Campaign materials approved ({readiness.materials_approved_count || 0} of {readiness.materials_total || 4})</li>
          <li className={readiness.onboarding_approved ? "done" : ""}>Organization onboarding documents approved ({readiness.onboarding_approved_count || 0} of {readiness.onboarding_total || 6})</li>
          <li className={readiness.support_approved ? "done" : ""}>Interview, check and offer communications approved ({readiness.support_approved_count || 0} of {readiness.support_total || 2})</li>
        </ul>
        {launched && (
          <div className="member-success" data-testid="published-info">
            <h3>{recruitmentModulesText.h_yourRecruitmentCampaignIsLive}</h3>
            <p>{workspaceModulesText.yourBoardApplicationIsReady}</p>
            <p>Launched {opportunity.published_at && new Date(opportunity.published_at).toLocaleString()}. Applicant Network announcement: {opportunity.broadcast_status || "Pending"}{opportunity.broadcast_mode === "test" && opportunity.broadcast_status === "Initiated" ? " (internal preview sent to the program owner)" : ""}.
              <br /><a href={publicUrl} target="_blank" rel="noreferrer"><Globe size={13} /> {publicUrl} <ExternalLink size={12} /></a></p>
            <Link className="button" to="/app/board-recruitment#br-section-applicants" data-testid="continue-to-applicants">CONTINUE TO APPLICANTS</Link>
          </div>
        )}
        {message && <p className="member-success">{message}</p>}
        {error && <p className="submit-error" data-testid="publish-error">{error}</p>}
        <div className="material-actions">
          {!launched && opportunity?.status !== "Closed" && (
            <button className="button" disabled={busy || !(readiness.profiles_approved && readiness.scheduling_saved && readiness.application_saved && readiness.materials_approved && readiness.onboarding_approved && readiness.support_approved)} onClick={publish} data-testid="publish-button">{workspaceModulesText.launchMyRecruitmentCampaign}</button>
          )}
          {launched && <button className="button button-back" onClick={closeCampaign} data-testid="close-campaign-button">Close Recruitment Campaign</button>}
          {launched && opportunity?.broadcast_status === "Failed" && <button className="button button-back" disabled={busy} onClick={retryNetwork} data-testid="retry-network-button">RETRY APPLICANT NETWORK ANNOUNCEMENT</button>}
          {opportunity?.status === "Closed" && <p className="workspace-note">{recruitmentModulesText.n_thisCampaignIsClosedApplications}</p>}
        </div>
        <p className="material-meta">{workspaceModulesText.launchingMakesTheApplicationPublic}<Link to={publicUrl}>{publicUrl || "…"}</Link>{workspaceModulesText.launchAnnouncementNote}</p>
      </section>}
    </div>
  );
};

export const RecruitmentMaterials = () => <Module3Launch mode="materials" />;
export const RecruitmentCampaignLaunch = () => <Module3Launch mode="launch" />;
