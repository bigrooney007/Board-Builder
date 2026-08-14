import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { memberApi } from "../api";
import { MaterialCard } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";
import { recruitmentContent } from "../../content/appContent";

export const SKILL_OPTIONS = ["Fundraising", "Corporate Partnerships", "Major Donors", "Grant Development", "Finance", "Accounting", "Governance", "Legal", "Marketing", "Communications", "Public Relations", "Community Relationships", "Strategic Planning", "Human Resources", "Technology", "Program Development", "Operations", "Government/Public Policy", "Healthcare", "Education", "Professional/Business Connections", "Lived Experience", "Other"];

const SkillPicker = ({ label, values, other, onToggle, onOther, testId, error }) => (
  <fieldset className="field choice-field" data-testid={testId}>
    <legend>{label} <b>*</b></legend>
    <div className="choice-grid">{SKILL_OPTIONS.map((option) => (
      <label className={`choice ${values.includes(option) ? "selected" : ""}`} key={option}>
        <input type="checkbox" checked={values.includes(option)} onChange={() => onToggle(option)} />
        <span>{option}</span>
      </label>
    ))}</div>
    {values.includes("Other") && (
      <label className="field"><span>Tell us about the other skills or experience</span>
        <input value={other} onChange={(event) => onOther(event.target.value)} data-testid={`${testId}-other`} />
      </label>
    )}
    {error && <p className="field-error">{error}</p>}
  </fieldset>
);

const KNOWN_ROWS = [
  ["organization_name", "Organization"],
  ["mission", "Mission"],
  ["board_kind", "Board type"],
  ["present_board", "Current board members"],
  ["active_board", "Actively participating"],
  ["new_members_count", "New board members to recruit"],
  ["current_board_strengths", "Present board strengths"],
  ["board_challenges", "Board challenges"],
  ["desired_board_skills", "Skills and experience to add"],
  ["priorities", "What new board members should help accomplish"],
];

const KnownInfoSummary = ({ data }) => {
  const rows = KNOWN_ROWS
    .map(([key, label]) => {
      const value = data[key];
      if (Array.isArray(value)) return value.length ? [label, value.join(", ")] : null;
      return value ? [label, String(value)] : null;
    })
    .filter(Boolean);
  if (!rows.length) return null;
  return (
    <div className="known-info-summary" data-testid="module1-known-info">
      <h3>What We Already Know About Your Organization and Board</h3>
      <p className="material-description">You provided this information when you got started — you never need to enter it again. It is used automatically throughout your recruitment process.</p>
      <dl>
        {rows.map(([label, value]) => (
          <div className="known-info-row" key={label}><dt>{label}</dt><dd>{value}</dd></div>
        ))}
      </dl>
    </div>
  );
};

export const Module1Profile = ({ onConfirmed }) => {
  const { byType, refresh } = useMaterials();
  const [stored, setStored] = useState({});
  const [form, setForm] = useState({ organization_name: "", mission: "", current_board_skills: [], current_board_skills_other: "", desired_board_skills: [], desired_board_skills_other: "" });
  const [errors, setErrors] = useState({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    memberApi.get("/workspace/profile").then((response) => {
      const profile = response.data.profile || {};
      const prefill = response.data.prefill || {};
      setStored({ ...prefill, ...Object.fromEntries(Object.entries(profile).filter(([, v]) => v !== "" && v !== null && !(Array.isArray(v) && !v.length))) });
      setForm((current) => ({
        ...current,
        organization_name: profile.organization_name || prefill.organization_name || "",
        mission: profile.mission || "",
        current_board_skills: profile.current_board_skills || [],
        current_board_skills_other: profile.current_board_skills_other || "",
        desired_board_skills: profile.desired_board_skills || [],
        desired_board_skills_other: profile.desired_board_skills_other || "",
      }));
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  const askOrgName = loaded && !(stored.organization_name || "").trim();
  const askMission = loaded && !(stored.mission || "").trim();
  const askDesiredSkills = loaded && !(stored.desired_board_skills || []).length;
  const askCurrentSkills = loaded && !(stored.current_board_skills || []).length && !(stored.current_board_strengths || "").trim();

  const toggle = (key) => (option) => setForm((current) => ({ ...current, [key]: current[key].includes(option) ? current[key].filter((item) => item !== option) : [...current[key], option] }));

  const saveAndConfirm = async () => {
    const found = {};
    if (askOrgName && !form.organization_name.trim()) found.organization_name = "Enter your organization name.";
    if (askMission && !form.mission.trim()) found.mission = "Enter your mission statement.";
    if (askDesiredSkills && !form.desired_board_skills.length) found.desired = "Select at least one option (or Other).";
    setErrors(found);
    if (Object.keys(found).length) return false;
    const payload = {};
    if (askOrgName) payload.organization_name = form.organization_name;
    if (askMission) payload.mission = form.mission;
    if (askDesiredSkills) {
      payload.desired_board_skills = form.desired_board_skills;
      payload.desired_board_skills_other = form.desired_board_skills_other;
    }
    if (askCurrentSkills && form.current_board_skills.length) {
      payload.current_board_skills = form.current_board_skills;
      payload.current_board_skills_other = form.current_board_skills_other;
    }
    await memberApi.put("/workspace/profile", { data: payload });
    await memberApi.post("/workspace/profile/confirm");
    if (onConfirmed) onConfirmed();
    return true;
  };

  if (!loaded) return <section className="workspace-panel">Loading…</section>;

  const askingAnything = askOrgName || askMission || askDesiredSkills || askCurrentSkills;

  return (
    <div data-testid="module1-workspace">
      <section className="workspace-panel" data-testid="module1-intake">
        <h2>The Board Members Your Organization Needs</h2>
        <p className="material-description">Based on the information you provided about your organization and board, we will identify the board members your nonprofit should prioritize recruiting.</p>
        <KnownInfoSummary data={stored} />
        {askingAnything && (
          <p className="workspace-note" data-testid="module1-missing-info-note">We just need a little more information before we identify your board members. You only enter it once.</p>
        )}
        {askOrgName && (
          <label className="field"><span>Organization name <b>*</b></span>
            <input value={form.organization_name} onChange={(event) => setForm({ ...form, organization_name: event.target.value })} data-testid="module1-organization-name" />
            {errors.organization_name && <p className="field-error">{errors.organization_name}</p>}
          </label>
        )}
        {askMission && (
          <label className="field"><span>What is your organization's mission statement? <b>*</b></span>
            <textarea rows="3" value={form.mission} onChange={(event) => setForm({ ...form, mission: event.target.value })} data-testid="module1-mission" />
            <span className="field-helper">Enter the mission statement you want applicants, board members and supporters to see in your Recruitment materials. You only enter it once — it is used automatically everywhere it belongs.</span>
            {errors.mission && <p className="field-error">{errors.mission}</p>}
          </label>
        )}
        {askCurrentSkills && (
          <SkillPicker
            label="What skills, experience and strengths are already represented on your present board?"
            values={form.current_board_skills} other={form.current_board_skills_other}
            onToggle={toggle("current_board_skills")} onOther={(value) => setForm({ ...form, current_board_skills_other: value })}
            testId="module1-current-skills" error={errors.current} />
        )}
        {askDesiredSkills && (
          <SkillPicker
            label="Which skills, experience or relationships would you most like to add to your board?"
            values={form.desired_board_skills} other={form.desired_board_skills_other}
            onToggle={toggle("desired_board_skills")} onOther={(value) => setForm({ ...form, desired_board_skills_other: value })}
            testId="module1-desired-skills" error={errors.desired} />
        )}
        <MaterialCard
          type="powerhouse_board_blueprint"
          title="The Board Members Your Organization Needs"
          buttonLabel={recruitmentContent.module2.generateBoardButton}
          description="One exact profile for each new board member you want to recruit — who they are, why they matter to your organization and what to look for. Read it, edit anything you want changed, then approve it. The approved result is used automatically throughout your recruitment campaign."
          material={byType.powerhouse_board_blueprint}
          refresh={refresh}
          beforeGenerate={saveAndConfirm}
          approvable
        />
        {byType.powerhouse_board_blueprint && (
          <div className="material-actions" style={{ marginTop: 18 }}>
            <Link className="button" to="/app/recruitment/self-guided/module/3" data-testid="continue-to-step-2">
              Continue to Step 3 — Launch Your Recruitment Campaign
            </Link>
          </div>
        )}
      </section>
    </div>
  );
};
