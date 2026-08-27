import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { CheckCircle, Copy, Download, Eye, FileText, LogOut, Pencil, RefreshCw, Search, Sparkles, Users, XCircle } from "lucide-react";
import { ClientDeliverySection } from "@/admin/ClientDeliverySection";
import { FunnelNumbersSection } from "@/admin/FunnelNumbersSection";
import { BoardFixSection } from "@/admin/BoardFixSection";
import { StrategicPlanningSection } from "@/admin/StrategicPlanningSection";
import { adminPageText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });
const statuses = ["New Applicant", "Active", "Under Review", "Contacted", "Presented to Nonprofit", "Interviewing", "Placed on Board", "Paused", "Withdrawn"];
const blankFilters = { search: "", country: "", state_region: "", cause: "", skill: "", board_type: "", fundraising: "", availability: "" };

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault(); setError("");
    try { const response = await client.post("/auth/login", { email, password }); onLogin(response.data); }
    catch (err) { setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Login failed."); }
  };
  return <main className="admin-login-page" data-testid="admin-login-page"><form className="admin-login-card" onSubmit={submit}><div className="admin-login-icon"><Users size={27} /></div><p className="eyebrow">Owner access</p><h1>Board Applicants Administration</h1><p>{adminPageText.privateAccessForTheNonprofit}</p><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required data-testid="admin-email-input" /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required data-testid="admin-password-input" /></label>{error && <p className="submit-error" data-testid="admin-login-error">{error}</p>}<button className="button" type="submit" data-testid="admin-login-button">Log In</button></form></main>;
};

const ReviewResumePanel = () => {
  const [progress, setProgress] = useState(null);
  useEffect(() => { client.get("/review-mode/progress").then((response) => setProgress(response.data.progress)).catch(() => {}); }, []);
  if (!progress) return null;
  const reset = async () => {
    if (!window.confirm("Start the Recruitment review from the beginning? This only resets your saved review position.")) return;
    try { await client.delete("/review-mode/progress"); } catch { /* ignore */ }
    window.location.href = "/recruit";
  };
  return (
    <div className="review-resume-panel" data-testid="review-resume-panel">
      <div>
        <h3>{adminPageText.h_recruitmentExperienceReview}</h3>
        <p>Last reviewed: <strong data-testid="review-last-label">{progress.last_label || progress.last_route}</strong></p>
        <p>Last activity: {progress.updated_at ? new Date(progress.updated_at).toLocaleString() : ""}</p>
      </div>
      <div className="review-resume-actions">
        <a className="button button-small" href={progress.last_route} data-testid="resume-review-button">Resume Recruitment Review</a>
        <button className="button button-back button-small" onClick={reset} data-testid="review-start-over-button">Start From Beginning</button>
      </div>
    </div>
  );
};

const ImportApplicants = ({ refresh }) => {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [consent, setConsent] = useState(false);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const send = async (commit) => {
    setError("");
    if (!file) { setError("Choose a CSV file first."); return; }
    if (!consent) { setError("Please confirm you have permission to contact these people."); return; }
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await client.post(`/admin/applicants-import?confirmed=true&commit=${commit}`, form);
      if (commit) { setResult(response.data.summary); setPreview(null); refresh(); }
      else { setResult(null); setPreview(response.data); }
    } catch (err) { setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Import failed."); }
    setBusy(false);
  };
  const rows = (summary, isPreview) => [
    [isPreview ? "New applicants to import" : "Imported", summary.imported],
    [isPreview ? "Existing applicants to update" : "Updated", summary.updated],
    ["Skipped — duplicate", summary.skipped_duplicate],
    ["Skipped — invalid email", summary.skipped_invalid_email],
    ["Skipped — unsubscribed/withdrawn", summary.skipped_unsubscribed],
    ...(isPreview ? [] : [["Failed", summary.failed], ["Synced to Resend", summary.resend_synced]]),
  ];
  return (
    <>
      <button className="button button-back button-small" onClick={() => setOpen(!open)} data-testid="admin-import-toggle">Import Board Applicants</button>
      {open && (
        <div className="admin-import-panel" data-testid="admin-import-panel">
          <h3>{adminPageText.h_importExistingBoardApplicants}</h3>
          <p>{adminPageText.uploadACsvWithAt}</p>
          <input type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files[0]); setPreview(null); setResult(null); }} data-testid="admin-import-file" />
          <label className="terms-check">
            <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} data-testid="admin-import-consent" />
            <span>{adminPageText.iConfirmThesePeopleGave}</span>
          </label>
          {error && <p className="submit-error" data-testid="admin-import-error">{error}</p>}
          {preview && (
            <div className="admin-import-summary" data-testid="admin-import-preview">
              <h4>{adminPageText.previewNothingHasBeenImported}</h4>
              <ul>{rows(preview.summary, true).map(([label, value]) => <li key={label}>{label}: <strong>{value}</strong></li>)}</ul>
              {preview.sample?.length > 0 && <p>Sample: {preview.sample.join(", ")}</p>}
            </div>
          )}
          {result && (
            <div className="admin-import-summary" data-testid="admin-import-result">
              <h4>Import complete</h4>
              <ul>{rows(result, false).map(([label, value]) => <li key={label}>{label}: <strong>{value}</strong></li>)}</ul>
            </div>
          )}
          <div className="material-actions">
            {!preview && <button className="button button-small" disabled={busy} onClick={() => send(false)} data-testid="admin-import-preview-button">{busy ? "Reading…" : "Preview Import"}</button>}
            {preview && <button className="button button-small" disabled={busy} onClick={() => send(true)} data-testid="admin-import-confirm-button">{busy ? "Importing…" : "Confirm Import"}</button>}
            <button className="button button-back button-small" onClick={() => { setOpen(false); setPreview(null); setResult(null); }}>Close</button>
          </div>
        </div>
      )}
    </>
  );
};

const Profile = ({ applicant, close, refresh }) => {
  const [status, setStatus] = useState(applicant.status);
  const [notes, setNotes] = useState(applicant.internal_notes || "");
  const [message, setMessage] = useState("");
  const save = async () => { await client.patch(`/admin/applicants/${applicant.applicant_id}`, { status, internal_notes: notes }); setMessage("Profile updated."); refresh(); };
  const retry = async () => { setMessage("Syncing…"); try { await client.post(`/admin/applicants/${applicant.applicant_id}/retry-resend`); setMessage("Resend sync complete."); refresh(); } catch { setMessage("Resend sync failed."); } };
  const groups = [
    ["Contact", ["applicant_id", "email", "phone", "linkedin_url", "country", "city", "state_region", "postal_code"]],
    ["Professional Background", ["job_title", "employer", "professional_field", "years_experience", "skills", "other_skill", "professional_summary"]],
    ["Board Preferences", ["causes", "other_cause", "board_types", "participation_preferences", "geographic_preferences", "availability", "monthly_commitment"]],
    ["Contribution", ["previous_board_experience", "board_experience_details", "fundraising_activities", "professional_relationships", "reason_for_joining", "commitment_answer", "understands_unpaid"]],
    ["Permissions", ["profile_sharing_permission", "board_opportunity_consent", "other_offers_consent", "privacy_accepted", "consent_at"]],
  ];
  const label = (key) => key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const display = (value) => Array.isArray(value) ? value.join(", ") : typeof value === "boolean" ? (value ? "Yes" : "No") : (value || "Not provided");
  return <div className="admin-profile-overlay" data-testid="admin-applicant-profile"><div className="admin-profile-panel"><button className="profile-close" onClick={close} data-testid="admin-profile-close-button">×</button><p className="eyebrow">Applicant profile</p><h2>{applicant.first_name} {applicant.last_name}</h2><div className="admin-profile-actions"><label>Status<select value={status} onChange={(event) => setStatus(event.target.value)} data-testid="admin-applicant-status-select">{statuses.map((item) => <option value={item} label={item} key={item} />)}</select></label>{applicant.resume_file_id && <a className="button button-back" href={`${API}/admin/applicants/${applicant.applicant_id}/resume`} data-testid="admin-resume-download-link"><Download size={16} /> Download résumé</a>}<button className="button button-back" onClick={retry} data-testid="admin-retry-resend-button"><RefreshCw size={16} /> Retry Resend</button></div>{groups.map(([title, keys]) => <section className="profile-group" key={title}><h3>{title}</h3><dl>{keys.map((key) => <div key={key}><dt>{label(key)}</dt><dd>{display(applicant[key])}</dd></div>)}</dl></section>)}<label className="admin-notes">Internal notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows="5" data-testid="admin-internal-notes-textarea" /></label>{message && <p className="admin-message" data-testid="admin-profile-message">{message}</p>}<button className="button" onClick={save} data-testid="admin-save-profile-button">Save Applicant Changes</button></div></div>;
};

const blogStatusClass = (status) => ({ "Pending Review": "pending", Published: "published", Rejected: "rejected", Generating: "generating" }[status] || "failed");
const renderBlogBody = (body) => (body || "").split(/\n{2,}|\n(?=## )/).map((block, index) => {
  const trimmed = block.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith("## ")) return <h2 key={index}>{trimmed.replace(/^##\s*/, "")}</h2>;
  return <p key={index}>{trimmed}</p>;
});

const TopicScheduleBlock = () => {
  const [schedule, setSchedule] = useState(null);
  const [openKey, setOpenKey] = useState("");
  useEffect(() => { client.get("/admin/blog/topics").then((r) => setSchedule(r.data.schedule)).catch(() => setSchedule([])); }, []);
  if (!schedule) return <p data-testid="topic-schedule-loading">Loading topic schedule…</p>;
  return (
    <div className="topic-schedule" data-testid="topic-schedule">
      <h2>100-Topic Publishing Schedule</h2>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr>{["Category", "Publish Day", "CTA", "Published", "Next Topic", ""].map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
          <tbody>
            {schedule.map((row) => (
              <React.Fragment key={row.category_key}>
                <tr data-testid={`topic-schedule-row-${row.category_key}`}>
                  <td>{row.category}</td>
                  <td>{row.publish_day}</td>
                  <td>{row.cta_url}</td>
                  <td>{row.published_count} of {row.topics.length}</td>
                  <td data-testid={`next-topic-${row.category_key}`}>{row.next_topic_number}. {row.next_topic_title}</td>
                  <td><button className="table-link" onClick={() => setOpenKey(openKey === row.category_key ? "" : row.category_key)} data-testid={`topic-schedule-toggle-${row.category_key}`}>{openKey === row.category_key ? "Hide Topics" : "All Topics"}</button></td>
                </tr>
                {openKey === row.category_key && row.topics.map((topic) => (
                  <tr key={topic.topic_number} className="topic-detail-row">
                    <td colSpan="2">{topic.topic_number}. {topic.topic_title}</td>
                    <td colSpan="2"><span className={`blog-status-badge ${topic.publication_status === "Published" ? "published" : topic.publication_status === "Next" ? "pending" : "generating"}`}>{topic.publication_status}</span></td>
                    <td colSpan="2">{topic.published_at?.slice(0, 10) || ""}</td>
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const BlogAdminSection = ({ posts, categories, generating, notice, onGenerate, onRefresh, onOpen }) => (
  <section data-testid="admin-blog-section">
    <TopicScheduleBlock />
    <div className="admin-filters blog-generate-row">
      {categories.map((category) => (
        <button key={category.key} className="button button-small" disabled={!!generating} onClick={() => onGenerate(category.key)} data-testid={`admin-generate-blog-${category.key}`}>
          <Sparkles size={14} /> {generating === category.key ? "Generating…" : `New ${category.name} Draft`}
        </button>
      ))}
      <button className="button button-back button-small" onClick={onRefresh} data-testid="admin-blog-refresh-button"><RefreshCw size={15} /> Refresh</button>
    </div>
    {notice && <p className="admin-message" data-testid="admin-blog-notice">{notice}</p>}
    <div className="admin-table-wrap">
      <table className="admin-table blog-admin-table">
        <thead><tr>{["Title", "Category", "Status", "Scheduled", "Published", "Created", "Actions"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead>
        <tbody>
          {posts.length === 0 && <tr><td colSpan="7" data-testid="admin-blog-empty">{adminPageText.noBlogPostsYetGenerate}</td></tr>}
          {posts.map((post) => (
            <tr key={post.blog_post_id} data-testid={`admin-blog-row-${post.blog_post_id}`}>
              <td><button className="table-link" onClick={() => onOpen(post)} data-testid={`admin-blog-open-${post.blog_post_id}`}>{post.title || "(untitled draft)"}</button></td>
              <td>{post.category}</td>
              <td><span className={`blog-status-badge ${blogStatusClass(post.publication_status)}`}>{post.publication_status}</span></td>
              <td>{post.scheduled_date}</td>
              <td>{post.published_at?.slice(0, 10) || ""}</td>
              <td>{post.created_at?.slice(0, 10)}</td>
              <td><button className="table-link" onClick={() => onOpen(post)} data-testid={`admin-blog-review-${post.blog_post_id}`}><Eye size={14} /> Review</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </section>
);

const BlogPreview = ({ post, close, refresh }) => {
  const [current, setCurrent] = useState(post);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ title: post.title || "", excerpt: post.excerpt || "", body: post.body || "" });
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const isPublished = current.publication_status === "Published";
  const fail = (err) => setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Action failed.");
  const act = async (action, successText) => {
    setBusy(action); setMessage(action === "regenerate" ? "Claude is writing a fresh version. This can take up to a minute…" : "");
    try {
      const response = await client.post(`/admin/blog/posts/${current.blog_post_id}/${action}`);
      if (response.data.post) { setCurrent(response.data.post); setDraft({ title: response.data.post.title || "", excerpt: response.data.post.excerpt || "", body: response.data.post.body || "" }); }
      setMessage(response.data.errors ? `Validation failed: ${response.data.errors.join("; ")}` : successText);
      refresh();
    } catch (err) { fail(err); }
    setBusy("");
  };
  const saveEdits = async () => {
    setBusy("save"); setMessage("");
    try {
      const response = await client.patch(`/admin/blog/posts/${current.blog_post_id}`, draft);
      setCurrent(response.data.post); setEditing(false); setMessage("Draft updated."); refresh();
    } catch (err) { fail(err); }
    setBusy("");
  };
  return (
    <div className="admin-profile-overlay" data-testid="admin-blog-preview">
      <div className="admin-profile-panel">
        <button className="profile-close" onClick={close} data-testid="admin-blog-preview-close">×</button>
        <p className="eyebrow">Blog draft review</p>
        <div className="blog-preview-meta">
          <span className="blog-category-tag">{current.category}</span>
          <span className={`blog-status-badge ${blogStatusClass(current.publication_status)}`} data-testid="admin-blog-preview-status">{current.publication_status}</span>
        </div>
        {current.error && <p className="submit-error" data-testid="admin-blog-preview-error">{current.error}</p>}
        <div className="admin-profile-actions blog-preview-actions">
          {!isPublished && !editing && <button className="button" onClick={() => act("approve", "Article published. It is now live on the blog.")} disabled={!!busy} data-testid="admin-blog-approve-button"><CheckCircle size={16} /> {busy === "approve" ? "Publishing…" : "Approve & Publish"}</button>}
          {!editing && <button className="button button-back" onClick={() => setEditing(true)} disabled={!!busy} data-testid="admin-blog-edit-button"><Pencil size={15} /> Edit Draft</button>}
          {!isPublished && !editing && <button className="button button-back" onClick={() => act("regenerate", "A fresh draft has been generated and is awaiting your review.")} disabled={!!busy} data-testid="admin-blog-regenerate-button"><RefreshCw size={15} /> {busy === "regenerate" ? "Regenerating…" : "Regenerate"}</button>}
          {!isPublished && !editing && current.publication_status !== "Rejected" && <button className="button button-back blog-reject-button" onClick={() => act("reject", "Draft rejected. It will not be published.")} disabled={!!busy} data-testid="admin-blog-reject-button"><XCircle size={15} /> Reject</button>}
        </div>
        {message && <p className="admin-message" data-testid="admin-blog-preview-message">{message}</p>}
        {editing ? (
          <div className="blog-edit-form" data-testid="admin-blog-edit-form">
            <label>Title<input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} data-testid="admin-blog-edit-title" /></label>
            <label>Excerpt<textarea rows="3" value={draft.excerpt} onChange={(event) => setDraft({ ...draft, excerpt: event.target.value })} data-testid="admin-blog-edit-excerpt" /></label>
            <label>{adminPageText.bodyUseAtTheStart}<textarea rows="22" value={draft.body} onChange={(event) => setDraft({ ...draft, body: event.target.value })} data-testid="admin-blog-edit-body" /></label>
            <div className="admin-profile-actions">
              <button className="button" onClick={saveEdits} disabled={!!busy} data-testid="admin-blog-save-edits-button">{busy === "save" ? "Saving…" : "Save Edits"}</button>
              <button className="button button-back" onClick={() => { setEditing(false); setDraft({ title: current.title || "", excerpt: current.excerpt || "", body: current.body || "" }); }} data-testid="admin-blog-cancel-edit-button">Cancel</button>
            </div>
          </div>
        ) : (
          <div className="blog-preview-render">
            <h2 className="blog-preview-title" data-testid="admin-blog-preview-title">{current.title || "(untitled draft)"}</h2>
            {current.excerpt && <p className="blog-preview-excerpt" data-testid="admin-blog-preview-excerpt">{current.excerpt}</p>}
            <article className="blog-article-body" data-testid="admin-blog-preview-body">{renderBlogBody(current.body)}</article>
            {current.cta_label && <div className="blog-preview-cta" data-testid="admin-blog-preview-cta"><h3>{current.cta_label}</h3><span className="button">{current.cta_button}</span></div>}
            {isPublished && (
              <div className="blog-linkedin-block" data-testid="admin-blog-linkedin-block">
                <div className="blog-linkedin-head">
                  <h3>LinkedIn Post</h3>
                  <div className="admin-profile-actions">
                    {current.linkedin_snippet && <button className="button button-small" onClick={() => { navigator.clipboard.writeText(current.linkedin_snippet); setMessage("LinkedIn post copied to your clipboard."); }} data-testid="admin-blog-copy-linkedin-button"><Copy size={14} /> Copy</button>}
                    <button className="button button-back button-small" onClick={() => act("linkedin-snippet", "LinkedIn post ready.")} disabled={!!busy} data-testid="admin-blog-generate-linkedin-button"><Sparkles size={14} /> {busy === "linkedin-snippet" ? "Writing…" : current.linkedin_snippet ? "Regenerate" : "Generate LinkedIn Post"}</button>
                  </div>
                </div>
                {current.linkedin_snippet ? <pre className="blog-linkedin-snippet" data-testid="admin-blog-linkedin-snippet">{current.linkedin_snippet}</pre> : <p className="admin-message">No LinkedIn post yet. Generate one above.</p>}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const ReferenceLibrarySection = () => {
  const [items, setItems] = useState([]);
  const [labels, setLabels] = useState({});
  const [form, setForm] = useState({ title: "", module: "0", resource_types: "" });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const load = useCallback(async () => { const response = await client.get("/admin/reference-library"); setItems(response.data.references); setLabels(response.data.module_labels); }, []);
  useEffect(() => { load(); }, [load]);
  const upload = async () => {
    if (!file) { setMessage("Choose a file to upload."); return; }
    setBusy(true); setMessage("");
    try {
      const payload = new FormData();
      payload.append("file", file); payload.append("title", form.title); payload.append("module", form.module); payload.append("resource_types", form.resource_types);
      const response = await client.post("/admin/reference-library", payload, { headers: { "Content-Type": "multipart/form-data" } });
      setMessage(`Uploaded (${response.data.extracted_characters.toLocaleString()} characters extracted). It stays unused until you approve it.`);
      setFile(null); setForm({ title: "", module: "0", resource_types: "" }); load();
    } catch (err) { setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Upload failed."); }
    setBusy(false);
  };
  const toggleApprove = async (item) => { await client.patch(`/admin/reference-library/${item.reference_id}`, { approved: !item.approved }); load(); };
  const remove = async (item) => { if (window.confirm(`Delete "${item.title}" from the reference library?`)) { await client.delete(`/admin/reference-library/${item.reference_id}`); load(); } };
  return (
    <section data-testid="admin-reference-library">
      <h2 className="reference-heading">{adminPageText.recruitmentExecutionReferenceLibrary}</h2>
      <p className="admin-message">{adminPageText.m_privateFounderonlyExamplesClaudeUses}</p>
      <div className="admin-filters reference-upload-row">
        <input type="file" accept=".docx,.pdf,.doc,.txt" onChange={(event) => setFile(event.target.files?.[0] || null)} data-testid="reference-file-input" />
        <input placeholder="Title (optional)" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} data-testid="reference-title-input" />
        <select value={form.module} onChange={(event) => setForm({ ...form, module: event.target.value })} data-testid="reference-module-select">{Object.entries(labels).map(([key, value]) => <option key={key} value={key}>{key === "0" ? value : `Module ${key} — ${value}`}</option>)}</select>
        <input placeholder={adminPageText.resourceTagsCommaSeparatedOptional} value={form.resource_types} onChange={(event) => setForm({ ...form, resource_types: event.target.value })} data-testid="reference-tags-input" />
        <button className="button button-small" disabled={busy} onClick={upload} data-testid="reference-upload-button">{busy ? "Uploading…" : "Upload Reference"}</button>
      </div>
      {message && <p className="admin-message" data-testid="reference-message">{message}</p>}
      <div className="reference-list">
        {items.length === 0 && <p className="reference-empty" data-testid="reference-empty">{adminPageText.noReferenceMaterialsYet}</p>}
        {items.map((item) => (
          <div className="reference-card" key={item.reference_id} data-testid={`reference-row-${item.reference_id}`}>
            <div className="reference-card-info">
              <h3 className="reference-card-title">{item.title}</h3>
              <p className="reference-card-meta">
                {item.module === 0 ? "General / all modules" : `Module ${item.module}`}
                {(item.resource_types || []).length > 0 && <> · Tags: {(item.resource_types || []).join(", ")}</>}
                {item.uploaded_at && <> · Uploaded {item.uploaded_at.slice(0, 10)}</>}
              </p>
              <span className={`blog-status-badge ${item.approved ? "published" : "pending"}`} data-testid={`reference-status-${item.reference_id}`}>{item.approved ? "Approved for AI Reference" : "Not Approved"}</span>
            </div>
            <div className="reference-card-actions">
              <button className={`button button-small ${item.approved ? "button-back" : ""}`} onClick={() => toggleApprove(item)} data-testid={`reference-approve-${item.reference_id}`}>{item.approved ? "Revoke Approval" : "Approve for AI Reference"}</button>
              <button className="table-link reference-delete-link" onClick={() => remove(item)} data-testid={`reference-delete-${item.reference_id}`}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default function AdminPage() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState("applicants");
  const [applicants, setApplicants] = useState([]);
  const [nonprofits, setNonprofits] = useState([]);
  const [filters, setFilters] = useState(blankFilters);
  const [selected, setSelected] = useState([]);
  const [profile, setProfile] = useState(null);
  const [blogPosts, setBlogPosts] = useState([]);
  const [blogCategories, setBlogCategories] = useState([]);
  const [blogPreview, setBlogPreview] = useState(null);
  const [generating, setGenerating] = useState("");
  const [blogNotice, setBlogNotice] = useState("");
  const loadBlog = useCallback(async () => { const response = await client.get("/admin/blog/posts"); setBlogPosts(response.data.posts); setBlogCategories(response.data.categories); }, []);
  const generateDraft = async (category) => {
    setGenerating(category); setBlogNotice("Claude is writing a new draft. This can take up to a minute…");
    try { await client.post("/blog/generate", { category, publish_now: false }); setBlogNotice("Draft generated and awaiting your review."); await loadBlog(); }
    catch (err) { setBlogNotice(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Generation failed."); await loadBlog(); }
    setGenerating("");
  };

  useEffect(() => { client.get("/auth/me").then((response) => setUser(response.data)).catch(() => setUser(false)).finally(() => setChecking(false)); }, []);
  const loadApplicants = useCallback(async () => { const response = await client.get("/admin/applicants", { params: filters }); setApplicants(response.data); }, [filters]);
  const loadNonprofits = useCallback(async () => { const response = await client.get("/admin/nonprofit-contacts"); setNonprofits(response.data); }, []);
  useEffect(() => { if (user) { loadApplicants(); loadNonprofits(); loadBlog(); } }, [user, loadApplicants, loadNonprofits, loadBlog]);
  const filterOptions = useMemo(() => ({
    state_region: [...new Set(applicants.map((item) => item.state_region).filter(Boolean))],
    cause: [...new Set(applicants.flatMap((item) => item.causes || []))],
    skill: [...new Set(applicants.flatMap((item) => item.skills || []))],
    board_type: [...new Set(applicants.flatMap((item) => item.board_types || []))],
    fundraising: [...new Set(applicants.flatMap((item) => item.fundraising_activities || []))],
    availability: [...new Set(applicants.map((item) => item.availability).filter(Boolean))],
  }), [applicants]);
  const openProfile = async (id) => { const response = await client.get(`/admin/applicants/${id}`); setProfile(response.data); };
  const logout = async () => { await client.post("/auth/logout"); setUser(false); };
  if (checking) return <div className="admin-loading" data-testid="admin-loading">Checking administrator access…</div>;
  if (!user) return <Login onLogin={setUser} />;
  return <main className="admin-page" data-testid="admin-dashboard"><header className="admin-header"><div><p className="eyebrow">Private administrator area</p><h1>Board Applicant Network</h1></div><div className="admin-header-actions"><a className="button button-small" href="/recruit" data-testid="admin-review-recruitment-button">Review Recruitment Experience</a><button onClick={logout} data-testid="admin-logout-button"><LogOut size={17} /> Log out</button></div></header><div className="admin-broadcast-note" data-testid="admin-broadcast-instruction">{adminPageText.sendBoardOpportunityAndNonprofit}</div><ReviewResumePanel /><nav className="admin-tabs"><button className={tab === "applicants" ? "active" : ""} onClick={() => setTab("applicants")} data-testid="admin-applicants-tab">Board Applicants</button><button className={tab === "nonprofits" ? "active" : ""} onClick={() => setTab("nonprofits")} data-testid="admin-nonprofits-tab">Nonprofit Contacts</button><button className={tab === "blog" ? "active" : ""} onClick={() => setTab("blog")} data-testid="admin-blog-tab">Blog Posts</button><button className={tab === "reference" ? "active" : ""} onClick={() => setTab("reference")} data-testid="admin-reference-tab">Reference Library</button><button className={tab === "clients" ? "active" : ""} onClick={() => setTab("clients")} data-testid="admin-clients-tab">Client Delivery</button><button className={tab === "strategic" ? "active" : ""} onClick={() => setTab("strategic")} data-testid="admin-strategic-tab">Strategic Planning</button><button className={tab === "funnels" ? "active" : ""} onClick={() => setTab("funnels")} data-testid="admin-funnels-tab">Funnel Numbers</button><button className={tab === "boardfix" ? "active" : ""} onClick={() => setTab("boardfix")} data-testid="admin-board-fix-tab">Board Fix</button></nav>{tab === "boardfix" ? <BoardFixSection /> : tab === "funnels" ? <FunnelNumbersSection /> : tab === "clients" ? <ClientDeliverySection /> : tab === "strategic" ? <StrategicPlanningSection /> : tab === "applicants" ? <section><div className="admin-filters"><label className="search-filter"><Search size={15} /><input placeholder={adminPageText.searchNameOrEmail} value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} data-testid="admin-applicant-search" /></label><select value={filters.country} onChange={(event) => setFilters({ ...filters, country: event.target.value })} data-testid="admin-country-filter"><option value="" label="All countries" /><option value="United States" label="United States" /><option value="United Kingdom" label="United Kingdom" /></select>{Object.entries(filterOptions).map(([key, options]) => <select key={key} value={filters[key]} onChange={(event) => setFilters({ ...filters, [key]: event.target.value })} data-testid={`admin-${key.replace("_", "-")}-filter`}><option value="" label={`All ${key.replace("_", " ")}`} />{options.map((option) => <option value={option} label={option} key={option} />)}</select>)}<button className="button button-small" onClick={loadApplicants} data-testid="admin-apply-filters-button">Apply Filters</button><a className="button button-back button-small" href={`${API}/admin/applicants-export.csv?ids=${selected.join(",")}`} data-testid="admin-export-csv-link"><Download size={15} /> Export {selected.length ? "Selected" : "All"}</a><ImportApplicants refresh={loadApplicants} /></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th><input type="checkbox" aria-label={adminPageText.selectAllApplicants} checked={applicants.length > 0 && selected.length === applicants.length} onChange={(event) => setSelected(event.target.checked ? applicants.map((item) => item.applicant_id) : [])} data-testid="admin-select-all-applicants" /></th>{["Applicant ID", "Name", "Email", "Phone", "Country / City", "Job title", "Professional field", "Main expertise", "Preferred causes", "Preferred board type", "Availability", "Status", "Resend", "Created"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead><tbody>{applicants.map((item) => <tr key={item.applicant_id} data-testid={`admin-applicant-row-${item.applicant_id}`}><td><input type="checkbox" checked={selected.includes(item.applicant_id)} onChange={() => setSelected((current) => current.includes(item.applicant_id) ? current.filter((id) => id !== item.applicant_id) : [...current, item.applicant_id])} /></td><td><button className="table-link" onClick={() => openProfile(item.applicant_id)}>{item.applicant_id}</button></td><td>{item.first_name} {item.last_name}</td><td>{item.email}</td><td>{item.phone}</td><td>{item.country}<small>{item.city}</small></td><td>{item.job_title}</td><td>{item.professional_field}</td><td>{item.skills?.[0]}</td><td>{item.causes?.[0]}</td><td>{item.board_types?.[0]}</td><td>{item.availability}</td><td>{item.status}</td><td><span className={`sync-badge ${item.resend_segment_status?.toLowerCase()}`}>{item.resend_segment_status}</span></td><td>{item.created_at?.slice(0, 10)}</td></tr>)}</tbody></table></div></section> : tab === "nonprofits" ? <section className="nonprofit-admin-section"><div className="admin-table-wrap"><table className="admin-table"><thead><tr>{["Name", "Email", "Phone", "Organization", "Country", "Assessment date", "Consent date", "Resend"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead><tbody>{nonprofits.map((item) => <tr key={`${item.email}-${item.submitted_at}`}><td>{item.name}</td><td>{item.email}</td><td>{item.phone}</td><td>{item.organization_name}</td><td>{item.country}</td><td>{item.submitted_at?.slice(0, 10)}</td><td>{item.email_permission_at?.slice(0, 10)}</td><td>{item.resend_sync_status}</td></tr>)}</tbody></table></div></section> : tab === "blog" ? <BlogAdminSection posts={blogPosts} categories={blogCategories} generating={generating} notice={blogNotice} onGenerate={generateDraft} onRefresh={loadBlog} onOpen={setBlogPreview} /> : <ReferenceLibrarySection />}{blogPreview && <BlogPreview post={blogPreview} close={() => setBlogPreview(null)} refresh={loadBlog} />}{profile && <Profile applicant={profile} close={() => setProfile(null)} refresh={loadApplicants} />}</main>;
}