import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { setAdminPreview } from "../adminPreview";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PREVIEW_PAGES = [
  { key: "three-mistakes", label: "1. Three Mistakes Video Page", path: "/offer/board-fix" },
  { key: "offer", label: "2. 50% Off Offer Page ($497 Checkout)", path: "/offer/fundraising-board-builder" },
  { key: "welcome", label: "3. Welcome Video Page", path: "/welcome" },
  { key: "intake", label: "4. Organization Intake", path: "/board-fix-intake" },
  { key: "dashboard", label: "5. Customer Dashboard", path: "/app" },
  { key: "activation", label: "5a. Board Fundraising Activation", path: "/app/fundraising-activation" },
  { key: "recruitment", label: "5b. Board Recruitment", path: "/app/board-recruitment" },
];

const ReviewCustomerFlow = () => {
  const [mode, setMode] = useState("fresh");
  const [memberId, setMemberId] = useState("");
  const [customers, setCustomers] = useState([]);
  useEffect(() => {
    axios.get(`${API}/admin/fbb/customers`, { withCredentials: true })
      .then((r) => setCustomers(r.data.customers || [])).catch(() => {});
  }, []);
  const accounts = customers.filter((c) => c.account_created && c.user_id);

  const open = (path) => {
    if (mode === "customer") {
      const selected = accounts.find((c) => c.user_id === memberId);
      if (!selected) return;
      setAdminPreview({ mode: "customer", memberId, name: selected.name || selected.email });
    } else {
      setAdminPreview({ mode: "fresh" });
    }
    window.location.assign(path);
  };

  return (
    <section className="member-card" data-testid="admin-review-customer-flow" style={{ marginBottom: 26 }}>
      <h2>Review Customer Flow</h2>
      <p>Open the actual customer-facing pages exactly as a customer sees them. Payment and login walls are bypassed for your admin session. Use the EXIT PREVIEW button in the banner to return here.</p>
      <div style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "center", margin: "10px 0 6px" }}>
        <strong>Preview Mode:</strong>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <input type="radio" name="fbb-preview-mode" checked={mode === "fresh"} onChange={() => setMode("fresh")} data-testid="preview-mode-fresh" />
          Fresh Customer
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <input type="radio" name="fbb-preview-mode" checked={mode === "customer"} onChange={() => setMode("customer")} data-testid="preview-mode-customer" />
          Existing Customer
        </label>
        {mode === "customer" && (
          <select value={memberId} onChange={(e) => setMemberId(e.target.value)} data-testid="preview-customer-select"
            style={{ padding: "8px 10px", borderRadius: 6, border: "1px solid #cfd6d2", minWidth: 240 }}>
            <option value="">Select Organization / Customer…</option>
            {accounts.map((c) => (
              <option key={c.user_id} value={c.user_id}>{c.organization ? `${c.organization} — ` : ""}{c.name || c.email}</option>
            ))}
          </select>
        )}
      </div>
      {mode === "customer" && accounts.length === 0 && <p><em data-testid="preview-no-accounts">No customers with accounts yet — use Fresh Customer mode.</em></p>}
      {mode === "customer" && <p style={{ fontSize: "0.88rem", margin: "0 0 6px" }}>Existing-customer preview is read-only: you see their real data but nothing you click will change it.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
        {PREVIEW_PAGES.map((page) => (
          <div key={page.key} style={{ display: "flex", alignItems: "center", gap: 12, borderTop: "1px solid #e3e8e4", paddingTop: 8 }}>
            <span style={{ flex: 1, fontWeight: 600 }}>{page.label}</span>
            <button className="button button-small" onClick={() => open(page.path)}
              disabled={mode === "customer" && !memberId}
              data-testid={`preview-open-${page.key}`}>OPEN PAGE</button>
          </div>
        ))}
      </div>
    </section>
  );
};

const FlowVideosManager = () => {
  const [videos, setVideos] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [notice, setNotice] = useState("");
  const [busyKey, setBusyKey] = useState("");

  const load = useCallback(() => {
    axios.get(`${API}/admin/flow-videos`, { withCredentials: true })
      .then((r) => setVideos(r.data.videos || []))
      .catch(() => setNotice("We could not load the flow videos."));
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (key) => {
    setBusyKey(key);
    setNotice("");
    try {
      const response = await axios.put(`${API}/admin/flow-videos/${key}`, { url: drafts[key] ?? "" }, { withCredentials: true });
      setVideos(response.data.videos || []);
      setDrafts((current) => ({ ...current, [key]: undefined }));
      setNotice("Video updated. The customer-facing page now uses the new video.");
    } catch (err) {
      setNotice(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save this video URL.");
    }
    setBusyKey("");
  };

  return (
    <section className="member-card" data-testid="admin-flow-videos" style={{ marginBottom: 26 }}>
      <h2>Flow Videos</h2>
      <p>Change the videos used throughout the Fundraising Board Builder customer journey. Paste a new YouTube URL and save — the customer-facing page uses it immediately.</p>
      {notice && <p data-testid="flow-videos-notice" style={{ fontWeight: 700 }}>{notice}</p>}
      {videos.map((video) => (
        <div key={video.key} data-testid={`flow-video-row-${video.key}`} style={{ borderTop: "1px solid #e3e8e4", padding: "14px 0" }}>
          <p style={{ margin: "0 0 4px", fontWeight: 700 }}>{video.name}</p>
          <p style={{ margin: "0 0 8px", fontSize: "0.9rem" }}>Current Video URL: {video.url ? <a href={video.url} target="_blank" rel="noreferrer" data-testid={`flow-video-current-${video.key}`}>{video.url}</a> : <em data-testid={`flow-video-current-${video.key}`}>No video set</em>}</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input value={drafts[video.key] ?? video.url} onChange={(e) => setDrafts({ ...drafts, [video.key]: e.target.value })}
              placeholder="Paste new YouTube URL" data-testid={`flow-video-input-${video.key}`}
              style={{ flex: 1, minWidth: 260, padding: "9px 12px", borderRadius: 6, border: "1px solid #cfd6d2" }} />
            <button className="button button-small" onClick={() => save(video.key)} disabled={busyKey === video.key}
              data-testid={`flow-video-save-${video.key}`}>{busyKey === video.key ? "Saving…" : "SAVE"}</button>
          </div>
        </div>
      ))}
    </section>
  );
};

const JourneyTable = () => {
  const [data, setData] = useState({ customers: [], leads: [] });
  const [error, setError] = useState("");
  const [showLeads, setShowLeads] = useState(false);

  useEffect(() => {
    axios.get(`${API}/admin/fbb/customers`, { withCredentials: true })
      .then((r) => setData(r.data))
      .catch(() => setError("We could not load the customer journey."));
  }, []);

  return (
    <section className="member-card" data-testid="admin-fbb-journey">
      <h2>Customer Journey</h2>
      <p>Every Fundraising Board Builder purchase and where each customer is in the journey.</p>
      {error && <p className="submit-error">{error}</p>}
      <div className="admin-table-wrap">
        <table className="admin-table" data-testid="fbb-customers-table">
          <thead><tr>{["Name", "Email", "Organization", "Stage", "Intake", "Account", "Planning Responses", "Strategy", "Applicants", "Started"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {data.customers.length === 0 && <tr><td colSpan={10} data-testid="fbb-no-customers">No Fundraising Board Builder customers yet.</td></tr>}
            {data.customers.map((row) => (
              <tr key={row.session_id} data-testid={`fbb-customer-row-${row.session_id}`}>
                <td>{row.name || "—"}</td>
                <td>{row.email || "—"}</td>
                <td>{row.organization || "—"}</td>
                <td><strong>{row.stage}</strong></td>
                <td>{row.intake_submitted ? "Completed" : "—"}</td>
                <td>{row.account_created ? "Created" : "—"}</td>
                <td>{row.activation?.planning_responses ?? 0}</td>
                <td>{row.activation?.strategy_status || "—"}</td>
                <td>{row.recruitment?.applicants ?? 0}</td>
                <td>{(row.created_at || "").slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ marginTop: 18 }}>
        <button className="table-link" onClick={() => setShowLeads(!showLeads)} data-testid="fbb-toggle-leads">
          {showLeads ? "Hide" : "Show"} homepage leads who have not purchased ({data.leads.length})
        </button>
      </p>
      {showLeads && (
        <div className="admin-table-wrap">
          <table className="admin-table" data-testid="fbb-leads-table">
            <thead><tr>{["Name", "Email", "Stage", "Video Email", "Captured"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {data.leads.map((lead) => (
                <tr key={`${lead.email}-${lead.created_at}`}>
                  <td>{lead.name}</td><td>{lead.email}</td><td>{lead.stage}</td>
                  <td>{lead.video_email_status || "—"}</td><td>{(lead.created_at || "").slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

export const FBBSection = () => (
  <section data-testid="admin-fbb-section">
    <ReviewCustomerFlow />
    <FlowVideosManager />
    <JourneyTable />
  </section>
);
