import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, GameProgress } from "./gameShared";

const ACTIVITY_OPTIONS = ["Individual giving", "Major donors", "Recurring donors", "Corporate sponsorships", "Corporate partnerships", "Grants", "Foundations", "Government funding", "Events", "Online fundraising", "Community fundraising", "Other"];
const TECH_OPTIONS = ["CRM", "Donor database", "Email marketing system", "Grant tracking", "Prospect research", "Online donation platform", "Spreadsheets", "No formal system", "Other"];
const MATERIAL_OPTIONS = ["Case for support", "Sponsorship proposal", "Grant materials", "Impact report", "Fundraising emails", "Donation page", "Corporate partnership materials", "Board fundraising resources", "Donor stewardship materials", "Other"];
const YES_NO = ["Yes", "No", "Not sure"];

const STEPS = [
  {
    key: "financial", title: "Current Financial & Fundraising Situation",
    intro: "Help us understand where your fundraising stands today.",
    fields: [
      { key: "annual_budget", label: "Current annual budget / revenue (if you know it)" },
      { key: "raised_last_12m", label: "Approximately how much did you raise through fundraising in the previous 12 months?" },
      { key: "major_income_sources", label: "What are the major sources of your organisation's income?", textarea: true },
    ],
  },
  {
    key: "activities", title: "Existing Fundraising Activities",
    intro: "How are you currently raising money?",
    fields: [
      { key: "methods", label: "Select everything you currently do", checks: ACTIVITY_OPTIONS },
      { key: "methods_detail", label: "Briefly explain how the activities you selected work today", textarea: true },
      { key: "working_well", label: "What is presently working well?", textarea: true },
      { key: "not_working", label: "What is not working as well as you need it to?", textarea: true },
    ],
  },
  {
    key: "team", title: "Existing Fundraising Team",
    intro: "Who is doing the fundraising work right now?",
    fields: [
      { key: "has_team", label: "Do you currently have a fundraising team?", options: YES_NO },
      { key: "who_handles", label: "Who currently handles fundraising?", textarea: true },
      { key: "has_staff", label: "Do you have fundraising staff?", options: YES_NO },
      { key: "uses_consultants", label: "Do you use consultants?", options: YES_NO },
      { key: "board_involvement", label: "How involved is the board currently?", textarea: true },
      { key: "board_member_count", label: "Approximate number of board members" },
    ],
  },
  {
    key: "donors", title: "Existing Individual Donors",
    intro: "Describe your existing donor base.",
    fields: [
      { key: "donor_types", label: "What types of individuals currently give?", textarea: true },
      { key: "why_they_give", label: "Why do you believe these people give?", textarea: true },
      { key: "give_toward", label: "What do they usually give toward?", textarea: true },
      { key: "group_description", label: "How would you describe these donors as a group?", textarea: true },
      { key: "typical_size", label: "Typical donation size (if known)" },
      { key: "recurring", label: "Do you have recurring donors?", options: YES_NO },
      { key: "major", label: "Do you have major donors?", options: YES_NO },
      { key: "stewardship", label: "How do you currently communicate with and steward donors?", textarea: true },
    ],
  },
  {
    key: "corporate", title: "Existing Corporate Sponsors & Partners",
    intro: "Describe your existing business supporters.",
    fields: [
      { key: "business_types", label: "What types of businesses currently support you?", textarea: true },
      { key: "why_support", label: "Why do those businesses support you?", textarea: true },
      { key: "what_support", label: "What do those businesses support?", textarea: true },
      { key: "group_description", label: "How would you describe those businesses as a group?", textarea: true },
      { key: "support_type", label: "What type of support do they provide?", textarea: true },
      { key: "how_connected", label: "How did your organisation originally connect with them?", textarea: true },
      { key: "typical_level", label: "Typical contribution level (if known)" },
    ],
  },
  {
    key: "grantors", title: "Existing Grantors",
    intro: "Describe your existing grantor base.",
    fields: [
      { key: "grantmaker_types", label: "What types of grantmakers currently fund you?", textarea: true },
      { key: "why_fund", label: "Why do you believe those grantmakers fund you?", textarea: true },
      { key: "usually_fund", label: "What do the grantmakers usually fund?", textarea: true },
      { key: "group_description", label: "How would you describe your grantmakers as a group?", textarea: true },
      { key: "typical_size", label: "Typical grant size (if known)" },
      { key: "recurring", label: "Are these recurring or one-time grants?", options: ["Mostly recurring", "Mostly one-time", "A mix", "Not sure"] },
    ],
  },
  {
    key: "technology", title: "Current Fundraising Technology",
    intro: "What do you currently use to manage fundraising?",
    fields: [
      { key: "tools", label: "Select everything you currently use", checks: TECH_OPTIONS },
      { key: "tech_working", label: "What is working well with your current fundraising technology?", textarea: true },
      { key: "tech_missing", label: "What do you believe is missing or needs improvement?", textarea: true },
    ],
  },
  {
    key: "materials", title: "Current Fundraising Materials",
    intro: "Which materials do you currently have?",
    fields: [
      { key: "materials", label: "Select everything you currently have", checks: MATERIAL_OPTIONS },
      { key: "materials_needed", label: "What needs to be created or improved?", textarea: true },
    ],
  },
  {
    key: "reflections", title: "The Big Picture",
    intro: "Last step — your honest read on your fundraising.",
    fields: [
      { key: "working_well", label: "What is presently working well in your fundraising?", textarea: true },
      { key: "limiting", label: "What is presently limiting your organisation's ability to raise more money?", textarea: true },
      { key: "tried", label: "What have you already tried that did not produce the fundraising results you expected?", textarea: true },
      { key: "opportunity", label: "What do you believe is the biggest fundraising opportunity available to your organisation right now?", textarea: true },
      { key: "challenge", label: "What is the biggest thing standing between your organisation and its fundraising goal right now?", textarea: true },
    ],
  },
];

const CheckGroup = ({ options, value, onChange, testId }) => {
  const selected = value || [];
  const toggle = (option) => onChange(selected.includes(option) ? selected.filter((item) => item !== option) : [...selected, option]);
  return (
    <div className="bfg-checks" data-testid={testId}>
      {options.map((option) => (
        <label key={option} className={`bfg-check ${selected.includes(option) ? "checked" : ""}`}>
          <input type="checkbox" checked={selected.includes(option)} onChange={() => toggle(option)} data-testid={`${testId}-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
          {option}
        </label>
      ))}
    </div>
  );
};

export default function GameSituationPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [step, setStep] = useState(0);
  const [sections, setSections] = useState({});
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Complete Your Game Setup | Board Fundraising Game"; }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    memberApi.get("/game/situation").then((response) => {
      if (response.data.completed) { navigate("/game/dashboard", { replace: true }); return; }
      setSections(response.data.sections || {});
      setStep(Math.min(response.data.current_step || 0, STEPS.length - 1));
      setReady(true);
    }).catch((err) => {
      if (err.response?.status === 403) { navigate("/game/start", { replace: true }); return; }
      setReady(true);
    });
  }, [loading, member, navigate]);

  if (loading || !ready) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const config = STEPS[step];
  const section = sections[config.key] || {};
  const setValue = (fieldKey) => (value) => setSections((current) => ({ ...current, [config.key]: { ...(current[config.key] || {}), [fieldKey]: value } }));

  const persist = async (nextStep) => {
    setError(""); setBusy(true); setSaved(false);
    try {
      await memberApi.put("/game/situation", { sections: { [config.key]: sections[config.key] || {} }, current_step: nextStep });
      return true;
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your progress. Please try again.");
      return false;
    } finally {
      setBusy(false);
    }
  };

  const next = async () => {
    if (step === STEPS.length - 1) {
      if (await persist(step)) {
        setBusy(true);
        try {
          await memberApi.post("/game/situation/complete");
          navigate("/game/dashboard");
        } catch {
          setError("We could not complete your setup. Please try again.");
          setBusy(false);
        }
      }
      return;
    }
    if (await persist(step + 1)) { setStep(step + 1); window.scrollTo({ top: 0 }); }
  };

  const saveAndExit = async () => {
    if (await persist(step)) { setSaved(true); navigate("/game/dashboard"); }
  };

  return (
    <BfgShell nav={<button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={saveAndExit} data-testid="bfg-situation-save-exit">Save & Exit</button>}>
      <main className="bfg-flow" data-testid="bfg-situation-page">
        <GameProgress steps={STEPS.map((item) => item.title)} current={step} />
        <div className="bfg-card" data-testid={`bfg-situation-step-${config.key}`}>
          <p className="bfg-eyebrow">Your Current Fundraising Situation</p>
          <h2>{config.title}</h2>
          <p style={{ marginTop: 10 }}>{config.intro}</p>
          {config.fields.map((field) => (
            field.checks ? (
              <label className="bfg-field" key={field.key}>
                <span>{field.label}</span>
                <CheckGroup options={field.checks} value={section[field.key]} onChange={setValue(field.key)} testId={`bfg-${config.key}-${field.key}`} />
              </label>
            ) : field.options ? (
              <label className="bfg-field" key={field.key}>
                <span>{field.label}</span>
                <select value={section[field.key] || ""} onChange={(event) => setValue(field.key)(event.target.value)} data-testid={`bfg-${config.key}-${field.key}`}>
                  <option value="">Select one</option>
                  {field.options.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
            ) : field.textarea ? (
              <label className="bfg-field" key={field.key}>
                <span>{field.label}</span>
                <textarea rows={3} value={section[field.key] || ""} onChange={(event) => setValue(field.key)(event.target.value)} data-testid={`bfg-${config.key}-${field.key}`} />
              </label>
            ) : (
              <label className="bfg-field" key={field.key}>
                <span>{field.label}</span>
                <input value={section[field.key] || ""} onChange={(event) => setValue(field.key)(event.target.value)} data-testid={`bfg-${config.key}-${field.key}`} />
              </label>
            )
          ))}
          {error && <p className="bfg-error" data-testid="bfg-situation-error">{error}</p>}
          {saved && <p className="bfg-success">Progress saved.</p>}
          <div className="bfg-form-actions">
            {step > 0 ? (
              <button className="bfg-btn bfg-btn-ghost" onClick={() => { setStep(step - 1); window.scrollTo({ top: 0 }); }} data-testid="bfg-situation-back">Back</button>
            ) : <span />}
            <button className="bfg-btn bfg-btn-primary" onClick={next} disabled={busy} data-testid="bfg-situation-next">
              {busy ? "Saving…" : step === STEPS.length - 1 ? "Complete My Game Setup" : "Save & Continue"}
            </button>
          </div>
        </div>
      </main>
    </BfgShell>
  );
}
