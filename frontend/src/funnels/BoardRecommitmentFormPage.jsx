import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ACTIVE = "I am ready to recommit, remain an active Board Member and step up in my role.";
const ADVISORY = "I would like to transition into an Advisory Board role.";
const STEP_DOWN = "I would like to step down from the Board.";

const EXPERTISE = ["Fundraising", "Major Gifts", "Grant Writing", "Finance / Accounting", "Legal", "Human Resources", "Marketing / Communications", "Public Relations", "Strategic Planning", "Organizational Development", "Nonprofit Leadership", "Corporate Partnerships", "Government Relations", "Education", "Youth Development", "Healthcare", "Mental Health", "Technology / AI", "Program Development", "Operations", "Project Management", "Community Engagement", "Volunteer Management", "Events", "Advocacy", "Other"];
const CONTRIBUTIONS = ["Fundraising / Resource Development", "Marketing & Communications", "Programs & Impact", "Partnerships", "Finance", "Governance / Board Development", "Strategic Planning", "Technology", "Volunteer Development", "Community Engagement", "Operations", "Board Recruitment", "Other"];
const AVAILABILITY = ["Less than 2 hours", "2–4 hours", "5–8 hours", "9–12 hours", "12+ hours"];

const INITIAL = {
  full_name: "", email: "", phone: "", form_variant: "full", recommitment: "",
  why_joined: "", expertise: [], expertise_other: "", participation_barriers: "", contribution_interests: [],
  ownership_area: "", leadership_interest: "", leadership_area: "", strengths_resources: "", monthly_availability: "",
  experience_improvement: "", decision_reason: "", anything_else: "",
};

const Field = ({ label, children }) => <label className="field"><span>{label}</span>{children}</label>;

export default function BoardRecommitmentFormPage() {
  usePageMeta("Board Recommitment Form | Nonprofit Board Builder", "Confirm how you would like to serve moving forward.", true);
  const { token } = useParams();
  const requestedVariant = new URLSearchParams(window.location.search).get("variant") === "active_advisory" ? "active_advisory" : "full";
  const [context, setContext] = useState(null);
  const [gate, setGate] = useState("loading");
  const [form, setForm] = useState({ ...INITIAL, form_variant: requestedVariant });
  const [errorText, setErrorText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/board-recommitment/${token}`).then((response) => {
      const serverVariant = response.data.form_variant === "active_advisory" ? "active_advisory" : requestedVariant;
      setContext(response.data);
      setForm((current) => ({
        ...current,
        form_variant: serverVariant,
        full_name: response.data.prefill?.full_name || "",
        email: response.data.prefill?.email || "",
        phone: response.data.prefill?.phone || "",
      }));
      setGate(response.data.submitted ? "already" : "ready");
    }).catch(() => setGate("invalid"));
  }, [token, requestedVariant]);

  const org = context?.organization_name || "the organization";
  const prefilled = Boolean(context?.prefill?.full_name && context?.prefill?.email);
  const choices = useMemo(() => form.form_variant === "active_advisory" ? [ACTIVE, ADVISORY] : [ACTIVE, ADVISORY, STEP_DOWN], [form.form_variant]);

  const set = (name) => (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  const toggle = (name, option) => setForm((current) => {
    const values = current[name] || [];
    if (values.includes(option)) return { ...current, [name]: values.filter((item) => item !== option) };
    if (name === "contribution_interests" && values.length >= 3) return current;
    return { ...current, [name]: [...values, option] };
  });

  const submit = async () => {
    let missing = !form.full_name.trim() || !form.email.trim() || !form.recommitment;
    if (form.recommitment === ACTIVE) {
      missing = missing
        || ["why_joined", "participation_barriers", "ownership_area", "strengths_resources", "monthly_availability", "experience_improvement"].some((name) => !String(form[name] || "").trim())
        || !form.expertise.length || !form.contribution_interests.length || !form.leadership_interest
        || (form.leadership_interest === "Yes" && !form.leadership_area.trim());
    } else if (form.recommitment === ADVISORY) {
      missing = missing || !form.decision_reason.trim() || !form.strengths_resources.trim() || !form.monthly_availability.trim();
    } else if (form.recommitment === STEP_DOWN) {
      missing = missing || !form.decision_reason.trim();
    }
    if (missing) {
      setErrorText("Please answer every required question before submitting.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    setBusy(true); setErrorText("");
    try {
      await axios.post(`${API}/board-recommitment/${token}`, form);
      setGate("done");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      setErrorText(error.response?.status === 409 ? "This response has already been submitted." : (error.response?.data?.detail || "We could not submit your response. Please review your answers and try again."));
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained isolated>
      <main data-testid="recommit-page">
        {gate === "loading" && <div className="intake-card"><p>Loading…</p></div>}
        {gate === "invalid" && <div className="intake-card"><h2>This Recommitment Form Is Not Available.</h2><p>Please contact the organization that sent you the link.</p></div>}
        {(gate === "done" || gate === "already") && (
          <div className="intake-card" data-testid="recommit-thankyou">
            <p className="purchase-confirmed"><CheckCircle2 size={20}/> Submitted</p>
            <h2>Thank You For Giving Us A Clear Answer.</h2>
            <p>Your response has been sent to <strong>{org}</strong>. The organization will review what you shared and follow up with you about the way forward.</p>
          </div>
        )}
        {gate === "ready" && (
          <>
            <section className="funnel-hero-banner brp-hero intake-hero">
              {context?.logo_data_url && <img src={context.logo_data_url} alt={`${org} logo`} style={{maxWidth:190,maxHeight:110,objectFit:"contain",margin:"0 auto 18px",display:"block"}}/>}
              <p className="eyebrow">BOARD RECOMMITMENT</p>
              <h1>How Would You Like To Serve Moving Forward?</h1>
              <p>This is a chance to be clear about the role that fits you now and the contribution you are realistically ready to make.</p>
            </section>
            <section className="intake-shell" data-testid="recommit-form">
              {context?.introduction && <div className="intake-card" style={{whiteSpace:"pre-wrap",marginBottom:18}}>{context.introduction}</div>}
              {errorText && <p className="submit-error">{errorText}</p>}

              {prefilled ? (
                <div className="intake-card" style={{marginBottom:18}}>
                  <strong>{context.prefill.full_name}</strong>
                  <p style={{margin:"4px 0 0"}}>{context.prefill.email}</p>
                  {context.prefill.role && <p style={{margin:"4px 0 0"}}>{context.prefill.role}</p>}
                </div>
              ) : (
                <div className="two-col-fields">
                  <Field label="Full Name *"><input value={form.full_name} onChange={set("full_name")}/></Field>
                  <Field label="Email Address *"><input type="email" value={form.email} onChange={set("email")}/></Field>
                </div>
              )}

              <fieldset className="field choice-field">
                <legend><strong>Which path best reflects how you want to move forward?</strong></legend>
                <div className="choice-grid">
                  {choices.map((choice) => (
                    <label className={`choice ${form.recommitment === choice ? "selected" : ""}`} key={choice}>
                      <input type="radio" name="recommitment" checked={form.recommitment === choice} onChange={() => setForm((current) => ({...current,recommitment:choice}))}/>
                      <span>{choice}</span>
                    </label>
                  ))}
                </div>
              </fieldset>

              {form.recommitment === ACTIVE && (
                <div data-testid="recommit-active-path">
                  <Field label={`Why do you want to continue serving on the Board of ${org}? *`}><textarea rows="3" value={form.why_joined} onChange={set("why_joined")}/></Field>
                  <fieldset className="field choice-field"><legend>What professional skills, experience or expertise can you bring? *</legend><div className="choice-grid">{EXPERTISE.map(option=><label className={`choice ${form.expertise.includes(option)?"selected":""}`} key={option}><input type="checkbox" checked={form.expertise.includes(option)} onChange={()=>toggle("expertise",option)}/><span>{option}</span></label>)}</div></fieldset>
                  {form.expertise.includes("Other") && <Field label="Other expertise"><input value={form.expertise_other} onChange={set("expertise_other")}/></Field>}
                  <Field label="What has made it difficult for you to participate as actively as you would like? *"><textarea rows="4" value={form.participation_barriers} onChange={set("participation_barriers")}/></Field>
                  <fieldset className="field choice-field"><legend>Where would you most like to contribute moving forward? Select up to 3. *</legend><div className="choice-grid">{CONTRIBUTIONS.map(option=><label className={`choice ${form.contribution_interests.includes(option)?"selected":""}`} key={option}><input type="checkbox" checked={form.contribution_interests.includes(option)} onChange={()=>toggle("contribution_interests",option)}/><span>{option}</span></label>)}</div></fieldset>
                  <Field label="What area are you willing to take greater responsibility for? *"><textarea rows="3" value={form.ownership_area} onChange={set("ownership_area")}/></Field>
                  <fieldset className="field choice-field"><legend>Are you ready to take on a leadership or committee responsibility? *</legend><div className="choice-grid">{["Yes","I would like to discuss this"].map(choice=><label className={`choice ${form.leadership_interest===choice?"selected":""}`} key={choice}><input type="radio" name="leadership" checked={form.leadership_interest===choice} onChange={()=>setForm(current=>({...current,leadership_interest:choice}))}/><span>{choice}</span></label>)}</div></fieldset>
                  {form.leadership_interest === "Yes" && <Field label="What responsibility would you be interested in leading? *"><textarea rows="3" value={form.leadership_area} onChange={set("leadership_area")}/></Field>}
                  <Field label="What skills, relationships, resources or strengths can you bring to the Board? *"><textarea rows="4" value={form.strengths_resources} onChange={set("strengths_resources")}/></Field>
                  <Field label="How much time can you realistically give each month? *"><select value={form.monthly_availability} onChange={set("monthly_availability")}><option value="">Choose one…</option>{AVAILABILITY.map(x=><option key={x}>{x}</option>)}</select></Field>
                  <Field label="What can the organization do to help you contribute effectively? *"><textarea rows="4" value={form.experience_improvement} onChange={set("experience_improvement")}/></Field>
                </div>
              )}

              {form.recommitment === ADVISORY && (
                <div data-testid="recommit-advisory-path">
                  <Field label="Why does an Advisory Board role feel like the right way for you to continue supporting the organization? *"><textarea rows="4" value={form.decision_reason} onChange={set("decision_reason")}/></Field>
                  <fieldset className="field choice-field"><legend>Where could your experience still be useful?</legend><div className="choice-grid">{CONTRIBUTIONS.map(option=><label className={`choice ${form.contribution_interests.includes(option)?"selected":""}`} key={option}><input type="checkbox" checked={form.contribution_interests.includes(option)} onChange={()=>toggle("contribution_interests",option)}/><span>{option}</span></label>)}</div></fieldset>
                  <Field label="What skills, relationships, resources or strengths would you still be willing to make available? *"><textarea rows="4" value={form.strengths_resources} onChange={set("strengths_resources")}/></Field>
                  <Field label="How much time can you realistically make available in an Advisory role? *"><select value={form.monthly_availability} onChange={set("monthly_availability")}><option value="">Choose one…</option>{AVAILABILITY.map(x=><option key={x}>{x}</option>)}</select></Field>
                </div>
              )}

              {form.recommitment === STEP_DOWN && (
                <div data-testid="recommit-step-down-path">
                  <Field label="Please briefly tell us what has led to your decision to step down from the Board. *"><textarea rows="5" value={form.decision_reason} onChange={set("decision_reason")}/></Field>
                </div>
              )}

              {form.recommitment && (
                <>
                  <Field label="Is there anything else you would like the Founder or Board leadership to know?"><textarea rows="3" value={form.anything_else} onChange={set("anything_else")}/></Field>
                  <div className="intake-nav" style={{justifyContent:"center"}}>
                    <button className="button rwr-cta-button" onClick={submit} disabled={busy}>{busy?"SUBMITTING…":"SUBMIT MY RESPONSE"}</button>
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
