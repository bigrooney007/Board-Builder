import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { RefreshCw } from "lucide-react";
import { VIDEO_KEYS } from "@/clean/platform";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

const LABELS = {
  main: "Main Home Page",
  recruitment: "Board Recruitment",
  "board-fundraising-game": "Board Fundraising Game",
  "strategic-planning": "Strategic Planning",
  "board-recommitment": "Board Recommitment",
  "facilitated-game": "Let's Organize Your Board Fundraising Game",
  "board-applicant-network": "Board Applicant Network",
};

const duration = (seconds) => {
  const value = Number(seconds || 0);
  if (value < 60) return `${Math.round(value)} sec`;
  return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
};

export function PlatformAnalyticsSection() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setData((await client.get("/admin/platform-analytics")).data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load platform analytics.");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const flows = useMemo(() => data?.flows || [], [data]);

  return (
    <section data-testid="clean-platform-analytics">
      <div className="admin-funnel-numbers-head">
        <div>
          <h2>Platform Funnel Analytics</h2>
          <p>One view of traffic, contact capture, video engagement, Stripe movement, dashboard entry, completion and average active use.</p>
        </div>
        <button className="button button-back button-small" onClick={load}><RefreshCw size={15} /> Refresh</button>
      </div>

      {error && <p className="submit-error">{error}</p>}

      {!data ? <p>Loading analytics…</p> : (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  {["Flow", "Unique Home Visitors", "Contact Details", "Checkout Clicks", "Stripe Sessions", "Paid", "Dashboard Entries", "Completed", "Avg. Platform Use"].map((item) => <th key={item}>{item}</th>)}
                </tr>
              </thead>
              <tbody>
                {flows.map((row) => (
                  <tr key={row.flow}>
                    <td><strong>{LABELS[row.flow] || row.flow}</strong></td>
                    <td>{row.homepage_visitors}</td>
                    <td>{row.contacts_entered}</td>
                    <td>{row.checkout_started}</td>
                    <td>{row.stripe_sessions}</td>
                    <td>{row.purchases}</td>
                    <td>{row.dashboard_entered}</td>
                    <td>{row.platform_completed}</td>
                    <td>{duration(row.average_use_seconds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 style={{ marginTop: 32 }}>Video Watch Rates</h3>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Video</th><th>Flow</th><th>Started</th><th>Completed</th><th>Average Watch Rate</th></tr></thead>
              <tbody>
                {VIDEO_KEYS.map(([key, name, flow]) => {
                  const row = (data.videos || []).find((item) => item.video_key === key) || {};
                  return (
                    <tr key={key}>
                      <td>{name}</td>
                      <td>{LABELS[flow] || flow}</td>
                      <td>{row.viewers || 0}</td>
                      <td>{row.completed || 0}</td>
                      <td>{Number(row.average_watch_rate || 0).toFixed(1)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
