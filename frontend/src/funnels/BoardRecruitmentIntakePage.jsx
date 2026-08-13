import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SKILL_OPTIONS = ["Fundraising", "Marketing / Communications", "Finance / Accounting", "Legal", "Business Leadership", "Corporate Partnerships", "Operations", "Human Resources", "Program Development", "Education", "Youth Development", "Healthcare / Mental Health", "Technology / AI", "Community Development", "Nonprofit Leadership", "Other"];
const STEP_TITLES = ["About You and Your Organization", "LinkedIn", "Your Present Board", "The Board You Need", "Board Logistics"];

const isUrl = (value) => /^https?:\/\/[^\s]+\.[^\s]+/.test(value.trim()) || /^[^\s]+\.[^\s]+\/?[^\s]*$/.test(value.trim());

const INITIAL = {
  your_name: "", email: "", organization_name: "", website: "", mission: "", city: "", state: "", board_type: "",
  org_linkedin: "", org_linkedin_url: "", personal_linkedin: "", personal_linkedin_url: "",
  present_board: "", present_board_not_sure: false, active_board: "", active_board_not_sure: false,
  new_members_count: "", new_members_not_sure: false, current_board_strengths: "", board_challenges: "",
  desired_skills: [], desired_skills_other: "", accomplish: "", specific_wants: "",
  meeting_frequency: "", meeting_frequency_other: "", meeting_format: "", meeting_location: "", virtual_meeting_info: "",
  board_term: "", board_term_other: "", time_commitment: "", max_board_size: "", max_board_size_unknown: false,
  application_deadline: "", deadline_date: "", anything_else: "",
};

const NumberOrNotSure = ({ label, value, notSure, onValue, onNotSure, testId, error }) => (
  <label className="field">
    <span>{label} <b>*</b></span>
    <input type="number" min="0" disabled={notSure} value={value} onChange={(event) => onValue(event.target.value)} data-testid={testId} />
    <span className="choice intake-not-sure"><input type="checkbox" checked={notSure} onChange={(event) => onNotSure(event.target.checked)} data-testid={`${testId}-not-sure`} /><span>Not Sure</span></span>
    {error && <p className="field-error">{error}</p>}
  </label>
);

const YesNo = ({ legend, value, onChange, testId, error }) => (
  <fieldset className="field choice-field">
    <legend>{legend} <b>*</b></legend>
    <div className="intake-yesno-row">
      {["Yes", "No"].map((option) => (
        <label className={`choice ${value === option ? "selected" : ""}`} key={option}>
          <input type="radio" checked={value === option} onChange={() => onChange(option)} data-testid={`${testId}-${option.toLowerCase()}`} />
          <span>{option}</span>
        </label>
      ))}
    </div>
    {error && <p className="field-error">{error}</p>}
  </fieldset>
);

export default function BoardRecruitmentIntakePage() {
  usePageMeta(...PAGE_META.boardRecruitmentIntake, true);
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

  useEffect(() => {
    if (!sessionId) return undefined;
    let attempts = 0;
    let timer;
    const check = async () => {
      attempts += 1;
      try {
        const response = await axios.get(`${API}/board-recruitment-intake/context`, { params: { session_id: sessionId } });
        setCalendlyUrl(response.data.calendly_url);
        setPurchaseSource(response.data.purchase_source);
        setForm((current) => {
          const merged = { ...current };
          const orgPrefill = response.data.organization_prefill || {};
          Object.entries(orgPrefill).forEach(([key, value]) => {
            if (!(key in merged)) return;
            const empty = Array.isArray(merged[key]) ? merged[key].length === 0 : !merged[key];
            if (empty) merged[key] = value;
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
  const setValue = (name) => (value) => setForm((current) => ({ ...current, [name]: value }));
  const toggleSkill = (option) => setForm((current) => ({
    ...current,
    desired_skills: current.desired_skills.includes(option) ? current.desired_skills.filter((item) => item !== option) : [...current.desired_skills, option],
  }));

  const validateStep = () => {
    const found = {};
    if (step === 0) {
      if (!form.your_name.trim()) found.your_name = "Enter your name.";
      if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) found.email = "Enter a valid email address.";
      if (!form.organization_name.trim()) found.organization_name = "Enter your organization name.";
      if (!form.mission.trim()) found.mission = "Enter your mission.";
      if (!form.city.trim()) found.city = "Enter your city.";
      if (!form.state.trim()) found.state = "Enter your state.";
      if (!form.board_type) found.board_type = "Choose your board type.";
    }
    if (step === 1) {
      if (!form.org_linkedin) found.org_linkedin = "Please choose an answer.";
      if (form.org_linkedin === "Yes" && !isUrl(form.org_linkedin_url)) found.org_linkedin_url = "Enter a valid LinkedIn page URL.";
      if (!form.personal_linkedin) found.personal_linkedin = "Please choose an answer.";
      if (form.personal_linkedin === "Yes" && !isUrl(form.personal_linkedin_url)) found.personal_linkedin_url = "Enter a valid LinkedIn profile URL.";
    }
    if (step === 2) {
      if (!form.present_board && !form.present_board_not_sure) found.present_board = "Enter a number or choose Not Sure.";
      if (!form.active_board && !form.active_board_not_sure) found.active_board = "Enter a number or choose Not Sure.";
      if (!form.new_members_count && !form.new_members_not_sure) found.new_members_count = "Enter a number or choose Not Sure.";
      if (!form.current_board_strengths.trim()) found.current_board_strengths = "Please share what your current board brings.";
      if (!form.board_challenges.trim()) found.board_challenges = "Please share your biggest board challenges.";
    }
    if (step === 3) {
      if (!form.desired_skills.length) found.desired_skills = "Select at least one option.";
      if (form.desired_skills.includes("Other") && !form.desired_skills_other.trim()) found.desired_skills_other = "Tell us about the other skills or experience.";
      if (!form.accomplish.trim()) found.accomplish = "Please share what you need your new board members to help accomplish.";
    }
    if (step === 4) {
      if (!form.meeting_frequency) found.meeting_frequency = "Please choose an answer.";
      if (form.meeting_frequency === "Other" && !form.meeting_frequency_other.trim()) found.meeting_frequency_other = "Tell us your meeting schedule.";
      if (!form.meeting_format) found.meeting_format = "Please choose an answer.";
      if (["In Person", "Hybrid"].includes(form.meeting_format) && !form.meeting_location.trim()) found.meeting_location = "Enter your meeting location.";
      if (!form.board_term) found.board_term = "Please choose an answer.";
      if (form.board_term === "Other" && !form.board_term_other.trim()) found.board_term_other = "Tell us the term length.";
      if (!form.max_board_size && !form.max_board_size_unknown) found.max_board_size = "Enter a number or choose Not Specified / I Don't Know.";
      if (!form.application_deadline) found.application_deadline = "Please choose an answer.";
      if (form.application_deadline === "Specific Date" && !form.deadline_date) found.deadline_date = "Choose the deadline date.";
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
      const payload = { ...form, session_id: sessionId };
      ["present_board", "active_board", "new_members_count"].forEach((key) => {
        if (form[`${key === "new_members_count" ? "new_members" : key}_not_sure`]) payload[key] = "Not Sure";
      });
      if (form.max_board_size_unknown) payload.max_board_size = "Not Specified / I Don't Know";
      const response = await axios.post(`${API}/board-recruitment-intake/submit`, payload);
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
      <main data-testid="intake-page">
        <section className="funnel-hero-banner brp-hero intake-hero" data-testid="intake-hero">
          <h1 data-testid="intake-headline">Tell Me About Your Organization and Board</h1>
          <p className="funnel-hero-banner-supporting" data-testid="intake-subtitle">Give me the information I need to start your board recruitment.</p>
          <i aria-hidden="true" />
        </section>

        {gate === "checking" && (
          <div className="intake-card" data-testid="intake-checking"><h2>Confirming Your Payment…</h2><p>Please wait while we verify your payment with Stripe.</p></div>
        )}

        {gate === "blocked" && (
          <div className="intake-card" data-testid="intake-blocked">
            <h2>This Form Is for Customers Who Have Completed Payment</h2>
            <p>We could not find a completed qualifying purchase. If you just paid, please use the link Stripe returned you to. Otherwise, choose how you would like to recruit your board:</p>
            <div className="intake-blocked-links">
              <Link className="button" to="/recruit-your-board-yourself" data-testid="intake-blocked-diy-link">Do It Yourself — $497</Link>
              <Link className="button button-outline" to="/board-recruitment-proposal" data-testid="intake-blocked-dwm-link">Do It With Me — $1,997</Link>
            </div>
          </div>
        )}

        {gate === "done" && (
          <div className="intake-card" data-testid="intake-done">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Information saved</p>
            {purchaseSource === "direct_diy_board_recruitment_497" ? (
              <>
                <h2>You're Ready to Start</h2>
                <p>Taking you to your start page…</p>
                <a className="button" href={nextUrl || "/recruitment-start-here"} data-testid="intake-start-here-link">Open My Start Page</a>
              </>
            ) : (
              <>
                <h2>Let's Schedule Your Call With Rooney</h2>
                <p>Taking you to the calendar…</p>
                <a className="button" href={nextUrl || calendlyUrl} data-testid="intake-calendly-link">Open the Calendar</a>
              </>
            )}
          </div>
        )}

        {gate === "ready" && (
          <section className="intake-shell" data-testid="intake-form">
            <div className="progress-copy"><span data-testid="intake-progress-label">Step {step + 1} of 5 — {STEP_TITLES[step]}</span><span>{Math.round(((step + 1) / 5) * 100)}%</span></div>
            <div className="progress-track" data-testid="intake-progress-track"><div style={{ width: `${((step + 1) / 5) * 100}%` }} /></div>

            {step === 0 && (
              <div data-testid="intake-step-1">
                <h2 className="intake-step-title">About You and Your Organization</h2>
                <div className="two-col-fields">
                  <label className="field"><span>Your Name <b>*</b></span><input value={form.your_name} onChange={set("your_name")} data-testid="intake-your-name" />{errors.your_name && <p className="field-error">{errors.your_name}</p>}</label>
                  <label className="field"><span>Email Address <b>*</b></span><input type="email" value={form.email} onChange={set("email")} data-testid="intake-email" />{errors.email && <p className="field-error">{errors.email}</p>}</label>
                </div>
                <label className="field"><span>Organization Name <b>*</b></span><input value={form.organization_name} onChange={set("organization_name")} data-testid="intake-organization-name" />{errors.organization_name && <p className="field-error">{errors.organization_name}</p>}</label>
                <label className="field"><span>Website</span><input value={form.website} onChange={set("website")} data-testid="intake-website" /></label>
                <label className="field"><span>Mission <b>*</b></span><textarea rows="3" value={form.mission} onChange={set("mission")} data-testid="intake-mission" />{errors.mission && <p className="field-error">{errors.mission}</p>}</label>
                <div className="two-col-fields">
                  <label className="field"><span>City <b>*</b></span><input value={form.city} onChange={set("city")} data-testid="intake-city" />{errors.city && <p className="field-error">{errors.city}</p>}</label>
                  <label className="field"><span>State <b>*</b></span><input value={form.state} onChange={set("state")} data-testid="intake-state" /><span className="field-helper">Required for US organizations.</span>{errors.state && <p className="field-error">{errors.state}</p>}</label>
                </div>
                <label className="field"><span>Board Type <b>*</b></span>
                  <select value={form.board_type} onChange={set("board_type")} data-testid="intake-board-type">
                    <option value="">Choose one…</option>
                    {["Governing Board", "Working Board", "Advisory Board", "Not Sure"].map((option) => <option key={option}>{option}</option>)}
                  </select>
                  {errors.board_type && <p className="field-error">{errors.board_type}</p>}
                </label>
              </div>
            )}

            {step === 1 && (
              <div data-testid="intake-step-2">
                <h2 className="intake-step-title">LinkedIn</h2>
                <YesNo legend="Does your nonprofit have a LinkedIn organization page?" value={form.org_linkedin} onChange={setValue("org_linkedin")} testId="intake-org-linkedin" error={errors.org_linkedin} />
                {form.org_linkedin === "Yes" && (
                  <label className="field"><span>LinkedIn Organization Page URL <b>*</b></span><input value={form.org_linkedin_url} onChange={set("org_linkedin_url")} data-testid="intake-org-linkedin-url" />{errors.org_linkedin_url && <p className="field-error">{errors.org_linkedin_url}</p>}</label>
                )}
                <YesNo legend="Do you personally have a LinkedIn account/profile?" value={form.personal_linkedin} onChange={setValue("personal_linkedin")} testId="intake-personal-linkedin" error={errors.personal_linkedin} />
                {form.personal_linkedin === "Yes" && (
                  <label className="field"><span>Your LinkedIn Profile URL <b>*</b></span><input value={form.personal_linkedin_url} onChange={set("personal_linkedin_url")} data-testid="intake-personal-linkedin-url" />{errors.personal_linkedin_url && <p className="field-error">{errors.personal_linkedin_url}</p>}</label>
                )}
              </div>
            )}

            {step === 2 && (
              <div data-testid="intake-step-3">
                <h2 className="intake-step-title">Your Present Board</h2>
                <NumberOrNotSure label="How many board members do you currently have?" value={form.present_board} notSure={form.present_board_not_sure} onValue={setValue("present_board")} onNotSure={setValue("present_board_not_sure")} testId="intake-present-board" error={errors.present_board} />
                <NumberOrNotSure label="How many of them are actively participating?" value={form.active_board} notSure={form.active_board_not_sure} onValue={setValue("active_board")} onNotSure={setValue("active_board_not_sure")} testId="intake-active-board" error={errors.active_board} />
                <NumberOrNotSure label="How many new board members would you like to recruit?" value={form.new_members_count} notSure={form.new_members_not_sure} onValue={setValue("new_members_count")} onNotSure={setValue("new_members_not_sure")} testId="intake-new-members" error={errors.new_members_count} />
                <label className="field"><span>What skills, experience or strengths are already represented on your current board? <b>*</b></span><textarea rows="4" value={form.current_board_strengths} onChange={set("current_board_strengths")} data-testid="intake-current-strengths" />{errors.current_board_strengths && <p className="field-error">{errors.current_board_strengths}</p>}</label>
                <label className="field"><span>What are the biggest challenges you are experiencing with your present board? <b>*</b></span><textarea rows="4" value={form.board_challenges} onChange={set("board_challenges")} data-testid="intake-board-challenges" />{errors.board_challenges && <p className="field-error">{errors.board_challenges}</p>}</label>
              </div>
            )}

            {step === 3 && (
              <div data-testid="intake-step-4">
                <h2 className="intake-step-title">The Board You Need</h2>
                <fieldset className="field choice-field">
                  <legend>What skills, experience, relationships or professional backgrounds would you like to add to your board? <b>*</b></legend>
                  <div className="choice-grid">
                    {SKILL_OPTIONS.map((option) => (
                      <label className={`choice ${form.desired_skills.includes(option) ? "selected" : ""}`} key={option}>
                        <input type="checkbox" checked={form.desired_skills.includes(option)} onChange={() => toggleSkill(option)} data-testid={`intake-skill-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                  {errors.desired_skills && <p className="field-error">{errors.desired_skills}</p>}
                </fieldset>
                {form.desired_skills.includes("Other") && (
                  <label className="field"><span>Tell us about the other skills or experience <b>*</b></span><input value={form.desired_skills_other} onChange={set("desired_skills_other")} data-testid="intake-skills-other" />{errors.desired_skills_other && <p className="field-error">{errors.desired_skills_other}</p>}</label>
                )}
                <label className="field"><span>What do you most need your new board members to help your organization accomplish? <b>*</b></span><textarea rows="4" value={form.accomplish} onChange={set("accomplish")} data-testid="intake-accomplish" />{errors.accomplish && <p className="field-error">{errors.accomplish}</p>}</label>
                <label className="field"><span>Is there anything specific you already know you want in the people you recruit?</span><textarea rows="3" value={form.specific_wants} onChange={set("specific_wants")} data-testid="intake-specific-wants" /></label>
              </div>
            )}

            {step === 4 && (
              <div data-testid="intake-step-5">
                <h2 className="intake-step-title">Board Logistics</h2>
                <label className="field"><span>How often does your board meet? <b>*</b></span>
                  <select value={form.meeting_frequency} onChange={set("meeting_frequency")} data-testid="intake-meeting-frequency">
                    <option value="">Choose one…</option>
                    {["Monthly", "Every Other Month", "Quarterly", "Other"].map((option) => <option key={option}>{option}</option>)}
                  </select>
                  {errors.meeting_frequency && <p className="field-error">{errors.meeting_frequency}</p>}
                </label>
                {form.meeting_frequency === "Other" && <label className="field"><span>Tell us your meeting schedule <b>*</b></span><input value={form.meeting_frequency_other} onChange={set("meeting_frequency_other")} data-testid="intake-frequency-other" />{errors.meeting_frequency_other && <p className="field-error">{errors.meeting_frequency_other}</p>}</label>}
                <label className="field"><span>How are your board meetings held? <b>*</b></span>
                  <select value={form.meeting_format} onChange={set("meeting_format")} data-testid="intake-meeting-format">
                    <option value="">Choose one…</option>
                    {["Virtual", "In Person", "Hybrid"].map((option) => <option key={option}>{option}</option>)}
                  </select>
                  {errors.meeting_format && <p className="field-error">{errors.meeting_format}</p>}
                </label>
                {["In Person", "Hybrid"].includes(form.meeting_format) && (
                  <label className="field"><span>Meeting Location <b>*</b></span><input value={form.meeting_location} onChange={set("meeting_location")} data-testid="intake-meeting-location" />{errors.meeting_location && <p className="field-error">{errors.meeting_location}</p>}</label>
                )}
                {form.meeting_format === "Hybrid" && (
                  <label className="field"><span>Virtual Meeting Information</span><input value={form.virtual_meeting_info} onChange={set("virtual_meeting_info")} data-testid="intake-virtual-info" /></label>
                )}
                <label className="field"><span>Board Member Term <b>*</b></span>
                  <select value={form.board_term} onChange={set("board_term")} data-testid="intake-board-term">
                    <option value="">Choose one…</option>
                    {["1 Year", "2 Years", "3 Years", "No Fixed Term", "Other"].map((option) => <option key={option}>{option}</option>)}
                  </select>
                  {errors.board_term && <p className="field-error">{errors.board_term}</p>}
                </label>
                {form.board_term === "Other" && <label className="field"><span>Tell us the term length <b>*</b></span><input value={form.board_term_other} onChange={set("board_term_other")} data-testid="intake-term-other" />{errors.board_term_other && <p className="field-error">{errors.board_term_other}</p>}</label>}
                <label className="field"><span>Expected Monthly Time Commitment</span><input value={form.time_commitment} onChange={set("time_commitment")} data-testid="intake-time-commitment" /></label>
                <label className="field"><span>Maximum Board Size According to Your Bylaws or Governing Documents <b>*</b></span>
                  <input type="number" min="1" disabled={form.max_board_size_unknown} value={form.max_board_size} onChange={set("max_board_size")} data-testid="intake-max-board-size" />
                  <span className="choice intake-not-sure"><input type="checkbox" checked={form.max_board_size_unknown} onChange={(event) => setForm({ ...form, max_board_size_unknown: event.target.checked, max_board_size: event.target.checked ? "" : form.max_board_size })} data-testid="intake-max-size-unknown" /><span>Not Specified / I Don't Know</span></span>
                  {errors.max_board_size && <p className="field-error">{errors.max_board_size}</p>}
                </label>
                <label className="field"><span>Application Deadline <b>*</b></span>
                  <select value={form.application_deadline} onChange={set("application_deadline")} data-testid="intake-application-deadline">
                    <option value="">Choose one…</option>
                    {["Open Until Positions Are Filled", "Specific Date"].map((option) => <option key={option}>{option}</option>)}
                  </select>
                  {errors.application_deadline && <p className="field-error">{errors.application_deadline}</p>}
                </label>
                {form.application_deadline === "Specific Date" && <label className="field"><span>Deadline Date <b>*</b></span><input type="date" value={form.deadline_date} onChange={set("deadline_date")} data-testid="intake-deadline-date" />{errors.deadline_date && <p className="field-error">{errors.deadline_date}</p>}</label>}
                <label className="field"><span>Is There Anything Else I Should Know Before We Start Recruiting Your Board?</span><textarea rows="3" value={form.anything_else} onChange={set("anything_else")} data-testid="intake-anything-else" /></label>
              </div>
            )}

            {submitError && <p className="submit-error" data-testid="intake-submit-error">{submitError}</p>}
            <div className="intake-nav">
              {step > 0 ? <button type="button" className="button button-outline" onClick={back} data-testid="intake-back-button">Back</button> : <span />}
              {step < 4 ? (
                <button type="button" className="button" onClick={next} data-testid="intake-next-button">Next</button>
              ) : (
                <button type="button" className="button" onClick={submit} disabled={busy} data-testid="intake-submit-button">{busy ? "Saving…" : "Submit"}</button>
              )}
            </div>
          </section>
        )}
      </main>
    </FunnelLayout>
  );
}
