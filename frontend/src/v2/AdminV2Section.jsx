import { useState } from "react";
import { Link } from "react-router-dom";
import { v2Api, errorMessage } from "./api";
import { ActionNotice, useV2Load } from "./ResourcePages";
import "./actions.css";
import { PRODUCTS } from "./content";

export default function AdminV2Section() {
  const { data, error, setError, loading, refresh } = useV2Load("/admin/overview");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const retry = async (email) => {
    setBusy(email.event_id); setError("");
    try { await v2Api.post(`/admin/emails/${email.event_id}/retry`); await refresh(); setMessage("The failed transactional email has been queued for a safe retry."); }
    catch (problem) { setError(errorMessage(problem)); }
    finally { setBusy(""); }
  };
  return <section className="v2-admin-section" data-testid="v2-admin-overview"><h2>Nonprofit Board Builder V2</h2><p>Isolated simplified journeys, purchases, generated materials and email status.</p><ActionNotice error={error} message={message} /><button className="v2-btn v2-btn-secondary" onClick={refresh}>Refresh V2 activity</button>{loading && <p role="status">Loading V2 activity...</p>}
    <section className="v2-paid-test-links"><h3>Test what customers see after payment</h3><p>Open the actual paid pages with sample data. No charge, live email or public campaign is created. Each test is separate from customer records.</p><div className="v2-actions">{Object.entries(PRODUCTS).map(([slug, product]) => <Link className="v2-btn v2-btn-secondary" key={slug} to={`/v2/admin-test/${slug}`}>Test {product.name}</Link>)}</div></section>
    {data && <>
      <div className="v2-table-wrap"><table><thead><tr><th>Customer and organization</th><th>Product and purchase</th><th>Activity</th><th>Resources</th></tr></thead><tbody>{(data.journeys || []).map((journey) => <tr key={journey.journey_id}><td><strong>{journey.organization}</strong><br />{journey.name}<br />{journey.email}</td><td>{journey.product}<br />V2 · {journey.payment_status || journey.state}<br />{journey.amount ? `$${Number(journey.amount) / 100}` : ""}</td><td>{journey.submission_count || journey.response_count || 0} responses<br />{journey.created_at ? new Date(journey.created_at).toLocaleString() : ""}</td><td><Link to={`/v2/resources/${journey.journey_id}`}>Review deliverables</Link></td></tr>)}</tbody></table></div>
      {!data.journeys?.length && <p>No V2 journeys have been created.</p>}
      <h3>Technical issues</h3>{(data.issues || []).map((issue, index) => <p className="v2-error" key={issue.id || index}>{typeof issue === "string" ? issue : `${issue.organization || issue.journey_id || "V2"}: ${issue.message || issue.error || issue.detail || issue.type}`}</p>)}{!data.issues?.length && <p>No outstanding issues were reported.</p>}
      <h3>Transactional email delivery</h3><ul className="v2-resource-list">{(data.emails || []).map((email) => <li key={email.event_id}><div><strong>{email.subject}</strong><small>{email.to} · {email.status}</small>{email.error && <small className="v2-error-inline">{email.error}</small>}</div>{email.status === "failed" && <button className="v2-btn v2-btn-secondary" disabled={Boolean(busy)} onClick={() => retry(email)}>{busy === email.event_id ? "Retrying..." : "Retry failed email"}</button>}</li>)}</ul>
      <p>Professional assistance uses the verified Calendly booking page. Booking details are managed through that existing service.</p>
    </>}
  </section>;
}
