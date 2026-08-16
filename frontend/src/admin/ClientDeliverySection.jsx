import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { enterOperatorMode } from "@/operatorMode";
import { adminClientDeliveryText, clientDeliverySectionText } from "../content/appContent";

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
      <p className="admin-message">{adminClientDeliveryText.m_walkThroughEachRealProduct}</p>
      <div className="admin-filters">
        {TEST_JOURNEYS.map((j) => (
          <a key={j.key} className="button button-small" href={j.route} data-testid={`test-journey-${j.key}`}>Test {j.label} Journey</a>
        ))}
      </div>
      <h2 className="reference-heading" style={{ marginTop: "28px" }}>{clientDeliverySectionText.doWithYouClients}</h2>
      <p className="admin-message">{adminClientDeliveryText.m_everyVerifiedDowithyouCustomerAcross}</p>
      {message && <p className="submit-error" data-testid="dwm-error">{message}</p>}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr>{["Founder", "Organization", "Offer", "Purchase Date", "Intake", "Workspace", ""].map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {clients.length === 0 && <tr><td colSpan="7" data-testid="dwm-empty">{clientDeliverySectionText.noVerifiedDoWithYou}</td></tr>}
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
