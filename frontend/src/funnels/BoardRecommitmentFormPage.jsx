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
const NETWORKS = ["Business Leaders", "Corporate Executives", "Donors / Philanthropists", "Foundations", "Community Leaders", "Government", "Schools / Universities", "Faith Communities", "Healthcare Organizations", "Technology Sector", "Media", "Professional Associations", "Other", "I am not currently comfortable making introductions"];
const HOW_RECRUITED = ["Invited by the Founder / Executive Director", "Invited by another Board Member", "Friend / Family / Personal Relationship", "Professional Relationship", "Volunteer / Supporter of the Organization", "Public Board Recruitment", "Founding Member", "Other"];
const CLARITY = ["Very Clear", "Somewhat Clear", "Not Very Clear", "Not Clear at All"];
const CONTRIBUTIONS = ["Fundraising", "Donor Introductions", "Corporate Partnerships / Sponsorship", "Grants / Foundations", "Finance", "Governance", "Strategic Planning", "Marketing / Communications", "Public Relations", "Programs", "Operations", "Human Resources", "Technology", "Community Engagement", "Government / Advocacy", "Events", "Volunteer Development", "Board Recruitment", "Leadership / Committee Service", "Other"];
const FUNDRAISING = ["Making introductions to potential donors", "Meeting with prospective donors", "Corporate sponsorship outreach", "Foundation / grant opportunities", "Donor stewardship", "Fundraising events", "Speaking about the organization", "Reviewing fundraising strategy", "Personal financial contribution", "I would like training before participating", "I am not currently comfortable participating in fundraising"];
const AVAILABILITY = ["Less than 2 hours", "2–4 hours", "5–8 hours", "9–12 hours", "More than 12 hours", "Varies significantly month to month"];
const MEETINGS = ["Yes", "Usually", "Sometimes", "No", "I need to discuss the meeting schedule"];

const INITIAL = {
  full_name: "", preferred_name: "", email: "", phone: "", city_state: "", linkedin: "", current_position: "", employer: "", industry: "", years_experience: "",
  expertise: [], expertise_other: "", networks: [], why_joined: "", how_recruited: "", original_role_expectation: "", role_clarity: "", clarity_help: "",
  board_experience: "", participation_barriers: "", board_improvement: "", strategic_clarity: "", planning_participation: "", planning_involvement_desire: "",
  recommitment: "", advisory_openness: "", support_role_openness: "", step_off_openness: "", contribution_interests: [], fundraising_comfort: [], ownership_areas: "",
  leadership_interest: "", support_needed: "", monthly_availability: "", meeting_participation: "", constraints: "", meaningful_service: "", anything_else: "", confirmation: false,
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
  const toggle = (name, option) => setForm((current) => ({
    ...current, [name]: current[name].includes(option) ? current[name].filter((item) => item !== option) : [...current[name], option],
  }));

  const submit = async () => {
    const required = ["full_name", "email", "current_position", "why_joined", "how_recruited", "original_role_expectation", "role_clarity", "board_experience", "participation_barriers", "board_improvement", "strategic_clarity", "planning_participation", "recommitment", "ownership_areas", "leadership_interest", "support_needed", "monthly_availability", "meeting_participation", "meaningful_service"];
    const missing = required.some((name) => !String(form[name]).trim()) || !form.expertise.length || !form.networks.length || !form.contribution_interests.length || !form.fundraising_comfort.length;
    if (missing) { setErrorText("Please answer every required question before submitting."); window.scrollTo(0, 0); return; }
    if (!form.confirmation) { setErrorText("Please check the confirmation box before submitting."); return; }
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

  return (
    <FunnelLayout restrained>
      <main data-testid="recommit-page">
        {gate === "loading" && <div className="intake-card"><p>Loading…</p></div>}
        {gate === "invalid" && (
          <div className="intake-card" data-testid="recommit-invalid"><h2>{recommitFormText.h_thisLinkIsNotValid}</h2><p>{boardRecommitmentFormPageText.pleaseContactThePersonWho}</p></div>
        )}
        {(gate === "done" || gate === "already") && (
          <div className="intake-card" data-testid="recommit-thankyou">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Submitted</p>
            <h2>{recommitFormText.h_thankYou}</h2>
            <p>{boardRecommitmentFormPageText.yourBoardMemberProfileAmp}<strong>{org}</strong>.</p>
            <p>{boardRecommitmentFormPageText.theOrganizationWillReviewYour}</p>
          </div>
        )}
        {gate === "ready" && (
          <>
            <section className="funnel-hero-banner brp-hero intake-hero" data-testid="recommit-hero">
              <h1>{recommitFormText.h_boardMemberProfileAmpRecommitment}</h1>
              <p className="funnel-hero-banner-supporting" data-testid="recommit-supporting">{org} is taking time to strengthen how the Board works together and make sure every Board Member has clarity about their role, capacity and areas of contribution.</p>
              <p className="funnel-hero-banner-secondary">{recommitFormText.s_pleaseCompleteThisFormHonestly}</p>
              <i aria-hidden="true" />
            </section>
            <section className="intake-shell" data-testid="recommit-form">
              {context?.introduction && (
                <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 16, borderRadius: 8, marginBottom: 18 }} data-testid="recommit-introduction">{context.introduction}</div>
              )}
              {errorText && <p className="submit-error" data-testid="recommit-error">{errorText}</p>}

              <h2 className="intake-step-title">{recommitFormText.h_aboutYou}</h2>
              <div className="two-col-fields">
                <Text label="Full Name" name="full_name" form={form} set={set} required />
                <Text label="Preferred Name" name="preferred_name" form={form} set={set} />
              </div>
              <div className="two-col-fields">
                <Text label="Email Address" name="email" type="email" form={form} set={set} required />
                <Text label="Phone Number" name="phone" type="tel" form={form} set={set} />
              </div>
              <div className="two-col-fields">
                <Text label="City / State / Region" name="city_state" form={form} set={set} />
                <Text label="LinkedIn Profile (optional)" name="linkedin" form={form} set={set} />
              </div>
              <div className="two-col-fields">
                <Text label="Current Professional Position" name="current_position" form={form} set={set} required />
                <Text label="Organization / Employer" name="employer" form={form} set={set} />
              </div>
              <div className="two-col-fields">
                <Text label="Industry / Professional Field" name="industry" form={form} set={set} />
                <Text label="Years of Professional Experience (optional)" name="years_experience" form={form} set={set} />
              </div>
              <Multi legend="What professional skills, experience or expertise do you bring that could support the organization?" name="expertise" options={EXPERTISE} form={form} toggle={toggle} />
              {form.expertise.includes("Other") && <Text label="Other expertise" name="expertise_other" form={form} set={set} />}
              <Multi legend="Which types of relationships or professional networks could you potentially help the organization connect with?" name="networks" options={NETWORKS} form={form} toggle={toggle} />

              <h2 className="intake-step-title">{recommitFormText.h_yourExperienceOnTheBoard}</h2>
              <Area label={`What originally interested you in serving on the Board of ${org}?`} name="why_joined" form={form} set={set} />
              <Select label="How did you originally become involved with the Board?" name="how_recruited" options={HOW_RECRUITED} form={form} set={set} />
              <Area label="When you joined the Board, what did you understand your role and responsibilities to be?" name="original_role_expectation" form={form} set={set} />
              <Select label="How clear are you today about what is expected of you as a Board Member?" name="role_clarity" options={CLARITY} form={form} set={set} />
              <Area label="What would help give you greater clarity about your role? (optional)" name="clarity_help" required={false} rows={3} form={form} set={set} />
              <Area label="How would you describe your experience serving on the Board so far?" name="board_experience" form={form} set={set} />
              <Area label="What, if anything, has made it difficult for you to participate as actively as you would like?" name="participation_barriers" form={form} set={set} />
              <Area label="What do you believe would help the Board work more effectively?" name="board_improvement" form={form} set={set} />
              <Select label="How clear are you about where the organization is heading over the next 12–24 months?" name="strategic_clarity" options={CLARITY} form={form} set={set} />
              <Select label="Have you had an opportunity to contribute to the organization's strategic direction or planning?" name="planning_participation" options={["Yes", "Somewhat", "No", "Not Sure"]} form={form} set={set} />
              <Area label="If you would like greater involvement in planning or strategic decisions, tell us how. (optional)" name="planning_involvement_desire" required={false} rows={3} form={form} set={set} />

              <h2 className="intake-step-title">{recommitFormText.h_recommitment}</h2>
              <fieldset className="field choice-field" data-testid="recommit-recommitment-options">
                <legend>{boardRecommitmentFormPageText.lookingAheadAreYouWilling}<b>*</b></legend>
                <div>
                  {(context.recommitment_options || []).map((option) => (
                    <label className={`choice ${form.recommitment === option ? "selected" : ""}`} key={option} style={{ display: "flex", marginBottom: 8 }}>
                      <input type="radio" name="recommitment" checked={form.recommitment === option} onChange={() => setForm((current) => ({ ...current, recommitment: option }))} data-testid={`recommit-option-${(context.recommitment_options || []).indexOf(option) + 1}`} />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
              {!generalVersion && context.allow_advisory && (
                <Select label="If continuing as an active Board Member is not realistic for you, would you be open to supporting the organization in an Advisory Board / Advisory role?" name="advisory_openness" options={["Yes", "Maybe — I would like to discuss it", "No"]} form={form} set={set} required={false} />
              )}
              {!generalVersion && context.allow_support_role && (
                <Select label="If continuing as an active Board Member is not realistic for you, would you be open to supporting the organization in another volunteer or support role?" name="support_role_openness" options={["Yes", "Maybe — I would like to discuss it", "No"]} form={form} set={set} required={false} />
              )}
              {!generalVersion && context.allow_step_off && (
                <Select label="Thinking honestly about your capacity and interest, do you believe you should remain on the board or transition off the board?" name="step_off_openness" options={["I should remain on the board", "I believe I should transition off the board", "I am not sure — I would like to discuss it"]} form={form} set={set} required={false} />
              )}

              <h2 className="intake-step-title">{recommitFormText.h_howYouWantToContribute}</h2>
              <Multi legend="If you continue serving, where would you most like to contribute?" name="contribution_interests" options={CONTRIBUTIONS} form={form} toggle={toggle} />
              <Multi legend="Which fundraising activities would you be comfortable helping with?" name="fundraising_comfort" options={FUNDRAISING} form={form} toggle={toggle} />
              <Area label="What areas of responsibility would you be willing to take greater ownership of over the next 6–12 months?" name="ownership_areas" form={form} set={set} />
              <Area label="Are there any areas where you would be interested in taking a leadership role?" name="leadership_interest" form={form} set={set} />
              <Area label="What support, information or resources would help you contribute more effectively?" name="support_needed" form={form} set={set} />

              <h2 className="intake-step-title">{recommitFormText.h_yourCapacity}</h2>
              <Select label="Realistically, how much time can you commit to Board responsibilities each month?" name="monthly_availability" options={AVAILABILITY} form={form} set={set} />
              <Select label="Are you able to participate consistently in the organization's current Board meeting schedule?" name="meeting_participation" options={MEETINGS} form={form} set={set} />
              <Area label="Is there anything about your current availability or circumstances that the organization should understand when discussing your Board responsibilities? (optional)" name="constraints" required={false} rows={3} form={form} set={set} />

              <h2 className="intake-step-title">{recommitFormText.h_finalQuestions}</h2>
              <Area label="If you continue serving, what would make your Board service meaningful and worthwhile to you?" name="meaningful_service" form={form} set={set} />
              <Area label="Is there anything else you would like the Founder or Board leadership to understand before you discuss your future role on the Board? (optional)" name="anything_else" required={false} rows={3} form={form} set={set} />

              <h2 className="intake-step-title">{recommitFormText.h_confirmation}</h2>
              <label className="choice" style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                <input type="checkbox" checked={form.confirmation} onChange={() => setForm((current) => ({ ...current, confirmation: !current.confirmation }))} data-testid="recommit-confirmation" />
                <span>{boardRecommitmentFormPageText.iConfirmThatTheInformation}<b>*</b></span>
              </label>

              {errorText && <p className="submit-error">{errorText}</p>}
              <div className="intake-nav" style={{ justifyContent: "center" }}>
                <button type="button" className="button rwr-cta-button" onClick={submit} disabled={busy} data-testid="recommit-submit">{busy ? "Submitting…" : "SUBMIT MY RESPONSE"}</button>
              </div>
            </section>
          </>
        )}
      </main>
    </FunnelLayout>
  );
}
