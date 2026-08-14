import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Globe } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard } from "./MaterialCard";

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
  ["linkedin_post", "LinkedIn Recruitment Post", "Generate My LinkedIn Recruitment Post", "A feed post in your voice for your LinkedIn profile and pages, speaking directly to your professional network."],
  ["recruitment_emails", "Recruitment Email", "Generate My Recruitment Email", "A professional email to send to your network, supporters, colleagues and community contacts inviting qualified people to consider the board opportunity."],
  ["social_posts", "Social Media Recruitment Post", "Generate My Social Media Recruitment Post", "A shorter, shareable recruitment post for Facebook, Instagram and similar channels."],
  ["referral_request_email", "Referral Recruitment Message", "Generate My Referral Recruitment Message", "A message asking board members, supporters, partners and colleagues to help identify people who may be a strong fit — and to forward your application link."],
];

const ApplicationPanel = ({ opportunity, coreQuestions, applicationSaved }) => {
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState(false);
  const publicUrl = opportunity ? `/board-opportunities/${opportunity.slug}/apply` : "";

  return (
    <section className="workspace-panel" data-testid="application-editor">
      <h2>Your Board Application</h2>
      <p className="material-description">Your hosted Board Application is created automatically using your organization's information and the proven standard board application structure — you do not need to configure anything. Every recruitment material below automatically uses this exact link.</p>
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
          <p className="material-meta">Use this link in your job post, LinkedIn post, emails and messages. It becomes publicly accessible when you launch your recruitment campaign below.</p>
        </>
      )}
      {message && <p className="member-success">{message}</p>}
    </section>
  );
};

export const Module3Launch = () => {
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
      <ApplicationPanel opportunity={opportunity} coreQuestions={coreQuestions} applicationSaved={!!readiness.application_saved} />

      <section className="workspace-panel" data-testid="campaign-materials">
        <h2>Your Recruitment Campaign Materials</h2>
        <p className="material-description">Each resource is created from the information you have already provided and the board members you identified in Step 2 — your Board Application link is inserted automatically. Generate each one, read it, edit anything you want changed, then approve it. Nothing is sent or published until you launch below.</p>
      </section>
      {CAMPAIGN_TOOLS.map(([type, title, buttonLabel, description]) => (
        <MaterialCard key={type} type={type} title={title} buttonLabel={buttonLabel} description={description} material={byType[type]} refresh={refreshAll} approvable />
      ))}

      <section className="workspace-panel publish-panel" data-testid="publish-panel">
        <h2>Launch My Recruitment Campaign</h2>
        <p className="material-description">Launching is the only action that makes your Board Application public and triggers the one-time Board Applicant Network announcement. Generating materials above never sends emails or publishes anything.</p>
        <p>Status: <strong className={`opportunity-status status-${(opportunity?.status || "Draft").replace(/\s/g, "-").toLowerCase()}`} data-testid="opportunity-status">{launched ? "Live" : opportunity?.status || "Draft"}</strong></p>
        <ul className="readiness-list">
          <li className={readiness.application_saved ? "done" : ""} data-testid="readiness-application">Board Application created</li>
          <li className={readiness.materials_generated ? "done" : ""} data-testid="readiness-materials">Campaign materials generated ({readiness.materials_count || 0} of {readiness.materials_total || 5})</li>
        </ul>
        {launched && (
          <div className="member-success" data-testid="published-info">
            <h3>Your Recruitment Campaign Is Live</h3>
            <p>Your Board Application is ready, your recruitment materials have been created, and your opportunity has been launched through the Nonprofit Board Builder recruitment network. Use the materials above to continue sharing your opportunity through your professional, social and referral networks.</p>
            <p>Launched {opportunity.published_at && new Date(opportunity.published_at).toLocaleString()}. Network announcement {opportunity.broadcast_status || "Initiated"} ({opportunity.broadcast_mode === "test" ? "delivered as an internal preview to the program owner" : "delivered to eligible Applicant Network members"}).
              <br /><a href={publicUrl} target="_blank" rel="noreferrer"><Globe size={13} /> {publicUrl} <ExternalLink size={12} /></a></p>
            <Link className="button" to="/app/recruitment/self-guided/module/4" data-testid="continue-to-step-3">Continue to Step 4 — Select and Interview Your Applicants</Link>
          </div>
        )}
        {message && <p className="member-success">{message}</p>}
        {error && <p className="submit-error" data-testid="publish-error">{error}</p>}
        <div className="material-actions">
          {!launched && opportunity?.status !== "Closed" && (
            <button className="button" disabled={busy || !(readiness.application_saved && readiness.materials_generated)} onClick={publish} data-testid="publish-button">Launch My Recruitment Campaign</button>
          )}
          {launched && <button className="button button-back" onClick={closeCampaign} data-testid="close-campaign-button">Close Recruitment Campaign</button>}
          {opportunity?.status === "Closed" && <p className="workspace-note">This campaign is closed. Applications show “Applications Closed”. All data remains.</p>}
        </div>
        <p className="material-meta">Launching makes the application public at <Link to={publicUrl}>{publicUrl || "…"}</Link> and initiates one Board Applicant Network announcement. Duplicate launches are prevented automatically. Your materials are for you to share — nothing is automatically posted to LinkedIn, job boards or social media.</p>
      </section>
    </div>
  );
};
