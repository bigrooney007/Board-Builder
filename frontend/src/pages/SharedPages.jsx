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
  const spec = resource?.design_spec || {};
  const headingScale = Number(spec.heading_scale) || 1;
  const spacingScale = Number(spec.spacing_scale) || 1;
  const logoPosition = spec.logo_position || "left";
  return (
    <main className="hosted-agreement-page" data-testid="shared-resource-page">
      {error && <div className="member-card" style={{ margin: "60px auto", maxWidth: 480 }}><h2>{error}</h2></div>}
      {resource && (
        <article className="hosted-agreement" style={{
          "--agreement-primary": spec.accent_intensity === "subtle" ? "#3b3b36" : primary,
          fontFamily: spec.body_font === "sans-serif" ? "'Helvetica Neue', Arial, sans-serif" : undefined,
          textAlign: spec.text_align === "center" ? "center" : undefined,
          borderTop: spec.accent_intensity === "strong" ? `6px solid ${primary}` : undefined,
        }}>
          <header className="hosted-agreement-head" style={logoPosition === "center" ? { textAlign: "center" } : undefined}>
            {resource.logo_data && <img src={resource.logo_data} alt={`${resource.organization_name} logo`} className="hosted-agreement-logo" style={{
              float: logoPosition === "right" ? "right" : undefined,
              display: logoPosition === "center" ? "block" : undefined,
              margin: logoPosition === "center" ? "0 auto 12px" : undefined,
            }} />}
            {resource.organization_name && <p className="hosted-agreement-org">{resource.organization_name}</p>}
            <h1 data-testid="shared-resource-title" style={headingScale !== 1 ? { fontSize: `${Math.round(headingScale * 28)}px` } : undefined}>{resource.title}</h1>
          </header>
          <div className="hosted-agreement-body" data-testid="shared-resource-body" style={spacingScale !== 1 ? { lineHeight: 1.7 * spacingScale } : undefined}>{resource.display_text}</div>
        </article>
      )}
    </main>
  );
}

const PROFILE_FIELDS = [
  ["full_name", "Full name", "text", true],
  ["preferred_name", "Preferred name", "text", false],
  ["email", "Email", "text", true],
  ["phone", "Phone", "text", false],
  ["location", "Location (city, state/region)", "text", false],
  ["professional_title", "Professional title", "text", false],
  ["employer", "Employer/organization", "text", false],
  ["linkedin", "LinkedIn profile", "text", false],
  ["bio", "Professional bio", "textarea", false],
  ["skills", "Skills", "textarea", false],
  ["professional_experience", "Professional experience", "textarea", false],
  ["board_experience", "Board experience", "textarea", false],
  ["fundraising_strengths", "Fundraising interests/strengths", "textarea", false],
  ["relationships", "Professional/community relationships", "textarea", false],
  ["committees_of_interest", "Committees of interest", "textarea", false],
  ["availability", "Availability", "textarea", false],
];

export function BoardProfileFormPage() {
  const { token } = useParams();
  const [org, setOrg] = useState("");
  const [data, setData] = useState({});
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    axios.get(`${API}/board-profile/${token}`).then((response) => {
      setOrg(response.data.organization_name);
      const prefill = response.data.prefill || {};
      setData((current) => ({ ...Object.fromEntries(Object.entries(prefill).filter(([, value]) => value)), ...current }));
    }).catch(() => setError("This form is not available."));
  }, [token]);
  const submit = async () => {
    setError("");
    if (!data.full_name?.trim() || !data.email?.trim()) { setError("Full name and email are required."); return; }
    try { await axios.post(`${API}/board-profile/${token}`, data); setStatus("submitted"); }
    catch (err) { setError(err.response?.data?.detail || "Could not submit the form."); }
  };
  return (
    <FunnelLayout>
      <main className="board-profile-page" data-testid="board-profile-page">
        {error && !status && <p className="submit-error" data-testid="board-profile-error">{error}</p>}
        {status === "submitted" ? (
          <section className="shared-resource-card"><h1>{sharedPagesText.h_thankYou}</h1><p>Your board member profile has been submitted to {org}.</p></section>
        ) : org && (
          <section className="shared-resource-card">
            <p className="eyebrow">Board Member Profile</p>
            <h1>{org}</h1>
            <p>Complete this profile so the organization has an accurate record of the skills, relationships and experience you bring to the board.</p>
            <div className="step-fields">
              {PROFILE_FIELDS.map(([name, label, type, required]) => (
                <label className="field" key={name} data-testid={`board-profile-${name}`}>
                  <span>{label}{required && <b> *</b>}</span>
                  {type === "textarea"
                    ? <textarea rows="3" value={data[name] || ""} onChange={(event) => setData({ ...data, [name]: event.target.value })} />
                    : <input value={data[name] || ""} onChange={(event) => setData({ ...data, [name]: event.target.value })} />}
                </label>
              ))}
            </div>
            <button className="button" onClick={submit} data-testid="board-profile-submit">Submit My Board Member Profile</button>
          </section>
        )}
      </main>
    </FunnelLayout>
  );
}
