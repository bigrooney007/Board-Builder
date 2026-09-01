import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { enterOperatorMode } from "@/operatorMode";
import { adminClientDeliveryText } from "../content/appContent";

const client = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });
const err = (e) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Action failed.");

const TEST_JOURNEYS = [
  { key: "recruitment", label: "Recruitment", route: "/app/recruitment/self-guided/module/1" },
  { key: "reactivation", label: "Reactivation", route: "/app/reactivation/self-guided/module/1" },
  { key: "activation", label: "Activation", route: "/app/activation/self-guided/module/1" },
];

const ENGAGEMENT_LABELS = { recruitment: "Board Recruitment", reactivation: "Board Reactivation", activation: "Board Fundraising Activation", recruitment_campaign_launch: "Recruitment Campaign Launch" };
const ENGAGEMENT_STATUSES = ["Active", "Paused", "Completed"];
const MEETING_STATUSES = ["Not Booked", "Booking Link Sent", "Booked"];

export const ClientDeliverySection = () => {
  const [clients, setClients] = useState([]);
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    try { const r = await client.get("/admin/dwm-clients"); setClients(r.data.clients); } catch (e) { setMessage(err(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openWorkspace = async (row) => {
    setMessage("");
    try {
      const r = await client.post(`/admin/dwm-clients/${row.session_id}/workspace`);
      const ws = r.data.workspace;
      enterOperatorMode(ws.user_id, ws.organization_name || row.organization_name || row.founder_name, ws.product);
      window.location.href = ws.entry_route;
    } catch (e) { setMessage(err(e)); }
  };

  const updateClient = async (row, patch) => {
    setMessage("");
    try {
      await client.patch(`/admin/dwm-clients/${row.session_id}`, patch);
      setClients((rows) => rows.map((r) => (r.session_id === row.session_id ? { ...r, ...patch } : r)));
    } catch (e) { setMessage(err(e)); }
  };

  const testCompleteTransformation = async () => {
    setMessage("");
    try {
      const r = await client.post("/admin/board-fix/preview-access");
      window.location.href = r.data.intake_url;
    } catch (e) { setMessage(err(e)); }
  };

  return (
    <section data-testid="admin-client-delivery">
      <h2 className="reference-heading">Test Product Journey</h2>
      <p className="admin-message">{adminClientDeliveryText.m_walkThroughEachRealProduct}</p>
      <div className="admin-filters">
        {TEST_JOURNEYS.map((j) => (
          <a key={j.key} className="button button-small" href={j.route} data-testid={`test-journey-${j.key}`}>Test {j.label} Journey</a>
        ))}
        <button className="button button-small" onClick={testCompleteTransformation} data-testid="test-journey-complete-transformation">Test Complete Board Transformation</button>
      </div>
      <p className="admin-message">The Complete Board Transformation test opens the real intake and the full 11-step journey on your own member account (same email as this admin login) — no Stripe payment is created and it is excluded from customer reporting. Make sure you are also logged in as a member with this email.</p>
      <h2 className="reference-heading" style={{ marginTop: "28px" }} data-testid="dfy-clients-heading">Done-For-You Clients</h2>
      <p className="admin-message">Every verified individual-engagement client. Open a client workspace to operate their Board Ultimate Fix pathway on their behalf.</p>
      {message && <p className="submit-error" data-testid="dwm-error">{message}</p>}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr>{["Founder", "Organization", "Engagement", "Purchase Date", "Intake", "First Meeting", "Status", "Current Step", ""].map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
          <tbody>
            {clients.length === 0 && <tr><td colSpan="9" data-testid="dwm-empty">No verified Done-For-You clients yet.</td></tr>}
            {clients.map((row) => (
              <tr key={row.session_id} data-testid={`dwm-row-${row.session_id.slice(-8)}`}>
                <td>{row.founder_name || row.founder_email}</td>
                <td>{row.organization_name || "—"}</td>
                <td>{ENGAGEMENT_LABELS[row.engagement_type] || row.offer}</td>
                <td>{row.purchase_date?.slice(0, 10)}</td>
                <td data-testid={`dwm-intake-${row.session_id.slice(-8)}`}>{row.intake_status}</td>
                <td>
                  <select value={row.first_meeting || "Not Booked"} onChange={(e) => updateClient(row, { first_meeting: e.target.value })} data-testid={`dwm-meeting-${row.session_id.slice(-8)}`}>
                    {MEETING_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td>
                  <select value={row.engagement_status || "Active"} onChange={(e) => updateClient(row, { engagement_status: e.target.value })} data-testid={`dwm-status-${row.session_id.slice(-8)}`}>
                    {ENGAGEMENT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td>
                  <input defaultValue={row.current_step || ""} placeholder={row.workspace_status === "Open" ? "In workspace" : "Not started"} onBlur={(e) => { if (e.target.value !== (row.current_step || "")) updateClient(row, { current_step: e.target.value }); }} style={{ width: 130 }} data-testid={`dwm-step-${row.session_id.slice(-8)}`} />
                </td>
                <td><button className="button button-small" onClick={() => openWorkspace(row)} data-testid={`open-workspace-${row.session_id.slice(-8)}`}>Open Client Workspace</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};
