import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { usePageMeta } from "@/seo";
import { recommitFormText } from "../content/appContent";
import { boardRecommitmentFormPageText } from "../content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EXPERTISE = ["Fundraising", "Major Gifts", "Grant Writing", "Finance / Accounting", "Legal", "Human Resources", "Marketing / Communications", "Public Relations", "Strategic Planning", "Organizational Development", "Nonprofit Leadership", "Corporate Partnerships", "Government Relations", "Education", "Youth Development", "Healthcare", "Mental Health", "Technology / AI", "Program Development", "Operations", "Project Management", "Community Engagement", "Volunteer Management", "Events", "Advocacy", "Other"];
const CONTRIBUTIONS = ["Fundraising / Resource Development", "Marketing & Communications", "Programs & Impact", "Partnerships", "Finance", "Governance / Board Development", "Strategic Planning", "Technology", "Volunteer Development", "Community Engagement", "Operations", "Board Recruitment", "Other"];
const AVAILABILITY = ["Less than 2 hours", "2–4 hours", "5–8 hours", "9–12 hours", "12+ hours"];
const YES = "Yes, I am ready to recommit and continue serving.";
const NO = "No, I am not able to recommit to serving on the Board.";
const UNSURE = "I am not sure yet. I need more information or would like to discuss my role before deciding.";

const INITIAL = {
  full_name: "", email: "", phone: "", recommitment: "",
  why_joined: "", expertise: [], expertise_other: "", participation_barriers: "", contribution_interests: [],
  ownership_area: "", leadership_interest: "", leadership_area: "", strengths_resources: "", monthly_availability: "",
  experience_improvement: "", decision_reason: "", advisory_openness: "", decision_support: "", anything_else: "",
};

const tid = (name) => `recommit-${name.replace(/_/g, "-")}`;
const Text = ({ label, name, form, set, required = false, type = "text" }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span><input type={type} value={form[name]} onChange={set(name)} data-testid={tid(name)} /></label>
);
const Area = ({ label, name, form, set, required = true, rows = 4 }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span><textarea rows={rows} value={form[name]} onChange={set(name)} data-testid={tid(name)} /></label>
);
const Select = ({ label, name, options, form, set, required = true }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span>
    <select value={form[name]} onChange={set(name)} data-testid={tid(name)}><option value="">Choose one…</option>{options.map((option) => <option key={option}>{option}</option>)}</select>
  </label>
);
const Multi = ({ legend, name, options, form, toggle, required = true }) => (
  <fieldset className="field choice-field"><legend>{legend} {required && <b>*</b>}</legend>
    <div className="choice-grid">
      {options.map((option) => (
        <label className={`choice ${form[name].includes(option) ? "selected" : ""}`} key={option}>
          <input type="checkbox" checked={form[name].includes(option)} onChange={() => toggle(name, option)} data-testid={`${tid(name)}-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
          <span>{option}</span>
        </label>
      ))}
    </div>
  </fieldset>
);
const Radios = ({ legend, name, options, form, setValue, testPrefix }) => (
  <fieldset className="field choice-field" data-testid={`${testPrefix}-options`}>
    <legend>{legend} <b>*</b></legend>
    <div>
      {options.map((option, index) => (
        <label className={`choice ${form[name] === option ? "selected" : ""}`} key={option} style={{ display: "flex", marginBottom: 8 }}>
          <input type="radio" name={name} checked={form[name] === option} onChange={() => setValue(name, option)} data-testid={`${testPrefix}-option-${index + 1}`} />
          <span>{option}</span>
        </label>
      ))}
    </div>
  </fieldset>
);

export default function BoardRecommitmentFormPage() {
  usePageMeta("Board Member Profile & Recommitment Form | Nonprofit Board Builder", "Complete your Board Member Profile & Recommitment Form.", true);
  const { token } = useParams();
  const generalVersion = new URLSearchParams(window.location.search).get("general") === "1";
  const [context, setContext] = useState(null);
  const [gate, setGate] = useState("loading");
  const [form, setForm] = useState(INITIAL);
  const [errorText, setErrorText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/board-recommitment/${token}`).then((response) => {
      setContext(response.data);
      setForm((current) => ({ ...current, ...Object.fromEntries(Object.entries({
        full_name: response.data.prefill.full_name, email: response.data.prefill.email, phone: response.data.prefill.phone,
      }).filter(([, value]) => value)) }));
      setGate(response.data.submitted ? "already" : "ready");
    }).catch(() => setGate("invalid"));
  }, [token]);

  const set = (name) => (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  const setValue = (name, value) => setForm((current) => ({ ...current, [name]: value }));
  const toggle = (name, option) => setForm((current) => {
    if (current[name].includes(option)) return { ...current, [name]: current[name].filter((item) => item !== option) };
    if (name === "contribution_interests" && current[name].length >= 3) return current;
    return { ...current, [name]: [...current[name], option] };
  });

  const submit = async () => {
    let missing = !form.full_name.trim() || !form.email.trim() || !form.recommitment;
    if (form.recommitment === YES) {
      missing = missing
        || ["why_joined", "participation_barriers", "ownership_area", "strengths_resources", "monthly_availability", "experience_improvement"].some((name) => !form[name].trim())
        || !form.expertise.length || !form.contribution_interests.length || !form.leadership_interest
        || (form.leadership_interest === "Yes" && !form.leadership_area.trim());
    } else if (form.recommitment === NO) {
      missing = missing || !form.decision_reason.trim();
    } else if (form.recommitment === UNSURE) {
      missing = missing || !form.decision_support.trim();
    }
    if (missing) { setErrorText("Please answer every required question before submitting."); window.scrollTo(0, 0); return; }
    setBusy(true);
    setErrorText("");
    try {
      await axios.post(`${API}/board-recommitment/${token}`, form);
      setGate("done");
      window.scrollTo(0, 0);
    } catch (error) {
      setErrorText(error.response?.status === 409 ? "This response has already been submitted." : "We could not submit your response. Please review your answers and try again.");
      setBusy(false);
    }
  };

  const org = context?.organization_name || "the organization";
  const reviewerLine = () => {
    const name = context?.founder_name || "";
    const title = context?.founder_title || "";
    if (name && title) return `${name}, ${title},`;
    if (name) return name;
    return `The leadership of ${org}`;
  };
  const prefilled = Boolean(context?.prefill?.full_name && context?.prefill?.email);

  return (
    <FunnelLayout restrained isolated>
      <main data-testid="recommit-page">
        {gate === "loading" && <div className="intake-card"><p>Loading…</p></div>}
        {gate === "invalid" && (
          <div className="intake-card" data-testid="recommit-invalid"><h2>{recommitFormText.h_thisLinkIsNotValid}</h2><p>{boardRecommitmentFormPageText.pleaseContactThePersonWho}</p></div>
        )}
        {(gate === "done" || gate === "already") && (
          <div className="intake-card" data-testid="recommit-thankyou">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Submitted</p>
            <h2>{recommitFormText.h_thankYou}</h2>
            <p>Thank you for completing your Board Member Profile & Recommitment Form for <strong>{org}</strong>.</p>
            <p data-testid="recommit-thankyou-reviewer">{reviewerLine()} will review your response and will be reaching out to you based on what you shared so you can discuss the way forward together.</p>
            <p>Thank you for taking the time to provide your response.</p>
          </div>
        )}
        {gate === "ready" && (
          <>
            <section className="funnel-hero-banner brp-hero intake-hero" data-testid="recommit-hero">
              {context.logo_data_url && <img src={context.logo_data_url} alt={`${org} logo`} style={{maxWidth:190,maxHeight:110,objectFit:"contain",margin:"0 auto 18px",display:"block"}} />}
              <h1>Board Member Profile & Recommitment Form</h1>
              <i aria-hidden="true" />
            </section>
            <section className="intake-shell" data-testid="recommit-form">
              <div data-testid="recommit-introduction">
                <p>As we strengthen the Board of <strong>{org}</strong> and prepare for the next phase of the organization, we are asking every current Board Member to confirm their commitment and help us understand how they would like to contribute moving forward.</p>
                <p>Your responses will help us engage you in areas that fit your strengths, interests and capacity and prepare for a short conversation about your role moving forward.</p>
                <p>Please answer honestly based on where you are today.</p>
              </div>
              {errorText && <p className="submit-error" data-testid="recommit-error">{errorText}</p>}

              {prefilled ? (
                <div className="intake-card" style={{ marginBottom: 18 }} data-testid="recommit-identity">
                  <p style={{ margin: 0 }}><strong>{context.prefill.full_name}</strong></p>
                  <p style={{ margin: "4px 0 0" }}>{context.prefill.email}</p>
                  {context.prefill.role && <p style={{ margin: "4px 0 0" }}>{context.prefill.role}</p>}
                </div>
              ) : (
                <div className="two-col-fields">
                  <Text label="Full Name" name="full_name" form={form} set={set} required />
                  <Text label="Email Address" name="email" type="email" form={form} set={set} required />
                </div>
              )}

              <Radios
                legend={`Are you ready to recommit and continue serving as an active Board Member of ${org}?`}
                name="recommitment" options={generalVersion ? [YES, UNSURE] : (context.recommitment_options || [YES, NO, UNSURE])} form={form} setValue={setValue} testPrefix="recommit"
              />

              {form.recommitment === YES && (
                <div data-testid="recommit-yes-path">
                  <Area label={`Why did you choose to join the Board of ${org}?`} name="why_joined" rows={3} form={form} set={set} />
                  <Multi legend="What professional skills, experience or expertise do you bring that could help strengthen the organization?" name="expertise" options={EXPERTISE} form={form} toggle={toggle} />
                  {form.expertise.includes("Other") && <Text label="Other expertise" name="expertise_other" form={form} set={set} />}
                  <Area label="What, if anything, has made it difficult for you to participate or contribute as actively as you would like?" name="participation_barriers" form={form} set={set} />
                  <Multi legend="How would you most like to contribute to the organization moving forward? (Select up to 3)" name="contribution_interests" options={CONTRIBUTIONS} form={form} toggle={toggle} />
                  <Area label="Of the areas you selected, is there one area you would be willing to take greater responsibility for helping the Board move forward?" name="ownership_area" form={form} set={set} />
                  <Radios legend="Are there any leadership or committee responsibilities you would be interested in taking on?" name="leadership_interest" options={["Yes", "I would like to discuss this"]} form={form} setValue={setValue} testPrefix="recommit-leadership" />
                  {form.leadership_interest === "Yes" && (
                    <Area label="Please tell us the area or responsibility you would be interested in leading." name="leadership_area" rows={3} form={form} set={set} />
                  )}
                  <Area label="Are there any skills, resources or other strengths you have that you would like the Board to know about?" name="strengths_resources" form={form} set={set} />
                  <Select label="Approximately how many hours per month are you realistically able to dedicate to Board service?" name="monthly_availability" options={AVAILABILITY} form={form} set={set} />
                  <Area label="What can we do to make your Board experience more enjoyable and help you contribute effectively?" name="experience_improvement" form={form} set={set} />
                  <Area label="Is there anything else you would like the Founder or Board leadership to know as we move forward together? (optional)" name="anything_else" required={false} rows={3} form={form} set={set} />
                </div>
              )}

              {form.recommitment === NO && (
                <div data-testid="recommit-no-path">
                  <Area label="Please briefly tell us what has led to your decision not to continue serving on the Board." name="decision_reason" form={form} set={set} />
                  {!generalVersion && context.allow_advisory && (
                    <Radios legend={`Would you be open to continuing to support ${org} in an Advisory Board role rather than serving as an active Board Member?`} name="advisory_openness" options={["Yes", "No", "I would like to discuss it"]} form={form} setValue={setValue} testPrefix="recommit-advisory" />
                  )}
                </div>
              )}

              {form.recommitment === UNSURE && (
                <div data-testid="recommit-unsure-path">
                  <Area label="What information, clarity or support would help you decide whether you are ready to recommit to serving on the Board?" name="decision_support" form={form} set={set} />
                  <Area label="Is there anything else you would like the Founder or Board leadership to understand before discussing your Board role with you? (optional)" name="anything_else" required={false} rows={3} form={form} set={set} />
                </div>
              )}

              {form.recommitment && (
                <>
                  {errorText && <p className="submit-error">{errorText}</p>}
                  <div className="intake-nav" style={{ justifyContent: "center" }}>
                    <button type="button" className="button rwr-cta-button" onClick={submit} disabled={busy} data-testid="recommit-submit">{busy ? "Submitting…" : "SUBMIT MY RESPONSE"}</button>
                  </div>
                </>
              )}
            </section>
          </>
        )}
      </main>
    </FunnelLayout>
  );
}
