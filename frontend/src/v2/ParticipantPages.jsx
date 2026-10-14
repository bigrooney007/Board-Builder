import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { ApplicationForm } from "../public/OpportunityPages";
import BoardRecommitmentFormPage from "../funnels/BoardRecommitmentFormPage";
import SpeakButton from "../game/SpeakButton";
import V2Shell, { ErrorNotice, Loading } from "./V2Shell";
import { errorMessage, v2Api } from "./api";
import "./actions.css";

const CATEGORIES = [
  { key: "individuals", title: "Individuals", type: "individual", plural: "people" },
  { key: "businesses", title: "Businesses", type: "business", plural: "businesses" },
  { key: "grantmakers", title: "Grantmakers", type: "grantmaker", plural: "grantmakers" },
];
const AUDIENCE_FIELDS = ["funder", "why", "where", "attract", "relationship", "ask", "amount"];
const FIELD_TITLES = {
  funder: "Specific type of funder", why: "Why they may give", where: "Where to find them",
  attract: "How to attract their interest", relationship: "How to develop the relationship and raise money",
  ask: "What to ask them to support", amount: "How much to ask and why",
};
const tokenKey = (token) => `nbb:v2:participant-draft:${token}`;
const randomId = () => window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const readSession = (key) => { try { return sessionStorage.getItem(key) || ""; } catch { return ""; } };
const writeSession = (key, value) => { try { sessionStorage.setItem(key, value); } catch { /* The form still works without browser storage. */ } };
const removeSession = (key) => { try { sessionStorage.removeItem(key); } catch { /* noop */ } };

// Only opaque access tokens are stored in this browser. Answers remain in the
// organization's server-side draft, scoped to this participant's secret token.
function useParticipantDraft(token) {
  const [data, setData] = useState(null);
  const [loadedToken, setLoadedToken] = useState("");
  const [error, setError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveState, setSaveState] = useState("");
  const draftToken = useRef("");
  const latest = useRef(null);
  const saved = useRef("");
  const timer = useRef(null);
  const queue = useRef(Promise.resolve());
  const complete = useRef(false);
  const activeToken = useRef(token);

  useEffect(() => {
    let active = true;
    activeToken.current = token;
    draftToken.current = readSession(tokenKey(token));
    latest.current = null; saved.current = ""; complete.current = false;
    setData(null); setLoadedToken(""); setError(""); setSaveState(""); setSaveError("");
    v2Api.get(`/forms/${encodeURIComponent(token)}`, {
      params: draftToken.current ? { draft_token: draftToken.current } : {},
    }).then(({ data: context }) => {
      if (!active) return;
      if (context.draft_token) {
        draftToken.current = context.draft_token;
        writeSession(tokenKey(token), context.draft_token);
      }
      complete.current = Boolean(context.submitted);
      saved.current = JSON.stringify(context.answers || {});
      setData(context); setLoadedToken(token);
    }).catch((failure) => {
      if (active) setError(errorMessage(failure, "This form is not available. Please contact the organization that sent you the link."));
    });
    return () => { active = false; clearTimeout(timer.current); };
  }, [token]);

  const persist = useCallback((answers) => {
    const serialized = JSON.stringify(answers);
    const requestedToken = token;
    queue.current = queue.current.catch(() => {}).then(async () => {
      if (complete.current || activeToken.current !== requestedToken || serialized === saved.current) return;
      setSaveState("saving"); setSaveError("");
      try {
        const response = await v2Api.put(`/forms/${encodeURIComponent(requestedToken)}/draft`, {
          answers, ...(draftToken.current ? { draft_token: draftToken.current } : {}),
        });
        if (activeToken.current !== requestedToken) return;
        draftToken.current = response.data.draft_token;
        writeSession(tokenKey(requestedToken), response.data.draft_token);
        saved.current = serialized; setSaveState("saved");
      } catch (failure) {
        if (activeToken.current === requestedToken) {
          setSaveState("failed");
          setSaveError(errorMessage(failure, "We could not save your progress. Keep this page open and try saving again."));
        }
        throw failure;
      }
    });
    return queue.current;
  }, [token]);

  const schedule = useCallback((answers) => {
    latest.current = answers;
    clearTimeout(timer.current);
    if (complete.current) return;
    if (JSON.stringify(answers) !== saved.current) setSaveState("waiting");
    timer.current = setTimeout(() => { persist(answers).catch(() => {}); }, 650);
  }, [persist]);

  const flush = useCallback(async () => {
    clearTimeout(timer.current);
    if (latest.current) await persist(latest.current);
    else await queue.current;
    return draftToken.current;
  }, [persist]);

  const submit = useCallback(async (answers, name, email, cv = null) => {
    // Keep identity and the current question in the saved draft if final
    // submission fails. The submitted payload contains only source answers.
    latest.current = { ...(latest.current || {}), ...answers, full_name: name, email };
    const secret = await flush();
    const keyName = `${tokenKey(token)}:submit`;
    const idempotencyKey = readSession(keyName) || randomId();
    writeSession(keyName, idempotencyKey);
    const payload = { name, email, answers, draft_token: secret, idempotency_key: idempotencyKey };
    if (cv) {
      const body = new FormData();
      body.append("payload", JSON.stringify(payload)); body.append("cv", cv);
      await v2Api.post(`/forms/${encodeURIComponent(token)}/submit`, body);
    } else {
      await v2Api.post(`/forms/${encodeURIComponent(token)}/submit`, payload);
    }
    complete.current = true; clearTimeout(timer.current);
    setSaveState(""); setSaveError("");
  }, [token, flush]);

  const startNew = useCallback(() => {
    removeSession(tokenKey(token)); removeSession(`${tokenKey(token)}:submit`);
    window.location.reload();
  }, [token]);
  return { data: loadedToken === token ? data : null, error, saveError, saveState, schedule, flush, submit, startNew };
}

function DraftStatus({ state, error, onSave }) {
  return <div className="v2-draft-status">
    <p role="status">{state === "saved" ? "Your latest answers have been saved. Keep this browser tab open to continue later." : state === "saving" || state === "waiting" ? "Saving your progress…" : "Your answers are saved as you go. Keep this browser tab open if you plan to continue later."}</p>
    <ErrorNotice error={error} />
    {error && <button className="v2-btn v2-btn-secondary" type="button" onClick={() => onSave().catch(() => {})}>Try saving again</button>}
  </div>;
}

function OrganizationHeader({ context, title }) {
  const name = context.branding?.organization_name || context.organization_name || context.organization || "Your organization";
  const logo = context.branding?.logo_data || context.logo_data_url;
  const color = /^#[0-9a-f]{6}$/i.test(context.branding?.primary_color || "") ? context.branding.primary_color : undefined;
  return <header className="v2-form-brand" style={color ? { borderTop: `4px solid ${color}` } : {}}>
    {logo && <img src={logo} alt={`${name} logo`} style={{ maxWidth: 180, maxHeight: 110, objectFit: "contain" }} />}
    <p className="v2-eyebrow">{name}</p><h1 style={{ textAlign: "center" }}>{title}</h1>
    {context.introduction && <p style={{ whiteSpace: "pre-wrap", textAlign: "left", overflowWrap: "anywhere" }}>{context.introduction}</p>}
  </header>;
}

function Submitted({ organization, recruitment = false }) {
  return <section className="v2-card" data-testid="v2-participant-submitted">
    <h1>Thank you for sharing your response.</h1>
    <p>Your response has been saved for {organization || "the organization"}. Its leadership will review what you shared and follow up where appropriate.</p>
    {recruitment && <p>Submitting an application does not guarantee an interview or appointment to the board.</p>}
    <p>You can close this page.</p>
  </section>;
}

function AnswerField({ name, label, value, onChange, required = true, short = false, uncertain = false }) {
  return <div className="v2-field">
    <label htmlFor={`v2-answer-${name}`}>{label}{required ? " *" : ""}</label>
    {short ? <input id={`v2-answer-${name}`} value={value || ""} onChange={(event) => onChange(event.target.value)} required={required} />
      : <textarea id={`v2-answer-${name}`} rows="4" value={value || ""} onChange={(event) => onChange(event.target.value)} required={required} data-testid={`v2-answer-${name}`} />}
    {!short && <SpeakButton value={value || ""} onChange={onChange} testId={`v2-speak-${name}`} />}
    {uncertain && <button type="button" className="v2-btn v2-btn-secondary" onClick={() => onChange("I am not sure yet.")}>I am not sure yet</button>}
  </div>;
}

function IdentityFields({ answers, onChange }) {
  return <div className="v2-grid">
    <label className="v2-field">Your name *<input required autoComplete="name" value={answers.full_name || ""} onChange={(event) => onChange("full_name", event.target.value)} data-testid="v2-participant-name" /></label>
    <label className="v2-field">Your email address *<input required type="email" autoComplete="email" value={answers.email || ""} onChange={(event) => onChange("email", event.target.value)} data-testid="v2-participant-email" /></label>
  </div>;
}

export function audienceQuestions(category) {
  const grant = category === "grantmakers";
  const business = category === "businesses";
  const people = grant ? "these grantmakers" : business ? "these businesses" : "these people";
  return [
    { title: `Which type of ${grant ? "grantmaker" : business ? "business" : "individual"} are you thinking about?`, fields: [
      { key: "funder", label: `Describe the specific type of ${grant ? "grantmaker" : business ? "business" : "individual"} you have in mind.` },
      { key: "why", label: grant ? "Why would their funding priorities align with your organization's mission?" : "Why would they have strong reasons to support your organization's mission?" },
    ] },
    { title: grant ? "Where could you identify these grantmakers?" : `Where could your organization find ${people}?`, fields: [{ key: "where", label: "Share the places, networks or sources you would use." }] },
    { title: `How could your organization attract the interest of ${people} and build credibility with them?`, fields: [{ key: "attract", label: "Explain how you would introduce your mission and establish credibility." }] },
    { title: grant ? "How would your organization develop a suitable approach and apply or request support?" : `How could your organization develop a relationship with ${people} and raise money from them?`, fields: [{ key: "relationship", label: grant ? "Describe the approach, relationship and application process you would use." : "Describe how you would develop the relationship and ask for financial support." }] },
    { title: "What would you ask them to support?", fields: [{ key: "ask", label: "Tell us what work, program or organizational need you would ask them to fund." }] },
    { title: "How much would you ask them to give, and why would that amount be appropriate?", fields: [{ key: "amount", label: "Include your suggested amount and reasoning, or explain what you still need to find out." }] },
  ];
}

const initialFlow = () => ({ mode: "identity", categoryIndex: 0, step: 0, audienceId: "", returnToReview: false, editReturn: null });
export const completeAudience = (audience) => AUDIENCE_FIELDS.every((key) => String(audience[key] || "").trim());

export function AudienceQuestionnaire({ initialAnswers = {}, prefill = {}, earlierAnswers = {}, earlierQuestions = [], onDraftChange, onSubmit, busy, error }) {
  const [answers, setAnswers] = useState(() => ({
    ...initialAnswers,
    full_name: initialAnswers.full_name || prefill.full_name || prefill.name || "",
    email: initialAnswers.email || prefill.email || "",
    audiences: Array.isArray(initialAnswers.audiences) ? initialAnswers.audiences : [],
    participation: initialAnswers.participation || "",
    _v2_flow: initialAnswers._v2_flow || initialFlow(),
  }));
  const [validation, setValidation] = useState("");
  const [copyNotice, setCopyNotice] = useState("");
  const flow = answers._v2_flow;
  const category = CATEGORIES[Math.min(Math.max(flow.categoryIndex || 0, 0), CATEGORIES.length - 1)];
  const audience = answers.audiences.find((item) => item.audience_id === flow.audienceId);
  const unfinishedAudience = answers.audiences.find((item) => !completeAudience(item));
  const questions = audienceQuestions(category.key);
  const question = questions[Math.min(Math.max(flow.step || 0, 0), questions.length - 1)];
  useEffect(() => { onDraftChange(answers); }, [answers, onDraftChange]);

  const update = (key, value) => setAnswers((current) => ({ ...current, [key]: value }));
  const move = (changes) => {
    setValidation("");
    setAnswers((current) => ({ ...current, _v2_flow: { ...current._v2_flow, ...changes } }));
  };
  const updateAudience = (key, value) => setAnswers((current) => ({ ...current, audiences: current.audiences.map((item) => item.audience_id === flow.audienceId ? { ...item, [key]: value } : item) }));
  const addAudience = () => {
    if (unfinishedAudience) {
      const firstUnanswered = audienceQuestions(unfinishedAudience.category).findIndex((page) => page.fields.some((field) => !String(unfinishedAudience[field.key] || "").trim()));
      move({ mode: "audience", audienceId: unfinishedAudience.audience_id, categoryIndex: CATEGORIES.findIndex((entry) => entry.key === unfinishedAudience.category), step: Math.max(0, firstUnanswered) });
      return;
    }
    const id = randomId();
    setAnswers((current) => ({
      ...current,
      audiences: [...current.audiences, { audience_id: id, category: category.key, ...Object.fromEntries(AUDIENCE_FIELDS.map((key) => [key, ""])) }],
      _v2_flow: { ...current._v2_flow, mode: "audience", step: 0, audienceId: id },
    }));
  };
  const editAudience = (item) => move({ mode: "audience", audienceId: item.audience_id, categoryIndex: CATEGORIES.findIndex((entry) => entry.key === item.category), step: 0, editReturn: { ...flow, editReturn: null } });
  const nextQuestion = (event) => {
    event.preventDefault();
    if (!audience) { move({ mode: "choice", step: 0 }); return; }
    if (question.fields.some((field) => !String(audience[field.key] || "").trim())) { setValidation("Please answer this question or tell us that you are not sure yet."); return; }
    if (flow.step < questions.length - 1) move({ step: flow.step + 1 });
    else if (flow.editReturn) move({ ...flow.editReturn, editReturn: null });
    else move({ mode: flow.returnToReview ? "review" : "choice", step: 0, audienceId: "", returnToReview: false });
  };
  const noAudience = () => {
    if (unfinishedAudience) { setValidation("Please finish or remove the audience you started before moving to another category."); return; }
    move(flow.returnToReview ? { mode: "review", returnToReview: false, audienceId: "", step: 0 } : flow.categoryIndex < CATEGORIES.length - 1 ? { mode: "choice", categoryIndex: flow.categoryIndex + 1, audienceId: "", step: 0 } : { mode: "participation", audienceId: "", step: 0 });
  };
  const submit = (event) => {
    event.preventDefault();
    if (answers.audiences.some((item) => !completeAudience(item))) { setValidation("Please finish or remove the unfinished audiences before submitting your response."); return; }
    if (!answers.full_name.trim() || !answers.email.trim() || !answers.participation.trim()) { setValidation("Please include your name, email address and personal participation statement."); return; }
    onSubmit(answers);
  };
  const earlier = Object.entries(earlierAnswers || {}).filter(([, value]) => value !== "" && value !== null && value !== undefined);
  const copyEarlier = async (text) => {
    try { await navigator.clipboard.writeText(text); setCopyNotice("Your earlier answer has been copied."); }
    catch { setCopyNotice("Please select the answer text and copy it with your device's copy command."); }
  };

  return <div data-testid="v2-fundraising-questionnaire">
    {earlier.length > 0 && <details className="v2-card" data-testid="v2-earlier-intake-answers">
      <summary>Your earlier fundraising answers</summary>
      <p>You already shared these answers before purchasing. You can reuse the wording that applies to a particular audience as you complete its strategy. Choose what fits, and add the details that you have not yet supplied.</p>
      {earlier.map(([id, source]) => {
        const descriptor = source && typeof source === "object" && !Array.isArray(source) ? source : null;
        const value = descriptor && Object.prototype.hasOwnProperty.call(descriptor, "value") ? descriptor.value : source;
        const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
        const originalQuestion = Array.isArray(earlierQuestions) ? earlierQuestions.find((item) => item.id === id || item.key === id) : earlierQuestions?.[id];
        const label = descriptor?.label || (typeof originalQuestion === "string" ? originalQuestion : originalQuestion?.label || originalQuestion?.prompt) || id.replace(/_/g, " ");
        return <section key={id}><h3>{label}</h3><p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{text}</p><div className="v2-actions">
          <button type="button" className="v2-btn v2-btn-secondary" onClick={() => copyEarlier(text)}>Copy this answer</button>
          {flow.mode === "audience" && audience && question.fields.map((field) => <button type="button" className="v2-btn v2-btn-secondary" key={field.key} onClick={() => updateAudience(field.key, text)}>Use for {FIELD_TITLES[field.key].toLowerCase()}</button>)}
          {flow.mode === "participation" && <button type="button" className="v2-btn v2-btn-secondary" onClick={() => update("participation", text)}>Use for my participation statement</button>}
        </div></section>;
      })}
      {copyNotice && <p role="status">{copyNotice}</p>}
    </details>}
    <section className="v2-card">
      {flow.mode === "identity" && <form onSubmit={(event) => { event.preventDefault(); move({ mode: "choice" }); }}>
        <h2>First, tell us who is contributing.</h2>
        <p>You will develop one funding audience at a time. You can skip a category and tell us when you are unsure about an answer. Your own ideas will be saved for the group discussion.</p>
        <IdentityFields answers={answers} onChange={update} />
        <button className="v2-btn" type="submit" data-testid="v2-fundraising-begin">Continue to fundraising ideas</button>
      </form>}
      {flow.mode === "choice" && <>
        <p className="v2-eyebrow">{category.title}</p>
        {unfinishedAudience ? <>
          <h2>Finish the audience you started before beginning another.</h2>
          <p>Your saved audience is {unfinishedAudience.funder || "not yet named"}. You can continue its strategy or remove it if you no longer want to suggest it.</p>
          <div className="v2-actions"><button type="button" className="v2-btn" onClick={addAudience} data-testid="v2-audience-resume">Continue this audience</button><button type="button" className="v2-btn v2-btn-secondary" onClick={() => update("audiences", answers.audiences.filter((item) => item.audience_id !== unfinishedAudience.audience_id))}>Remove this unfinished audience</button></div>
        </> : <>
          <h2>Do you know {answers.audiences.some((item) => item.category === category.key && completeAudience(item)) ? "another" : "a specific"} type of {category.type} {category.key === "individuals" ? "who" : "that"} could have strong reasons to fund your organization's mission?</h2>
          <p>If you have an audience in mind, we will help you explain how your organization could reach it. You can move on if you do not have a suggestion in this category.</p>
          <div className="v2-actions">
            <button type="button" className="v2-btn" onClick={addAudience} data-testid={`v2-audience-yes-${category.key}`}>Yes, I have an audience in mind</button>
            <button type="button" className="v2-btn v2-btn-secondary" onClick={noAudience} data-testid={`v2-audience-no-${category.key}`}>No, continue</button>
          </div>
        </>}
        <button type="button" className="v2-btn v2-btn-secondary" onClick={() => move(flow.categoryIndex > 0 ? { categoryIndex: flow.categoryIndex - 1 } : { mode: "identity" })}>Back</button>
      </>}
      {flow.mode === "audience" && audience && <form onSubmit={nextQuestion} key={`${audience.audience_id}-${flow.step}`}>
        <p className="v2-eyebrow">{category.title} · Question {flow.step + 1} of {questions.length}</p>
        <h2>{question.title}</h2>
        <p>Share what you know. You can indicate uncertainty and refine the idea during your group's discussion.</p>
        {question.fields.map((field) => <AnswerField key={field.key} name={field.key} label={field.label} value={audience[field.key]} onChange={(value) => updateAudience(field.key, value)} uncertain />)}
        <div className="v2-actions">
          <button type="button" className="v2-btn v2-btn-secondary" onClick={() => move(flow.step > 0 ? { step: flow.step - 1 } : flow.editReturn ? { ...flow.editReturn, editReturn: null } : { mode: flow.returnToReview ? "review" : "choice" })}>Back</button>
          <button type="submit" className="v2-btn" data-testid="v2-audience-next">{flow.step === questions.length - 1 ? "Save this audience" : "Continue"}</button>
        </div>
      </form>}
      {flow.mode === "audience" && !audience && <><p>This saved audience is no longer available.</p><button type="button" className="v2-btn" onClick={() => move({ mode: "choice", audienceId: "", step: 0 })}>Return to this funding category</button></>}
      {flow.mode === "participation" && <form onSubmit={(event) => { event.preventDefault(); move({ mode: "review" }); }}>
        <h2>How would you personally be willing to participate in helping your organization raise money?</h2>
        <p>Explain the contribution you would like to make. The group will discuss participation together before any responsibilities are agreed.</p>
        <AnswerField name="participation" label="Your personal participation" value={answers.participation} onChange={(value) => update("participation", value)} uncertain />
        <div className="v2-actions"><button type="button" className="v2-btn v2-btn-secondary" onClick={() => move({ mode: "choice", categoryIndex: 2 })}>Back</button><button className="v2-btn" type="submit">Review my response</button></div>
      </form>}
      {flow.mode === "review" && <form onSubmit={submit}>
        <h2>Review your fundraising contribution.</h2>
        <p>These are the ideas you provided. The group will decide which suggestions to adopt at its meeting.</p>
        <IdentityFields answers={answers} onChange={update} />
        {CATEGORIES.map((entry, index) => <section key={entry.key}>
          <h3>{entry.title}</h3>
          {!answers.audiences.some((item) => item.category === entry.key) && <p>You have not suggested an audience in this category.</p>}
          {answers.audiences.filter((item) => item.category === entry.key).map((item) => <div className="v2-card" key={item.audience_id}>
            <h4>{item.funder || "Unfinished audience"}{!completeAudience(item) ? " (unfinished)" : ""}</h4>
            <dl>{AUDIENCE_FIELDS.map((key) => <div key={key}><dt><strong>{FIELD_TITLES[key]}</strong></dt><dd style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", margin: "0 0 12px" }}>{item[key] || "Not answered yet"}</dd></div>)}</dl>
            <div className="v2-actions"><button className="v2-btn v2-btn-secondary" type="button" onClick={() => editAudience(item)}>Edit this audience</button><button className="v2-btn v2-btn-secondary" type="button" onClick={() => update("audiences", answers.audiences.filter((aud) => aud.audience_id !== item.audience_id))}>Remove this audience</button></div>
          </div>)}
          <button className="v2-btn v2-btn-secondary" type="button" onClick={() => move({ mode: "choice", categoryIndex: index, returnToReview: true })}>Add an audience under {entry.title.toLowerCase()}</button>
        </section>)}
        <AnswerField name="participation" label="How you would personally be willing to participate" value={answers.participation} onChange={(value) => update("participation", value)} uncertain />
        <ErrorNotice error={error || validation} />
        <div className="v2-actions"><button type="button" className="v2-btn v2-btn-secondary" onClick={() => move({ mode: "participation" })}>Back</button><button className="v2-btn" disabled={busy} type="submit" data-testid="v2-fundraising-submit">{busy ? "Submitting your contribution…" : "Submit my fundraising contribution"}</button></div>
      </form>}
      {flow.mode !== "review" && <ErrorNotice error={validation || error} />}
    </section>
    {answers.audiences.length > 0 && flow.mode !== "review" && <details className="v2-card">
      <summary>Review or edit your saved audiences ({answers.audiences.length})</summary>
      {answers.audiences.map((item) => <div key={item.audience_id} className="v2-actions"><span>{item.funder || "Unfinished audience"}{!completeAudience(item) ? " (unfinished)" : ""}</span><button type="button" className="v2-btn v2-btn-secondary" onClick={() => editAudience(item)}>Edit</button><button type="button" className="v2-btn v2-btn-secondary" onClick={() => update("audiences", answers.audiences.filter((aud) => aud.audience_id !== item.audience_id))}>Remove</button></div>)}
    </details>}
  </div>;
}

function StrategicQuestion({ question, value, onChange }) {
  const prompt = question.prompt || question.label;
  const options = question.options || [];
  if (question.type === "multi") return <fieldset className="v2-field">
    <legend>{prompt}{question.required ? " *" : ""}</legend>
    {options.map((option) => <label className="v2-check" key={option}><input type="checkbox" checked={(value || []).includes(option)} onChange={() => onChange((value || []).includes(option) ? value.filter((item) => item !== option) : [...(value || []), option])} />{option}</label>)}
  </fieldset>;
  if (question.type === "choice" || question.type === "select") return <label className="v2-field">{prompt}{question.required ? " *" : ""}<select required={question.required} value={value || ""} onChange={(event) => onChange(event.target.value)}><option value="">Choose one</option>{options.map((option) => <option key={option}>{option}</option>)}</select></label>;
  return <AnswerField name={question.id} label={prompt} value={value} onChange={onChange} required={Boolean(question.required)} short={question.type === "short" || question.type === "text"} />;
}

function StrategicQuestionnaire({ context, onDraftChange, onSubmit, busy, error }) {
  const sections = context.sections || context.form?.sections || [];
  const [answers, setAnswers] = useState(() => ({ ...context.answers, full_name: context.answers?.full_name || context.prefill?.full_name || context.prefill?.name || "", email: context.answers?.email || context.prefill?.email || "" }));
  const [step, setStep] = useState(() => Math.min(Math.max(Math.floor(Number(context.answers?._v2_step)) || 0, 0), sections.length));
  const [validation, setValidation] = useState("");
  const section = sections[step - 1];
  useEffect(() => { onDraftChange({ ...answers, _v2_step: step }); }, [answers, step, onDraftChange]);
  const update = (id, value) => setAnswers((current) => ({ ...current, [id]: value }));
  const advance = (event) => {
    event.preventDefault();
    if (section) {
      const unanswered = section.questions.find((question) => question.required && (question.type === "multi" ? !(answers[question.id] || []).length : !String(answers[question.id] || "").trim()));
      if (unanswered) { setValidation(`Please answer: ${unanswered.prompt || unanswered.label}`); return; }
    }
    setValidation("");
    if (step >= sections.length) onSubmit(answers);
    else setStep(step + 1);
  };
  return <form className="v2-card" onSubmit={advance} data-testid="v2-strategic-questionnaire">
    {step === 0 ? <><h2>First, tell us who is contributing.</h2><IdentityFields answers={answers} onChange={update} /></> : <>
      <p className="v2-eyebrow">Section {step} of {sections.length}</p><h2>{section?.title}</h2>
      {section?.questions.map((question) => <StrategicQuestion key={question.id} question={question} value={answers[question.id]} onChange={(value) => update(question.id, value)} />)}
    </>}
    <ErrorNotice error={validation || error} />
    <div className="v2-actions">{step > 0 && <button type="button" className="v2-btn v2-btn-secondary" onClick={() => { setStep(step - 1); setValidation(""); }}>Back</button>}<button className="v2-btn" disabled={busy} type="submit">{busy ? "Submitting your ideas…" : step === sections.length ? "Submit my strategic planning ideas" : "Continue"}</button></div>
  </form>;
}

function RecommitmentLayout({ children, saveState, saveError, onSave, color, done }) {
  const brandStyle = /^#[0-9a-f]{6}$/i.test(color || "") ? { borderTop: `4px solid ${color}` } : {};
  return <V2Shell title="Board recommitment form" narrow><div className="v2-action-page v2-participant-recommit" style={brandStyle}>
    {children}{!done && <DraftStatus state={saveState} error={saveError} onSave={onSave} />}
  </div></V2Shell>;
}

export function ParticipantPage() {
  const { token } = useParams();
  const draft = useParticipantDraft(token);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const context = draft.data;
  useEffect(() => { setSubmitted(false); setSubmitError(""); setBusy(false); }, [token]);
  const loadRecommitment = useCallback(() => Promise.resolve(context), [context]);
  const submitRecommitment = useCallback(async (_, answers) => {
    await draft.submit(answers, answers.full_name, answers.email);
    setSubmitted(true);
  }, [draft.submit]);
  const submitIdeas = async (answers) => {
    if (busy) return;
    setBusy(true); setSubmitError("");
    try {
      const clean = context.product === "board-fundraising-game" ? { audiences: answers.audiences, participation: answers.participation } : Object.fromEntries(Object.entries(answers).filter(([key]) => !key.startsWith("_v2_")));
      await draft.submit(clean, answers.full_name, answers.email);
      setSubmitted(true);
    } catch (failure) { setSubmitError(errorMessage(failure, "We could not submit your response. Your saved progress is available for you to try again.")); }
    finally { setBusy(false); }
  };
  const submitApplication = async (answers, cv) => {
    await draft.submit(answers, answers.full_name || answers.name, answers.email, cv);
    setSubmitted(true);
  };

  if (context?.product === "board-recommitment") return <BoardRecommitmentFormPage
    key={token} loadForm={loadRecommitment} submitForm={submitRecommitment} onDraftChange={draft.schedule}
    Layout={RecommitmentLayout} ContentTag="div" layoutProps={{ saveState: draft.saveState, saveError: draft.saveError, onSave: draft.flush, color: context.branding?.primary_color, done: submitted || context.submitted }}
  />;
  const title = context?.product === "recruit" ? "Apply to join the board" : context?.product === "strategic-planning" ? "Your strategic planning ideas" : "Your fundraising ideas";
  return <V2Shell title={title} narrow><div className="v2-action-page">
    {!context && !draft.error && <Loading>Opening your participation form…</Loading>}
    {draft.error && <section className="v2-card"><h1>We could not open this form.</h1><ErrorNotice error={draft.error} />{readSession(tokenKey(token)) && <button className="v2-btn v2-btn-secondary" type="button" onClick={draft.startNew}>Start a new response on this device</button>}</section>}
    {context && (submitted || context.submitted) && <Submitted organization={context.organization_name || context.organization} recruitment={context.product === "recruit"} />}
    {context && !submitted && !context.submitted && <>
      <OrganizationHeader context={context} title={title} />
      {context.product === "recruit" && context.application_open === false && <section className="v2-card"><h2>Applications are not currently open.</h2><p>This recruitment campaign is not accepting applications. Please contact the organization if you have a question about its board opportunity.</p></section>}
      {context.product === "recruit" && context.application_open !== false && <section className="v2-card">
        {context.board_opportunity && <div className="v2-notice" style={{ whiteSpace: "pre-wrap" }}>{context.board_opportunity}</div>}
        <h2>Your application</h2>
        <p>Share the experience and contribution you could bring to this organization. Your application and supporting documents will be available to its authorized leadership.</p>
        <ApplicationForm key={token} questions={context.questions || []} initialAnswers={{ ...context.prefill, ...context.answers }} submitLabel="Submit my board application" onSubmit={submitApplication} onDraftChange={draft.schedule} requireCv={Boolean(context.require_cv)} />
        <p className="v2-notice">Uploaded files are included when you submit. If you return to a saved draft, please select your CV again.</p>
      </section>}
      {context.product === "board-fundraising-game" && <AudienceQuestionnaire key={token} initialAnswers={context.answers} prefill={context.prefill} earlierAnswers={context.earlier_intake_answers} earlierQuestions={context.earlier_intake_questions} onDraftChange={draft.schedule} onSubmit={submitIdeas} busy={busy} error={submitError} />}
      {context.product === "strategic-planning" && <StrategicQuestionnaire key={token} context={context} onDraftChange={draft.schedule} onSubmit={submitIdeas} busy={busy} error={submitError} />}
      {!["recruit", "board-fundraising-game", "strategic-planning"].includes(context.product) && <ErrorNotice>This form does not have a supported product. Please contact the organization that sent you the link.</ErrorNotice>}
      {(context.product !== "recruit" || context.application_open !== false) && <DraftStatus state={draft.saveState} error={draft.saveError} onSave={draft.flush} />}
    </>}
  </div></V2Shell>;
}

export default ParticipantPage;
