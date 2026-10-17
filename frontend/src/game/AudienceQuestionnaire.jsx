import { useEffect, useRef, useState } from "react";
import { SpeakButton } from "./SpeakButton";
import GuidedAudioButton from "./GuidedAudioButton";
import { useGuidedNarration } from "./useGuidedNarration";

// Both the existing free leader route and personal invitation route use this form.
export default function AudienceQuestionnaire({ configuration: config, initial, storageKey, context, save, complete }) {
  const [value, setValue] = useState(() => {
    let local; try { local = JSON.parse(localStorage.getItem(storageKey) || "null"); } catch {}
    return local || { workflow_version: config.workflow_version, audiences: initial?.audiences || {}, involvement: initial?.involvement || "", category_status: initial?.category_status || {}, progress: { category: 0, phase: "welcome", question: 0, audience_index: 0, ...(initial?.progress || {}) } };
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const queue = useRef(Promise.resolve());
  const progress = value.progress;
  const category = config.categories[progress.category || 0];
  const list = value.audiences[category] || [];
  const audience = list[progress.audience_index || 0];
  const question = config.questions[category]?.[progress.question || 0];
  const phase = progress.phase || "welcome";
  const gate = list.length ? config.another_questions[category] : config.opening_questions[category];
  const prompt = phase === "answer" ? question.prompt : phase === "participation" ? config.participation_question : phase === "gate" ? gate : config.instructions;
  const narration = useGuidedNarration("fundraising-free", "audience-" + category + "-" + phase + "-" + progress.question, prompt);
  const persist = (next) => {
    // Serialize requests so an older autosave cannot overwrite a later step.
    const task = queue.current.catch(() => {}).then(() => save(next));
    queue.current = task;
    return task;
  };
  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(value));
    const timer = setTimeout(() => persist(value).catch(() => setError("Your latest changes could not be saved. Please try again before leaving.")), 900);
    return () => clearTimeout(timer);
    // save is supplied by the existing route; changing its identity must not trigger another save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, storageKey]);
  const change = (next) => { setValue(next); setError(""); };
  const move = async (next) => {
    setBusy(true); setError("");
    try { await persist(next); setValue(next); window.scrollTo({ top: 0 }); }
    catch (e) { setError(e.response?.data?.detail || "We could not save your progress. Please try again."); }
    setBusy(false);
  };
  const setProgress = (patch) => move({ ...value, progress: { ...progress, ...patch } });
  const updateAnswer = (text) => change({ ...value, audiences: { ...value.audiences, [category]: list.map((item, index) => index === progress.audience_index ? { ...item, [question.key]: text } : item) } });
  const add = () => {
    const id = window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    move({ ...value, audiences: { ...value.audiences, [category]: [...list, { id }] }, category_status: { ...value.category_status, [category]: "" }, progress: { category: progress.category || 0, audience_index: list.length, question: 0, phase: "answer" } });
  };
  const finishCategory = () => move({ ...value, category_status: { ...value.category_status, [category]: "complete" }, progress: progress.category < 2 ? { category: progress.category + 1, phase: "gate", question: 0, audience_index: 0 } : { ...progress, phase: "participation" } });
  const submit = async () => {
    setBusy(true); setError("");
    try { await persist(value); await complete(value); localStorage.removeItem(storageKey); }
    catch (e) { setError(e.response?.data?.detail || "We could not submit your contribution. Please try again."); }
    setBusy(false);
  };
  return <section className="guided-question" data-testid="bfg-audience-questionnaire">
    <div className="guided-question-top"><span>{phase === "answer" ? `${config.labels[category]} · Audience ${(progress.audience_index || 0) + 1} · Question ${(progress.question || 0) + 1} of ${config.questions[category].length}` : "YOUR FUNDRAISING IDEAS"}</span><GuidedAudioButton narration={narration}/></div>
    <p className="guided-kicker">{context.organization_name}</p>
    {context.goal_display && <p className="guided-lead">Fundraising goal: {context.goal_display}{(context.deadline || context.deadline_display) ? ` by ${context.deadline || context.deadline_display}` : ""}</p>}
    {phase === "welcome" && <><h1>{context.member?.is_primary ? "Prepare your own fundraising recommendations before inviting your board." : "You have been invited to share your ideas about reaching your organization’s fundraising goal."}</h1><p className="guided-lead">{config.instructions}</p><button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={() => setProgress({ phase: "gate" })}>START MY GAME</button></>}
    {phase === "gate" && <><h1>{gate}</h1><div className="guided-actions"><button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={add}>YES</button><button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={finishCategory}>NO, CONTINUE</button><button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => setProgress({ phase: "review" })}>REVIEW MY ANSWERS</button></div></>}
    {phase === "answer" && <><h1>{question.prompt}</h1><p className="guided-instruction">{question.help}</p><textarea disabled={busy} rows={7} maxLength={12000} aria-label="Your audience answer" value={audience?.[question.key] || ""} onChange={e => updateAnswer(e.target.value)}/><SpeakButton value={audience?.[question.key] || ""} onChange={updateAnswer}/><button className="bfg-btn bfg-btn-ghost" onClick={() => updateAnswer("I am not sure yet.")}>I AM NOT SURE YET</button><div className="guided-actions"><button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => setProgress(progress.question > 0 ? { question: progress.question - 1 } : { phase: "review" })}>BACK / REVIEW</button><button className="bfg-btn bfg-btn-primary" disabled={busy || !audience?.[question.key]?.trim()} onClick={() => setProgress(progress.question < config.questions[category].length - 1 ? { question: progress.question + 1 } : { phase: "gate" })}>{busy ? "SAVING…" : progress.question < config.questions[category].length - 1 ? "NEXT QUESTION" : "SAVE THIS AUDIENCE AND CONTINUE"}</button></div></>}
    {phase === "participation" && <><h1>{config.participation_question}</h1><p>{config.participation_help}</p><textarea disabled={busy} rows={7} maxLength={6000} aria-label="Your personal participation" value={value.involvement} onChange={e => change({ ...value, involvement: e.target.value })}/><SpeakButton value={value.involvement} onChange={involvement => change({ ...value, involvement })}/><button className="bfg-btn bfg-btn-primary" disabled={busy || !value.involvement.trim()} onClick={() => setProgress({ phase: "review" })}>REVIEW MY CONTRIBUTION</button></>}
    {phase === "review" && <><h1>Review Your Own Fundraising Ideas</h1>{config.categories.map((cat, ci) => <section key={cat}><h2>{config.labels[cat]}</h2>{!(value.audiences[cat] || []).length && <p>No audiences supplied in this category.</p>}{(value.audiences[cat] || []).map((item, index) => <div className="guided-process-summary" key={item.id}><strong>{item.who_why || "Audience in progress"}</strong>{config.questions[cat].map(q => <p key={q.key}><strong>{q.prompt}</strong><br/>{item[q.key] || "Not answered yet"}</p>)}<button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => setProgress({ category: ci, audience_index: index, question: 0, phase: "answer" })}>EDIT THIS AUDIENCE</button></div>)}<button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => setProgress({ category: ci, phase: "gate" })}>ADD OR FINISH {config.labels[cat].toUpperCase()}</button></section>)}<h2>Your participation</h2><p>{value.involvement || "Not answered yet"}</p><div className="guided-actions"><button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => setProgress({ phase: "participation" })}>EDIT PARTICIPATION</button><button className="bfg-btn bfg-btn-primary" disabled={busy || !value.involvement.trim() || !config.categories.every(cat => value.category_status[cat] === "complete")} onClick={submit}>{busy ? "SAVING…" : "SUBMIT MY CONTRIBUTION"}</button></div></>}
    {error && <p className="bfg-error" role="alert">{error}</p>}
  </section>;
}
