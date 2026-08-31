import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { FunnelLayout } from "@/funnels/FunnelLayout";
import { sharedPagesText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function SharedResourcePage() {
  const { token } = useParams();
  const [resource, setResource] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots"; meta.content = "noindex, nofollow";
    document.head.appendChild(meta);
    return () => document.head.removeChild(meta);
  }, []);
  useEffect(() => {
    axios.get(`${API}/shared/${token}`).then((response) => setResource(response.data)).catch(() => setError("This shared resource is not available."));
  }, [token]);
  const primary = resource?.primary_color || "#1d3a2f";
  const createdBy = resource?.created_by || {};
  return (
    <main className="hosted-agreement-page" data-testid="shared-resource-page">
      {error && <div className="member-card" style={{ margin: "60px auto", maxWidth: 480 }}><h2>{error}</h2></div>}
      {resource && (
        <article className="hosted-agreement standard-document" style={{ "--agreement-primary": primary, borderColor: primary }}>
          <header className="hosted-agreement-head standard-document-cover">
            {resource.logo_data && <img src={resource.logo_data} alt={`${resource.organization_name} logo`} className="hosted-agreement-logo standard-document-logo" />}
            <h1 data-testid="shared-resource-title">{resource.title}</h1>
            {resource.organization_name && <p className="hosted-agreement-org standard-document-org">{resource.organization_name}</p>}
          </header>
          <div className="hosted-agreement-body standard-document-body" data-testid="shared-resource-body">{resource.display_text}</div>
          {(createdBy.name || createdBy.organization) && (
            <footer className="standard-document-created-by" data-testid="shared-resource-created-by">
              <h2>Created By</h2>
              {createdBy.name && <p>{createdBy.name}</p>}
              {createdBy.title && <p>{createdBy.title}</p>}
              {createdBy.organization && <p>{createdBy.organization}</p>}
            </footer>
          )}
        </article>
      )}
    </main>
  );
}

const EXPERTISE_OPTIONS = ["Fundraising", "Major Gifts", "Grant Writing", "Finance / Accounting", "Legal", "Human Resources", "Marketing / Communications", "Public Relations", "Strategic Planning", "Organizational Development", "Nonprofit Leadership", "Corporate Partnerships", "Government Relations", "Education", "Youth Development", "Healthcare", "Mental Health", "Technology / AI", "Program Development", "Operations", "Project Management", "Community Engagement", "Volunteer Management", "Events", "Advocacy", "Other"];
const CONTRIBUTION_OPTIONS = ["Fundraising / Resource Development", "Marketing & Communications", "Programs & Impact", "Partnerships", "Finance", "Governance / Board Development", "Strategic Planning", "Technology", "Volunteer Development", "Community Engagement", "Operations", "Board Recruitment", "Other"];
const NETWORK_OPTIONS = ["Business Leaders", "Corporate Executives", "Foundations / Philanthropy", "Community Leaders", "Government / Public Sector", "Schools / Universities", "Faith Communities", "Healthcare Organizations", "Technology Sector", "Media", "Professional Associations", "Other"];
const HOURS_OPTIONS = ["Less than 2 hours", "2–4 hours", "5–8 hours", "9–12 hours", "12+ hours"];
const LEADERSHIP_OPTIONS = ["Yes", "I would like to discuss this", "Not at this time"];

const IDENTITY_FIELDS = [
  ["full_name", "Full Name", true], ["preferred_name", "Preferred Name", false], ["email", "Email Address", true],
  ["phone", "Phone Number", false], ["mailing_address", "Mailing Address", false], ["linkedin", "LinkedIn Profile (optional)", false],
];

const MultiSelect = ({ label, options, value, onChange, max = 0, note = "" }) => (
  <fieldset className="field choice-field">
    <legend>{label}{max ? ` (select up to ${max})` : ""}</legend>
    {note && <p style={{ fontSize: "0.85rem", color: "#555" }}>{note}</p>}
    <div className="choice-grid">
      {options.map((option) => {
        const selected = (value || []).includes(option);
        return (
          <label className={`choice ${selected ? "selected" : ""}`} key={option}>
            <input type="checkbox" checked={selected} onChange={() => {
              const list = value || [];
              if (selected) onChange(list.filter((item) => item !== option));
              else if (!max || list.length < max) onChange([...list, option]);
            }} data-testid={`board-profile-option-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
            <span>{option}</span>
          </label>
        );
      })}
    </div>
  </fieldset>
);

export function BoardProfileFormPage() {
  const { token } = useParams();
  const [org, setOrg] = useState("");
  const [data, setData] = useState({ expertise: [], contribution_areas: [], networks: [] });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    axios.get(`${API}/board-profile/${token}`).then((response) => {
      setOrg(response.data.organization_name);
      const prefill = response.data.prefill || {};
      setData((current) => ({ ...current, ...Object.fromEntries(Object.entries({
        full_name: prefill.full_name, email: prefill.email, professional_title: prefill.professional_title,
        employer: prefill.employer, linkedin: prefill.linkedin, mailing_address: prefill.location,
      }).filter(([, value]) => value)) }));
    }).catch(() => setError("This form is not available."));
  }, [token]);
  const set = (name, value) => setData((current) => ({ ...current, [name]: value }));
  const uploadHeadshot = (file) => {
    if (!file) return;
    if (file.size > 1000000) { setError("The headshot must be under 1MB."); return; }
    const reader = new FileReader();
    reader.onload = () => set("headshot_data", reader.result);
    reader.readAsDataURL(file);
  };
  const submit = async () => {
    setError("");
    if (!data.full_name?.trim() || !data.email?.trim()) { setError("Full name and email are required."); return; }
    try { await axios.post(`${API}/board-profile/${token}`, data); setStatus("submitted"); window.scrollTo(0, 0); }
    catch (err) { setError(err.response?.data?.detail || "Could not submit the form."); }
  };
  const Text = ({ name, label, required = false }) => (
    <label className="field" data-testid={`board-profile-${name}`}>
      <span>{label}{required && <b> *</b>}</span>
      <input value={data[name] || ""} onChange={(event) => set(name, event.target.value)} />
    </label>
  );
  const Area = ({ name, label, helper = "" }) => (
    <label className="field" data-testid={`board-profile-${name}`}>
      <span>{label}</span>
      {helper && <span style={{ display: "block", fontSize: "0.85rem", color: "#555", marginBottom: 4 }}>{helper}</span>}
      <textarea rows="3" value={data[name] || ""} onChange={(event) => set(name, event.target.value)} />
    </label>
  );
  return (
    <FunnelLayout>
      <main className="board-profile-page" data-testid="board-profile-page">
        {error && !status && <p className="submit-error" data-testid="board-profile-error">{error}</p>}
        {status === "submitted" ? (
          <section className="shared-resource-card"><h1>{sharedPagesText.h_thankYou}</h1><p>Your Board Member Profile has been submitted to {org}. It will help us prepare for your onboarding conversation and understand where your experience can best support the Board.</p></section>
        ) : org && (
          <section className="shared-resource-card">
            <p className="eyebrow">New Board Member Profile Form</p>
            <h1>{org}</h1>
            <p>Welcome to the Board. This form will help us better understand your professional background, strengths, interests, relationships and capacity so we can engage you meaningfully as you begin serving with {org}. Your responses will also help us prepare for your onboarding conversation and understand where your experience can best support the Board and organization.</p>
            <p>This form does not assign your final responsibilities. During onboarding, we will discuss how your interests and experience align with the organization's needs and agree together on the way you will contribute.</p>
            <div className="step-fields">
              <h2 className="intake-step-title">About You</h2>
              {IDENTITY_FIELDS.map(([name, label, required]) => <Text key={name} name={name} label={label} required={required} />)}
              <h2 className="intake-step-title">Professional Background</h2>
              <Text name="professional_title" label="Current Position" />
              <Text name="employer" label="Organization / Employer" />
              <Text name="industry" label="Industry / Professional Field" />
              <MultiSelect label="What areas of professional expertise do you bring?" options={EXPERTISE_OPTIONS} value={data.expertise} onChange={(value) => set("expertise", value)} />
              <Text name="certifications" label="Professional Certifications or Licenses (optional)" />
              <Area name="board_experience" label="Previous Board Experience (optional)" helper="Please tell us about any nonprofit, corporate or community Boards you have previously served on." />
              <h2 className="intake-step-title">How You Would Like to Contribute</h2>
              <MultiSelect label="Which areas would you most like to contribute to as a member of the Board?" options={CONTRIBUTION_OPTIONS} value={data.contribution_areas} onChange={(value) => set("contribution_areas", value)} max={3} />
              <Area name="greater_responsibility" label="Of the areas you selected, which one would you be most interested in taking greater responsibility for helping the Board move forward, and what would you hope to help accomplish?" />
              <h2 className="intake-step-title">Leadership Interest</h2>
              <fieldset className="field choice-field" data-testid="board-profile-leadership-interest">
                <legend>Would you be interested in taking on a Board leadership or committee responsibility if an appropriate opportunity aligns with your experience and interests?</legend>
                <div className="choice-grid">
                  {LEADERSHIP_OPTIONS.map((option) => (
                    <label className={`choice ${data.leadership_interest === option ? "selected" : ""}`} key={option}>
                      <input type="radio" checked={data.leadership_interest === option} onChange={() => set("leadership_interest", option)} />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
              {data.leadership_interest === "Yes" && <Area name="leadership_type" label="What type of Board leadership or committee work would you be most interested in?" />}
              <h2 className="intake-step-title">Professional Networks</h2>
              <MultiSelect label="Which types of professional or community relationships do you have that you may be comfortable helping the organization connect with when appropriate?" options={NETWORK_OPTIONS} value={data.networks} onChange={(value) => set("networks", value)} note="Selecting an area does not commit you to making introductions. It simply helps us understand the relationships and perspectives represented around the Board." />
              <h2 className="intake-step-title">Additional Strengths & Capacity</h2>
              <Area name="additional_strengths" label="Are there any other skills, resources, languages, lived/professional experience or strengths you would like the Board to know about?" />
              <label className="field" data-testid="board-profile-monthly-hours">
                <span>Approximately how many hours per month can you realistically dedicate to Board service?</span>
                <select value={data.monthly_hours || ""} onChange={(event) => set("monthly_hours", event.target.value)}>
                  <option value="">Select…</option>
                  {HOURS_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <Area name="what_would_help" label="What would help you contribute effectively and have a meaningful experience serving on this Board?" />
              <Area name="why_joined" label={`Why did you choose to join ${org}?`} />
              <h2 className="intake-step-title">Biography & Headshot</h2>
              <Area name="bio" label="Professional Biography (approximately 150–250 words)" helper="Your biography and headshot may be used for appropriate Board introductions and organization materials according to the organization's process. They are not published automatically." />
              <label className="field" data-testid="board-profile-headshot">
                <span>Professional Headshot (image upload, optional)</span>
                <input type="file" accept="image/*" onChange={(event) => uploadHeadshot(event.target.files?.[0])} />
                {data.headshot_data && <span style={{ fontSize: "0.85rem", color: "#1d3a2f" }}>Headshot attached ✓</span>}
              </label>
            </div>
            <button className="button" onClick={submit} data-testid="board-profile-submit">{sharedPagesText.submitMyBoardMemberProfile}</button>
          </section>
        )}
      </main>
    </FunnelLayout>
  );
}
