import { useCallback, useEffect, useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
    <FlowVideosManager />
    <JourneyTable />
  </section>
);
