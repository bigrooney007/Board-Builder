import React, { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Pencil } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";

const STRENGTH_AREAS = ["Fundraising", "Major donors", "Corporate partnerships", "Grants", "Finance", "Accounting", "Governance", "Law", "Marketing", "Communications", "Public relations", "Community engagement", "Strategic planning", "Human resources", "Technology", "Program development", "Operations", "Government", "Healthcare", "Education", "Professional connections", "Lived experience", "Other"];
const RESPONSIBILITIES = ["Attend meetings consistently", "Participate in strategic planning", "Serve on a committee", "Make introductions", "Support fundraising", "Build business relationships", "Engage donors", "Help recruit volunteers", "Support community outreach", "Provide professional expertise", "Make a personal financial contribution", "Other"];
const FUNDRAISING_ACTIVITIES = ["Business introductions", "Corporate partnerships", "Major donor introductions", "Donor meetings", "Grants", "Sponsorship", "Events", "Fundraising campaigns", "Community fundraising", "Reviewing fundraising materials", "Fundraising committee", "Other"];

const STEPS = [
  { heading: "Your Organization", fields: [
    { name: "organization_name", label: "Organization name", type: "text" },
    { name: "website", label: "Website", type: "text", optional: true },
    { name: "mission", label: "Mission", type: "textarea" },
    { name: "city", label: "City", type: "text" },
    { name: "state_region", label: "State/region", type: "text" },
    { name: "country", label: "Country", type: "text" },
    { name: "priorities", label: "What are the three most important things your organization needs to accomplish during the next 12 months?", type: "textarea" },
    { name: "highest_priority_program", label: "Which program or area of the organization is the highest priority right now?", type: "textarea" },
    { name: "biggest_challenges", label: "What are the biggest challenges preventing the organization from accomplishing these priorities?", type: "textarea" },
  ] },
  { heading: "Your Present Board", fields: [
    { name: "present_board", label: "How many people are presently on the board?", type: "text" },
    { name: "active_board", label: "How many are consistently active?", type: "text" },
    { name: "continuing_members", label: "How many present members do you expect will continue serving?", type: "text" },
    { name: "board_strengths", label: "What are the main strengths already represented on the board?", type: "choices", options: STRENGTH_AREAS },
    { name: "board_weaknesses", label: "Where is the present board weakest?", type: "choices", options: STRENGTH_AREAS },
    { name: "missing_from_board", label: "What is currently missing from the board?", type: "textarea" },
  ] },
  { heading: "The Board You Want to Build", fields: [
    { name: "new_members_count", label: "How many new board members do you want to recruit?", type: "text" },
    { name: "board_kind", label: "What kind of board are you building?", type: "select", options: ["Governing board", "Working board", "Fundraising board", "Combination", "Not sure"] },
    { name: "strengthen_areas", label: "Which areas must the new board members strengthen?", type: "choices", options: STRENGTH_AREAS },
    { name: "valuable_experience", label: "What professional experience would be particularly valuable?", type: "textarea" },
    { name: "valuable_relationships", label: "What relationships or networks would be particularly valuable?", type: "textarea" },
    { name: "communities_represented", label: "Which communities or lived experiences should ideally be represented?", type: "textarea", optional: true },
    { name: "particular_person", label: "Is there any particular type of person you already know you want to recruit?", type: "textarea", optional: true },
  ] },
  { heading: "Expectations of Board Members", fields: [
    { name: "meeting_frequency", label: "How often does the board meet?", type: "text" },
    { name: "meeting_format", label: "Are meetings:", type: "select", options: ["In person", "Virtual", "Hybrid"] },
    { name: "location_requirement", label: "Where must board members be located?", type: "select", options: ["Same city/community", "Same state", "Anywhere in the United States", "United States and United Kingdom", "Anywhere", "Other"] },
    { name: "monthly_time_commitment", label: "Approximate monthly time commitment expected", type: "text" },
    { name: "service_unpaid", label: "Is board service unpaid?", type: "select", options: ["Yes", "No", "Other"] },
    { name: "responsibilities", label: "What responsibilities will all board members be expected to accept?", type: "choices", options: RESPONSIBILITIES },
    { name: "fundraising_activities", label: "What fundraising activities may board members be expected to support?", type: "choices", options: FUNDRAISING_ACTIVITIES },
  ] },
  { heading: "Recruitment Logistics", fields: [
    { name: "launch_timing", label: "When do you want the recruitment campaign to launch?", type: "text" },
    { name: "selection_timing", label: "When would you ideally like the new board members selected?", type: "text" },
    { name: "has_deadline", label: "Is there an application deadline?", type: "select", options: ["Yes", "No"] },
    { name: "application_deadline", label: "Application deadline date", type: "text", optional: true, showIf: (data) => data.has_deadline === "Yes" },
    { name: "who_interviews", label: "Who will interview applicants?", type: "text" },
    { name: "final_decision", label: "Who makes the final board-selection decision?", type: "text" },
    { name: "bylaws_requirements", label: "Do your bylaws contain any requirements that affect board recruitment?", type: "select", options: ["Yes", "No", "Not sure"] },
    { name: "bylaws_details", label: "Describe the relevant requirements", type: "textarea", optional: true, showIf: (data) => data.bylaws_requirements === "Yes" },
    { name: "min_board_size", label: "Minimum board size under your bylaws", type: "text", optional: true },
    { name: "max_board_size", label: "Maximum board size under your bylaws", type: "text", optional: true },
  ] },
];

const emptyData = () => {
  const data = {};
  STEPS.forEach((step) => step.fields.forEach((field) => { data[field.name] = field.type === "choices" ? [] : ""; }));
  return data;
};

const BlueprintPanel = () => {
  const { byType, refresh } = useMaterials();
  return (
    <section className="workspace-panel" data-testid="module1-blueprint">
      <h2>Identify the Board Your Organization Needs</h2>
      <p className="material-description">Compare the board you have with the powerhouse board your organization needs, and identify the exact profiles of the new board members you should recruit.</p>
      <MaterialCard
        type="powerhouse_board_blueprint"
        title="Your Powerhouse Board Blueprint"
        buttonLabel="Identify the Board Members I Need"
        description="Generated from your public Recruitment form and confirmed profile: what your present board already brings, what is missing, what a powerhouse board looks like for your organization, and one exact profile for each new board member you want to recruit. The saved version drives Modules 2 and 3."
        material={byType.powerhouse_board_blueprint}
        refresh={refresh}
      />
    </section>
  );
};

export const Module1Profile = ({ onConfirmed }) => {
  const [data, setData] = useState(emptyData());
  const [step, setStep] = useState(0);
  const [mode, setMode] = useState("loading"); // loading | form | summary
  const [confirmed, setConfirmed] = useState(false);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    memberApi.get("/workspace/profile").then((response) => {
      const { profile, prefill, confirmed: isConfirmed } = response.data;
      const merged = emptyData();
      Object.entries(prefill || {}).forEach(([key, value]) => { if (value && merged[key] !== undefined) merged[key] = value; });
      Object.entries(profile || {}).forEach(([key, value]) => { if (merged[key] !== undefined && value !== "" && !(Array.isArray(value) && !value.length)) merged[key] = value; });
      setData(merged);
      setConfirmed(isConfirmed);
      setMode(Object.keys(profile || {}).length ? "summary" : "form");
    }).catch(() => setMode("form"));
  }, []);

  const update = (name, value) => { setData((current) => ({ ...current, [name]: value })); setErrors((current) => ({ ...current, [name]: undefined })); };

  const visibleFields = (index) => STEPS[index].fields.filter((field) => !field.showIf || field.showIf(data));

  const validateStep = () => {
    const found = {};
    visibleFields(step).forEach((field) => {
      const value = data[field.name];
      if (!field.optional && (value === "" || (Array.isArray(value) && !value.length))) found[field.name] = "This field is required.";
    });
    setErrors(found);
    return !Object.keys(found).length;
  };

  const persist = async () => {
    setSaving(true);
    try { await memberApi.put("/workspace/profile", { data }); setConfirmed(false); } catch { /* keep local */ }
    setSaving(false);
  };

  const next = async () => {
    if (!validateStep()) return;
    await persist();
    if (step < STEPS.length - 1) setStep(step + 1);
    else setMode("summary");
  };

  const confirm = async () => {
    setSaving(true);
    try {
      await memberApi.post("/workspace/profile/confirm");
      setConfirmed(true);
      if (onConfirmed) onConfirmed();
    } catch { /* ignore */ }
    setSaving(false);
  };

  if (mode === "loading") return <section className="workspace-panel">Loading your Recruitment Profile…</section>;

  if (mode === "summary") {
    return (
      <>
      <section className="workspace-panel" data-testid="module1-summary">
        <h2>Your Board Recruitment Profile</h2>
        {confirmed ? <p className="member-success" data-testid="profile-confirmed-badge"><CheckCircle2 size={15} /> Recruitment Profile Confirmed — Module 2 generation is available.</p> : <p className="workspace-note">Review your profile and confirm it to unlock Module 2 generation.</p>}
        {STEPS.map((stepDef, index) => (
          <div className="profile-summary-group" key={stepDef.heading}>
            <h3>{stepDef.heading}</h3>
            <dl>{stepDef.fields.filter((field) => !field.showIf || field.showIf(data)).map((field) => (
              <div key={field.name}><dt>{field.label}</dt><dd data-testid={`summary-${field.name}`}>{Array.isArray(data[field.name]) ? data[field.name].join(", ") || "—" : data[field.name] || "—"}</dd></div>
            ))}</dl>
          </div>
        ))}
        <div className="material-actions">
          <button className="button button-back" onClick={() => { setStep(0); setMode("form"); }} data-testid="edit-profile-button"><Pencil size={15} /> Edit</button>
          {!confirmed && <button className="button" disabled={saving} onClick={confirm} data-testid="confirm-profile-button">Confirm My Recruitment Profile</button>}
        </div>
      </section>
      {confirmed && <BlueprintPanel />}
      </>
    );
  }

  const fields = visibleFields(step);
  return (
    <section className="workspace-panel" data-testid="module1-profile-form">
      <div className="step-progress">
        <span className="step-count" data-testid="module1-step-count">Step {step + 1} of {STEPS.length}</span>
        <div className="step-progress-bar"><i style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} /></div>
      </div>
      <h2>{STEPS[step].heading}</h2>
      <div className="step-fields" key={step}>
        {fields.map((field) => {
          if (field.type === "choices") {
            return (
              <fieldset className="field choice-field" key={field.name} data-testid={`profile-${field.name}`}>
                <legend>{field.label}{!field.optional && <b> *</b>}</legend>
                <div className="choice-grid">{field.options.map((option) => (
                  <label className={`choice ${data[field.name].includes(option) ? "selected" : ""}`} key={option}>
                    <input type="checkbox" checked={data[field.name].includes(option)} onChange={() => update(field.name, data[field.name].includes(option) ? data[field.name].filter((item) => item !== option) : [...data[field.name], option])} />
                    <span>{option}</span>
                  </label>
                ))}</div>
                {errors[field.name] && <p className="field-error">{errors[field.name]}</p>}
              </fieldset>
            );
          }
          return (
            <label className="field" key={field.name} data-testid={`profile-${field.name}`}>
              <span>{field.label}{!field.optional && <b> *</b>}</span>
              {field.type === "textarea" && <textarea rows="3" value={data[field.name]} onChange={(event) => update(field.name, event.target.value)} />}
              {field.type === "select" && <select value={data[field.name]} onChange={(event) => update(field.name, event.target.value)}><option value="">Select one</option>{field.options.map((option) => <option key={option} value={option}>{option}</option>)}</select>}
              {field.type === "text" && <input value={data[field.name]} onChange={(event) => update(field.name, event.target.value)} />}
              {errors[field.name] && <p className="field-error">{errors[field.name]}</p>}
            </label>
          );
        })}
      </div>
      <div className="step-actions">
        {step > 0 ? <button className="button button-back" onClick={() => setStep(step - 1)} data-testid="module1-back"><ArrowLeft size={15} /> Back</button> : <button className="button button-back" onClick={() => setMode("summary")}>View Summary</button>}
        <button className="button" disabled={saving} onClick={next} data-testid="module1-continue">{saving ? "Saving…" : step === STEPS.length - 1 ? "Review My Recruitment Profile" : <>Continue <ArrowRight size={15} /></>}</button>
      </div>
    </section>
  );
};
