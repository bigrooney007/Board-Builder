import { useEffect, useState } from "react";
import axios from "axios";
import "./autofundraiser.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/autofundraiser`;
const KEY_NAME = "autoFundraiserAdminKey";

function headers(key) {
  return { "X-Auto-Fundraiser-Admin": key };
}

function formatDate(value) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString(); } catch { return value; }
}

export default function AutoFundraiserAdminPage() {
  const [key, setKey] = useState(sessionStorage.getItem(KEY_NAME) || "");
  const [draftKey, setDraftKey] = useState("");
  const [tab, setTab] = useState("leads");
  const [homepage, setHomepage] = useState(null);
  const [leads, setLeads] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async (adminKey = key) => {
    if (!adminKey) return;
    setBusy(true); setError("");
    try {
      const [home, leadList] = await Promise.all([
        axios.get(`${API}/admin/homepage`, { headers: headers(adminKey) }),
        axios.get(`${API}/admin/leads`, { headers: headers(adminKey) }),
      ]);
      setHomepage(home.data);
      setLeads(leadList.data.items || []);
      sessionStorage.setItem(KEY_NAME, adminKey);
      setKey(adminKey);
    } catch (err) {
      setError(err.response?.data?.detail || "We could not open the Auto Fundraiser admin.");
      sessionStorage.removeItem(KEY_NAME);
      setKey("");
    } finally { setBusy(false); }
  };

  useEffect(() => {
    document.title = "Auto Fundraiser Admin";
    if (key) load(key);
  }, []);

  const login = () => {
    if (!draftKey.trim()) return;
    load(draftKey.trim());
  };

  const saveHomepage = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      const { data } = await axios.put(`${API}/admin/homepage`, homepage, { headers: headers(key) });
      setHomepage(data); setMessage("Homepage copy saved.");
    } catch (err) { setError(err.response?.data?.detail || "We could not save the homepage."); }
    finally { setBusy(false); }
  };

  const sendEmail = async (leadId, kind) => {
    setBusy(true); setError(""); setMessage("");
    try {
      const { data } = await axios.post(`${API}/admin/leads/${leadId}/email`, { kind }, { headers: headers(key) });
      setMessage(data.sent ? "Email sent." : "Email was not sent. Check the production email configuration.");
    } catch (err) { setError(err.response?.data?.detail || "We could not send that email."); }
    finally { setBusy(false); }
  };

  if (!key || !homepage) return <div className="af-admin-login">
    <img src="/autofundraiser-logo.png" alt="Auto Fundraiser" />
    <div className="af-admin-login-card">
      <span>AUTO FUNDRAISER ADMIN</span>
      <h1>Open the operating dashboard.</h1>
      <label>Admin key<input type="password" value={draftKey} onChange={(e) => setDraftKey(e.target.value)} onKeyDown={(e) => e.key === "Enter" && login()} /></label>
      {error && <p className="af-error">{error}</p>}
      <button className="af-primary af-primary-wide" disabled={busy || !draftKey.trim()} onClick={login}>{busy ? "OPENING…" : "OPEN ADMIN"}</button>
    </div>
  </div>;

  return <div className="af-admin">
    <aside className="af-admin-side">
      <img src="/autofundraiser-logo.png" alt="Auto Fundraiser" />
      <button className={tab === "leads" ? "active" : ""} onClick={() => setTab("leads")}>People & Progress</button>
      <button className={tab === "homepage" ? "active" : ""} onClick={() => setTab("homepage")}>Homepage</button>
      <button onClick={() => { sessionStorage.removeItem(KEY_NAME); setKey(""); setHomepage(null); }}>Log out</button>
    </aside>

    <main className="af-admin-main">
      <header className="af-admin-top">
        <div><span>AUTO FUNDRAISER</span><h1>{tab === "leads" ? "People & Progress" : "Homepage Editor"}</h1></div>
        <button className="af-secondary" disabled={busy} onClick={() => load()}>{busy ? "REFRESHING…" : "REFRESH"}</button>
      </header>
      {message && <div className="af-admin-message">{message}</div>}
      {error && <p className="af-error">{error}</p>}

      {tab === "homepage" ? <section className="af-admin-panel">
        <div className="af-admin-panel-heading"><div><h2>Edit the Auto Fundraiser homepage</h2><p>These fields control the diagnostic entry page and the $497 result offer.</p></div><button className="af-primary" disabled={busy} onClick={saveHomepage}>{busy ? "SAVING…" : "SAVE HOMEPAGE"}</button></div>
        <div className="af-admin-form">
          {[
            ["headline", "Homepage headline"],
            ["problem_statement", "Problem statement"],
            ["supporting_text", "Supporting text"],
            ["composer_placeholder", "Composer placeholder"],
            ["no_strategy_label", "No-strategy option"],
            ["cta", "Primary CTA"],
            ["result_offer_heading", "Result offer heading"],
            ["result_offer_text", "Result offer text"],
            ["price", "Displayed price"],
          ].map(([field, label]) => <label key={field}>{label}
            {["problem_statement", "supporting_text", "result_offer_text"].includes(field)
              ? <textarea rows={4} value={homepage[field] || ""} onChange={(e) => setHomepage({ ...homepage, [field]: e.target.value })} />
              : <input value={homepage[field] || ""} onChange={(e) => setHomepage({ ...homepage, [field]: e.target.value })} />}
          </label>)}
          <label>Price in cents<input type="number" value={homepage.price_cents || 49700} onChange={(e) => setHomepage({ ...homepage, price_cents: Number(e.target.value) })} /></label>
        </div>
      </section> : <section className="af-admin-panel">
        <div className="af-admin-metrics">
          <div><strong>{leads.length}</strong><span>People entered</span></div>
          <div><strong>{leads.filter((x) => x.diagnosis).length}</strong><span>Diagnoses ready</span></div>
          <div><strong>{leads.filter((x) => x.paid).length}</strong><span>Paid</span></div>
          <div><strong>{leads.reduce((sum, x) => sum + Number(x.contributor_count || 0), 0)}</strong><span>Contributors invited</span></div>
        </div>

        <div className="af-lead-table-wrap">
          <table className="af-lead-table">
            <thead><tr><th>Person</th><th>Organization</th><th>Stage</th><th>Paid</th><th>Contributors</th><th>Last activity</th><th>Follow up</th></tr></thead>
            <tbody>
              {leads.map((lead) => <tr key={lead.lead_id}>
                <td><strong>{lead.name}</strong><span>{lead.email}</span></td>
                <td>{lead.organization_name}</td>
                <td><span className="af-stage">{lead.stage}</span></td>
                <td>{lead.paid ? <span className="af-complete">YES</span> : <span className="af-waiting">NO</span>}</td>
                <td>{lead.contributor_count || 0}</td>
                <td>{formatDate(lead.last_activity_at)}</td>
                <td><div className="af-admin-actions">
                  {!lead.paid && ["SOURCE_CAPTURED", "CLARIFYING"].includes(lead.stage) && <button onClick={() => sendEmail(lead.lead_id, "resume")}>Resume email</button>}
                  {!lead.paid && lead.diagnosis && <button onClick={() => sendEmail(lead.lead_id, "payment")}>Payment email</button>}
                </div></td>
              </tr>)}
              {leads.length === 0 && <tr><td colSpan="7" className="af-empty">Nobody has entered Auto Fundraiser yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>}
    </main>
  </div>;
}
