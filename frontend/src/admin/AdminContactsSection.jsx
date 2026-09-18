import { useEffect, useState } from "react";
import axios from "axios";
import AdminLifecycleTemplates from "./AdminLifecycleTemplates";

const api = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });

export const AdminContactsSection = () => {
  const [data, setData] = useState(null);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = () => api.get("/admin/contacts").then((r) => setData(r.data)).catch(() => setError("Could not load contacts."));
  useEffect(load, []); // eslint-disable-line react-hooks/exhaustive-deps

  const open = async (contact) => {
    if (!contact.user_id) { setDetail({ contact, limited: true }); return; }
    setBusy(contact.user_id);
    try { setDetail((await api.get(`/admin/contacts/detail/${contact.user_id}`)).data); }
    catch { setError("Could not load contact detail."); }
    setBusy("");
  };

  const access = async (userId, entitlement, action) => {
    setBusy("access");
    try { await api.post("/admin/contacts/access", { user_id: userId, entitlement, action }); await open({ user_id: userId }); load(); }
    catch { setError("Access change failed."); }
    setBusy("");
  };

  if (error && !data) return <p style={{ color: "#b91c1c" }}>{error}</p>;
  if (!data) return <p>Loading contacts…</p>;

  if (detail) {
    const contact = detail.contact || detail.limited && detail.contact || detail.contact;
    return (
      <div data-testid="admin-contact-detail">
        <p style={{ fontWeight: 800, color: "#b45309" }}>ADMIN SUPPORT VIEW — read-only workspace inspection</p>
        <button onClick={() => setDetail(null)} data-testid="admin-contact-back">← Back to Contacts</button>
        <h3 style={{ marginTop: 12 }}>{contact?.first_name} {contact?.last_name} — {contact?.email}</h3>
        {detail.limited ? (
          <p>This contact is an invited participant without a platform account. See their responses inside the inviting organization's detail view.</p>
        ) : (
          <>
            <div style={{ margin: "10px 0" }}>
              {["board_fundraising_game", "fbb_recruitment", "facilitated_board_fundraising_game"].map((entitlement) => {
                const has = (contact.entitlements || []).includes(entitlement);
                return (
                  <button key={entitlement} disabled={busy === "access"} style={{ marginRight: 8 }}
                    onClick={() => access(contact.user_id, entitlement, has ? "revoke" : "grant")}
                    data-testid={`admin-access-${entitlement}`}>
                    {has ? `Revoke ${entitlement}` : `Grant ${entitlement}`}
                  </button>
                );
              })}
            </div>
            <h4>Activity Timeline</h4>
            {(detail.timeline || []).slice(0, 40).map((event, index) => (
              <p key={index} style={{ fontSize: 13 }}>{event.at?.slice(0, 16).replace("T", " ")} — {event.event}</p>
            ))}
            <h4 style={{ marginTop: 14 }}>Email History</h4>
            {(detail.email_history || []).slice(0, 25).map((email) => (
              <p key={email.log_id} style={{ fontSize: 13 }}>{email.sent_at?.slice(0, 16).replace("T", " ")} — [{email.status}] {email.template_id} {email.subject}</p>
            ))}
            {(detail.email_history || []).length === 0 && <p style={{ fontSize: 13 }}>No lifecycle emails yet.</p>}
            <h4 style={{ marginTop: 14 }}>Payments</h4>
            {(detail.payments || []).map((payment) => (
              <p key={payment.session_id} style={{ fontSize: 13 }}>{payment.updated_at?.slice(0, 10)} — {payment.offer} — {payment.payment_status} (${(payment.amount || 0) / 100})</p>
            ))}
            <h4 style={{ marginTop: 14 }}>Game Responses (First / Second / Complete Idea / Strengthened / Accepted)</h4>
            {(detail.game_responses || []).map((response, index) => (
              <details key={index} style={{ marginTop: 6 }}>
                <summary>{response.participant} — Area {response.section_id}</summary>
                <p style={{ fontSize: 13 }}><b>First:</b> {response.first_response}</p>
                <p style={{ fontSize: 13 }}><b>Second:</b> {response.second_response}</p>
                <p style={{ fontSize: 13 }}><b>Complete Idea:</b> {response.complete_user_idea}</p>
                <p style={{ fontSize: 13 }}><b>Strengthened:</b> {response.strengthened_version}</p>
                <p style={{ fontSize: 13 }}><b>Accepted:</b> {response.accepted_version || "—"}</p>
              </details>
            ))}
            <h4 style={{ marginTop: 14 }}>Strategies</h4>
            {(detail.strategies || []).map((strategy) => (
              <p key={strategy.strategy_id} style={{ fontSize: 13 }}>{strategy.mode} v{strategy.version} — {strategy.status} — {strategy.generated_at?.slice(0, 10)}</p>
            ))}
            <h4 style={{ marginTop: 14 }}>Relationship Mapping ({(detail.relationship_mapping || []).length})</h4>
            <h4 style={{ marginTop: 14 }}>Access History</h4>
            {(detail.access_history || []).map((row) => (
              <p key={row.history_id} style={{ fontSize: 13 }}>{row.at?.slice(0, 16).replace("T", " ")} — {row.action} {row.entitlement} ({row.access_status})</p>
            ))}
          </>
        )}
      </div>
    );
  }

  return (
    <div data-testid="admin-contacts-section">
      <h3>Contacts / Users ({data.total})</h3>
      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
      <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left" }}>
            <th>Name</th><th>Email</th><th>Phone</th><th>Organization</th><th>Source</th>
            <th>Products</th><th>Type</th><th>Paid</th><th>Access</th><th>Lifecycle</th><th>Stage</th><th>Status</th><th>Next Email</th><th>Created</th><th>Last Email</th><th></th>
          </tr>
        </thead>
        <tbody>
          {data.contacts.map((contact) => (
            <tr key={contact.contact_id} style={{ borderTop: "1px solid #e5e7eb" }} data-testid={`admin-contact-${contact.contact_id}`}>
              <td>{contact.name}</td><td>{contact.email}</td><td>{contact.phone}</td>
              <td>{contact.organization}</td><td>{contact.source}</td>
              <td>{(contact.products || []).join("; ")}</td><td>{contact.contact_type}</td>
              <td>{contact.paid ? "Paid" : "Unpaid"}</td><td>{contact.access_status}</td>
              <td>{contact.lifecycle || ""}</td>
              <td>{contact.current_stage}</td>
              <td>{contact.lifecycle_status || ""}</td>
              <td>{(contact.next_scheduled_email || "").slice(0, 10)}</td>
              <td>{(contact.created_at || "").slice(0, 10)}</td>
              <td>{(contact.last_email_sent || "").slice(0, 10)}</td>
              <td><button disabled={busy === contact.user_id} onClick={() => open(contact)} data-testid={`admin-open-contact-${contact.contact_id}`}>Open</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <AdminLifecycleTemplates />
    </div>
  );
};

export default AdminContactsSection;
