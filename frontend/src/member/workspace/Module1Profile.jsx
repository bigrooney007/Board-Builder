import React, { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard, printText } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";

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

const detailedBlueprintText = (material) => {
  const structured = material?.versions?.slice().reverse().find((v) => v.structured)?.structured || {};
  const roles = structured.detailed_roles?.length ? structured.detailed_roles : (structured.priority_roles || []);
  const lines = ["BOARD RECRUITMENT PROFILE — DETAILED REPORT", ""];
  roles.forEach((role, index) => {
    lines.push(`${index + 1}. ${role.role_name || ""}`);
    ["summary", "why_this_role_matters", "professional_background_to_look_for", "useful_networks", "how_this_role_contributes", "how_this_complements_the_present_board"].forEach((key) => {
      if (role[key]) lines.push(`${key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())}: ${role[key]}`);
    });
    if (role.relevant_skills?.length) lines.push("Relevant skills: " + role.relevant_skills.join(", "));
    lines.push("");
  });
  return lines.join("\n").trim();
};

export const Module1Profile = ({ onConfirmed }) => {
  const { byType, refresh } = useMaterials();
  const [data, setData] = useState({ current_board_skills: [], current_board_skills_other: "", desired_board_skills: [], desired_board_skills_other: "", ideal_board_additional_notes: "" });
  const [errors, setErrors] = useState({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    memberApi.get("/workspace/profile").then((response) => {
      const profile = response.data.profile || {};
      setData((current) => ({
        ...current,
        current_board_skills: profile.current_board_skills || [],
        current_board_skills_other: profile.current_board_skills_other || "",
        desired_board_skills: profile.desired_board_skills || [],
        desired_board_skills_other: profile.desired_board_skills_other || "",
        ideal_board_additional_notes: profile.ideal_board_additional_notes || "",
      }));
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  const toggle = (key) => (option) => setData((current) => ({ ...current, [key]: current[key].includes(option) ? current[key].filter((item) => item !== option) : [...current[key], option] }));

  const saveAndConfirm = async () => {
    const found = {};
    if (!data.current_board_skills.length) found.current = "Select at least one option (or Other).";
    if (!data.desired_board_skills.length) found.desired = "Select at least one option (or Other).";
    setErrors(found);
    if (Object.keys(found).length) return false;
    await memberApi.put("/workspace/profile", { data });
    await memberApi.post("/workspace/profile/confirm");
    if (onConfirmed) onConfirmed();
    return true;
  };

  if (!loaded) return <section className="workspace-panel">Loading…</section>;

  return (
    <div data-testid="module1-workspace">
      <section className="workspace-panel" data-testid="module1-intake">
        <h2>Identify the Board Members Your Organization Needs</h2>
        <p className="material-description">You have already told us about your organization and the kind of board you want to build. Now tell us what your present board already brings and what you believe is missing. We will use that information to identify the exact board-member profiles your organization should recruit.</p>
        <SkillPicker
          label="What skills, experience and strengths are already represented on your present board?"
          values={data.current_board_skills} other={data.current_board_skills_other}
          onToggle={toggle("current_board_skills")} onOther={(value) => setData({ ...data, current_board_skills_other: value })}
          testId="module1-current-skills" error={errors.current} />
        <SkillPicker
          label="Which skills, experience or relationships would you most like to add to your board?"
          values={data.desired_board_skills} other={data.desired_board_skills_other}
          onToggle={toggle("desired_board_skills")} onOther={(value) => setData({ ...data, desired_board_skills_other: value })}
          testId="module1-desired-skills" error={errors.desired} />
        <label className="field" data-testid="module1-additional-notes">
          <span>Is there anything else you believe your ideal board needs that we have not captured? (optional)</span>
          <textarea rows="3" value={data.ideal_board_additional_notes} onChange={(event) => setData({ ...data, ideal_board_additional_notes: event.target.value })} />
        </label>
        <MaterialCard
          type="powerhouse_board_blueprint"
          title="Your Powerhouse Board Blueprint"
          buttonLabel="Identify the Board Members I Need"
          description="Built from the organization information you have already provided plus your answers above: what your present board already brings, the important gaps, what a powerhouse board looks like for your organization, and one exact profile for each new board member you want to recruit. The saved result drives Modules 2 and 3."
          material={byType.powerhouse_board_blueprint}
          refresh={refresh}
          beforeGenerate={saveAndConfirm}
          extraActions={
            <button className="button button-back" onClick={() => printText("Board Recruitment Profile — Detailed Report", detailedBlueprintText(byType.powerhouse_board_blueprint))} data-testid="download-detailed-blueprint">
              <Download size={14} /> Download Detailed Board Recruitment Profile
            </button>
          }
        />
      </section>
    </div>
  );
};
