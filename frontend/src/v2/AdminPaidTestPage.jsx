import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import V2Shell, { ErrorNotice, Loading } from "./V2Shell";
import { PRODUCTS } from "./content";
import { errorMessage, v2Api } from "./api";

export default function AdminPaidTestPage() {
  const { product } = useParams();
  const navigate = useNavigate();
  const [journey, setJourney] = useState(null);
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    if (!PRODUCTS[product]) { setLoading(false); return undefined; }
    Promise.all([v2Api.get(`/admin/test-journeys/${product}`), v2Api.get(`/admin/test-journeys/${product}/inbox`)])
      .then(([saved, inbox]) => { if (active) { setJourney(saved.data.journey); setEmails(inbox.data.emails || []); } })
      .catch((problem) => { if (active) setError(errorMessage(problem, "Sign in through your existing administrator dashboard to open this test.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [product]);
  const start = async () => {
    if (busy) return;
    setBusy(true); setError("");
    try { const { data } = await v2Api.post(`/admin/test-journeys/${product}`); navigate(data.next); }
    catch (problem) { setError(errorMessage(problem, "The test could not be started. Please try again.")); }
    finally { setBusy(false); }
  };
  return <V2Shell title={`Admin paid test: ${PRODUCTS[product]?.name || "Board Builder"}`}>
    <section className="v2-intro"><p className="v2-eyebrow">ADMINISTRATOR CUSTOMER TEST</p><h1>{PRODUCTS[product]?.name || "Choose a product"}: after payment</h1><p>Your sample organization, brand colors, meeting details and questionnaire answers are already filled in. Confirm the setup and use the prepared contacts and responses to test each action without typing. Recruitment applicants and sample CVs appear after you launch the test campaign. Group decisions and final approvals remain yours to make.</p><p>No payment is taken. Generated examples are labeled samples, and emails are captured here instead of being sent. Test campaigns stay out of the public marketplace and live applicant network.</p><Link to="/admin?tab=v2">Return to my admin dashboard</Link></section>
    {loading ? <Loading>Opening your admin test…</Loading> : <><ErrorNotice error={error} />{!error && PRODUCTS[product] && <section className="v2-card"><h2>Test the paid experience</h2><div className="v2-actions">{journey && <Link className="v2-button" to={journey.setup_complete ? `/v2/resources/${journey.journey_id}` : `/v2/setup/${journey.journey_id}`}>Continue my saved test</Link>}<button className="v2-button v2-button-secondary" disabled={busy} onClick={start}>{busy ? "Starting your test…" : "Start a fresh paid test"}</button></div>{journey && <div className="v2-actions"><Link to={`/v2/library/${journey.journey_id}`}>View approved test resources</Link><Link to={`/v2/responses/${journey.journey_id}`}>View test responses</Link>{["board-fundraising-game", "strategic-planning"].includes(product) && <Link to={`/v2/group/${journey.journey_id}`}>Open test group session</Link>}</div>}</section>}
    {!error && <section className="v2-card v2-test-inbox"><h2>Captured test emails</h2><p>These messages were not sent. Reopen this page after completing an action to review its notifications.</p>{!emails.length ? <p>No test messages have been captured yet.</p> : emails.map((email) => <details key={email.event_id}><summary>{email.subject}</summary><p>To: {email.to}. Captured for testing, not delivered.</p><p className="v2-preserve-text">{email.text}</p>{email.action_path && <Link className="v2-button v2-button-secondary" to={email.action_path}>Open the email action</Link>}</details>)}</section>}</>}
  </V2Shell>;
}
