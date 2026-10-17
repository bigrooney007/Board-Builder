import React, { useCallback, useEffect, useId, useState } from "react";
import { CTA } from "@/content/fundraisingArticles";
import { renderArticleMarkup } from "@/content/fundraisingArticleMarkup";
import { BLOG_FEED_URL } from "@/seo/blogMetadata";

const paragraphs = text => text.split(/\n\s*\n/).map(part => part.trim()).filter(Boolean);
const draftFor = guide => ({ ...guide, ctaButton: guide.ctaButton || CTA,
  visualEyebrow: guide.visualEyebrow || "Your next board meeting", visualFootnote: guide.visualFootnote || "A strategy your board can act on",
  intro: guide.intro.join("\n\n"), steps: guide.steps.map(step => ({ ...step,
    navLabel: step.navLabel || "", paragraphs: step.paragraphs.join("\n\n"),
    questions: (step.questions || []).join("\n"), afterQuestions: step.afterQuestions || "" })) });
const guideFor = draft => ({ ...draft, intro: paragraphs(draft.intro), steps: draft.steps.map(step => ({ ...step,
  paragraphs: paragraphs(step.paragraphs), questions: step.questions.split("\n").map(text => text.trim()).filter(Boolean) })) });
const failure = error => typeof error.response?.data?.detail === "string" ? error.response.data.detail
  : error.response?.status === 422 ? "Complete the required text and keep each section within its length limit."
  : "Your guide could not be saved or loaded. Please try again.";

function TextField({ label, value, onChange, multiline = false, required = true, maxLength = 200, rows = 3 }) {
  const id = useId();
  const props = { id, value: value || "", required, maxLength, onChange: event => onChange(event.target.value) };
  return <div className="blog-guide-field"><label htmlFor={id}>{label}</label>{multiline ? <textarea {...props} rows={rows} /> : <input {...props} />}</div>;
}

export default function FundraisingGuideAdmin({ client }) {
  const [guides, setGuides] = useState([]);
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [copied, setCopied] = useState(false);
  const load = useCallback(async () => {
    setError("");
    try {
      const response = await client.get("/admin/blog/guides");
      if (!Array.isArray(response.data.guides)) throw new Error("Missing guide content");
      setGuides(response.data.guides);
    } catch (err) { setError(failure(err)); }
  }, [client]);
  useEffect(() => { load(); }, [load]);
  const change = key => value => setDraft(previous => ({ ...previous, [key]: value }));
  const stepChange = (index, key) => value => setDraft(previous => ({ ...previous,
    steps: previous.steps.map((step, position) => position === index ? { ...step, [key]: value } : step) }));
  const save = async event => {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      const response = await client.put(`/admin/blog/guides/${draft.slug}`, guideFor(draft));
      const saved = response.data.guide;
      setGuides(previous => previous.map(guide => guide.slug === saved.slug ? saved : guide));
      setDraft(null); setMessage("Saved and published. Your public guide now uses this wording.");
    } catch (err) { setError(failure(err)); }
    finally { setBusy(false); }
  };
  const preview = draft ? guideFor(draft) : null;

  return <>
    <section className="blog-guide-admin" aria-label="Edit fundraising guides">
      <h3>Edit Your Fundraising Guides</h3>
      <p>Change the wording on either article page here. Save and Publish updates the page immediately.</p>
      {error && <p className="submit-error" role="alert">{error} {!draft && <button className="button button-back button-small" onClick={load}>Retry Loading Guides</button>}</p>}
      {message && <p className="admin-message" role="status">{message}</p>}
      {!guides.length && !error && <p>Loading your guides...</p>}
      <div className="blog-guide-cards">{guides.map(guide => <div className="blog-guide-card" key={guide.slug}>
        <h4>{guide.title}</h4><p>{guide.excerpt}</p>
        <div className="material-actions"><button className="button button-back button-small" disabled={!!draft} aria-label={`Edit guide: ${guide.title}`} onClick={() => { setDraft(draftFor(guide)); setError(""); setMessage(""); }}>Edit Guide</button>
          <a href={`/blog/${guide.slug}`} target="_blank" rel="noreferrer">Open public page</a></div>
      </div>)}</div>
      {draft && <form className="blog-guide-form" onSubmit={save}>
        <h4>Editing: {draft.title}</h4>
        <p className="workspace-note">Separate paragraphs with a blank line. Your page address stays /blog/{draft.slug}.</p>
        <fieldset disabled={busy}><legend>Page heading and introduction</legend>
          <TextField label="Article title (search and sharing)" value={draft.title} onChange={change("title")} />
          <div className="blog-guide-field-pair"><TextField label="Main heading" value={draft.headline} onChange={change("headline")} /><TextField label="Heading second line" value={draft.headlineAccent} onChange={change("headlineAccent")} required={false} /></div>
          <TextField label="Topic label" value={draft.topic} onChange={change("topic")} />
          <TextField label="Article description" value={draft.excerpt} onChange={change("excerpt")} multiline maxLength={250} />
          <TextField label="Introduction" value={draft.intro} onChange={change("intro")} multiline rows={9} maxLength={20000} />
          <TextField label="Key message" value={draft.takeaway} onChange={change("takeaway")} multiline maxLength={3000} />
        </fieldset>
        {draft.steps.map((step, index) => <fieldset key={step.id} disabled={busy}><legend>Section {index + 1}</legend>
          <div className="blog-guide-field-pair"><TextField label={`Section ${index + 1} label`} value={step.label} onChange={stepChange(index, "label")} /><TextField label={`Section ${index + 1} navigation label (optional)`} value={step.navLabel} onChange={stepChange(index, "navLabel")} required={false} /></div>
          <TextField label={`Section ${index + 1} heading`} value={step.title} onChange={stepChange(index, "title")} />
          <TextField label={`Section ${index + 1} text`} value={step.paragraphs} onChange={stepChange(index, "paragraphs")} multiline rows={8} maxLength={20000} />
          <details><summary>Optional question list</summary>
            <TextField label={`Section ${index + 1} questions (one per line)`} value={step.questions} onChange={stepChange(index, "questions")} multiline rows={5} required={false} maxLength={10000} />
            <TextField label={`Section ${index + 1} text after questions`} value={step.afterQuestions} onChange={stepChange(index, "afterQuestions")} multiline required={false} maxLength={3000} />
          </details>
        </fieldset>)}
        <fieldset disabled={busy}><legend>Invitation to begin</legend>
          <TextField label="Closing heading" value={draft.closingTitle} onChange={change("closingTitle")} />
          <TextField label="Closing text" value={draft.closing} onChange={change("closing")} multiline maxLength={3000} />
          <TextField label="Button text" value={draft.ctaButton} onChange={change("ctaButton")} />
          <TextField label="Offer explanation" value={draft.offerNote} onChange={change("offerNote")} multiline maxLength={3000} />
        </fieldset>
        <details className="blog-guide-extras"><summary>Sidebar and cover description</summary>
          <TextField label="Sidebar top line" value={draft.visualEyebrow} onChange={change("visualEyebrow")} />
          <TextField label="Sidebar heading" value={draft.visualTitle} onChange={change("visualTitle")} />
          {draft.visualItems.map((value, index) => <TextField key={index} label={`Sidebar point ${index + 1}`} value={value} onChange={next => setDraft(previous => ({ ...previous, visualItems: previous.visualItems.map((item, position) => position === index ? next : item) }))} />)}
          <TextField label="Sidebar bottom line" value={draft.visualFootnote} onChange={change("visualFootnote")} />
          <TextField label="Cover image description" value={draft.image_alt} onChange={change("image_alt")} maxLength={500} />
        </details>
        <details className="blog-guide-preview"><summary>Preview changes before publishing</summary>
          <iframe title="Guide preview" sandbox="" srcDoc={`<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/styles/fundraising-articles.css"></head><body>${renderArticleMarkup(preview)}</body></html>`} />
        </details>
        <div className="material-actions"><button className="button" type="submit" disabled={busy}>{busy ? "Saving..." : "Save and Publish Guide"}</button><button className="button button-back" type="button" disabled={busy} onClick={() => { setDraft(null); setError(""); }}>Cancel Edits</button></div>
      </form>}
    </section>
    <section className="blog-feed-settings" aria-label="LinkedIn blog feed">
      <h3>LinkedIn Company Page RSS Link</h3>
      <p>Paste this link into the RSS field on your LinkedIn company page. New published articles appear in the feed automatically.</p>
      <label>Published article feed<input readOnly value={BLOG_FEED_URL} onFocus={event => event.target.select()} /></label>
      <div className="material-actions"><button className="button button-back button-small" onClick={async () => {
        try { await navigator.clipboard.writeText(BLOG_FEED_URL); setCopied(true); } catch { setCopied(false); }
      }}>Copy Feed Link</button><a href={BLOG_FEED_URL} target="_blank" rel="noreferrer">Open feed</a>{copied && <span role="status">Feed link copied.</span>}</div>
      <p className="workspace-note">The feed contains published articles and these two guides. Drafts enter it when you publish them. LinkedIn controls how your company page picks up the feed.</p>
    </section>
  </>;
}
