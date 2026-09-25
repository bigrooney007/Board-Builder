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

const ENGAGEMENT_LABELS = { recruitment: "Board Recruitment", reactivation: "Board Reactivation", activation: "Board Fundraising Activation", recruitment_campaign_launch: "Recruitment Campaign Launch", recruitment_supported:"Board Recruitment With Rooney", board_recommitment_supported:"Board Recommitment With Rooney", fundraising_game_supported:"Board Fundraising Game With Rooney", strategic_planning_supported:"Strategic Planning With Rooney" };
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

  const testFundraisingActivation = async () => {
    setMessage("");
    try {
      const r = await client.post("/admin/board-fix/activation-preview-access");
      window.location.href = r.data.intake_url;
    } catch (e) { setMessage(err(e)); }
  };

  const [intakeView, setIntakeView] = useState(null);
  const viewIntake = async (row) => {
    setMessage("");
    try {
      const r = await client.get(`/admin/dwm-clients/${row.session_id}/intake`);
      setIntakeView({ row, offer: r.data.offer, intake: r.data.intake });
    } catch (e) { setMessage(err(e)); }
  };

  const [leadDays, setLeadDays] = useState("");
  const [leadDaysMessage, setLeadDaysMessage] = useState("");
  useEffect(() => {
    client.get("/admin/activation-delivery-settings")
      .then((r) => setLeadDays(r.data.meeting_readiness_lead_days === null ? "" : String(r.data.meeting_readiness_lead_days)))
      .catch(() => {});
  }, []);
  const saveLeadDays = async () => {
    setLeadDaysMessage("");
    try {
      const value = leadDays === "" ? null : Number(leadDays);
      await client.put("/admin/activation-delivery-settings", { meeting_readiness_lead_days: value });
      setLeadDaysMessage(value === null ? "Saved — the meeting-readiness check is OFF until you set a number of days." : `Saved — readiness check runs ${value} day${value === 1 ? "" : "s"} before each client's Board meeting.`);
    } catch (e) { setLeadDaysMessage(err(e)); }
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
        <button className="button button-small" onClick={testFundraisingActivation} data-testid="test-journey-fundraising-activation">Test Fundraising Activation</button>
      </div>
      <p className="admin-message">The Complete Board Transformation test automatically provisions your member identity from this admin login (same email and password — no separate account to create), grants the normal Complete customer entitlement, logs you in as a member, and opens the real customer intake at /board-fix-intake. No Stripe payment is created and it is excluded from revenue and customer reporting. Your previous test progress is never erased.</p>
      <p className="admin-message" data-testid="test-activation-explainer">The Fundraising Activation test grants your member identity ONLY the Fundraising Activation entitlement (temporarily replacing other test entitlements so you see exactly what a $497 customer sees), logs you in as a member, and opens the real customer intake at /board-activation-intake. No Stripe payment is created. Run the Complete Board Transformation test again any time to restore that access.</p>
      <h2 className="reference-heading" style={{ marginTop: "28px" }} data-testid="activation-delivery-settings-heading">Email-Led Activation Settings</h2>
      <p className="admin-message">How many days BEFORE a Fundraising Activation client's Board meeting should the readiness check run? When it runs and responses are still outstanding, the client is emailed and asked whether to proceed with the responses received so far. Leave the field empty to keep this check off (the separate 3-day outstanding-response reminder always runs).</p>
      <div className="admin-filters" style={{ alignItems: "center" }}>
        <input type="number" min="0" max="60" value={leadDays} onChange={(e) => setLeadDays(e.target.value)} placeholder="days" style={{ width: 90 }} data-testid="activation-lead-days-input" />
        <button className="button button-small" onClick={saveLeadDays} data-testid="activation-lead-days-save">Save</button>
        {leadDaysMessage && <span className="admin-message" data-testid="activation-lead-days-message">{leadDaysMessage}</span>}
      </div>
      <h2 className="reference-heading" style={{ marginTop: "28px" }} data-testid="dfy-clients-heading">Supported-Service Clients</h2>
      <p className="admin-message">Every verified client who chose to work with Rooney. Open their real customer workspace and carry the process forward with them.</p>
      {message && <p className="submit-error" data-testid="dwm-error">{message}</p>}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr>{["Founder", "Organization", "Engagement", "Purchase Date", "Intake", "First Meeting", "Status", "Current Step", ""].map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
          <tbody>
            {clients.length === 0 && <tr><td colSpan="9" data-testid="dwm-empty">No verified supported-service clients yet.</td></tr>}
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
                <td style={{ whiteSpace: "nowrap" }}>
                  <button className="button button-small" onClick={() => openWorkspace(row)} data-testid={`open-workspace-${row.session_id.slice(-8)}`}>Take Me To This Client's Dashboard</button>{" "}
                  {row.intake_status === "Completed" && (
                    <button className="button button-small button-outline" onClick={() => viewIntake(row)} data-testid={`view-intake-${row.session_id.slice(-8)}`}>View Client Intake</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {intakeView && (
        <section className="admin-table-wrap" style={{ marginTop: 18 }} data-testid="dwm-intake-view">
          <h3 data-testid="dwm-intake-view-heading">Client Intake — {intakeView.row.founder_name || intakeView.row.founder_email} ({intakeView.offer})</h3>
          <button className="button button-small button-outline" onClick={() => setIntakeView(null)} data-testid="dwm-intake-close">Close</button>
          <table className="admin-table" style={{ marginTop: 10 }}>
            <tbody>
              {Object.entries({ ...(intakeView.intake.data || {}), ...intakeView.intake })
                .filter(([key, value]) => !["data", "session_id", "intake_id", "user_id"].includes(key) && value !== "" && value !== null && (typeof value !== "object" || Array.isArray(value)))
                .map(([key, value]) => (
                  <tr key={key}>
                    <td style={{ fontWeight: 700, textTransform: "capitalize", verticalAlign: "top", width: 260 }}>{key.replaceAll("_", " ")}</td>
                    <td style={{ whiteSpace: "pre-wrap" }}>{Array.isArray(value) ? value.join(", ") : String(value)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </section>
      )}
    </section>
  );
};
