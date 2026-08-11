import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, ExternalLink, Globe, Lock, Plus, Trash2 } from "lucide-react";
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
      // fetch full versions (list endpoint omits structured but includes display_text) — list keeps display_text
      setByType(map);
    } catch { /* ignore */ }
    setLoaded(true);
  }, [applicationId]);
  useEffect(() => { refresh(); }, [refresh]);
  return { byType, refresh, loaded };
};

export const Module2Strategy = ({ profileConfirmed }) => {
  const { byType, refresh } = useMaterials();
  const [intake, setIntake] = useState({ know_people: "", know_people_details: "", reach_channels: [], recruit_outside: "", public_channels: [] });
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    memberApi.get("/workspace/profile").then((response) => {
      const data = response.data.strategy_intake || {};
      if (Object.keys(data).length) { setIntake({ know_people: data.know_people || "", know_people_details: data.know_people_details || "", reach_channels: data.reach_channels || [], recruit_outside: data.recruit_outside || "", public_channels: data.public_channels || [] }); setSaved(true); }
    }).catch(() => {});
  }, []);
  const toggle = (key, option) => setIntake((current) => ({ ...current, [key]: current[key].includes(option) ? current[key].filter((item) => item !== option) : [...current[key], option] }));
  const saveIntake = async () => {
    try { await memberApi.put("/workspace/strategy-intake", { data: intake }); setSaved(true); } catch { /* ignore */ }
  };
  const REACH = ["Email", "LinkedIn", "Facebook", "Instagram", "Text message", "Phone", "In person", "Other"];
  const PUBLIC = ["LinkedIn", "Other professional/job platforms", "Social media", "Professional associations", "Community networks", "Other"];
  return (
    <div data-testid="module2-workspace">
      <section className="workspace-panel">
        <h2>Generate Your Board Recruitment Strategy</h2>
        <p className="material-description">Your strategy is built around the exact board member profiles identified in Module 1. Answer these short questions first so the strategy fits how you can actually recruit.</p>
        {!profileConfirmed && <p className="workspace-note" data-testid="strategy-locked-note"><Lock size={14} /> Complete and confirm your Recruitment Profile in Module 1 to generate your strategy.</p>}
        <label className="field"><span>Do you already know people you would like to invite to consider joining your board?</span>
          <select value={intake.know_people} onChange={(event) => setIntake({ ...intake, know_people: event.target.value })} data-testid="intake-know-people">
            <option value="">Select one</option>{["Yes", "No", "I have some people in mind"].map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
        {(intake.know_people === "Yes" || intake.know_people === "I have some people in mind") && (
          <label className="field"><span>Who are they or what type of relationship do you have with them?</span>
            <textarea rows="3" value={intake.know_people_details} onChange={(event) => setIntake({ ...intake, know_people_details: event.target.value })} data-testid="intake-know-people-details" />
          </label>
        )}
        <fieldset className="field choice-field"><legend>How can you reach the people you already know?</legend>
          <div className="choice-grid">{REACH.map((option) => <label className={`choice ${intake.reach_channels.includes(option) ? "selected" : ""}`} key={option}><input type="checkbox" checked={intake.reach_channels.includes(option)} onChange={() => toggle("reach_channels", option)} /><span>{option}</span></label>)}</div>
        </fieldset>
        <label className="field"><span>Do you also want to recruit professionals outside your existing network?</span>
          <select value={intake.recruit_outside} onChange={(event) => setIntake({ ...intake, recruit_outside: event.target.value })} data-testid="intake-recruit-outside">
            <option value="">Select one</option>{["Yes", "No", "Not sure"].map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
        <fieldset className="field choice-field"><legend>Where are you comfortable recruiting publicly?</legend>
          <div className="choice-grid">{PUBLIC.map((option) => <label className={`choice ${intake.public_channels.includes(option) ? "selected" : ""}`} key={option}><input type="checkbox" checked={intake.public_channels.includes(option)} onChange={() => toggle("public_channels", option)} /><span>{option}</span></label>)}</div>
        </fieldset>
        <button className="button button-back" onClick={saveIntake} data-testid="save-strategy-intake">{saved ? "Update My Answers" : "Save My Answers"}</button>
        {saved && <p className="member-success">Answers saved. They are used when your strategy is generated.</p>}
      </section>
      <MaterialCard
        type="recruitment_strategy"
        title="Board Recruitment Strategy"
        buttonLabel="Generate My Recruitment Strategy"
        description="A practical strategy covering LinkedIn/professional platforms, your personal network, email outreach, social/direct messages and the Board Applicant Network as applicable, with a clear recruitment sequence. Module 3 creates the actual materials. The saved version becomes the Approved Recruitment Strategy used by later modules."
        material={byType.recruitment_strategy}
        refresh={refresh}
      />
    </div>
  );
};

const LAUNCH_TOOLS = [
  ["social_posts", "Social Media Recruitment Posts", "Generate My Social Media Recruitment Post", "Use this to introduce the board opportunity to your social networks and invite qualified people to learn more or apply."],
  ["board_recruitment_job_post", "Board Recruitment Job Post", "Generate My Board Recruitment Job Post", "Use this version when publishing your opportunity through LinkedIn Jobs or another professional/volunteer opportunity platform."],
  ["linkedin_post", "LinkedIn Recruitment Post", "Generate My LinkedIn Recruitment Post", "A feed-post version for your LinkedIn profile and pages."],
  ["linkedin_launch_instructions", "LinkedIn Jobs Launch Guide", "Show Me How to Launch This Through LinkedIn Jobs", "Follow this practical guide to put the board opportunity in front of professionals through LinkedIn's Jobs area, starting with a small controlled test budget where available."],
  ["board_opportunity", "Board Opportunity", "Generate My Board Opportunity", "The complete description of the board opportunity used across your recruitment materials and hosted application."],
  ["application_questions", "Board Application Form", "Generate My Board Application", "Create the application prospective board members will complete so you can collect the information needed to decide who should move forward."],
  ["personal_invitation_email", "Personal Invitation Email", "Generate My Personal Invitation Email", "Use this to personally invite someone you already know to consider the board opportunity."],
  ["personal_invitation_message", "Personal Invitation Message", "Generate My Personal Invitation Message", "Use this shorter version for LinkedIn, Facebook, text or another direct-message channel."],
  ["recruitment_emails", "Recruitment Emails", "Generate My Recruitment Emails", "Announcement, invitation and follow-up emails for your supporters and contacts."],
];

export const Module3Launch = () => {
  const { byType, refresh } = useMaterials();
  const [opportunity, setOpportunity] = useState(null);
  const [coreQuestions, setCoreQuestions] = useState([]);
  const [readiness, setReadiness] = useState({});
  const [customQuestions, setCustomQuestions] = useState([]);
  const [newQuestion, setNewQuestion] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(false);

  const loadOpportunity = useCallback(async () => {
    try {
      const response = await memberApi.get("/workspace/opportunity");
      setOpportunity(response.data.opportunity);
      setCoreQuestions(response.data.core_questions);
      setReadiness(response.data.readiness);
      setCustomQuestions(response.data.opportunity.custom_questions || []);
    } catch { /* ignore */ }
  }, []);
  useEffect(() => { loadOpportunity(); }, [loadOpportunity]);

  const refreshAll = async () => { await refresh(); await loadOpportunity(); };

  const move = (index, delta) => {
    const next = [...customQuestions];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setCustomQuestions(next);
  };

  const saveApplication = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      await memberApi.put("/workspace/opportunity/application", { custom_questions: customQuestions });
      setMessage("Board Application saved.");
      await loadOpportunity();
    } catch (err) { setError(err.response?.data?.detail || "Could not save the application."); }
    setBusy(false);
  };

  const publish = async () => {
    if (!window.confirm("Publishing will make your Board Application public and notify eligible professionals in the Nonprofit Board Builder Applicant Network about this opportunity.\n\nPublish and Launch Recruitment?")) return;
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

  const publicUrl = opportunity ? `/board-opportunities/${opportunity.slug}/apply` : "";

  return (
    <div data-testid="module3-workspace">
      {LAUNCH_TOOLS.map(([type, title, buttonLabel, description]) => (
        <MaterialCard key={type} type={type} title={title} buttonLabel={buttonLabel} description={description} material={byType[type]} refresh={refreshAll} />
      ))}

      <section className="workspace-panel" data-testid="application-editor">
        <h2>Your Board Application</h2>
        <p>Every application always contains the required core questions below. Claude adds up to 5 organization-specific questions that you can edit, reorder, delete or replace.</p>
        <h3>Required Core Questions (cannot be removed)</h3>
        <ol className="core-question-list">{coreQuestions.map((question) => <li key={question.id}>{question.label}{question.required ? "" : " (optional)"}</li>)}<li>Upload résumé/CV (required)</li></ol>
        <h3>Organization-Specific Questions</h3>
        {customQuestions.length === 0 && <p className="workspace-note">Generate the Board Application Form above or add your own questions.</p>}
        {customQuestions.map((question, index) => (
          <div className="custom-question-row" key={question.id} data-testid={`custom-question-${index + 1}`}>
            <input value={question.label} onChange={(event) => setCustomQuestions(customQuestions.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item))} />
            <button className="icon-button" onClick={() => move(index, -1)} aria-label="Move up"><ArrowUp size={15} /></button>
            <button className="icon-button" onClick={() => move(index, 1)} aria-label="Move down"><ArrowDown size={15} /></button>
            <button className="icon-button" onClick={() => setCustomQuestions(customQuestions.filter((item, itemIndex) => itemIndex !== index))} aria-label="Delete question" data-testid={`delete-question-${index + 1}`}><Trash2 size={15} /></button>
          </div>
        ))}
        <div className="custom-question-row add">
          <input placeholder="Add your own question" value={newQuestion} onChange={(event) => setNewQuestion(event.target.value)} data-testid="add-question-input" />
          <button className="button button-back" onClick={() => { if (newQuestion.trim()) { setCustomQuestions([...customQuestions, { id: "", label: newQuestion.trim(), type: "textarea" }]); setNewQuestion(""); } }} data-testid="add-question-button"><Plus size={15} /> Add</button>
        </div>
        <h3>Your Board Application Link</h3>
        <p className="material-description">Use this link in LinkedIn, social posts, job posts, emails and direct messages. It becomes publicly accessible when you publish your recruitment campaign below.</p>
        {publicUrl && (
          <div className="material-actions">
            <code className="app-link-code" data-testid="application-link">{`${window.location.origin}${publicUrl}`}</code>
            <button className="button button-back" onClick={() => { navigator.clipboard?.writeText(`${window.location.origin}${publicUrl}`); setMessage("Application link copied."); }} data-testid="copy-application-link">Copy Link</button>
          </div>
        )}
        <div className="material-actions">
          <button className="button" disabled={busy} onClick={saveApplication} data-testid="save-application-button">Save Board Application</button>
          <button className="button button-back" onClick={() => setPreview(!preview)} data-testid="preview-application-button">{preview ? "Hide Preview" : "Preview Application"}</button>
        </div>
        {preview && (
          <div className="application-preview" data-testid="application-preview">
            <h3>Application Preview — {opportunity?.organization_name}</h3>
            {[...coreQuestions.map((q) => q.label + (q.required ? " *" : "")), "Upload résumé/CV *", ...customQuestions.map((q) => q.label)].map((label) => (
              <div className="preview-question" key={label}><span>{label}</span><i /></div>
            ))}
          </div>
        )}
      </section>

      <section className="workspace-panel publish-panel" data-testid="publish-panel">
        <h2>Publish Recruitment Campaign</h2>
        <p>Status: <strong className={`opportunity-status status-${(opportunity?.status || "Draft").replace(/\s/g, "-").toLowerCase()}`} data-testid="opportunity-status">{opportunity?.status || "Draft"}</strong></p>
        <ul className="readiness-list">
          <li className={readiness.strategy_approved ? "done" : ""} data-testid="readiness-strategy">Recruitment Strategy approved</li>
          <li className={readiness.opportunity_saved ? "done" : ""} data-testid="readiness-opportunity">Board Opportunity saved</li>
          <li className={readiness.application_saved ? "done" : ""} data-testid="readiness-application">Board Application saved</li>
        </ul>
        {opportunity?.status === "Published" && (
          <p className="member-success" data-testid="published-info">
            Published {opportunity.published_at && new Date(opportunity.published_at).toLocaleString()}. Network announcement {opportunity.broadcast_status || "Initiated"} ({opportunity.broadcast_mode === "test" ? "TEST MODE — sent only to the owner test address" : "live"}).
            <br /><a href={publicUrl} target="_blank" rel="noreferrer"><Globe size={13} /> {publicUrl} <ExternalLink size={12} /></a>
          </p>
        )}
        {message && <p className="member-success">{message}</p>}
        {error && <p className="submit-error" data-testid="publish-error">{error}</p>}
        <div className="material-actions">
          {opportunity?.status !== "Published" && opportunity?.status !== "Closed" && (
            <button className="button" disabled={busy || !(readiness.strategy_approved && readiness.opportunity_saved && readiness.application_saved)} onClick={publish} data-testid="publish-button">Publish and Launch Recruitment</button>
          )}
          {opportunity?.status === "Published" && <button className="button button-back" onClick={closeCampaign} data-testid="close-campaign-button">Close Recruitment Campaign</button>}
          {opportunity?.status === "Closed" && <p className="workspace-note">This campaign is closed. Applications show “Applications Closed”. All data remains.</p>}
        </div>
        <p className="material-meta">Publishing makes the application public at <Link to={publicUrl}>{publicUrl || "…"}</Link> and initiates one Board Applicant Network announcement. Duplicate broadcasts are prevented automatically.</p>
      </section>
    </div>
  );
};
