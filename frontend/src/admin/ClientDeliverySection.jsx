import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { enterOperatorMode } from "@/operatorMode";

const client = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });
const err = (e) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Action failed.");

const TEST_JOURNEYS = [
  { key: "recruitment", label: "Recruitment", route: "/app/recruitment/self-guided/module/1" },
  { key: "reactivation", label: "Reactivation", route: "/app/reactivation/self-guided/module/1" },
  { key: "activation", label: "Activation", route: "/app/activation/self-guided/module/1" },
];

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

  return (
    <section data-testid="admin-client-delivery">
      <h2 className="reference-heading">Test Product Journey</h2>
      <p className="admin-message">Walk through each real product as a customer would, inside your isolated TEST MODE workspace. No payment is required, no emails are sent automatically, and nothing touches real client data.</p>
      <div className="admin-filters">
        {TEST_JOURNEYS.map((j) => (
          <a key={j.key} className="button button-small" href={j.route} data-testid={`test-journey-${j.key}`}>Test {j.label} Journey</a>
        ))}
      </div>
      <h2 className="reference-heading" style={{ marginTop: "28px" }}>Do-With-You Clients</h2>
      <p className="admin-message">Every verified Do-With-You customer across Recruitment, Reactivation and Activation. Open a client workspace to operate their actual product workflow on their behalf — everything you generate belongs to that client's project.</p>
      {message && <p className="submit-error" data-testid="dwm-error">{message}</p>}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr>{["Founder", "Organization", "Offer", "Purchase Date", "Intake", "Workspace", ""].map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {clients.length === 0 && <tr><td colSpan="7" data-testid="dwm-empty">No verified Do-With-You clients yet.</td></tr>}
            {clients.map((row) => (
              <tr key={row.session_id} data-testid={`dwm-row-${row.session_id.slice(-8)}`}>
                <td>{row.founder_name || row.founder_email}</td>
                <td>{row.organization_name || "—"}</td>
                <td>{row.offer}</td>
                <td>{row.purchase_date?.slice(0, 10)}</td>
                <td>{row.intake_status}</td>
                <td>{row.workspace_status}</td>
                <td><button className="button button-small" onClick={() => openWorkspace(row)} data-testid={`open-workspace-${row.session_id.slice(-8)}`}>Open Client Workspace</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};
