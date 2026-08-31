import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { RefreshCw } from "lucide-react";

const client = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });

const STAGES = [
  ["form_submitted", "Initial Form"], ["checkout_started", "Checkout Started"], ["paid", "Paid"], ["intake_completed", "Intake"],
  ["onboarding", "Onboarding"], ["recruitment", "Recruitment"], ["reactivation", "Reactivation"], ["activation", "Fundraising Activation"], ["completed", "Completed"],
];

const KV = ({ data }) => (
  <dl className="board-fix-kv">
    {Object.entries(data || {}).map(([key, value]) => (
      <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{Array.isArray(value) ? value.join(", ") : String(value)}</dd></div>
    ))}
  </dl>
);

const PathwayDetail = ({ pathway }) => (
  <div className="board-fix-journey-pathway" data-testid={`board-fix-journey-pathway-${pathway.key}`}>
    <p><strong>{pathway.label}</strong> — {pathway.done ? "Completed" : pathway.started ? `${pathway.percent}% complete` : "Not entered"}</p>
    <p>Additional intake: {pathway.intake_completed ? `Completed ${pathway.intake_submitted_at?.slice(0, 16) || ""}` : "Required — not completed"}</p>
    {!pathway.done && pathway.current_step && (
      <p>Current step: {pathway.current_step}{pathway.next_step ? ` — Next step: ${pathway.next_step}` : ""}</p>
    )}
    {pathway.completed_steps.length > 0 && <p>Completed steps: {pathway.completed_steps.join("; ")}</p>}
    {pathway.status_line && <p>Status: {pathway.status_line}</p>}
    {(pathway.resources || []).length > 0 && (
      <p>Generated resources: {pathway.resources.map((r) => `${r.title}${r.status ? ` (${r.status})` : ""}`).join("; ")}</p>
    )}
  </div>
);

const BoardFixStepsBlock = ({ steps }) => (
  <div data-testid="board-fix-steps-block">
    <p>Orientation: {steps.orientation_accessed_at ? `Accessed ${steps.orientation_accessed_at.slice(0, 16)}` : "Not accessed yet"}
      {steps.orientation_selections?.step_off ? ` — Step-off members: ${steps.orientation_selections.step_off}, Advisory candidates: ${steps.orientation_selections.advisory}` : ""}</p>
    <p>Board Member Profile/Recommitment Form: {steps.recommitment_form_status === "NONE" ? "Not generated" : steps.recommitment_form_status}</p>
    <p>Board member responses: {steps.responses_received} of {steps.board_members_on_roster} on the roster</p>
    <p>Individual interpretations generated: {steps.interpretations_generated}</p>
    <p>Board summary: {steps.board_summary_status === "NONE" ? "Not generated" : steps.board_summary_status}</p>
    <p>Transition / difficult-conversation scripts: {steps.conversation_scripts}</p>
    <p>Board members recruited: {steps.board_members_recruited}</p>
  </div>
);

export const BoardFixSection = () => {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState("");
  const [openEmail, setOpenEmail] = useState("");
  const load = useCallback(async () => {
    setError("");
    try { const r = await client.get("/admin/board-fix/customers"); setPayload(r.data); }
    catch { setError("Could not load Board Fix customers."); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (error) return <p className="submit-error" data-testid="board-fix-admin-error">{error}</p>;
  if (!payload) return <p data-testid="board-fix-admin-loading">Loading…</p>;

  return (
    <section data-testid="admin-board-fix-section">
      <div className="admin-funnel-numbers-head">
        <h2>Complete Board Fix Customers</h2>
        <button className="button button-small button-back" onClick={load} data-testid="board-fix-refresh-button"><RefreshCw size={15} /> Refresh</button>
      </div>
      <div className="board-fix-overview" data-testid="board-fix-overview">
        {STAGES.map(([key, label]) => (
          <div className="board-fix-stage" key={key} data-testid={`board-fix-stage-${key}`}><strong>{payload.overview[key] ?? 0}</strong><span>{label}</span></div>
        ))}
      </div>
      {payload.funnel_report && (
        <>
          <h3 style={{ marginTop: 24 }}>Public Funnel Report</h3>
          <div className="board-fix-overview" data-testid="board-fix-funnel-report">
            {[["homepage_visits", "Homepage Visitors"], ["form_submits", "Board Transformation Form"], ["video_views", "Video Page Reached"],
              ["paid", "Paid"], ["journey_started", "Journey Started"],
              ["purchases_homepage_funnel", "Paid via Homepage Funnel"], ["purchases_direct_or_unattributed", "Paid Direct / Unattributed"]].map(([key, label]) => (
              <div className="board-fix-stage" key={key} data-testid={`board-fix-funnel-${key}`}><strong>{payload.funnel_report[key] ?? 0}</strong><span>{label}</span></div>
            ))}
          </div>
        </>
      )}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", margin: "18px 0" }} data-testid="board-fix-experience-links">
        <a className="button button-small" href="/board-fix-intake" target="_blank" rel="noreferrer" data-testid="board-fix-experience-intake">Experience: Intake Form</a>
        <a className="button button-small" href="/board-fix-orientation" target="_blank" rel="noreferrer" data-testid="board-fix-experience-orientation">Experience: Welcome to Board Fix</a>
        <a className="button button-small" href="/board-fix-roadmap" target="_blank" rel="noreferrer" data-testid="board-fix-experience-dashboard">Experience: Board Fix Dashboard</a>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table" data-testid="board-fix-customers-table">
          <thead><tr>{["Customer", "Organization", "Status", "Last Activity", ""].map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
          <tbody>
            {payload.customers.length === 0 && <tr><td colSpan="5" data-testid="board-fix-empty">No Board Fix customers yet.</td></tr>}
            {payload.customers.map((customer) => (
              <>
                <tr key={customer.email} data-testid={`board-fix-row-${customer.email}`}>
                  <td>{customer.name}<small>{customer.email}</small></td>
                  <td>{customer.organization}</td>
                  <td>{customer.status}</td>
                  <td>{customer.last_activity?.slice(0, 10)}</td>
                  <td><button className="table-link" onClick={() => setOpenEmail(openEmail === customer.email ? "" : customer.email)} data-testid={`board-fix-open-${customer.email}`}>{openEmail === customer.email ? "Hide Journey" : "View Journey"}</button></td>
                </tr>
                {openEmail === customer.email && (
                  <tr className="topic-detail-row"><td colSpan="5">
                    <div className="board-fix-journey" data-testid={`board-fix-journey-${customer.email}`}>
                      {customer.next_action && <p className="board-fix-next-action" data-testid={`board-fix-next-action-${customer.email}`}><strong>Next expected action:</strong> {customer.next_action}</p>}
                      <h3>Pre-Purchase</h3>
                      <p>Initial form: {customer.form ? `Submitted ${customer.form.submitted_at?.slice(0, 16)}` : "Not submitted"}</p>
                      {customer.form && <KV data={customer.form.answers} />}
                      <p>Sales page / checkout: {customer.payment ? `Checkout initiated ${customer.payment.created_at?.slice(0, 16)} — ${customer.payment.payment_status} — $${(customer.payment.amount / 100).toFixed(0)}` : (customer.paid ? "paid" : "No checkout started")}</p>
                      <h3>Purchase</h3>
                      <p>{customer.purchase ? `${customer.purchase.product} — $${(customer.purchase.amount / 100).toFixed(0)} — purchased ${customer.purchase.purchased_at?.slice(0, 16)}${customer.member_user_id ? ` — account ${customer.member_user_id}` : ""}` : (customer.paid ? "Paid — account not yet created" : "Not purchased")}</p>
                      <h3>Master Intake</h3>
                      <p>Detailed intake: {customer.intake ? `Completed ${customer.intake.submitted_at?.slice(0, 16)}` : "Not completed"}</p>
                      {customer.intake && <KV data={customer.intake.data} />}
                      <h3>Onboarding</h3>
                      <p data-testid={`board-fix-roadmap-access-${customer.email}`}>Roadmap: {customer.roadmap_accessed_at ? `First accessed ${customer.roadmap_accessed_at.slice(0, 16)}` : "Not accessed yet"}</p>
                      {customer.board_fix_steps && <BoardFixStepsBlock steps={customer.board_fix_steps} />}
                      <h3>Pathways</h3>
                      {customer.pathways.length === 0 && <p>No member account linked yet.</p>}
                      {customer.pathways.map((pathway) => <PathwayDetail key={pathway.key} pathway={pathway} />)}
                    </div>
                  </td></tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};
