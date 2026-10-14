import { useEffect, useState } from "react";
import { v2Api, errorMessage } from "./api";
import { PRODUCTS } from "./content";
import LandingContent from "./LandingContent";
import "./v2.css";
import "./landingEditor.css";

const FIELDS = [
  ["eyebrow", "Introductory label"], ["headline", "Main heading"], ["intro", "Opening explanation", true],
  ["hero_note", "Text beneath Start for Free", true],
  ["education_eyebrow", "Educational section label"], ["education_heading", "Educational section heading"],
  ["service_heading", "Materials and support heading"], ["outcome", "What you provide", true],
  ["service_body", "Self-guided and professional assistance explanation", true],
  ["closing_heading", "Closing heading"], ["closing_body", "Closing explanation", true],
];
const copy = (value) => JSON.parse(JSON.stringify(value));
const sameContent = (left, right) => Boolean(left && right && Object.keys(left).length === Object.keys(right).length
  && Object.keys(left).every((key) => JSON.stringify(left[key]) === JSON.stringify(right[key])));

function EditorField({ product, name, label, long = false, rows = 5, value, onChange }) {
  const id = `v2-editor-${product}-${name}`;
  return <div className="v2-editor-field"><label htmlFor={id}>{label}</label>{long
    ? <textarea id={id} required rows={rows} maxLength={12000} value={value} onChange={(event) => onChange(event.target.value)} />
    : <input id={id} required maxLength={300} value={value} onChange={(event) => onChange(event.target.value)} />}</div>;
}

// Remount when the chosen offer changes, preventing one page's state from
// leaking into another even when the administrator changes offers quickly.
function PageEditor({ product, onStateChange }) {
  const [saved, setSaved] = useState(null);
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState(false);
  const [reload, setReload] = useState(0);
  const dirty = Boolean(saved && !sameContent(draft, saved.draft));
  const unpublished = Boolean(saved && !sameContent(draft, saved.published));

  useEffect(() => { onStateChange({ dirty, busy }); }, [dirty, busy, onStateChange]);

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    v2Api.get(`/admin/landing-content/${product}`).then(({ data }) => {
      if (active) { setSaved(data); setDraft(copy(data.draft)); }
    }).catch((problem) => { if (active) setError(errorMessage(problem, "We could not load this offer page. Please retry.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [product, reload]);

  useEffect(() => {
    const warn = (event) => { event.preventDefault(); event.returnValue = ""; };
    if (dirty) window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const write = async (publish) => {
    setBusy(true); setError(""); setMessage("");
    try {
      let state = saved;
      if (dirty || !saved.saved_at) {
        const result = await v2Api.put(`/admin/landing-content/${product}`, { revision: saved.revision, content: draft });
        state = result.data; setSaved(state); setDraft(copy(state.draft));
      }
      if (publish) {
        const result = await v2Api.post(`/admin/landing-content/${product}/publish`, { revision: state.revision });
        setSaved(result.data); setDraft(copy(result.data.draft));
        setMessage("Your words are published. Visitors will see them when they open or reload this offer page. No deployment is needed.");
      } else setMessage("Your draft is saved. Visitors continue to see the published version until you select Publish changes.");
    } catch (problem) { setError(errorMessage(problem, "We could not save this page. Your text is still here. Please try again.")); }
    finally { setBusy(false); }
  };
  const edit = (key, value) => { setDraft((current) => ({ ...current, [key]: value })); setMessage(""); };
  const step = (index, part, value) => edit("teaching", draft.teaching.map((item, i) => i === index ? item.map((text, j) => j === part ? value : text) : item));
  const formValid = draft && FIELDS.every(([key]) => draft[key]?.trim()) && draft.teaching.every(([heading, body]) => heading.trim() && body.trim());

  if (loading) return <p role="status">Loading the saved educational content…</p>;
  if (!draft) return <><p className="v2-editor-error" role="alert">{error}</p><button className="button" onClick={() => setReload((count) => count + 1)}>Retry loading</button></>;
  return <div className="v2-page-editor" data-testid="v2-landing-editor">
    <div className="v2-editor-status"><p>{dirty ? "You have unsaved changes." : unpublished ? "Your saved draft has unpublished changes." : "This is the current published text."}{saved.published_at && <> Last published: {new Date(saved.published_at).toLocaleString()}.</>}</p><a href={`/v2/${product}`} target="_blank" rel="noopener noreferrer">Open published page</a></div>
    <form onSubmit={(event) => { event.preventDefault(); write(false); }}>
      <fieldset disabled={busy} className="v2-editor-fields"><legend>{PRODUCTS[product].name} educational content</legend>
        <p>Write in your own words. Leave a blank line between paragraphs. Text is displayed safely as text, so you do not need HTML.</p>
        {FIELDS.slice(0, 6).map(([key, label, long]) => <EditorField key={key} product={product} name={key} label={label} long={long} rows={key === "intro" ? 6 : 3} value={draft[key]} onChange={(value) => edit(key, value)} />)}
        <h3>Teaching steps</h3>
        {draft.teaching.map(([heading, body], index) => <div className="v2-editor-step" key={index}><h4>Step {index + 1}</h4><EditorField product={product} name={`step-${index}-heading`} label={`Step ${index + 1} heading`} value={heading} onChange={(value) => step(index, 0, value)} /><EditorField product={product} name={`step-${index}-explanation`} label={`Step ${index + 1} explanation`} long rows={6} value={body} onChange={(value) => step(index, 1, value)} /><div className="v2-editor-actions"><button type="button" disabled={index === 0} onClick={() => { const items = copy(draft.teaching); [items[index - 1], items[index]] = [items[index], items[index - 1]]; edit("teaching", items); }}>Move up</button><button type="button" disabled={index === draft.teaching.length - 1} onClick={() => { const items = copy(draft.teaching); [items[index + 1], items[index]] = [items[index], items[index + 1]]; edit("teaching", items); }}>Move down</button><button type="button" disabled={draft.teaching.length === 1} onClick={() => edit("teaching", draft.teaching.filter((_, i) => i !== index))}>Remove step</button></div></div>)}
        <button type="button" disabled={draft.teaching.length >= 20} onClick={() => edit("teaching", [...draft.teaching, ["", ""]])}>Add a teaching step</button>
        {FIELDS.slice(6).map(([key, label, long]) => <EditorField key={key} product={product} name={key} label={label} long={long} value={draft[key]} onChange={(value) => edit(key, value)} />)}
      </fieldset>
      {error && <p className="v2-editor-error" role="alert">{error}</p>}{message && <p className="v2-editor-message" role="status">{message}</p>}
      <div className="v2-editor-actions"><button className="button" type="submit" disabled={busy || !formValid || (!dirty && Boolean(saved.saved_at))}>Save draft</button><button type="button" disabled={busy} onClick={() => setPreview(!preview)}>{preview ? "Hide page preview" : "Preview my changes"}</button><button className="button" type="button" disabled={busy || !formValid || !unpublished} onClick={() => write(true)}>{busy ? "Saving…" : "Publish changes"}</button><button type="button" disabled={busy} onClick={() => { if (!dirty || window.confirm("Discard unsaved changes and reload the saved draft? Copy any text you want to keep first.")) { setMessage(""); setReload((count) => count + 1); } }}>Reload saved draft</button></div>
    </form>
    {preview && <section className="v2-editor-preview" aria-label="Your unpublished page preview"><h3>Preview of your current words</h3><p>This preview uses the same layout as the customer page. Select Publish changes when you are ready for visitors to see it.</p><div className="v2-app"><div className="v2-main"><LandingContent product={product} content={draft} preview /></div></div></section>}
  </div>;
}

export default function AdminLandingContent({ onEditorStateChange }) {
  const [product, setProduct] = useState("recruit");
  const [editorState, setEditorState] = useState({ dirty: false, busy: false });
  useEffect(() => { onEditorStateChange?.(editorState); }, [editorState, onEditorStateChange]);
  const choose = (slug) => {
    if (slug === product || editorState.busy) return;
    if (editorState.dirty && !window.confirm("Switch offers and discard unsaved changes? Save your draft first if you want to keep your writing.")) return;
    setEditorState({ dirty: false, busy: false }); setProduct(slug);
  };
  return <section className="v2-landing-admin"><h2>Offer Page Text</h2><p>Edit the educational homepage for each of your four offers. You can save your writing, preview the page and publish it whenever you are ready.</p><p>The main homepage, testimonials, product images, Start for Free links and $197 checkout prices remain managed by the existing application.</p><div className="v2-editor-product-tabs" role="group" aria-label="Choose an offer page">{Object.entries(PRODUCTS).map(([slug, content]) => <button key={slug} type="button" disabled={editorState.busy} aria-pressed={slug === product} onClick={() => choose(slug)}>{content.name}</button>)}</div><PageEditor key={product} product={product} onStateChange={setEditorState} /></section>;
}
