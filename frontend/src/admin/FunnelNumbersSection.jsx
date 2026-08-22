import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { RefreshCw } from "lucide-react";

const client = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });

const money = (cents) => `$${(cents / 100).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

export const FunnelNumbersSection = () => {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setError("");
    try { const r = await client.get("/admin/funnel-stats"); setStats(r.data); }
    catch (e) { setError(typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Could not load funnel numbers."); }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <section className="admin-funnel-numbers" data-testid="admin-funnel-numbers">
      <div className="admin-funnel-numbers-head">
        <h2>Funnel Numbers</h2>
        <button className="button button-small button-back" onClick={load} data-testid="funnel-stats-refresh-button"><RefreshCw size={15} /> Refresh</button>
      </div>
      {error && <p className="submit-error" data-testid="funnel-stats-error">{error}</p>}
      {!stats && !error && <p data-testid="funnel-stats-loading">Loading…</p>}
      {stats && (
        <div className="admin-table-wrap">
          <table className="admin-table" data-testid="funnel-stats-table">
            <thead>
              <tr>
                <th>Funnel</th><th>Form Submits</th><th>Video Views</th>
                <th>DIY Purchases</th><th>DWY Purchases</th><th>Total Purchases</th><th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {stats.funnels.map((funnel) => (
                <tr key={funnel.key} data-testid={`funnel-stats-row-${funnel.key}`}>
                  <td>{funnel.label}</td>
                  <td data-testid={`funnel-submits-${funnel.key}`}>{funnel.form_submits}</td>
                  <td data-testid={`funnel-views-${funnel.key}`}>{funnel.video_views}</td>
                  <td>{funnel.purchases_diy}</td>
                  <td>{funnel.purchases_dwy}</td>
                  <td data-testid={`funnel-purchases-${funnel.key}`}>{funnel.purchases}</td>
                  <td data-testid={`funnel-revenue-${funnel.key}`}>{money(funnel.revenue_cents)}</td>
                </tr>
              ))}
              <tr className="admin-funnel-totals" data-testid="funnel-stats-totals">
                <td><strong>All Funnels</strong></td>
                <td><strong>{stats.totals.form_submits}</strong></td>
                <td><strong>{stats.totals.video_views}</strong></td>
                <td colSpan="2" />
                <td><strong>{stats.totals.purchases}</strong></td>
                <td><strong>{money(stats.totals.revenue_cents)}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
      <p className="admin-funnel-note">Video views count each time a visitor opens an offer sales video page (one per browser session). Purchases and revenue include DIY, DWY and legacy checkout payments marked paid in Stripe.</p>
    </section>
  );
};
