import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TOTAL = 10;

const IdeaList = ({ ideas, setIdeas, placeholder, testId }) => {
  const [draft, setDraft] = useState("");
  const add = () => { const value = draft.trim(); if (!value) return; setIdeas([...(ideas || []), value]); setDraft(""); };
  return (
    <div>
      <div className="bfg-idea-list">
        {(ideas || []).map((idea, index) => (
          <div className="bfg-idea" key={`${idea}-${index}`}>
            <span>{idea}</span>
            <button type="button" aria-label="Remove idea" onClick={() => setIdeas(ideas.filter((_, i) => i !== index))}>×</button>
          </div>
        ))}
      </div>
      <div className="bfg-idea-add">
        <input value={draft} placeholder={placeholder || "Add an idea…"} onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); add(); } }} data-testid={testId} />
        <button type="button" className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={add} data-testid={`${testId}-add`}>Add Idea</button>
      </div>
    </div>
  );
};

const fillText = (text, context) => {
  let out = String(text || "")
    .replaceAll("{organisation}", context.organization_name || "your organisation")
    .replaceAll("{organization}", context.organization_name || "your organisation")
    .replaceAll("{goal}", context.goal_display || "its fundraising goal");
  if (context.deadline_display) out = out.replaceAll("{deadline}", context.deadline_display);
  else out = out.replaceAll(" by {deadline}", "").replaceAll("{deadline}", "");
  return out;
};

const SectionPlayer = ({ section, context, token, onCompleted }) => {
  const fill = (text) => fillText(text, context);
  const [loaded, setLoaded] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [firstLocked, setFirstLocked] = useState(false);
  const [firstResponse, setFirstResponse] = useState([]);
  const [firstText, setFirstText] = useState("");
  const [finalResponse, setFinalResponse] = useState([]);
  const [selections, setSelections] = useState({});
  const [additional, setAdditional] = useState({});
  const [stageResponses, setStageResponses] = useState({});
  const [prefs, setPrefs] = useState([]);
  const [doNotWant, setDoNotWant] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoaded(false); setRevealed(false); setFirstLocked(false); setError("");
    setFirstResponse([]); setFirstText(""); setFinalResponse([]); setSelections({}); setAdditional({}); setStageResponses({}); setPrefs([]); setDoNotWant([]);
    axios.get(`${API}/game/play/${token}/section/${section.id}`).then((r) => {
      const response = r.data.response || {};
      setFirstResponse(response.first_response || []);
      setFirstText((response.first_response || [])[0] || "");
      setFinalResponse(response.final_response || []);
      setSelections(response.guided_selections || {});
      setAdditional(response.additional_ideas || {});
      setStageResponses(response.stage_responses || {});
      setPrefs(response.preferences || []);
      setDoNotWant(response.do_not_want || []);
      const locked = !!response.first_move_locked;
      setFirstLocked(locked);
      setRevealed(locked || section.type === "preferences");
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, [section.id, token, section.type]);

  const payload = useCallback(() => ({
    first_response: section.type === "journey" ? (firstText.trim() ? [firstText.trim()] : []) : firstResponse,
    guided_selections: selections,
    additional_ideas: additional,
    stage_responses: stageResponses,
    final_response: finalResponse,
    preferences: prefs,
    do_not_want: doNotWant,
  }), [section.type, firstText, firstResponse, selections, additional, stageResponses, finalResponse, prefs, doNotWant]);

  const reveal = async () => {
    setBusy(true); setError("");
    try {
      await axios.put(`${API}/game/play/${token}/section/${section.id}`, { ...payload(), first_move_locked: true });
      setFirstLocked(true);
      if (section.type === "standard" && finalResponse.length === 0) setFinalResponse(firstResponse);
      setRevealed(true);
      window.scrollTo({ top: 0 });
    } catch { setError("We could not save your answer. Please try again."); }
    setBusy(false);
  };

  const complete = async () => {
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/game/play/${token}/section/${section.id}/complete`, payload());
      onCompleted(response.data.sections_completed);
    } catch { setError("We could not save this section. Please try again."); setBusy(false); }
  };

  const toggleSelection = (groupKey, text) => setSelections((current) => {
    const list = current[groupKey] || [];
    return { ...current, [groupKey]: list.includes(text) ? list.filter((item) => item !== text) : [...list, text] };
  });

  const togglePref = (option) => setPrefs((current) => (
    current.some((pref) => pref.option === option)
      ? current.filter((pref) => pref.option !== option)
      : [...current, { option, note: "", involvement: "" }]
  ));
  const setPrefField = (option, field) => (value) => setPrefs((current) => current.map((pref) => pref.option === option ? { ...pref, [field]: value } : pref));

  if (!loaded) return <div className="bfg-card"><p>Loading…</p></div>;

  return (
    <div className="bfg-card" data-testid={`bfg-play-section-${section.id}`}>
      <p className="bfg-eyebrow">Section {section.id} of {TOTAL}</p>
      <h2>{fill(section.title)}</h2>
      <div className="bfg-scenario" data-testid="bfg-play-scenario">{fill(section.scenario)}</div>

      {section.type === "preferences" ? (
        <>
          <h3 style={{ fontSize: 19, marginTop: 8 }}>{fill(section.first_move_question)}</h3>
          <p style={{ fontSize: 14, marginTop: 6 }}>{fill(section.first_move_support)}</p>
          {section.options.map((option) => {
            const selected = prefs.find((pref) => pref.option === option);
            return (
              <div className={`bfg-pref-option ${selected ? "selected" : ""}`} key={option}>
                <button type="button" onClick={() => togglePref(option)} data-testid={`bfg-pref-${section.id}-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                  <span>{option}</span><span className="bfg-tick">{selected ? "✓" : ""}</span>
                </button>
                {selected && (
                  <div className="bfg-pref-detail">
                    <input placeholder={fill(section.note_question)} value={selected.note}
                      onChange={(event) => setPrefField(option, "note")(event.target.value)} />
                    {section.involvement_options && (
                      <select value={selected.involvement} onChange={(event) => setPrefField(option, "involvement")(event.target.value)}>
                        <option value="">{fill(section.involvement_question)}</option>
                        {section.involvement_options.map((level) => <option key={level} value={level}>{level}</option>)}
                      </select>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {section.do_not_want_question && (
            <>
              <h3 style={{ fontSize: 18, marginTop: 28 }}>{fill(section.do_not_want_question)}</h3>
              <p style={{ fontSize: 14, marginTop: 6 }}>Select anything you would prefer not to do.</p>
              {section.options.filter((option) => option !== "Other").map((option) => {
                const selected = doNotWant.includes(option);
                return (
                  <div className={`bfg-pref-option ${selected ? "selected" : ""}`} key={`dnw-${option}`}>
                    <button type="button" onClick={() => setDoNotWant(selected ? doNotWant.filter((item) => item !== option) : [...doNotWant, option])}>
                      <span>{option}</span><span className="bfg-tick">{selected ? "✓" : ""}</span>
                    </button>
                  </div>
                );
              })}
            </>
          )}
        </>
      ) : (
        <>
          <p className="bfg-eyebrow" style={{ marginTop: 8 }}>Your First Move</p>
          <h3 style={{ fontSize: 19 }}>{fill(section.first_move_question)}</h3>
          {section.first_move_support && <p style={{ fontSize: 14, marginTop: 6 }}>{fill(section.first_move_support)}</p>}
          {section.type === "journey" ? (
            <label className="bfg-field"><span className="sr-only">Your answer</span>
              <textarea rows={4} value={firstText} readOnly={firstLocked} placeholder={section.first_move_placeholder}
                onChange={(event) => setFirstText(event.target.value)} data-testid="bfg-first-move-text" />
            </label>
          ) : firstLocked && revealed ? (
            <div className="bfg-idea-list" style={{ marginTop: 12 }}>
              {firstResponse.map((idea) => <div className="bfg-idea" key={idea}><span>{idea}</span></div>)}
              {firstResponse.length === 0 && <p className="bfg-note">No first ideas were added.</p>}
            </div>
          ) : (
            <IdeaList ideas={firstResponse} setIdeas={setFirstResponse} placeholder={section.first_move_placeholder} testId="bfg-first-move-input" />
          )}

          {!revealed && (
            <div className="bfg-form-actions">
              <span />
              <button className="bfg-btn bfg-btn-primary" onClick={reveal} disabled={busy} data-testid="bfg-reveal-btn">
                {busy ? "Saving…" : section.reveal_label || "Show Me What To Consider"}
              </button>
            </div>
          )}

          {revealed && (
            <>
              {section.wisdom && (
                <div className="bfg-wisdom" data-testid="bfg-play-wisdom">
                  <h4>Fundraising Wisdom</h4>
                  <p>{fill(section.wisdom)}</p>
                </div>
              )}
              {(section.groups || []).map((group) => (
                <div key={group.key} style={{ marginTop: 24 }}>
                  <h3 style={{ fontSize: 19 }}>{group.heading}</h3>
                  {group.support && <p style={{ fontSize: 14, marginTop: 6 }}>{group.support}</p>}
                  {group.items.map((item) => {
                    const selected = (selections[group.key] || []).includes(item.text);
                    return (
                      <button type="button" key={item.text} className={`bfg-prompt-card ${selected ? "selected" : ""}`}
                        onClick={() => toggleSelection(group.key, item.text)}
                        data-testid={`bfg-prompt-${group.key}-${group.items.indexOf(item)}`}>
                        <span className="bfg-tick">{selected ? "✓" : ""}</span>
                        {item.text}
                        {item.hint && <small>{item.hint}</small>}
                      </button>
                    );
                  })}
                  {group.followup_question && (
                    <div style={{ marginTop: 16 }}>
                      <h4 style={{ fontSize: 15.5, color: "#cbd5e1" }}>{fill(group.followup_question)}</h4>
                      <IdeaList ideas={additional[group.key] || []} setIdeas={(ideas) => setAdditional({ ...additional, [group.key]: ideas })}
                        placeholder="Add an idea…" testId={`bfg-additional-${group.key}`} />
                    </div>
                  )}
                </div>
              ))}
              {(section.stages || []).length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <h3 style={{ fontSize: 19 }}>{fill(section.stages_question)}</h3>
                  {section.stages.map((stage) => (
                    <div className="bfg-stage-block" key={stage.key}>
                      <h4>{stage.label}</h4>
                      <p>{stage.description}</p>
                      {section.type === "stages" ? (
                        <IdeaList ideas={Array.isArray(stageResponses[stage.key]) ? stageResponses[stage.key] : []}
                          setIdeas={(ideas) => setStageResponses({ ...stageResponses, [stage.key]: ideas })}
                          placeholder="Add an action…" testId={`bfg-stage-${stage.key}`} />
                      ) : (
                        <textarea value={typeof stageResponses[stage.key] === "string" ? stageResponses[stage.key] : ""}
                          onChange={(event) => setStageResponses({ ...stageResponses, [stage.key]: event.target.value })}
                          data-testid={`bfg-stage-${stage.key}`} />
                      )}
                    </div>
                  ))}
                </div>
              )}
              {section.type === "standard" && (
                <div style={{ marginTop: 26 }}>
                  <p className="bfg-eyebrow">Your Final Ideas</p>
                  {section.final_question && <h3 style={{ fontSize: 18 }}>{fill(section.final_question)}</h3>}
                  <p style={{ fontSize: 14, marginTop: 6 }}>Add or change your ideas now that you have seen what to consider.</p>
                  <IdeaList ideas={finalResponse} setIdeas={setFinalResponse} placeholder="Add an idea…" testId="bfg-final-input" />
                </div>
              )}
            </>
          )}
        </>
      )}

      {error && <p className="bfg-error">{error}</p>}
      {(revealed || section.type === "preferences") && (
        <div className="bfg-form-actions">
          <span />
          <button className="bfg-btn bfg-btn-primary" onClick={complete} disabled={busy} data-testid="bfg-complete-section-btn">
            {busy ? "Saving…" : section.complete_label}
          </button>
        </div>
      )}
    </div>
  );
};

export default function GamePlayPage() {
  const { token } = useParams();
  const [context, setContext] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [view, setView] = useState("welcome");
  const [sectionId, setSectionId] = useState(1);
  const [completedCount, setCompletedCount] = useState(0);

  const load = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/game/play/${token}`);
      setContext(response.data);
      const progress = response.data.progress || {};
      setCompletedCount(Object.values(progress).filter((item) => item.completed).length);
    } catch { setNotFound(true); }
  }, [token]);

  useEffect(() => { document.title = "Board Fundraising Game"; load(); }, [load]);

  const firstIncomplete = useMemo(() => {
    if (!context) return 1;
    for (let id = 1; id <= TOTAL; id += 1) {
      if (!context.progress?.[String(id)]?.completed) return id;
    }
    return TOTAL;
  }, [context]);

  if (notFound) {
    return (
      <div className="bfg" style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
        <div className="bfg-card" style={{ maxWidth: 420, textAlign: "center" }} data-testid="bfg-play-invalid">
          <h2>This Game Link Is Not Valid</h2>
          <p style={{ marginTop: 10 }}>Please use the link from your invitation email, or ask your organisation to send it again.</p>
        </div>
      </div>
    );
  }
  if (!context) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const section = context.sections.find((item) => item.id === sectionId);
  const completedSections = context.sections.filter((item) => context.progress?.[String(item.id)]?.completed);
  const night = context.game_night;

  const onCompleted = async (count) => {
    setCompletedCount(count);
    await load();
    setView(count >= TOTAL && sectionId === TOTAL ? "finished" : "section-done");
    window.scrollTo({ top: 0 });
  };

  const startSection = (id) => { setSectionId(id); setView("section"); window.scrollTo({ top: 0 }); };

  return (
    <div className="bfg" style={{ minHeight: "100vh" }}>
      <header className="bfg-nav">
        <span className="bfg-logo">
          <span className="bfg-logo-mark">BG</span>
          <span><strong>Nonprofit Board Builder</strong><em>Board Fundraising Game</em></span>
        </span>
      </header>
      <main className="bfg-play" data-testid="bfg-play-page">
        {view !== "welcome" && view !== "finished" && (
          <>
            <div className="bfg-play-progressbar"><span style={{ width: `${(completedCount / TOTAL) * 100}%` }} /></div>
            <p className="bfg-play-progress-label" data-testid="bfg-play-progress">{completedCount} of {TOTAL} Strategy Sections Completed</p>
          </>
        )}

        {view === "welcome" && (
          <div className="bfg-card" data-testid="bfg-play-welcome">
            <p className="bfg-eyebrow">Board Fundraising Game</p>
            <h1>Welcome, {context.first_name}</h1>
            <p style={{ marginTop: 14 }}>
              {context.organization_name} is working to raise {context.goal_display}{context.deadline_display ? ` by ${context.deadline_display}` : ""}.
              {" "}Before your board meets for Game Night, you are going to help build the fundraising strategy that can make that goal possible.
            </p>
            <p style={{ marginTop: 14 }}>
              You do not need to be a fundraising expert.
              {" "}The game will walk you through how a complete fundraising strategy is built, one section at a time. You will share what you already know, learn how to think about each part of the strategy and then add any new ideas that come to mind.
            </p>
            <p style={{ marginTop: 14 }}>
              Complete one section before leaving the game. Once a section is finished, your progress will be saved and you can return through this same link at any time.
            </p>
            <div className="bfg-play-progressbar"><span style={{ width: `${(completedCount / TOTAL) * 100}%` }} /></div>
            <p className="bfg-play-progress-label" data-testid="bfg-welcome-progress">{completedCount} of {TOTAL} Strategy Sections Completed</p>
            <div style={{ marginTop: 22 }}>
              <button className="bfg-btn bfg-btn-primary" style={{ width: "100%" }} onClick={() => startSection(firstIncomplete)} data-testid="bfg-start-game-btn">
                {completedCount > 0 ? "Continue My Game" : "Start My Game"}
              </button>
            </div>
            {completedSections.length > 0 && completedCount < TOTAL && (
              <div style={{ marginTop: 22 }}>
                <p className="bfg-eyebrow">Review My Previous Sections</p>
                <div className="bfg-review-list">
                  {completedSections.map((item) => (
                    <button key={item.id} onClick={() => startSection(item.id)} data-testid={`bfg-review-section-${item.id}`}>
                      <span>{item.id}. {fillText(item.title, context)}</span><span>✓</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {completedCount >= TOTAL && (
              <button className="bfg-btn bfg-btn-ghost" style={{ width: "100%", marginTop: 12 }} onClick={() => setView("finished")} data-testid="bfg-view-completion-btn">
                View My Completion Summary
              </button>
            )}
          </div>
        )}

        {view === "section" && section && (
          <SectionPlayer section={section} context={context} token={token} onCompleted={onCompleted} />
        )}

        {view === "section-done" && (
          <div className="bfg-card bfg-section-done" data-testid="bfg-section-complete">
            <h2>Section Complete</h2>
            <p style={{ marginTop: 12 }}>{completedCount} of {TOTAL} Strategy Sections Completed</p>
            <div style={{ marginTop: 22, display: "grid", gap: 10 }}>
              <button className="bfg-btn bfg-btn-primary" onClick={() => startSection(firstIncomplete)} data-testid="bfg-next-section-btn">
                Continue To Next Section
              </button>
              <button className="bfg-btn bfg-btn-ghost" onClick={() => { setView("welcome"); window.scrollTo({ top: 0 }); }} data-testid="bfg-back-to-welcome-btn">
                Save & Return Later
              </button>
            </div>
          </div>
        )}

        {view === "finished" && (
          <div className="bfg-card" data-testid="bfg-play-finished">
            <p className="bfg-eyebrow">Individual Game Complete</p>
            <h1>You're Ready For Game Night</h1>
            <p style={{ marginTop: 14 }}>Thank you, {context.first_name}.</p>
            <p style={{ marginTop: 12 }}>
              You have helped {context.organization_name} think through who can fund the mission, where to find them, how to attract them, the process required to raise money, the technology, team and materials needed to execute, and the role you would personally like to play.
            </p>
            <p style={{ marginTop: 12 }}>
              Your ideas will now become part of the Board Fundraising Game your board plays together during your next meeting.
            </p>
            <div className="bfg-play-progressbar"><span style={{ width: "100%" }} /></div>
            <p className="bfg-play-progress-label">{TOTAL} of {TOTAL} Strategy Sections Completed</p>
            {night && (night.date_display || night.time_display) && (
              <div className="bfg-night-summary" style={{ marginTop: 18 }}>
                {night.date_display && <div className="bfg-summary-row"><span>Game Night</span><strong>{night.date_display}</strong></div>}
                {night.time_display && <div className="bfg-summary-row"><span>Time</span><strong>{night.time_display}</strong></div>}
              </div>
            )}
            <p style={{ marginTop: 18 }}>
              Come ready to review the ideas contributed by your board, identify your strongest fundraising priorities and build your organisation's fundraising strategy together.
            </p>
            <button className="bfg-btn bfg-btn-ghost" style={{ marginTop: 18 }} onClick={() => setView("welcome")} data-testid="bfg-finished-review-btn">
              Review My Previous Sections
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
