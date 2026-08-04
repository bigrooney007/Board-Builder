import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Download, FileText, LogOut, RefreshCw, Search, Users } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });
const statuses = ["New Applicant", "Active", "Under Review", "Contacted", "Presented to Nonprofit", "Interviewing", "Placed on Board", "Paused", "Withdrawn"];
const blankFilters = { search: "", country: "", state_region: "", cause: "", skill: "", board_type: "", fundraising: "", availability: "" };

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault(); setError("");
    try { const response = await client.post("/auth/login", { email, password }); onLogin(response.data); }
    catch (err) { setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Login failed."); }
  };
  return <main className="admin-login-page" data-testid="admin-login-page"><form className="admin-login-card" onSubmit={submit}><div className="admin-login-icon"><Users size={27} /></div><p className="eyebrow">Owner access</p><h1>Board Applicants Administration</h1><p>Private access for the Nonprofit Board Builder owner.</p><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required data-testid="admin-email-input" /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required data-testid="admin-password-input" /></label>{error && <p className="submit-error" data-testid="admin-login-error">{error}</p>}<button className="button" type="submit" data-testid="admin-login-button">Log In</button></form></main>;
};

const Profile = ({ applicant, close, refresh }) => {
  const [status, setStatus] = useState(applicant.status);
  const [notes, setNotes] = useState(applicant.internal_notes || "");
  const [message, setMessage] = useState("");
  const save = async () => { await client.patch(`/admin/applicants/${applicant.applicant_id}`, { status, internal_notes: notes }); setMessage("Profile updated."); refresh(); };
  const retry = async () => { setMessage("Syncing…"); try { await client.post(`/admin/applicants/${applicant.applicant_id}/retry-resend`); setMessage("Resend sync complete."); refresh(); } catch { setMessage("Resend sync failed."); } };
  const groups = [
    ["Contact", ["applicant_id", "email", "phone", "linkedin_url", "country", "city", "state_region", "postal_code"]],
    ["Professional Background", ["job_title", "employer", "professional_field", "years_experience", "skills", "other_skill", "professional_summary"]],
    ["Board Preferences", ["causes", "other_cause", "board_types", "participation_preferences", "geographic_preferences", "availability", "monthly_commitment"]],
    ["Contribution", ["previous_board_experience", "board_experience_details", "fundraising_activities", "professional_relationships", "reason_for_joining", "commitment_answer", "understands_unpaid"]],
    ["Permissions", ["profile_sharing_permission", "board_opportunity_consent", "other_offers_consent", "privacy_accepted", "consent_at"]],
  ];
  const label = (key) => key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const display = (value) => Array.isArray(value) ? value.join(", ") : typeof value === "boolean" ? (value ? "Yes" : "No") : (value || "Not provided");
  return <div className="admin-profile-overlay" data-testid="admin-applicant-profile"><div className="admin-profile-panel"><button className="profile-close" onClick={close} data-testid="admin-profile-close-button">×</button><p className="eyebrow">Applicant profile</p><h2>{applicant.first_name} {applicant.last_name}</h2><div className="admin-profile-actions"><label>Status<select value={status} onChange={(event) => setStatus(event.target.value)} data-testid="admin-applicant-status-select">{statuses.map((item) => <option key={item}>{item}</option>)}</select></label>{applicant.resume_file_id && <a className="button button-back" href={`${API}/admin/applicants/${applicant.applicant_id}/resume`} data-testid="admin-resume-download-link"><Download size={16} /> Download résumé</a>}<button className="button button-back" onClick={retry} data-testid="admin-retry-resend-button"><RefreshCw size={16} /> Retry Resend</button></div>{groups.map(([title, keys]) => <section className="profile-group" key={title}><h3>{title}</h3><dl>{keys.map((key) => <div key={key}><dt>{label(key)}</dt><dd>{display(applicant[key])}</dd></div>)}</dl></section>)}<label className="admin-notes">Internal notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows="5" data-testid="admin-internal-notes-textarea" /></label>{message && <p className="admin-message" data-testid="admin-profile-message">{message}</p>}<button className="button" onClick={save} data-testid="admin-save-profile-button">Save Applicant Changes</button></div></div>;
};

export default function AdminPage() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState("applicants");
  const [applicants, setApplicants] = useState([]);
  const [nonprofits, setNonprofits] = useState([]);
  const [filters, setFilters] = useState(blankFilters);
  const [selected, setSelected] = useState([]);
  const [profile, setProfile] = useState(null);

  useEffect(() => { client.get("/auth/me").then((response) => setUser(response.data)).catch(() => setUser(false)).finally(() => setChecking(false)); }, []);
  const loadApplicants = useCallback(async () => { const response = await client.get("/admin/applicants", { params: filters }); setApplicants(response.data); }, [filters]);
  const loadNonprofits = useCallback(async () => { const response = await client.get("/admin/nonprofit-contacts"); setNonprofits(response.data); }, []);
  useEffect(() => { if (user) { loadApplicants(); loadNonprofits(); } }, [user, loadApplicants, loadNonprofits]);
  const filterOptions = useMemo(() => ({
    state_region: [...new Set(applicants.map((item) => item.state_region).filter(Boolean))],
    cause: [...new Set(applicants.flatMap((item) => item.causes || []))],
    skill: [...new Set(applicants.flatMap((item) => item.skills || []))],
    board_type: [...new Set(applicants.flatMap((item) => item.board_types || []))],
    fundraising: [...new Set(applicants.flatMap((item) => item.fundraising_activities || []))],
    availability: [...new Set(applicants.map((item) => item.availability).filter(Boolean))],
  }), [applicants]);
  const openProfile = async (id) => { const response = await client.get(`/admin/applicants/${id}`); setProfile(response.data); };
  const logout = async () => { await client.post("/auth/logout"); setUser(false); };
  if (checking) return <div className="admin-loading" data-testid="admin-loading">Checking administrator access…</div>;
  if (!user) return <Login onLogin={setUser} />;
  return <main className="admin-page" data-testid="admin-dashboard"><header className="admin-header"><div><p className="eyebrow">Private administrator area</p><h1>Board Applicant Network</h1></div><button onClick={logout} data-testid="admin-logout-button"><LogOut size={17} /> Log out</button></header><div className="admin-broadcast-note" data-testid="admin-broadcast-instruction">Send board-opportunity and nonprofit broadcasts through the Resend Broadcast dashboard using the Board Applicants or Nonprofit Leaders segment.</div><nav className="admin-tabs"><button className={tab === "applicants" ? "active" : ""} onClick={() => setTab("applicants")} data-testid="admin-applicants-tab">Board Applicants</button><button className={tab === "nonprofits" ? "active" : ""} onClick={() => setTab("nonprofits")} data-testid="admin-nonprofits-tab">Nonprofit Contacts</button></nav>{tab === "applicants" ? <section><div className="admin-filters"><label className="search-filter"><Search size={15} /><input placeholder="Search name or email" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} data-testid="admin-applicant-search" /></label><select value={filters.country} onChange={(event) => setFilters({ ...filters, country: event.target.value })} data-testid="admin-country-filter"><option value="">All countries</option><option>United States</option><option>United Kingdom</option></select>{Object.entries(filterOptions).map(([key, options]) => <select key={key} value={filters[key]} onChange={(event) => setFilters({ ...filters, [key]: event.target.value })} data-testid={`admin-${key.replace("_", "-")}-filter`}><option value="">All {key.replace("_", " ")}</option>{options.map((option) => <option key={option}>{option}</option>)}</select>)}<button className="button button-small" onClick={loadApplicants} data-testid="admin-apply-filters-button">Apply Filters</button><a className="button button-back button-small" href={`${API}/admin/applicants-export.csv?ids=${selected.join(",")}`} data-testid="admin-export-csv-link"><Download size={15} /> Export {selected.length ? "Selected" : "All"}</a></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th><input type="checkbox" aria-label="Select all applicants" checked={applicants.length > 0 && selected.length === applicants.length} onChange={(event) => setSelected(event.target.checked ? applicants.map((item) => item.applicant_id) : [])} data-testid="admin-select-all-applicants" /></th>{["Applicant ID", "Name", "Email", "Phone", "Country / City", "Job title", "Professional field", "Main expertise", "Preferred causes", "Preferred board type", "Availability", "Status", "Resend", "Created"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead><tbody>{applicants.map((item) => <tr key={item.applicant_id} data-testid={`admin-applicant-row-${item.applicant_id}`}><td><input type="checkbox" checked={selected.includes(item.applicant_id)} onChange={() => setSelected((current) => current.includes(item.applicant_id) ? current.filter((id) => id !== item.applicant_id) : [...current, item.applicant_id])} /></td><td><button className="table-link" onClick={() => openProfile(item.applicant_id)}>{item.applicant_id}</button></td><td>{item.first_name} {item.last_name}</td><td>{item.email}</td><td>{item.phone}</td><td>{item.country}<small>{item.city}</small></td><td>{item.job_title}</td><td>{item.professional_field}</td><td>{item.skills?.[0]}</td><td>{item.causes?.[0]}</td><td>{item.board_types?.[0]}</td><td>{item.availability}</td><td>{item.status}</td><td><span className={`sync-badge ${item.resend_segment_status?.toLowerCase()}`}>{item.resend_segment_status}</span></td><td>{item.created_at?.slice(0, 10)}</td></tr>)}</tbody></table></div></section> : <section className="nonprofit-admin-section"><div className="admin-table-wrap"><table className="admin-table"><thead><tr>{["Name", "Email", "Phone", "Organization", "Country", "Assessment date", "Consent date", "Resend"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead><tbody>{nonprofits.map((item) => <tr key={`${item.email}-${item.submitted_at}`}><td>{item.name}</td><td>{item.email}</td><td>{item.phone}</td><td>{item.organization_name}</td><td>{item.country}</td><td>{item.submitted_at?.slice(0, 10)}</td><td>{item.marketing_consent_at?.slice(0, 10)}</td><td>{item.marketing_resend_status}</td></tr>)}</tbody></table></div></section>}{profile && <Profile applicant={profile} close={() => setProfile(null)} refresh={loadApplicants} />}</main>;
}