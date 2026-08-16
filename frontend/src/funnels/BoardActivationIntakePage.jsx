import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { PAGE_META, usePageMeta } from "@/seo";
import { activationIntakeText } from "../content/appContent";
import { boardActivationIntakePageText } from "../content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const METHOD_OPTIONS = ["Individual Giving", "Major Donors", "Corporate Sponsorships", "Corporate Partnerships", "Foundations / Grants", "Government Funding", "Fundraising Events", "Membership", "Earned Revenue", "Faith Community Support", "Online Fundraising / Campaigns", "Other", "We Do Not Have a Consistent Fundraising Process"];
const CARRIER_OPTIONS = ["Founder", "Executive Director", "Staff", "Board Chair", "A Few Board Members", "Most of the Board", "Fundraising Committee", "Volunteers", "External Fundraising Consultant", "Other", "No One Consistently"];
const INVOLVEMENT_OPTIONS = ["Most Board Members actively participate", "Some Board Members participate", "Very little Board participation", "No meaningful Board fundraising participation", "Not Sure"];
const ACTIVITY_OPTIONS = ["Personal Giving", "Identifying Potential Donors", "Making Introductions", "Donor Meetings", "Corporate Introductions", "Corporate Sponsorship", "Corporate Partnerships", "Grant / Foundation Connections", "Fundraising Events", "Donor Stewardship", "Speaking About the Mission", "Sharing Fundraising Content", "Fundraising Planning", "Asking for Donations", "Other", "None"];
const STEP_TITLES = ["Your Organization's Direction", "Your Fundraising Today", "Who Carries Fundraising", "Your Board & Fundraising", "What You Want to Change"];

const INITIAL = {
  your_name: "", email: "", organization_name: "", direction_12_24: "", organization_priorities: "",
  fundraising_goal: "", amount_needed: "", money_accomplish: "", current_methods: [], current_methods_other: "",
  written_strategy: "", fundraising_calendar: "",
  fundraising_carriers: [], fundraising_carriers_detail: "", present_board: "", active_board: "",
  board_fundraising_involvement: "", board_fundraising_activities: [], board_fundraising_activities_other: "",
  perceived_barriers: "", board_skills_relationships: "",
  previous_fundraising_planning: "", broader_strategic_planning: "", desired_change: "", success_definition: "", anything_else: "",
};

const TextField = ({ label, name, form, set, errors, required = true, type = "text", disabled = false }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span><input type={type} value={form[name]} onChange={set(name)} disabled={disabled} data-testid={`aintake-${name.replace(/_/g, "-")}`} />{errors[name] && <p className="field-error">{errors[name]}</p>}</label>
);

const AreaField = ({ label, name, form, set, errors, required = true, rows = 4 }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span><textarea rows={rows} value={form[name]} onChange={set(name)} data-testid={`aintake-${name.replace(/_/g, "-")}`} />{errors[name] && <p className="field-error">{errors[name]}</p>}</label>
);

const SelectField = ({ label, name, options, form, set, errors, required = true }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span>
    <select value={form[name]} onChange={set(name)} data-testid={`aintake-${name.replace(/_/g, "-")}`}>
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
          <input type="checkbox" checked={form[name].includes(option)} onChange={() => toggle(name, option)} data-testid={`aintake-${name.replace(/_/g, "-")}-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
          <span>{option}</span>
        </label>
      ))}
    </div>
    {errors[name] && <p className="field-error">{errors[name]}</p>}
  </fieldset>
);

export default function BoardActivationIntakePage() {
  usePageMeta(...PAGE_META.boardActivationIntake, true);
  const location = useLocation();
  const sessionId = useMemo(() => new URLSearchParams(location.search).get("session_id") || "", [location.search]);
  const [gate, setGate] = useState(sessionId ? "checking" : "blocked");
  const [calendlyUrl, setCalendlyUrl] = useState("https://calendly.com/boardbuilder/recruitboard");
  const [purchaseSource, setPurchaseSource] = useState("");
  const [nextUrl, setNextUrl] = useState("");
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(INITIAL);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const amountNotSure = form.amount_needed === "Not Sure";

  useEffect(() => {
    if (!sessionId) return undefined;
    let attempts = 0;
    let timer;
    const check = async () => {
      attempts += 1;
      try {
        const response = await axios.get(`${API}/board-activation-intake/context`, { params: { session_id: sessionId } });
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
  const toggleAmountNotSure = () => setForm((current) => ({ ...current, amount_needed: current.amount_needed === "Not Sure" ? "" : "Not Sure" }));

  const REQUIRED_BY_STEP = [
    ["your_name", "email", "organization_name", "direction_12_24", "organization_priorities"],
    ["fundraising_goal", "amount_needed", "money_accomplish", "current_methods", "written_strategy", "fundraising_calendar"],
    ["fundraising_carriers", "present_board", "active_board"],
    ["board_fundraising_involvement", "board_fundraising_activities", "perceived_barriers", "board_skills_relationships"],
    ["previous_fundraising_planning", "broader_strategic_planning", "desired_change", "success_definition"],
  ];

  const validateStep = () => {
    const found = {};
    REQUIRED_BY_STEP[step].forEach((name) => {
      const value = form[name];
      if (Array.isArray(value) ? !value.length : !String(value).trim()) found[name] = "This question is required.";
    });
    if (step === 0 && form.email && !/^\S+@\S+\.\S+$/.test(form.email.trim())) found.email = "Enter a valid email address.";
    if (step === 2 && form.present_board !== "" && form.active_board !== "") {
      const total = Number(form.present_board);
      const active = Number(form.active_board);
      if (Number.isNaN(total) || Number.isNaN(active) || total < 0 || active < 0) found.active_board = "Board counts must be whole numbers of zero or more.";
      else if (active > total) found.active_board = "Active Board Members cannot exceed your total Board Members.";
    }
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
      const response = await axios.post(`${API}/board-activation-intake/submit`, { ...form, session_id: sessionId });
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
      <main data-testid="aintake-page">
        <section className="funnel-hero-banner brp-hero intake-hero" data-testid="aintake-hero">
          <h1 data-testid="aintake-headline">{activationIntakeText.h_tellMeAboutYourFundraising}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="aintake-subtitle">{activationIntakeText.s_giveMeTheInformationI}</p>
          <i aria-hidden="true" />
        </section>

        {gate === "checking" && (
          <div className="intake-card" data-testid="aintake-checking"><h2>{activationIntakeText.h_confirmingYourPayment}</h2><p>{boardActivationIntakePageText.pleaseWaitWhileWeVerify}</p></div>
        )}

        {gate === "blocked" && (
          <div className="intake-card" data-testid="aintake-blocked">
            <h2>{activationIntakeText.h_thisFormIsForCustomers}</h2>
            <p>{boardActivationIntakePageText.weCouldNotFindA}</p>
            <div className="intake-blocked-links">
              <Link className="button" to="/activate-your-board-yourself" data-testid="aintake-blocked-diy-link">{boardActivationIntakePageText.doItYourself497}</Link>
              <Link className="button button-outline" to="/board-activation-proposal" data-testid="aintake-blocked-dwm-link">{boardActivationIntakePageText.doItWithRooney2}</Link>
            </div>
          </div>
        )}

        {gate === "done" && (
          <div className="intake-card" data-testid="aintake-done">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Information saved</p>
            {purchaseSource === "direct_diy_board_activation_497" ? (
              <>
                <h2>{activationIntakeText.h_youreReadyToStart}</h2>
                <p>{boardActivationIntakePageText.takingYouToYourStart}</p>
                <a className="button" href={nextUrl || "/activation-start-here"} data-testid="aintake-start-here-link">{boardActivationIntakePageText.openMyStartPage}</a>
              </>
            ) : (
              <>
                <h2>{activationIntakeText.h_letsScheduleYourCallWith}</h2>
                <p>{boardActivationIntakePageText.takingYouToTheCalendar}</p>
                <a className="button" href={nextUrl || calendlyUrl} data-testid="aintake-calendly-link">Open the Calendar</a>
              </>
            )}
          </div>
        )}

        {gate === "ready" && (
          <section className="intake-shell" data-testid="aintake-form">
            <div className="progress-copy"><span data-testid="aintake-progress-label">Step {step + 1} of 5 — {STEP_TITLES[step]}</span><span>{Math.round(((step + 1) / 5) * 100)}%</span></div>
            <div className="progress-track"><div style={{ width: `${((step + 1) / 5) * 100}%` }} /></div>

            {step === 0 && (
              <div data-testid="aintake-step-1">
                <h2 className="intake-step-title">{activationIntakeText.h_yourOrganizationsDirection}</h2>
                <div className="two-col-fields">
                  <TextField label="Your Name" name="your_name" form={form} set={set} errors={errors} />
                  <TextField label="Email Address" name="email" type="email" form={form} set={set} errors={errors} />
                </div>
                <TextField label="Organization Name" name="organization_name" form={form} set={set} errors={errors} />
                <AreaField label="Where Is the Organization Trying to Go Over the Next 12–24 Months?" name="direction_12_24" form={form} set={set} errors={errors} />
                <AreaField label="What Are the Most Important Priorities the Organization Needs to Fund or Move Forward Right Now?" name="organization_priorities" form={form} set={set} errors={errors} />
              </div>
            )}

            {step === 1 && (
              <div data-testid="aintake-step-2">
                <h2 className="intake-step-title">{activationIntakeText.h_yourFundraisingToday}</h2>
                <AreaField label="What Is Your Organization's Fundraising Goal for the Next 12 Months?" name="fundraising_goal" form={form} set={set} errors={errors} />
                <TextField label="How Much Money Does Your Organization Need to Raise Over the Next 12 Months?" name="amount_needed" form={form} set={set} errors={errors} disabled={amountNotSure} />
                <label className="choice" style={{ marginTop: -8, marginBottom: 14, display: "inline-flex" }}>
                  <input type="checkbox" checked={amountNotSure} onChange={toggleAmountNotSure} data-testid="aintake-amount-not-sure" />
                  <span>Not Sure</span>
                </label>
                <AreaField label="What Will This Money Help Your Organization Accomplish?" name="money_accomplish" form={form} set={set} errors={errors} />
                <MultiField legend="How Is Your Organization Currently Raising Money?" name="current_methods" options={METHOD_OPTIONS} form={form} toggle={toggle} errors={errors} />
                {form.current_methods.includes("Other") && (
                  <TextField label="Tell us how else your organization raises money" name="current_methods_other" required={false} form={form} set={set} errors={errors} />
                )}
                <SelectField label="Does Your Organization Currently Have a Written Fundraising Strategy?" name="written_strategy" options={["Yes", "Partially", "No"]} form={form} set={set} errors={errors} />
                <SelectField label="Does Your Organization Currently Have a Fundraising Calendar or Clear Execution Plan That Tells People What Fundraising Activity Should Happen and When?" name="fundraising_calendar" options={["Yes", "Partially", "No", "Not Sure"]} form={form} set={set} errors={errors} />
              </div>
            )}

            {step === 2 && (
              <div data-testid="aintake-step-3">
                <h2 className="intake-step-title">{activationIntakeText.h_whoCarriesFundraising}</h2>
                <MultiField legend="Who Currently Carries Most of the Fundraising Responsibility in Your Organization?" name="fundraising_carriers" options={CARRIER_OPTIONS} form={form} toggle={toggle} errors={errors} />
                <AreaField label="Anything you want to add about how fundraising responsibility currently works?" name="fundraising_carriers_detail" required={false} rows={3} form={form} set={set} errors={errors} />
                <TextField label="How Many Board Members Do You Currently Have?" name="present_board" type="number" form={form} set={set} errors={errors} />
                <TextField label="How Many of Those Board Members Are Currently Active?" name="active_board" type="number" form={form} set={set} errors={errors} />
              </div>
            )}

            {step === 3 && (
              <div data-testid="aintake-step-4">
                <h2 className="intake-step-title">{activationIntakeText.h_yourBoardFundraising}</h2>
                <SelectField label="How Involved Is Your Board in Fundraising Today?" name="board_fundraising_involvement" options={INVOLVEMENT_OPTIONS} form={form} set={set} errors={errors} />
                <MultiField legend="What Fundraising Activities Are Your Board Members Currently Involved In?" name="board_fundraising_activities" options={ACTIVITY_OPTIONS} form={form} toggle={toggle} errors={errors} />
                {form.board_fundraising_activities.includes("Other") && (
                  <TextField label="Tell us what other fundraising activities your Board is involved in" name="board_fundraising_activities_other" required={false} form={form} set={set} errors={errors} />
                )}
                <AreaField label="What Do You Believe Is Preventing Your Board Members From Becoming More Involved in Fundraising?" name="perceived_barriers" form={form} set={set} errors={errors} />
                <AreaField label="What Skills, Professional Experience, Relationships or Networks Already Exist Around Your Board That Could Help With Fundraising? (You can write Not Sure.)" name="board_skills_relationships" form={form} set={set} errors={errors} />
              </div>
            )}

            {step === 4 && (
              <div data-testid="aintake-step-5">
                <h2 className="intake-step-title">{activationIntakeText.h_whatYouWantToChange}</h2>
                <SelectField label="Has Your Board Previously Participated in Developing a Fundraising Plan?" name="previous_fundraising_planning" options={["Yes", "Partially", "No", "Not Sure"]} form={form} set={set} errors={errors} />
                <SelectField label="Has Your Board Participated in Broader Organizational or Strategic Planning?" name="broader_strategic_planning" options={["Yes", "Partially", "No", "Not Sure"]} form={form} set={set} errors={errors} />
                <AreaField label="What Would You Most Like to Change About Your Board's Involvement in Fundraising?" name="desired_change" form={form} set={set} errors={errors} />
                <AreaField label="What Would a Successful Fundraising Board Look Like for Your Organization?" name="success_definition" form={form} set={set} errors={errors} />
                <AreaField label="Is There Anything Else I Should Understand About Your Board or Fundraising Situation?" name="anything_else" required={false} rows={3} form={form} set={set} errors={errors} />
              </div>
            )}

            {submitError && <p className="submit-error" data-testid="aintake-submit-error">{submitError}</p>}
            <div className="intake-nav">
              {step > 0 ? <button type="button" className="button button-outline" onClick={back} data-testid="aintake-back-button">Back</button> : <span />}
              {step < 4 ? (
                <button type="button" className="button" onClick={next} data-testid="aintake-next-button">Next</button>
              ) : (
                <button type="button" className="button" onClick={submit} disabled={busy} data-testid="aintake-submit-button">{busy ? "Saving…" : "Submit"}</button>
              )}
            </div>
          </section>
        )}
      </main>
    </FunnelLayout>
  );
}
