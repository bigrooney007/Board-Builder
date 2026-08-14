import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RECRUITED_OPTIONS = ["Friends / Family / Personal Relationships", "Professional Network", "Referrals", "Public Recruitment", "Volunteers / Supporters", "Founding Team", "Other"];
const SIGN_OPTIONS = ["Missing Board meetings", "Attending but rarely participating", "Not completing agreed responsibilities", "Not fundraising", "Not making introductions", "Not serving on committees", "Not responding to communication", "Leaving most of the work to the founder", "Unclear about their role", "Other"];
const TRANSITION_OPTIONS = ["Step Down From the Board", "Transition to an Advisory Board / Advisory Role", "Transition to Another Volunteer/Support Role", "Other", "We Have Not Decided Yet"];
const STEP_TITLES = ["Your Organization's Direction", "Your Current Board", "How Your Board Was Built", "Disengagement", "Meetings & Transitions"];

const INITIAL = {
  your_name: "", email: "", organization_name: "", mission: "", direction_12_24: "", board_help_accomplish: "", active_board_vision: "",
  present_board: "", active_board: "", disengaged_board: "", current_skills: "", missing_skills: "",
  recruited_how: [], original_responsibilities: "", roles_defined: "", roles_description: "", expected_contribution: "", actually_happening: "",
  strategic_plan: "", board_participated_planning: "", planning_involvement: "",
  disengage_reason: "", disengage_when: "", disengagement_signs: [], disengagement_signs_other: "", reactivation_attempts: "", attempts_outcome: "",
  meeting_frequency: "", typical_meeting: "", clear_responsibilities_after_meetings: "", transition_options: [], anything_else: "",
  has_bylaws: "", resignation_process: "",
};

const TextField = ({ label, name, form, set, errors, required = true, type = "text" }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span><input type={type} value={form[name]} onChange={set(name)} data-testid={`rintake-${name.replace(/_/g, "-")}`} />{errors[name] && <p className="field-error">{errors[name]}</p>}</label>
);

const AreaField = ({ label, name, form, set, errors, required = true, rows = 4 }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span><textarea rows={rows} value={form[name]} onChange={set(name)} data-testid={`rintake-${name.replace(/_/g, "-")}`} />{errors[name] && <p className="field-error">{errors[name]}</p>}</label>
);

const SelectField = ({ label, name, options, form, set, errors, required = true }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span>
    <select value={form[name]} onChange={set(name)} data-testid={`rintake-${name.replace(/_/g, "-")}`}>
      <option value="">Choose one…</option>
      {options.map((option) => <option key={option}>{option}</option>)}
    </select>
    {errors[name] && <p className="field-error">{errors[name]}</p>}
  </label>
);

const MultiField = ({ legend, name, options, form, toggle, errors }) => (
  <fieldset className="field choice-field">
    <legend>{legend} <b>*</b></legend>
    <div className="choice-grid">
      {options.map((option) => (
        <label className={`choice ${form[name].includes(option) ? "selected" : ""}`} key={option}>
          <input type="checkbox" checked={form[name].includes(option)} onChange={() => toggle(name, option)} data-testid={`rintake-${name.replace(/_/g, "-")}-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
          <span>{option}</span>
        </label>
      ))}
    </div>
    {errors[name] && <p className="field-error">{errors[name]}</p>}
  </fieldset>
);

export default function BoardReactivationIntakePage() {
  usePageMeta(...PAGE_META.boardReactivationIntake, true);
  const location = useLocation();
  const sessionId = useMemo(() => new URLSearchParams(location.search).get("session_id") || "", [location.search]);
  const [gate, setGate] = useState(sessionId ? "checking" : "blocked");
  const [calendlyUrl, setCalendlyUrl] = useState("https://calendly.com/boardbuilder/recruitboard");
  const [purchaseSource, setPurchaseSource] = useState("");
  const [nextUrl, setNextUrl] = useState("");
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(INITIAL);
  const [bylawsFile, setBylawsFile] = useState(null);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    if (!sessionId) return undefined;
    let attempts = 0;
    let timer;
    const check = async () => {
      attempts += 1;
      try {
        const response = await axios.get(`${API}/board-reactivation-intake/context`, { params: { session_id: sessionId } });
        setCalendlyUrl(response.data.calendly_url);
        setPurchaseSource(response.data.purchase_source);
        setForm((current) => {
          const merged = { ...current };
          Object.entries(response.data.organization_prefill || {}).forEach(([key, value]) => {
            if (key in merged && !merged[key]) merged[key] = value;
          });
          merged.your_name = merged.your_name || response.data.prefill.name || "";
          merged.email = merged.email || response.data.prefill.email || "";
          return merged;
        });
        setGate("ready");
        return;
      } catch (error) {
        if (error.response?.status === 402 && attempts < 8) { timer = setTimeout(check, 2500); return; }
        setGate("blocked");
      }
    };
    check();
    return () => clearTimeout(timer);
  }, [sessionId]);

  const set = (name) => (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  const toggle = (name, option) => setForm((current) => ({
    ...current,
    [name]: current[name].includes(option) ? current[name].filter((item) => item !== option) : [...current[name], option],
  }));

  const REQUIRED_BY_STEP = [
    ["your_name", "email", "organization_name", "mission", "direction_12_24", "board_help_accomplish", "active_board_vision"],
    ["present_board", "active_board", "disengaged_board", "current_skills", "missing_skills"],
    ["recruited_how", "original_responsibilities", "roles_defined", "expected_contribution", "actually_happening"],
    ["strategic_plan", "board_participated_planning", "disengage_reason", "disengage_when", "disengagement_signs", "reactivation_attempts", "attempts_outcome"],
    ["meeting_frequency", "typical_meeting", "clear_responsibilities_after_meetings", "transition_options"],
  ];

  const validateStep = () => {
    const found = {};
    REQUIRED_BY_STEP[step].forEach((name) => {
      const value = form[name];
      if (Array.isArray(value) ? !value.length : !String(value).trim()) found[name] = "This question is required.";
    });
    if (step === 0 && form.email && !/^\S+@\S+\.\S+$/.test(form.email.trim())) found.email = "Enter a valid email address.";
    setErrors(found);
    return !Object.keys(found).length;
  };

  const next = () => { if (validateStep()) { setStep(step + 1); window.scrollTo(0, 0); } };
  const back = () => { setStep(step - 1); setErrors({}); window.scrollTo(0, 0); };

  const submit = async () => {
    if (!validateStep()) return;
    setBusy(true);
    setSubmitError("");
    try {
      const response = await axios.post(`${API}/board-reactivation-intake/submit`, { ...form, session_id: sessionId });
      if (form.has_bylaws === "Yes, I have them" && bylawsFile) {
        try {
          const upload = new FormData();
          upload.append("session_id", sessionId);
          upload.append("file", bylawsFile);
          await axios.post(`${API}/board-reactivation-intake/bylaws`, upload);
        } catch { /* bylaws are optional — never block completion */ }
      }
      setNextUrl(response.data.redirect_url);
      setGate("done");
      setTimeout(() => window.location.replace(response.data.redirect_url), 1500);
    } catch (error) {
      setSubmitError(error.response?.data?.detail || "We could not save your information. Please try again.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="rintake-page">
        <section className="funnel-hero-banner brp-hero intake-hero" data-testid="rintake-hero">
          <h1 data-testid="rintake-headline">Tell Me About Your Board</h1>
          <p className="funnel-hero-banner-supporting" data-testid="rintake-subtitle">Give me the information I need to start reactivating your Board. Ask once — remembered throughout your Reactivation journey.</p>
          <i aria-hidden="true" />
        </section>

        {gate === "checking" && (
          <div className="intake-card" data-testid="rintake-checking"><h2>Confirming Your Payment…</h2><p>Please wait while we verify your payment with Stripe.</p></div>
        )}

        {gate === "blocked" && (
          <div className="intake-card" data-testid="rintake-blocked">
            <h2>This Form Is for Customers Who Have Completed Payment</h2>
            <p>We could not find a completed qualifying purchase. If you just paid, please use the link Stripe returned you to. Otherwise, choose how you would like to reactivate your board:</p>
            <div className="intake-blocked-links">
              <Link className="button" to="/reactivate-your-board-yourself" data-testid="rintake-blocked-diy-link">Do It Yourself — $497</Link>
              <Link className="button button-outline" to="/board-reactivation-proposal" data-testid="rintake-blocked-dwm-link">Do It With Me — $1,997</Link>
            </div>
          </div>
        )}

        {gate === "done" && (
          <div className="intake-card" data-testid="rintake-done">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Information saved</p>
            {purchaseSource === "direct_diy_board_reactivation_497" ? (
              <>
                <h2>You're Ready to Start</h2>
                <p>Taking you to your start page…</p>
                <a className="button" href={nextUrl || "/reactivation-start-here"} data-testid="rintake-start-here-link">Open My Start Page</a>
              </>
            ) : (
              <>
                <h2>Let's Schedule Your Call With Rooney</h2>
                <p>Taking you to the calendar…</p>
                <a className="button" href={nextUrl || calendlyUrl} data-testid="rintake-calendly-link">Open the Calendar</a>
              </>
            )}
          </div>
        )}

        {gate === "ready" && (
          <section className="intake-shell" data-testid="rintake-form">
            <div className="progress-copy"><span data-testid="rintake-progress-label">Step {step + 1} of 5 — {STEP_TITLES[step]}</span><span>{Math.round(((step + 1) / 5) * 100)}%</span></div>
            <div className="progress-track"><div style={{ width: `${((step + 1) / 5) * 100}%` }} /></div>

            {step === 0 && (
              <div data-testid="rintake-step-1">
                <h2 className="intake-step-title">Your Organization's Direction</h2>
                <div className="two-col-fields">
                  <TextField label="Your Name" name="your_name" form={form} set={set} errors={errors} />
                  <TextField label="Email Address" name="email" type="email" form={form} set={set} errors={errors} />
                </div>
                <TextField label="Organization Name" name="organization_name" form={form} set={set} errors={errors} />
                <AreaField label="Organization Mission" name="mission" rows={3} form={form} set={set} errors={errors} />
                <AreaField label="Where Is the Organization Trying to Go Over the Next 12–24 Months?" name="direction_12_24" form={form} set={set} errors={errors} />
                <AreaField label="What Do You Need Your Board to Help the Organization Accomplish?" name="board_help_accomplish" form={form} set={set} errors={errors} />
                <AreaField label="What Would an Active, Functioning Board Look Like to You?" name="active_board_vision" form={form} set={set} errors={errors} />
              </div>
            )}

            {step === 1 && (
              <div data-testid="rintake-step-2">
                <h2 className="intake-step-title">Your Current Board</h2>
                <TextField label="How Many Board Members Do You Currently Have?" name="present_board" type="number" form={form} set={set} errors={errors} />
                <TextField label="How Many Are Actively Participating?" name="active_board" type="number" form={form} set={set} errors={errors} />
                <TextField label="How Many Are Currently Disengaged or Inactive?" name="disengaged_board" type="number" form={form} set={set} errors={errors} />
                <AreaField label="What Professional Skills and Experience Currently Exist on Your Board?" name="current_skills" form={form} set={set} errors={errors} />
                <AreaField label="What Important Skills, Experience or Relationships Are Missing?" name="missing_skills" form={form} set={set} errors={errors} />
              </div>
            )}

            {step === 2 && (
              <div data-testid="rintake-step-3">
                <h2 className="intake-step-title">How Your Board Was Built</h2>
                <MultiField legend="How Were Most of Your Current Board Members Originally Recruited?" name="recruited_how" options={RECRUITED_OPTIONS} form={form} toggle={toggle} errors={errors} />
                <AreaField label="What Were Board Members Told Their Responsibilities Would Be When They Joined?" name="original_responsibilities" form={form} set={set} errors={errors} />
                <SelectField label="Do Your Current Board Members Have Clearly Defined Roles or Areas of Responsibility?" name="roles_defined" options={["Yes", "Some Do", "No", "Not Sure"]} form={form} set={set} errors={errors} />
                {["Yes", "Some Do"].includes(form.roles_defined) && (
                  <AreaField label="Describe How Responsibilities Are Currently Assigned" name="roles_description" required={false} rows={3} form={form} set={set} errors={errors} />
                )}
                <AreaField label="What Are Board Members Currently Expected to Contribute?" name="expected_contribution" form={form} set={set} errors={errors} />
                <AreaField label="What Is Actually Happening Instead?" name="actually_happening" form={form} set={set} errors={errors} />
              </div>
            )}

            {step === 3 && (
              <div data-testid="rintake-step-4">
                <h2 className="intake-step-title">Disengagement</h2>
                <SelectField label="Does the Organization Currently Have a Strategic Plan?" name="strategic_plan" options={["Yes", "No", "In Progress"]} form={form} set={set} errors={errors} />
                <SelectField label="Have Your Current Board Members Participated in Creating or Adopting the Organization's Strategic Direction?" name="board_participated_planning" options={["Yes", "Some Members", "No", "Not Sure"]} form={form} set={set} errors={errors} />
                <AreaField label="If relevant, briefly explain how the Board has been involved in planning." name="planning_involvement" required={false} rows={3} form={form} set={set} errors={errors} />
                <AreaField label="Why Do You Believe Your Board Members Became Disengaged?" name="disengage_reason" form={form} set={set} errors={errors} />
                <TextField label="When Did You Begin Noticing the Disengagement?" name="disengage_when" form={form} set={set} errors={errors} />
                <MultiField legend="What Does Board Disengagement Currently Look Like?" name="disengagement_signs" options={SIGN_OPTIONS} form={form} toggle={toggle} errors={errors} />
                {form.disengagement_signs.includes("Other") && (
                  <TextField label="Tell us what else disengagement looks like" name="disengagement_signs_other" required={false} form={form} set={set} errors={errors} />
                )}
                <AreaField label="What Have You Already Tried to Reactivate the Board?" name="reactivation_attempts" form={form} set={set} errors={errors} />
                <AreaField label="What Happened When You Tried?" name="attempts_outcome" form={form} set={set} errors={errors} />
              </div>
            )}

            {step === 4 && (
              <div data-testid="rintake-step-5">
                <h2 className="intake-step-title">Meetings & Transitions</h2>
                <SelectField label="How Often Does Your Board Meet?" name="meeting_frequency" options={["Monthly", "Every Other Month", "Quarterly", "Rarely / Irregularly", "We Are Not Currently Meeting", "Other"]} form={form} set={set} errors={errors} />
                <AreaField label="What Does a Typical Board Meeting Currently Look Like?" name="typical_meeting" form={form} set={set} errors={errors} />
                <SelectField label="Do Board Members normally leave meetings with clear individual responsibilities?" name="clear_responsibilities_after_meetings" options={["Yes", "Sometimes", "No"]} form={form} set={set} errors={errors} />
                <MultiField legend="If a Board Member is no longer willing or able to serve actively, what options would your organization be open to considering?" name="transition_options" options={TRANSITION_OPTIONS} form={form} toggle={toggle} errors={errors} />
                <SelectField label="Do you have your organization's bylaws?" name="has_bylaws" options={["Yes, I have them", "No, I don't have them"]} form={form} set={set} errors={errors} />
                {form.has_bylaws === "Yes, I have them" && (
                  <label className="field" data-testid="rintake-bylaws-upload">
                    <span>Upload your organization's bylaws (PDF, Word or text)</span>
                    <input type="file" accept=".pdf,.doc,.docx,.txt" onChange={(event) => setBylawsFile(event.target.files?.[0] || null)} data-testid="rintake-bylaws-file" />
                    {bylawsFile && <span className="field-helper">Selected: {bylawsFile.name}</span>}
                  </label>
                )}
                {form.has_bylaws === "No, I don't have them" && (
                  <AreaField label="Please describe your organization's board resignation process." name="resignation_process" required={false} rows={3} form={form} set={set} errors={errors} />
                )}
                <AreaField label="Is There Anything Else I Should Know About Your Board Before We Begin?" name="anything_else" required={false} rows={3} form={form} set={set} errors={errors} />
              </div>
            )}

            {submitError && <p className="submit-error" data-testid="rintake-submit-error">{submitError}</p>}
            <div className="intake-nav">
              {step > 0 ? <button type="button" className="button button-outline" onClick={back} data-testid="rintake-back-button">Back</button> : <span />}
              {step < 4 ? (
                <button type="button" className="button" onClick={next} data-testid="rintake-next-button">Next</button>
              ) : (
                <button type="button" className="button" onClick={submit} disabled={busy} data-testid="rintake-submit-button">{busy ? "Saving…" : "Submit"}</button>
              )}
            </div>
          </section>
        )}
      </main>
    </FunnelLayout>
  );
}
