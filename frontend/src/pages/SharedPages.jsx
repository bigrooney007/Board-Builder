import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { FunnelLayout } from "@/funnels/FunnelLayout";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function SharedResourcePage() {
  const { token } = useParams();
  const [resource, setResource] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    axios.get(`${API}/shared/${token}`).then((response) => setResource(response.data)).catch(() => setError("This shared resource is not available."));
  }, [token]);
  return (
    <FunnelLayout>
      <main className="shared-resource-page" data-testid="shared-resource-page">
        {error && <p className="submit-error">{error}</p>}
        {resource && (
          <article className="shared-resource-card">
            <h1 data-testid="shared-resource-title">{resource.title}</h1>
            <pre className="material-display" data-testid="shared-resource-body">{resource.display_text}</pre>
          </article>
        )}
      </main>
    </FunnelLayout>
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
          <section className="shared-resource-card"><h1>Thank you</h1><p>Your board member profile has been submitted to {org}.</p></section>
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
