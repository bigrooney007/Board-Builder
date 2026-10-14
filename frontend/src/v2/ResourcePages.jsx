import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import V2Shell, { AssistanceLink } from "./V2Shell";
import { v2Api, errorMessage, resourceUrl } from "./api";
import "./actions.css";

const TITLES = {
  recruit: "Your Board Recruitment Pack",
  "board-fundraising-game": "Your Board Fundraising Resources",
  "strategic-planning": "Your Strategic Planning Resources",
  "board-recommitment": "Your Board Recommitment Resources",
};

export function useV2Load(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const currentPath = useRef(path);
  const mounted = useRef(true);
  const sequence = useRef(0);
  currentPath.current = path;
  const refresh = useCallback(async () => {
    const requestSequence = ++sequence.current;
    setError("");
    const current = () => mounted.current && currentPath.current === path && requestSequence === sequence.current;
    try { const response = await v2Api.get(path); if (!current()) return null; setData(response.data); return response.data; }
    catch (problem) { if (current()) setError(errorMessage(problem)); return null; }
    finally { if (current()) setLoading(false); }
  }, [path]);
  useEffect(() => { mounted.current = true; setData(null); setLoading(true); refresh(); return () => { mounted.current = false; }; }, [refresh]);
  return { data, error, setError, loading, refresh };
}

export function ActionNotice({ error, message }) {
  return <>{error && <p className="v2-error" role="alert">{error}</p>}{message && <p className="v2-notice" role="status">{message}</p>}</>;
}

export function CopyButton({ text, children = "Copy", className = "" }) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  return <><button type="button" className={`v2-btn v2-btn-secondary ${className}`} onClick={async () => {
    try { await navigator.clipboard.writeText(text || ""); setCopied(true); setError(""); }
    catch { setError("Please select the text and copy it using your device's copy command."); }
  }}>{copied ? "Copied" : children}</button>{error && <small role="status">{error}</small>}</>;
}

export function DownloadLink({ path, filename, children }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return <><a className="v2-btn v2-btn-secondary" href={resourceUrl(path)} aria-disabled={busy} onClick={async (event) => {
    event.preventDefault(); if (busy) return; setBusy(true); setError("");
    try {
      const response = await v2Api.get(path, { responseType: "blob" });
      const objectUrl = URL.createObjectURL(response.data);
      const attachment = document.createElement("a");
      const suppliedName = response.headers?.["content-disposition"]?.match(/filename="?([^";]+)"?/i)?.[1];
      attachment.href = objectUrl; attachment.download = filename || suppliedName || "board-builder-resource";
      document.body.appendChild(attachment); attachment.click(); attachment.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (problem) { setError(errorMessage(problem, "We could not download this resource. Please try again.")); }
    finally { setBusy(false); }
  }}>{busy ? "Preparing download..." : children}</a>{error && <small className="v2-error-inline" role="alert">{error}</small>}</>;
}

const statusText = (resource) => resource.status === "approved" && resource.approved_revision === resource.revision
  ? `Approved version ${resource.revision}`
  : resource.status === "preparing" ? "Being prepared"
    : resource.status === "failed" ? "Preparation needs a retry" : `Version ${resource.revision || 1} needs approval`;

export function DocumentPreview({ resource, branding }) {
  return <article className="v2-document" style={{ "--document-brand": branding?.primary_color || "#334155" }}>
    {branding?.logo_data && <img className="v2-document-logo" src={branding.logo_data} alt={`${branding.organization_name || "Organization"} logo`} />}
    {branding?.organization_name && <p className="v2-document-org">{branding.organization_name}</p>}
    <h2>{resource.title}</h2>
    <div className="v2-document-text">{resource.text}</div>
  </article>;
}

export function ResourcesPage() {
  const { journeyId } = useParams();
  const { data, error, setError, loading, refresh } = useV2Load(`/journeys/${journeyId}/resources`);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  const journey = data?.journey || {};
  const resources = data?.resources || [];
  const preparing = resources.some((resource) => resource.status === "preparing");
  useEffect(() => { if (!preparing) return undefined; const interval = window.setInterval(refresh, 3000); return () => window.clearInterval(interval); }, [preparing, refresh]);
  const groups = [...new Set(resources.map((r) => r.group || "Resources"))];
  const retry = async (resource) => {
    setBusy(resource.resource_id); setMessage(""); setError("");
    try { await v2Api.post(`/journeys/${journeyId}/resources/${resource.resource_id}/retry`); await refresh(); setMessage("Your resource is being prepared again. You can refresh this page to check it."); }
    catch (problem) { setError(errorMessage(problem)); }
    finally { setBusy(""); }
  };
  return <V2Shell title={TITLES[journey.product] || "Your resources"}><div className="v2-action-page" data-testid="v2-resources">
    <header><p className="v2-eyebrow">{journey.organization}</p><h1>{TITLES[journey.product] || "Your Resources"}</h1>
      <p>Everything you need is here. Open a resource to review it, make changes and approve it. We will save the exact version you approve and email it to you.</p></header>
    <ActionNotice error={error} message={message} />
    {loading && <p role="status">Loading your resources...</p>}
    {data && <>
      <section className="v2-card"><h2>Your next actions</h2><div className="v2-actions">
        {journey.product === "recruit" ? <>
          <Link className="v2-btn" to={`/v2/campaign/${journeyId}`}>Review and launch your campaign</Link>
          <Link className="v2-btn v2-btn-secondary" to={`/v2/responses/${journeyId}`}>View applicants</Link>
          <DownloadLink path={`/journeys/${journeyId}/pack?format=docx`}>Download editable recruitment pack</DownloadLink>
        </> : <>
          {journey.leader_form_token && <Link className="v2-btn" to={`/v2/forms/${journey.leader_form_token}`}>Complete your own questionnaire</Link>}
          <Link className="v2-btn" to={`/v2/invite/${journeyId}`}>{journey.product === "board-recommitment" ? "Invite board members" : "Invite participants"}</Link>
          <Link className="v2-btn v2-btn-secondary" to={`/v2/responses/${journeyId}`}>View submitted responses</Link>
          {journey.product !== "board-recommitment" && <Link className="v2-btn v2-btn-secondary" to={`/v2/group/${journeyId}`}>Open your group session</Link>}
        </>}
        <button className="v2-btn v2-btn-secondary" onClick={refresh}>Refresh resources</button>
      </div>
      {journey.form_token && <div className="v2-link-box"><label>{journey.product === "recruit" ? "Application link, activated when you launch your campaign" : "Your organization's form link"}<input readOnly value={`${window.location.origin}/v2/forms/${journey.form_token}`} /></label><CopyButton text={`${window.location.origin}/v2/forms/${journey.form_token}`}>Copy form link</CopyButton></div>}
      {journey.product === "recruit" && <p>Review and approve the public-facing campaign resources before launching. Then share your application link through LinkedIn, Facebook, your website, your networks and direct email outreach.</p>}
      {journey.product !== "recruit" && <p>You can copy the form link into an email you send yourself. Personal invitation links let people securely return to their own answers.</p>}
      </section>
      {groups.map((group) => <section className="v2-card" key={group}><h2>{group}</h2><ul className="v2-resource-list">
        {resources.filter((r) => (r.group || "Resources") === group).map((resource) => <li key={resource.resource_id}>
          <div><Link to={`/v2/resources/${journeyId}/${resource.resource_id}`}>{resource.title}</Link><small>{statusText(resource)}</small>{resource.error && <small className="v2-error-inline">{resource.error}</small>}</div>
          {resource.status === "failed" ? <button disabled={busy === resource.resource_id} className="v2-btn v2-btn-secondary" onClick={() => retry(resource)}>Retry preparation</button> : <Link className="v2-btn v2-btn-secondary" to={`/v2/resources/${journeyId}/${resource.resource_id}`}>View and edit</Link>}
        </li>)}
      </ul></section>)}
      {journey.product === "recruit" && <section className="v2-card"><h2>Promote your board opportunity</h2>
        <p>Publish the approved announcement and application link on your website. Use your LinkedIn and Facebook posts to explain the opportunity, and send the outreach email to people in your personal and professional networks. Ask trusted contacts to share it with suitable candidates.</p>
        <a className="v2-btn v2-btn-secondary" href="https://youtu.be/tESJV4jJVWs" target="_blank" rel="noreferrer">Watch the optional 30-minute campaign launch instructions</a>
      </section>}
      <section className="v2-card"><h2>Would you like help carrying out this process?</h2><p>We can work with you to prepare, facilitate or implement the process. Book a conversation so we can discuss the support you need and provide a separate quotation.</p><AssistanceLink /></section>
    </>}
  </div></V2Shell>;
}

export function ResourceEditorPage() {
  const { journeyId, resourceId } = useParams();
  const { data: resource, error, setError, loading, refresh } = useV2Load(`/journeys/${journeyId}/resources/${resourceId}`);
  const [text, setText] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => { if (resource) setText(resource.text || ""); }, [resource]);
  useEffect(() => { if (resource?.status !== "preparing") return undefined; const interval = window.setInterval(refresh, 3000); return () => window.clearInterval(interval); }, [resource?.status, refresh]);
  const dirty = resource && text !== (resource.text || "");
  const approved = resource?.status === "approved" && resource?.approved_revision === resource?.revision;
  const action = async (kind) => {
    if (busy) return;
    setBusy(true); setError(""); setMessage("");
    try {
      if (kind === "save") {
        await v2Api.put(`/journeys/${journeyId}/resources/${resourceId}`, { text, expected_revision: resource.revision });
        setEditing(false); setMessage("Your changes have been saved. Review the revised version and approve it when you are ready.");
      } else if (kind === "approve") {
        const response = await v2Api.post(`/journeys/${journeyId}/resources/${resourceId}/approve`, { expected_revision: resource.revision });
        if (response.data.delivery_error || response.data.email?.status === "queue_failed") setError("This exact version is approved and saved, but its email could not be queued. Use Retry approved email delivery below.");
        else setMessage("This exact version has been approved and saved. Its email is queued for delivery to you. Repeated approval will not create another email.");
      } else if (kind === "send") {
        await v2Api.post(`/journeys/${journeyId}/resources/${resourceId}/send`, { recipient: "applicant" });
        setMessage("Your approved communication is queued for delivery to this applicant.");
      } else { await v2Api.post(`/journeys/${journeyId}/resources/${resourceId}/retry`); setMessage("Preparation has been requested again."); }
      await refresh();
    } catch (problem) { setError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  const candidateMessage = resource?.submission_id && ["interview_invitation", "interview-invitation", "rejection", "rejection_email"].some((key) => resource.key?.includes(key));
  return <V2Shell title={resource?.title || "Review your resource"}><div className="v2-action-page" data-testid="v2-resource-editor">
    <Link className="v2-back-link" to={`/v2/resources/${journeyId}`}>Your resources</Link>
    <ActionNotice error={error} message={message} />
    {loading && <p role="status">Loading this resource...</p>}
    {resource && <>
      <header><h1>{resource.title}</h1><p>{statusText(resource)}</p><p>Review the wording before approval. Your approved version is saved and emailed to you. Editing it creates a new version that needs fresh approval.</p></header>
      {resource.status === "preparing" && <section className="v2-card"><p>This resource is being prepared using your organization's information.</p><button className="v2-btn v2-btn-secondary" onClick={refresh}>Check preparation</button></section>}
      {resource.status === "failed" && <section className="v2-card"><p>{resource.error || "This resource could not be prepared."}</p><button className="v2-btn" disabled={busy} onClick={() => action("retry")}>Retry preparation</button></section>}
      {["ready", "approved"].includes(resource.status) && <>
        {editing ? <label className="v2-field"><span>Edit your resource</span><textarea data-testid="v2-resource-text" className="v2-editor" rows={22} value={text} onChange={(event) => setText(event.target.value)} /></label> : <DocumentPreview resource={resource} branding={resource.branding} />}
        <div className="v2-actions">
          {editing ? <><button data-testid="v2-resource-save" className="v2-btn" disabled={busy || !dirty} onClick={() => action("save")}>Save changes for review</button><button className="v2-btn v2-btn-secondary" onClick={() => { setText(resource.text || ""); setEditing(false); }}>Cancel editing</button></> : <button data-testid="v2-resource-edit" className="v2-btn v2-btn-secondary" onClick={() => setEditing(true)}>Edit</button>}
          <button data-testid="v2-resource-approve" className="v2-btn" disabled={busy || dirty || editing || (approved && !resource.delivery_error)} onClick={() => action("approve")}>{resource.delivery_error ? "Retry approved email delivery" : approved ? "Approved and saved" : "Approve, save and email to me"}</button>
          <CopyButton text={text}>Copy text</CopyButton>
          {["pdf", "docx", "txt"].map((format) => <DownloadLink key={format} path={`/journeys/${journeyId}/resources/${resourceId}/download?format=${format}`}>Download {format.toUpperCase()}</DownloadLink>)}
        </div>
        {candidateMessage && <section className="v2-card"><h2>Send to this applicant</h2><p>You can copy this email into your own account, or explicitly send the approved version through our email service.</p><button className="v2-btn" disabled={busy || !approved} onClick={() => { if (window.confirm("Send this approved message to the applicant's submitted email address?")) action("send"); }}>Send approved email to applicant</button></section>}
        {resource.structured?.form_link && <div className="v2-link-box"><label>Functional form link<input readOnly value={resource.structured.form_link} /></label><CopyButton text={resource.structured.form_link}>Copy link</CopyButton></div>}
        {resource.structured?.video_url && <a href={resource.structured.video_url} target="_blank" rel="noreferrer" className="v2-btn v2-btn-secondary">Open the optional instructional video</a>}
      </>}
      {resource.delivery_error && <p className="v2-error" role="alert">{resource.delivery_error}</p>}
      {resource.submission_id && <Link className="v2-back-link" to={`/v2/responses/${journeyId}/${resource.submission_id}`}>Return to the submitted response</Link>}
    </>}
  </div></V2Shell>;
}

export function ResponsesPage() {
  const { journeyId } = useParams();
  const { data, error, loading, refresh } = useV2Load(`/journeys/${journeyId}/responses`);
  return <V2Shell><div className="v2-action-page" data-testid="v2-responses"><Link className="v2-back-link" to={`/v2/resources/${journeyId}`}>Your resources</Link>
    <header><h1>Submitted responses</h1><p>Open a response to read what the person shared and take the next action.</p></header><ActionNotice error={error} />
    {loading && <p role="status">Loading responses...</p>}
    {data && <section className="v2-card"><ul className="v2-resource-list">{(data.responses || []).map((response) => <li key={response.submission_id}><div><Link to={`/v2/responses/${journeyId}/${response.submission_id}`}>{response.name}</Link><small>Submitted {new Date(response.submitted_at).toLocaleString()}</small></div><Link className="v2-btn v2-btn-secondary" to={`/v2/responses/${journeyId}/${response.submission_id}`}>View response</Link></li>)}</ul>{!data.responses?.length && <p>No responses have been submitted yet. We will email you when someone responds.</p>}<button className="v2-btn v2-btn-secondary" onClick={refresh}>Refresh responses</button></section>}
  </div></V2Shell>;
}

export function ResponsePage() {
  const { journeyId, submissionId } = useParams();
  const navigate = useNavigate();
  const { data, error, setError, loading } = useV2Load(`/journeys/${journeyId}/responses/${submissionId}`);
  const [busy, setBusy] = useState("");
  const submission = data?.submission || data;
  const product = data?.product || data?.journey?.product || submission?.product;
  const isRecruitment = product === "recruit" || Boolean(submission?.cv);
  const generate = async (kind) => {
    setBusy(kind); setError("");
    try { const response = await v2Api.post(`/journeys/${journeyId}/responses/${submissionId}/generate`, { kind }); const resource = response.data.resource || response.data; navigate(`/v2/resources/${journeyId}/${resource.resource_id}`); }
    catch (problem) { setError(errorMessage(problem)); }
    finally { setBusy(""); }
  };
  const questionName = (key) => {
    const source = submission?.source_questions || [];
    const all = Array.isArray(source) ? source : [...(source.questions || []), ...(source.sections || [])];
    const question = all.flatMap((section) => section.questions || [section]).find((q) => q.id === key);
    return question?.prompt || question?.label || key.replace(/_/g, " ");
  };
  return <V2Shell><div className="v2-action-page" data-testid="v2-response"><Link className="v2-back-link" to={`/v2/responses/${journeyId}`}>Submitted responses</Link><ActionNotice error={error} />
    {loading && <p role="status">Loading the submitted response...</p>}
    {submission && <><header><h1>{submission.name}'s response</h1><p>Submitted {new Date(submission.submitted_at).toLocaleString()}. The information below is the person's original submission.</p></header>
      {(data?.journey?.organization || data?.organization) && <p><strong>Organization:</strong> {data?.journey?.organization || data.organization}</p>}
      {data?.board_opportunity && <details className="v2-card"><summary>The board opportunity</summary><div className="v2-document-text">{data.board_opportunity}</div></details>}
      <section className="v2-card"><dl className="v2-answer-list">{Object.entries(submission.answers || {}).map(([key, value]) => <div key={key}><dt>{questionName(key)}</dt><dd>{Array.isArray(value) ? value.map((item, index) => typeof item === "object" ? <AudienceDetails key={item.audience_id || index} audience={item} /> : <p key={index}>{item}</p>) : typeof value === "object" && value ? <pre>{JSON.stringify(value, null, 2)}</pre> : String(value || "No answer supplied")}</dd></div>)}</dl>
        {submission.cv && <p><DownloadLink path={`/journeys/${journeyId}/responses/${submissionId}/cv`} filename={submission.cv.filename}>Download {submission.cv.filename || "supporting document"}</DownloadLink></p>}
      </section>
      {(isRecruitment || product === "board-recommitment") && <section className="v2-card"><h2>{isRecruitment ? "Prepare your next conversation" : "Prepare a respectful follow-up conversation"}</h2><p>{isRecruitment ? "Generate questions based on this application and your organization's board needs. You decide who to interview and how to proceed." : "The guide explores what this board member actually said, including their concerns and possible contribution. Submitting this form does not automatically confirm recommitment."}</p><div className="v2-actions">
        <button data-testid="v2-generate-guide" className="v2-btn" disabled={Boolean(busy)} onClick={() => generate("guide")}>{busy === "guide" ? "Preparing guide..." : isRecruitment ? "Generate interview guide" : "Generate conversation guide"}</button>
        {isRecruitment && <><button className="v2-btn v2-btn-secondary" disabled={Boolean(busy)} onClick={() => generate("interview-invitation")}>Prepare interview invitation email</button><button className="v2-btn v2-btn-secondary" disabled={Boolean(busy)} onClick={() => generate("rejection")}>Prepare rejection email</button></>}
      </div></section>}
      {!isRecruitment && product !== "board-recommitment" && <Link className="v2-btn" to={`/v2/group/${journeyId}`}>Open the group review session</Link>}
    </>}
  </div></V2Shell>;
}

export function AudienceDetails({ audience }) {
  const labels = [["funder", "Specific funding audience"], ["why", "Why they may support your mission"], ["where", "Where to find them"], ["attract", "How to attract their interest and establish credibility"], ["relationship", "How to build the relationship and raise money"], ["ask", "What to ask them to support"], ["amount", "How much to ask and why"]];
  return <dl className="v2-audience-details">{labels.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{audience?.[key] || "Not supplied"}</dd></div>)}</dl>;
}

export function InvitationsPage() {
  const { journeyId } = useParams();
  const { data, error, setError, loading, refresh } = useV2Load(`/journeys/${journeyId}/invitations`);
  const [form, setForm] = useState({ name: "", email: "", role: "Board member", send: false });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const sendKeys = useRef({});
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { await v2Api.post(`/journeys/${journeyId}/invitations`, form); setMessage(form.send ? "The invitation is saved and queued for email delivery." : "The personal invitation link is ready. Copy it and send it from your own email account."); setForm({ name: "", email: "", role: "Board member", send: false }); await refresh(); }
    catch (problem) { setError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  const send = async (invitation) => {
    setBusy(true); setError("");
    try {
      sendKeys.current[invitation.invitation_id] ||= window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
      await v2Api.post(`/journeys/${journeyId}/invitations/${invitation.invitation_id}/send`, { idempotency_key: sendKeys.current[invitation.invitation_id] });
      delete sendKeys.current[invitation.invitation_id];
      setMessage("The invitation is queued for email delivery. The status below will reflect our email service's result."); await refresh();
    }
    catch (problem) { setError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  const template = typeof data?.invitation_template === "string" ? data.invitation_template : data?.invitation_template?.text || data?.invitation_template?.body || "";
  return <V2Shell><div className="v2-action-page" data-testid="v2-invitations"><Link className="v2-back-link" to={`/v2/resources/${journeyId}`}>Your resources</Link><header><h1>Invite your board members and other participants</h1><p>You can send invitations through our email service or copy the message and links into your own email account.</p></header><ActionNotice error={error} message={message} />
    {loading && <p role="status">Loading your invitations...</p>}
    {data && <>
      <section className="v2-card"><h2>Invitation message</h2><div className="v2-document-text">{template}</div><div className="v2-actions"><CopyButton text={template}>Copy invitation message</CopyButton>{data.form_link && <CopyButton text={data.form_link}>Copy shared form link</CopyButton>}</div>{data.form_link && <label className="v2-field">Shared form link<input readOnly value={data.form_link} /></label>}<p>When you send a message from your own account, our platform cannot confirm delivery or opening. A completed form will still appear in your responses.</p></section>
      <form className="v2-card" onSubmit={submit}><h2>Create a personal invitation</h2><div className="v2-grid"><label className="v2-field">Name<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label className="v2-field">Email address<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label><label className="v2-field">Role<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>{["Board member", "Staff", "Volunteer", "Other"].map((role) => <option key={role}>{role}</option>)}</select></label></div><label className="v2-check"><input type="checkbox" checked={form.send} onChange={(e) => setForm({ ...form, send: e.target.checked })} />Send the invitation through our email service</label><button className="v2-btn" disabled={busy}>{busy ? "Saving invitation..." : form.send ? "Create and send invitation" : "Create link for me to send"}</button></form>
      <section className="v2-card"><h2>Your invitations</h2><ul className="v2-resource-list">{(data.invitations || []).map((invitation) => <li key={invitation.invitation_id}><div><strong>{invitation.name}</strong><small>{invitation.email}</small><small>{invitation.submitted_at || invitation.submitted ? "Response received" : `Email: ${invitation.delivery_status || invitation.email_status || (invitation.send ? "Queued" : "Not sent through our platform")}`}</small></div><div className="v2-actions"><CopyButton text={invitation.form_link || invitation.link || `${window.location.origin}/v2/forms/${invitation.form_token || invitation.token}`}>Copy personal link</CopyButton><button className="v2-btn v2-btn-secondary" disabled={busy || Boolean(invitation.submitted_at || invitation.submitted)} onClick={() => send(invitation)}>{invitation.delivery_status === "failed" ? "Retry invitation" : "Send or resend invitation"}</button></div></li>)}</ul>{!data.invitations?.length && <p>No personal invitations have been created yet.</p>}<button className="v2-btn v2-btn-secondary" onClick={refresh}>Refresh delivery and response status</button></section>
    </>}
  </div></V2Shell>;
}

export function CampaignPage() {
  const { journeyId } = useParams();
  const { data, error, setError, loading, refresh } = useV2Load(`/journeys/${journeyId}/campaign`);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const command = async (action, status) => {
    setBusy(true); setError(""); setMessage("");
    try {
      await v2Api.post(`/journeys/${journeyId}/campaign/${action}`, action === "launch" ? { confirmed: true, expected_revision: data.revision || data.expected_revision } : action === "status" ? { status } : {});
      await refresh(); setConfirmed(false); setMessage("Your campaign's current results are shown below. Only completed activities are reported as successful.");
    } catch (problem) { setError(errorMessage(problem)); await refresh(); }
    finally { setBusy(false); }
  };
  const required = data?.required_resources || [];
  const ready = required.length > 0 && required.every((resource) => resource.approved === true || resource.ready === true || (resource.status === "approved" && (!resource.approved_revision || resource.approved_revision === resource.revision)));
  const activities = Array.isArray(data?.activities) ? data.activities : Object.entries(data?.activities || {}).map(([key, value]) => typeof value === "string" ? { key, title: key.replace(/_/g, " "), status: value } : { key, ...value });
  return <V2Shell><div className="v2-action-page" data-testid="v2-campaign"><Link className="v2-back-link" to={`/v2/resources/${journeyId}`}>Your recruitment pack</Link><header><h1>Launch your board recruitment campaign</h1><p>Review the approved opportunity and form before you confirm. Launching activates your application form, publishes the approved opportunity to our marketplace and requests an announcement to eligible opted-in applicant network contacts.</p></header><ActionNotice error={error} message={message} />
    {loading && <p role="status">Loading your campaign preview...</p>}
    {data && <>
      <section className="v2-card"><h2>Campaign preview</h2><p>Campaign status: <strong>{data.status || "Not launched"}</strong></p><div className="v2-document-text">{typeof data.preview === "string" ? data.preview : data.preview?.text || data.preview?.board_opportunity || data.preview?.summary || "Your approved board opportunity will appear here."}</div><h3>Required approved materials</h3><ul className="v2-resource-list">{required.map((resource) => <li key={resource.resource_id || resource.key}><span>{resource.title || resource.key}<small>{resource.approved || resource.status === "approved" ? "Approved" : "Approval required"}</small></span>{resource.resource_id && <Link to={`/v2/resources/${journeyId}/${resource.resource_id}`}>Review resource</Link>}</li>)}</ul>
        {!ready && <p>Approve the current versions of these resources before launching your campaign.</p>}
        {!['active', 'closed'].includes(data.status) && <><label className="v2-check"><input data-testid="v2-campaign-confirm" type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />I have reviewed these materials and approve activating the application form, marketplace publication and the permitted applicant network announcement.</label><button data-testid="v2-campaign-launch" className="v2-btn" disabled={busy || !ready || !confirmed} onClick={() => command("launch")}>Launch my board recruitment campaign</button></>}
      </section>
      <section className="v2-card"><h2>Launch results</h2>{activities.length ? <ul className="v2-resource-list">{activities.map((activity) => <li key={activity.key || activity.name || activity.title}><div><strong>{activity.title || activity.name || activity.key?.replace(/_/g, " ")}</strong><small>{activity.status || "Not started"}</small>{(activity.detail || activity.error || activity.message) && <p>{activity.detail || activity.error || activity.message}</p>}{activity.mode === "test" && <small>Test delivery only. No live applicant network broadcast.</small>}</div></li>)}</ul> : <p>No launch activities have completed yet.</p>}
        <div className="v2-actions"><button className="v2-btn v2-btn-secondary" onClick={refresh}>Refresh actual results</button><button className="v2-btn v2-btn-secondary" disabled={busy || !activities.some((a) => ["failed", "partial", "pending"].includes(a.status))} onClick={() => command("retry")}>Retry unfinished launch activities</button></div>
      </section>
      {data.application_link && <section className="v2-card"><h2>Your application link</h2><label className="v2-field">Public application link<input readOnly value={data.application_link} /></label><div className="v2-actions"><CopyButton text={data.application_link}>Copy application link</CopyButton><a className="v2-btn v2-btn-secondary" href={data.application_link} target="_blank" rel="noreferrer">Preview application form</a>{data.marketplace_link && <a className="v2-btn v2-btn-secondary" href={data.marketplace_link}>View marketplace listing</a>}</div><p>Share this link with the approved promotional materials on LinkedIn, Facebook, your organization's website, personal and professional networks and direct emails.</p></section>}
      {['active', 'paused', 'closed'].includes(data.status) && <section className="v2-card"><h2>Manage application availability</h2><p>Existing applications and approved resources remain available when you pause or close your campaign.</p><div className="v2-actions">{data.status === "active" && <button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => command("status", "paused")}>Pause campaign</button>}{data.status === "paused" && <button className="v2-btn" disabled={busy} onClick={() => command("status", "active")}>Resume campaign</button>}{data.status !== "closed" && <button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => { if (window.confirm("Close this campaign to new applications? Existing submissions and your materials will remain available.")) command("status", "closed"); }}>Close campaign</button>}</div></section>}
    </>}
  </div></V2Shell>;
}
