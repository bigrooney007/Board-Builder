import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, ExternalLink, Globe } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard, currentVersion, printText } from "./MaterialCard";

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

export const useStrategyIntake = () => {
  const [intake, setIntake] = useState({ know_people: "", know_people_details: "", reach_channels: [], recruit_outside: "", public_channels: [] });
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    memberApi.get("/workspace/profile").then((response) => {
      const data = response.data.strategy_intake || {};
      setIntake({ know_people: data.know_people || "", know_people_details: data.know_people_details || "", reach_channels: data.reach_channels || [], recruit_outside: data.recruit_outside || "", public_channels: data.public_channels || [] });
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);
  return { intake, setIntake, loaded };
};

const StrategyReadySummary = ({ material }) => {
  const version = currentVersion(material);
  const structured = material?.versions?.slice().reverse().find((v) => v.structured)?.structured || {};
  const channels = (structured.channels || []).map((entry) => entry.channel).filter(Boolean);
  return (
    <div className="strategy-ready" data-testid="strategy-ready">
      <h4>Your Recruitment Strategy Is Ready</h4>
      {channels.length > 0 && (
        <>
          <p>Recruitment Channels:</p>
          <ul>{channels.map((channel) => <li key={channel}>{channel}</li>)}</ul>
        </>
      )}
      <button className="button" onClick={() => printText("Board Recruitment Strategy", version?.display_text || "")} data-testid="download-strategy-pdf">
        <Download size={15} /> Download My Recruitment Strategy
      </button>
    </div>
  );
};

export const Module2Strategy = ({ profileConfirmed }) => {
  const { byType, refresh } = useMaterials();
  const { intake, setIntake } = useStrategyIntake();
  const [errors, setErrors] = useState({});
  const toggle = (key, option) => setIntake((current) => ({ ...current, [key]: current[key].includes(option) ? current[key].filter((item) => item !== option) : [...current[key], option] }));
  const REACH = ["Email", "LinkedIn", "Facebook", "Instagram", "Text Message", "Phone", "In Person", "Other"];
  const PUBLIC = ["LinkedIn", "Other professional/job platforms", "Social Media", "Professional Associations", "Community Networks", "Other"];
  const knowsPeople = intake.know_people === "Yes" || intake.know_people === "I have some people in mind";

  const saveIntake = async () => {
    const found = {};
    if (!intake.know_people) found.know_people = "Please choose an answer.";
    if (knowsPeople && !intake.reach_channels.length) found.reach_channels = "Select at least one way you can reach them.";
    if (!intake.referral_network) found.referral_network = "Please choose an answer.";
    if (!intake.recruit_outside) found.recruit_outside = "Please choose an answer.";
    if (intake.recruit_outside === "Yes" && !intake.public_channels.length) found.public_channels = "Select at least one place you are willing to recruit publicly.";
    setErrors(found);
    if (Object.keys(found).length) return false;
    await memberApi.put("/workspace/strategy-intake", { data: intake });
    return true;
  };

  return (
    <div data-testid="module2-workspace">
      <section className="workspace-panel">
        <h2>Build Your Recruitment Strategy</h2>
        <p className="material-description">Answer the short questions below so we can build a Recruitment Strategy around the board members you identified in Module 1 and the ways you are actually able to reach potential candidates. Your answers are saved automatically when you generate.</p>
        {!profileConfirmed && <p className="workspace-note" data-testid="strategy-locked-note">Complete Module 1 first so your strategy is built around the board members you identified.</p>}
        <label className="field"><span>Do you already know people you would like to invite to consider joining your board? <b>*</b></span>
          <select value={intake.know_people} onChange={(event) => setIntake({ ...intake, know_people: event.target.value })} data-testid="intake-know-people">
            <option value="">Select one</option>{["Yes", "No", "I have some people in mind"].map((option) => <option key={option}>{option}</option>)}
          </select>
          {errors.know_people && <p className="field-error">{errors.know_people}</p>}
        </label>
        {knowsPeople && (
          <>
            <label className="field"><span>Who are they or what relationship do you have with them?</span>
              <textarea rows="3" value={intake.know_people_details} onChange={(event) => setIntake({ ...intake, know_people_details: event.target.value })} data-testid="intake-know-people-details" />
            </label>
            <fieldset className="field choice-field"><legend>How can you reach the people you already know? <b>*</b></legend>
              <div className="choice-grid">{REACH.map((option) => <label className={`choice ${intake.reach_channels.includes(option) ? "selected" : ""}`} key={option}><input type="checkbox" checked={intake.reach_channels.includes(option)} onChange={() => toggle("reach_channels", option)} /><span>{option}</span></label>)}</div>
              {errors.reach_channels && <p className="field-error">{errors.reach_channels}</p>}
            </fieldset>
          </>
        )}
        <label className="field"><span>Would you be willing to ask people you trust to refer or introduce potential board members? <b>*</b></span>
          <select value={intake.referral_network} onChange={(event) => setIntake({ ...intake, referral_network: event.target.value })} data-testid="intake-referral-network">
            <option value="">Select one</option>{["Yes", "No", "Not Sure"].map((option) => <option key={option}>{option}</option>)}
          </select>
          {errors.referral_network && <p className="field-error">{errors.referral_network}</p>}
        </label>
        <label className="field"><span>Do you also want to recruit people outside your existing network? <b>*</b></span>
          <select value={intake.recruit_outside} onChange={(event) => setIntake({ ...intake, recruit_outside: event.target.value })} data-testid="intake-recruit-outside">
            <option value="">Select one</option>{["Yes", "No", "Not Sure"].map((option) => <option key={option}>{option}</option>)}
          </select>
          {errors.recruit_outside && <p className="field-error">{errors.recruit_outside}</p>}
        </label>
        {intake.recruit_outside === "Yes" && (
          <fieldset className="field choice-field"><legend>Where are you willing to recruit publicly? <b>*</b></legend>
            <div className="choice-grid">{PUBLIC.map((option) => <label className={`choice ${intake.public_channels.includes(option) ? "selected" : ""}`} key={option}><input type="checkbox" checked={intake.public_channels.includes(option)} onChange={() => toggle("public_channels", option)} /><span>{option}</span></label>)}</div>
            {errors.public_channels && <p className="field-error">{errors.public_channels}</p>}
          </fieldset>
        )}
        <MaterialCard
          type="recruitment_strategy"
          title="Board Recruitment Strategy"
          buttonLabel="Generate My Recruitment Strategy"
          description="A practical strategy built around the exact board member profiles from Module 1 and the recruitment channels you can actually use. Module 3 creates the actual launch materials."
          material={byType.recruitment_strategy}
          refresh={refresh}
          beforeGenerate={saveIntake}
          hideDisplay
          summary={<StrategyReadySummary material={byType.recruitment_strategy} />}
        />
      </section>
    </div>
  );
};

const PUBLIC_OUTREACH_TOOLS = [
  ["board_recruitment_job_post", "Board Recruitment Job Post", "Generate My Board Recruitment Job Post", "Use this version when publishing your opportunity through LinkedIn Jobs or another professional/volunteer opportunity platform."],
  ["social_posts", "Social Media Recruitment Posts", "Generate My Social Media Recruitment Post", "Use this to introduce the board opportunity to your social networks and invite qualified people to learn more or apply."],
  ["linkedin_post", "LinkedIn Recruitment Post", "Generate My LinkedIn Recruitment Post", "A feed-post version for your LinkedIn profile and pages."],
  ["linkedin_launch_instructions", "LinkedIn Jobs Launch Guide", "Show Me How to Launch Through LinkedIn Jobs", "Follow this practical guide to put the board opportunity in front of professionals through LinkedIn's Jobs area, starting with a small controlled test budget where available."],
];

const ApplicationPanel = ({ opportunity, coreQuestions, applicationSaved, reload }) => {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(false);
  const publicUrl = opportunity ? `/board-opportunities/${opportunity.slug}/apply` : "";

  const generateApplication = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      await memberApi.post("/workspace/opportunity/application/generate");
      setMessage("Your Board Application is ready and saved.");
      await reload();
    } catch (err) { setError(err.response?.data?.detail || "Could not create the Board Application."); }
    setBusy(false);
  };

  return (
    <section className="workspace-panel" data-testid="application-editor">
      <h2>Your Board Application</h2>
      <p className="material-description">Create the application prospective board members will complete so you can collect the information needed to decide who should move forward. It uses the proven standard board application structure — personalized with your organization's information — and is saved automatically. You do not need to design the form.</p>
      {!applicationSaved && (
        <button className="button" disabled={busy} onClick={generateApplication} data-testid="generate-application-button">{busy ? "Creating…" : "Generate My Board Application"}</button>
      )}
      {applicationSaved && (
        <>
          <p className="member-success" data-testid="application-saved-note">Your Board Application is generated and saved.</p>
          <h3>Your Board Application Link</h3>
          <p className="material-description">Use this link in LinkedIn, social posts, job posts, emails and direct messages. It becomes publicly accessible when you publish your recruitment campaign below.</p>
          {publicUrl && (
            <div className="material-actions">
              <code className="app-link-code" data-testid="application-link">{`${window.location.origin}${publicUrl}`}</code>
              <button className="button button-back" onClick={() => { navigator.clipboard?.writeText(`${window.location.origin}${publicUrl}`); setMessage("Application link copied."); }} data-testid="copy-application-link">Copy Link</button>
            </div>
          )}
          <div className="material-actions">
            <button className="button button-back" onClick={() => setPreview(!preview)} data-testid="preview-application-button">{preview ? "Hide Preview" : "Preview Application"}</button>
          </div>
          {preview && (
            <div className="application-preview" data-testid="application-preview">
              <h3>Application Preview — {opportunity?.organization_name}</h3>
              {[...coreQuestions.map((q) => q.label + (q.required ? " *" : "")), "Upload résumé/CV *"].map((label) => (
                <div className="preview-question" key={label}><span>{label}</span><i /></div>
              ))}
            </div>
          )}
        </>
      )}
      {message && <p className="member-success">{message}</p>}
      {error && <p className="submit-error">{error}</p>}
    </section>
  );
};

export const Module3Launch = () => {
  const { byType, refresh } = useMaterials();
  const { intake } = useStrategyIntake();
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
    if (!window.confirm("Publishing will make your Board Application public and notify eligible professionals in the Nonprofit Board Builder Applicant Network about this opportunity.\n\nPublish Recruitment Campaign?")) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await memberApi.post("/workspace/opportunity/publish");
      setMessage(`Recruitment campaign published. Network announcement: ${response.data.broadcast_status}.`);
      await loadOpportunity();
    } catch (err) { setError(err.response?.data?.detail || "Could not publish the campaign."); }
    setBusy(false);
  };

  const closeCampaign = async () => {
    if (!window.confirm("Close this recruitment campaign? The application page will show Applications Closed. Existing applications and materials remain.")) return;
    try { await memberApi.post("/workspace/opportunity/close"); await loadOpportunity(); } catch (err) { setError(err.response?.data?.detail || "Could not close the campaign."); }
  };

  const knowsPeople = intake.know_people === "Yes" || intake.know_people === "I have some people in mind";
  const publicApplies = intake.recruit_outside !== "No";
  const referralApplies = intake.referral_network !== "No";
  const publicUrl = opportunity ? `/board-opportunities/${opportunity.slug}/apply` : "";

  return (
    <div data-testid="module3-workspace">
      <ApplicationPanel opportunity={opportunity} coreQuestions={coreQuestions} applicationSaved={!!readiness.application_saved} reload={loadOpportunity} />

      <MaterialCard type="board_opportunity" title="Board Opportunity" buttonLabel="Generate My Board Opportunity"
        description="The complete description of the board opportunity used across your recruitment materials and hosted application. Your application link is inserted automatically. Approve it before you can publish."
        material={byType.board_opportunity} refresh={refreshAll} approvable />

      {publicApplies && PUBLIC_OUTREACH_TOOLS.map(([type, title, buttonLabel, description]) => (
        <MaterialCard key={type} type={type} title={title} buttonLabel={buttonLabel} description={description} material={byType[type]} refresh={refreshAll} approvable />
      ))}
      <MaterialCard type="recruitment_emails" title="Recruitment Emails" buttonLabel="Generate My Recruitment Emails"
        description="Announcement, invitation and follow-up emails for your supporters and contacts."
        material={byType.recruitment_emails} refresh={refreshAll} approvable />
      {knowsPeople && (
        <>
          <MaterialCard type="personal_invitation_email" title="Personal Invitation Email" buttonLabel="Generate My Personal Invitation Email"
            description="Use this to personally invite someone you already know to consider the board opportunity."
            material={byType.personal_invitation_email} refresh={refreshAll} approvable />
          <MaterialCard type="personal_invitation_message" title="Personal Invitation Message" buttonLabel="Generate My Personal Invitation Message"
            description="A shorter version for LinkedIn, Facebook, text or another direct-message channel."
            material={byType.personal_invitation_message} refresh={refreshAll} approvable />
        </>
      )}
      {referralApplies && (
        <>
          <MaterialCard type="referral_request_email" title="Referral Request Email" buttonLabel="Generate My Referral Request Email"
            description="Ask people you trust to refer or introduce potential board members. Your application link is inserted automatically."
            material={byType.referral_request_email} refresh={refreshAll} approvable />
          <MaterialCard type="referral_request_message" title="Referral Request Message" buttonLabel="Generate My Referral Request Message"
            description="A concise direct-message version of the referral request for LinkedIn, text or other channels."
            material={byType.referral_request_message} refresh={refreshAll} approvable />
        </>
      )}

      <section className="workspace-panel publish-panel" data-testid="publish-panel">
        <h2>Publish Recruitment Campaign</h2>
        <p className="material-description">Publishing is the only action that makes your Board Application public and triggers the one-time Board Applicant Network announcement. Generating materials above never sends emails or publishes anything.</p>
        <p>Status: <strong className={`opportunity-status status-${(opportunity?.status || "Draft").replace(/\s/g, "-").toLowerCase()}`} data-testid="opportunity-status">{opportunity?.status || "Draft"}</strong></p>
        <ul className="readiness-list">
          <li className={readiness.strategy_approved ? "done" : ""} data-testid="readiness-strategy">Recruitment Strategy generated (Module 2)</li>
          <li className={readiness.opportunity_saved ? "done" : ""} data-testid="readiness-opportunity">Board Opportunity approved</li>
          <li className={readiness.application_saved ? "done" : ""} data-testid="readiness-application">Board Application created</li>
        </ul>
        {opportunity?.status === "Published" && (
          <p className="member-success" data-testid="published-info">
            Published {opportunity.published_at && new Date(opportunity.published_at).toLocaleString()}. Network announcement {opportunity.broadcast_status || "Initiated"} ({opportunity.broadcast_mode === "test" ? "delivered as an internal preview to the program owner" : "delivered to eligible Applicant Network members"}).
            <br /><a href={publicUrl} target="_blank" rel="noreferrer"><Globe size={13} /> {publicUrl} <ExternalLink size={12} /></a>
          </p>
        )}
        {message && <p className="member-success">{message}</p>}
        {error && <p className="submit-error" data-testid="publish-error">{error}</p>}
        <div className="material-actions">
          {opportunity?.status !== "Published" && opportunity?.status !== "Closed" && (
            <button className="button" disabled={busy || !(readiness.strategy_approved && readiness.opportunity_saved && readiness.application_saved)} onClick={publish} data-testid="publish-button">Publish Recruitment Campaign</button>
          )}
          {opportunity?.status === "Published" && <button className="button button-back" onClick={closeCampaign} data-testid="close-campaign-button">Close Recruitment Campaign</button>}
          {opportunity?.status === "Closed" && <p className="workspace-note">This campaign is closed. Applications show “Applications Closed”. All data remains.</p>}
        </div>
        <p className="material-meta">Publishing makes the application public at <Link to={publicUrl}>{publicUrl || "…"}</Link> and initiates one Board Applicant Network announcement. Duplicate broadcasts are prevented automatically.</p>
      </section>
    </div>
  );
};
