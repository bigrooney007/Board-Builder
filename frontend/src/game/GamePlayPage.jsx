import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TOTAL = 10;

const norm = (t) => String(t).toLowerCase().replace(/[^\w\s]/g, "").replace(/\s+/g, " ").trim();
const dedupe = (items) => {
  const seen = new Set(); const out = [];
  items.forEach((item) => { const k = norm(item); if (k && !seen.has(k)) { seen.add(k); out.push(String(item).trim()); } });
  return out;
};

const AddList = ({ items, setItems, placeholder, addLabel, testId }) => {
  const [text, setText] = useState("");
  const add = () => { if (text.trim()) { setItems([...items, text.trim()]); setText(""); } };
  return (
    <div className="bfg-ig-add" data-testid={testId}>
      <div className="bfg-ig-row">
        <input value={text} placeholder={placeholder || ""} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} data-testid={`${testId}-input`} />
        <button type="button" className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={add} data-testid={`${testId}-btn`}>{addLabel || "Add Idea"}</button>
      </div>
      <div className="bfg-ig-chips">
        {items.map((item, i) => (
          <span className="bfg-ig-chip" key={i}>{item}
            <button type="button" onClick={() => setItems(items.filter((_, x) => x !== i))} aria-label="Remove">×</button>
          </span>
        ))}
      </div>
    </div>
  );
};

const Cards = ({ items, numbered }) => (
  <div className="bfg-ig-cards">
    {(items || []).map((card, i) => (
      <div className="bfg-ig-card" key={i}>
        <strong>{numbered ? `${i + 1}. ` : ""}{card.text}</strong>
        {card.hint && <p>{card.hint}</p>}
      </div>
    ))}
  </div>
);

export default function GamePlayPage() {
  const { token } = useParams();
  const [ctx, setCtx] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [view, setView] = useState("welcome");
  const [sectionId, setSectionId] = useState(1);
  const [step, setStep] = useState(0);
  const [resp, setResp] = useState(null);
  const [audiences, setAudiences] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [firstText, setFirstText] = useState("");

  useEffect(() => { document.title = "Board Fundraising Game"; }, []);

  const load = useCallback(async () => {
    try { setCtx((await axios.get(`${API}/game/play/${token}`)).data); } catch { setNotFound(true); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const sections = ctx?.sections || [];
  const progress = ctx?.progress || {};
  const completedCount = Object.values(progress).filter((p) => p.completed).length;
  const fill = useCallback((text) => String(text || "")
    .replaceAll("{organisation}", ctx?.organization_name || "your organisation")
    .replaceAll("{goal}", ctx?.goal_display || "its fundraising goal")
    .replaceAll("{deadline}", ctx?.deadline_display || "its deadline"), [ctx]);

  const section = sections.find((s) => s.id === sectionId);

  const openSection = async (id) => {
    setError("");
    try {
      const data = (await axios.get(`${API}/game/play/${token}/section/${id}`)).data.response || {};
      const sec = sections.find((s) => s.id === id);
      const stageState = {};
      (sec.stages || []).forEach((st) => { const v = data.stage_responses?.[st.key]; stageState[st.key] = Array.isArray(v) ? v : v ? [v] : []; });
      setResp({
        first: data.first_response || [], locked: Boolean(data.first_move_locked),
        guided: data.guided_selections || {}, final: data.final_response || [],
        stages: stageState, prefs: data.preferences || [], doNotWant: data.do_not_want || [],
        extras: data.extras || {},
      });
      setFirstText((data.first_response || [])[0] || "");
      if (id === 2 || id === 3) {
        const s1 = (await axios.get(`${API}/game/play/${token}/section/1`)).data.response || {};
        setAudiences(s1.group_game_ideas || []);
      }
      setSectionId(id); setStep(0); setView("section");
      window.scrollTo({ top: 0 });
    } catch { setError("We could not load this section. Please try again."); }
  };

  const buildPayload = (r, sec) => {
    let gg = [];
    if (sec.type === "discover") gg = dedupe([...(r.first || []), ...Object.values(r.guided).flat(), ...(r.final || [])]);
    if (sec.type === "journey" || sec.type === "stages") {
      gg = [];
      (sec.stages || []).forEach((st) => (r.stages[st.key] || []).forEach((a) => gg.push(`${st.label}: ${a}`)));
      gg = dedupe(gg);
    }
    return {
      first_response: r.first, first_move_locked: r.locked,
      guided_selections: r.guided, additional_ideas: {}, stage_responses: r.stages,
      final_response: r.final, preferences: r.prefs, do_not_want: r.doNotWant,
      group_game_ideas: gg, extras: r.extras,
    };
  };

  const save = async (r, complete) => {
    setSaving(true); setError("");
    try {
      const url = `${API}/game/play/${token}/section/${sectionId}${complete ? "/complete" : ""}`;
      await axios[complete ? "post" : "put"](url, buildPayload(r, section));
      if (complete) { await load(); setView("done"); window.scrollTo({ top: 0 }); }
      setSaving(false);
      return true;
    } catch { setError("We could not save. Please try again."); setSaving(false); return false; }
  };

  if (notFound) return <div className="bfg" style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}><div className="bfg-card"><h2>This game link is not valid</h2><p style={{ marginTop: 10 }}>Please ask your organisation to resend your invitation.</p></div></div>;
  if (!ctx) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const Header = () => (
    <header className="bfg-ig-head" data-testid="bfg-ig-header">
      <p className="bfg-eyebrow" style={{ margin: 0 }}>Board Fundraising Game</p>
      <strong>{ctx.organization_name}</strong>
      {view === "section" && (
        <>
          <span className="bfg-ig-count">Section {sectionId} of {TOTAL}</span>
          <div className="bfg-ig-bar"><span style={{ width: `${(completedCount / TOTAL) * 100}%` }} /></div>
        </>
      )}
    </header>
  );

  // ---------- Welcome / Progress / Done ----------
  if (view === "welcome") {
    const started = completedCount > 0 || Object.values(progress).some((p) => p.first_move_locked);
    return (
      <div className="bfg bfg-ig"><Header />
        <main className="bfg-flow" data-testid="bfg-ig-welcome">
          <div className="bfg-card">
            <h1>Welcome To Your Board Fundraising Game</h1>
            <p style={{ marginTop: 14 }}>{ctx.organization_name} wants to raise {ctx.goal_display}{ctx.deadline_display ? ` by ${ctx.deadline_display}` : ""}.</p>
            <p style={{ marginTop: 10 }}>Before your board meets for Game Night, you are going to build your own version of the fundraising strategy you believe can help your organisation reach that goal.</p>
            <h2 style={{ marginTop: 22 }}>You Do Not Need To Be A Fundraising Expert</h2>
            <p style={{ marginTop: 10 }}>The game will teach you how a complete fundraising strategy is built while helping you contribute the knowledge, relationships and ideas you already have.</p>
            <p style={{ marginTop: 10 }}>In each section, we will ask what you think first. Then we will show you how fundraisers think about that part of the strategy and give you another opportunity to add to your ideas.</p>
            <p style={{ marginTop: 10 }}>Your board will bring everyone's ideas together during Game Night and decide what should become part of the organisation's fundraising strategy.</p>
            <div className="bfg-ig-card" style={{ marginTop: 18 }}>
              <strong>10 Strategy Sections</strong>
              <p>Complete one section at a time. Your progress is saved after every completed section.</p>
            </div>
            <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20, width: "100%" }}
              onClick={() => started ? setView("progress") : openSection(1)} data-testid="bfg-ig-start-btn">
              {started ? "Continue My Game" : "Start My Game"}
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (view === "progress" || view === "done") {
    const allDone = completedCount >= TOTAL;
    const nextId = sections.find((s) => !progress[String(s.id)]?.completed)?.id;
    return (
      <div className="bfg bfg-ig"><Header />
        <main className="bfg-flow" data-testid={view === "done" ? "bfg-ig-section-done" : "bfg-ig-progress"}>
          <div className="bfg-card">
            {view === "done" && !allDone && (<><h1>Section Complete</h1><p style={{ marginTop: 8 }}>{completedCount} of {TOTAL} sections completed</p></>)}
            {view === "done" && allDone && (
              <div data-testid="bfg-ig-game-complete">
                <h1>You're Ready For Game Night</h1>
                <p style={{ marginTop: 12 }}>Thank you, {ctx.first_name}.</p>
                <p style={{ marginTop: 8 }}>You have now built your own view of how {ctx.organization_name} can work toward its {ctx.goal_display} fundraising goal.</p>
                <p style={{ marginTop: 8 }}>You identified who could fund the mission, where to find them, how to attract them, the process required to raise money, the technology, team and materials needed to execute, and what the execution timeline could look like.</p>
                <p style={{ marginTop: 8 }}>You also told us how you want to help build the fundraising system and how you want to participate in raising money.</p>
                <h2 style={{ marginTop: 18 }}>What Happens Next?</h2>
                <p style={{ marginTop: 8 }}>During Game Night, your board will see the ideas contributed by everyone, prioritise the strongest ones and use those decisions to build the organisation's fundraising strategy.</p>
                <p style={{ marginTop: 12, fontWeight: 700 }}>10 of 10 Sections Completed</p>
                {ctx.game_night?.date_display && <p style={{ marginTop: 8 }}>Game Night: {ctx.game_night.date_display}{ctx.game_night.time_display ? ` · Time: ${ctx.game_night.time_display}` : ""}</p>}
                <p style={{ marginTop: 8 }}>Come ready to think, decide and build the strategy together.</p>
              </div>
            )}
            {view === "progress" && (<><h1>Your Game Progress</h1><p style={{ marginTop: 8 }}>{completedCount} of {TOTAL} Sections Completed</p></>)}
            <div style={{ marginTop: 18 }}>
              {sections.map((s) => {
                const done = progress[String(s.id)]?.completed;
                return (
                  <div className="bfg-ig-progressrow" key={s.id} data-testid={`bfg-ig-prow-${s.id}`}>
                    <span>{done ? "✓" : `${s.id}.`} {fill(s.title)}</span>
                    {done ? (
                      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => openSection(s.id)} data-testid={`bfg-ig-review-${s.id}`}>Review</button>
                    ) : s.id === nextId ? (
                      <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => openSection(s.id)} data-testid={`bfg-ig-continue-${s.id}`}>Continue</button>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {view === "done" && !allDone && nextId && (
              <div className="bfg-form-actions">
                <button className="bfg-btn bfg-btn-ghost" onClick={() => setView("progress")} data-testid="bfg-ig-save-exit-btn">Save & Exit</button>
                <button className="bfg-btn bfg-btn-primary" onClick={() => openSection(nextId)} data-testid="bfg-ig-next-section-btn">Continue To Next Section</button>
              </div>
            )}
            {error && <p className="bfg-error">{error}</p>}
          </div>
        </main>
      </div>
    );
  }

  // ---------- Section player ----------
  if (!section || !resp) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const steps = (() => {
    if (section.type === "preferences") return section.key === "direct_fundraising"
      ? ["situation", "choose", "details", "exclude", "review"] : ["situation", "choose", "details", "review"];
    const base = ["situation", "first", "wisdom"];
    if (section.stages?.length) return [...base, ...section.stages.map((s) => `stage:${s.key}`), "final"];
    const mid = section.groups.map((g) => `group:${g.key}`);
    if (section.extra === "connect_audiences") mid.push("connect");
    if (section.extra === "material_status") mid.push("status");
    return [...base, ...mid, "final"];
  })();
  const stepKey = steps[step];
  const next = () => { setStep(Math.min(step + 1, steps.length - 1)); window.scrollTo({ top: 0 }); };
  const setR = (patch) => setResp((r) => ({ ...r, ...patch }));
  const setExtra = (key, value) => setR({ extras: { ...resp.extras, [key]: value } });
  const context = ctx.situation_context?.[section.situation_context] || [];

  const complete = async () => { await save(resp, true); };
  const saveExit = async () => { const ok = await save(resp, false); if (ok) setView("progress"); };

  const body = () => {
    if (stepKey === "situation") return (
      <>
        <h1>{fill(section.title)}</h1>
        <p style={{ marginTop: 14, whiteSpace: "pre-line" }}>{fill(section.scenario)}</p>
        <button className="bfg-btn bfg-btn-primary bfg-ig-cta" onClick={next} data-testid="bfg-ig-situation-next">
          {section.type === "preferences" ? section.situation_button : "Make My First Move"}
        </button>
      </>
    );
    if (stepKey === "first") {
      const textMode = section.first_mode === "text";
      return (
        <>
          <p className="bfg-eyebrow">Your First Move</p>
          <h1>{fill(section.first_move_heading || section.first_move_question)}</h1>
          {section.first_move_heading && <p style={{ marginTop: 10 }}>{fill(section.first_move_question)}</p>}
          {section.first_move_support && <p className="bfg-note" style={{ marginTop: 8 }}>{fill(section.first_move_support)}</p>}
          {context.length > 0 && (
            <div className="bfg-ig-card" style={{ marginTop: 14 }} data-testid="bfg-ig-context">
              <strong>{section.context_heading}</strong>
              {context.map((line, i) => <p key={i}>{line}</p>)}
            </div>
          )}
          {textMode ? (
            <label className="bfg-field"><span> </span>
              <textarea rows={6} value={firstText} disabled={resp.locked} onChange={(e) => setFirstText(e.target.value)} data-testid="bfg-ig-first-text" />
            </label>
          ) : (
            resp.locked
              ? <div className="bfg-ig-chips" style={{ marginTop: 14 }}>{resp.first.map((t, i) => <span className="bfg-ig-chip locked" key={i}>{t}</span>)}</div>
              : <AddList items={resp.first} setItems={(v) => setR({ first: v })} placeholder={section.first_placeholder} addLabel={section.first_add_label} testId="bfg-ig-first" />
          )}
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" data-testid="bfg-ig-lock-btn"
            onClick={() => {
              if (!resp.locked) setResp((r) => ({ ...r, first: textMode ? (firstText.trim() ? [firstText.trim()] : []) : r.first, locked: true }));
              next();
            }}>
            {resp.locked ? "Continue" : section.first_lock_label || "Lock In My First Ideas"}
          </button>
        </>
      );
    }
    if (stepKey === "wisdom") return (
      <>
        <p className="bfg-eyebrow">Fundraising Wisdom</p>
        <h1>Fundraising Wisdom</h1>
        <p style={{ marginTop: 14, whiteSpace: "pre-line" }}>{fill(section.wisdom)}</p>
        <button className="bfg-btn bfg-btn-primary bfg-ig-cta" onClick={next} data-testid="bfg-ig-wisdom-next">{section.wisdom_button || "Think Deeper"}</button>
      </>
    );
    if (stepKey.startsWith("group:")) {
      const group = section.groups.find((g) => `group:${g.key}` === stepKey);
      const items = resp.guided[group.key] || [];
      const setItems = (v) => setR({ guided: { ...resp.guided, [group.key]: v } });
      return (
        <>
          <h1>{fill(group.heading)}</h1>
          {group.support && <p className="bfg-note" style={{ marginTop: 8 }}>{group.support}</p>}
          {group.kind === "select" ? (
            <div className="bfg-ig-cards">
              {group.items.map((card, i) => {
                const on = items.includes(card.text);
                return (
                  <button type="button" key={i} className={`bfg-ig-card selectable ${on ? "on" : ""}`}
                    onClick={() => setItems(on ? items.filter((t) => t !== card.text) : [...items, card.text])}
                    data-testid={`bfg-ig-select-${i}`}>
                    <strong>{card.text}</strong>
                  </button>
                );
              })}
            </div>
          ) : (
            <Cards items={group.items} numbered={section.id === 1} />
          )}
          <h2 style={{ marginTop: 24 }}>{fill(group.ask)}</h2>
          {group.ask_support && <p className="bfg-note" style={{ marginTop: 6 }}>{group.ask_support}</p>}
          <AddList items={group.kind === "select" ? items.filter((t) => !group.items.some((c) => c.text === t)) : items}
            setItems={(v) => group.kind === "select" ? setItems([...items.filter((t) => group.items.some((c) => c.text === t)), ...v]) : setItems(v)}
            placeholder={group.placeholder} addLabel={group.add_label} testId={`bfg-ig-group-${group.key}`} />
          {section.extra === "audience_tags" && items.length > 0 && audiences.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <p className="bfg-note">Optionally tag which audiences an idea would work especially well for:</p>
              {items.map((idea) => (
                <div className="bfg-ig-card" key={idea}>
                  <strong>{idea}</strong>
                  <div className="bfg-ig-chips">
                    {audiences.map((aud) => {
                      const tags = resp.extras.idea_audiences?.[idea] || [];
                      const on = tags.includes(aud);
                      return <button type="button" key={aud} className={`bfg-ig-tag ${on ? "on" : ""}`}
                        onClick={() => setExtra("idea_audiences", { ...(resp.extras.idea_audiences || {}), [idea]: on ? tags.filter((t) => t !== aud) : [...tags, aud] })}>{aud}</button>;
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
          {section.extra === "role_fillers" && items.length > 0 && (
            <div style={{ marginTop: 16 }}>
              {items.map((role) => (
                <div className="bfg-ig-progressrow" key={role}>
                  <span>{role}</span>
                  <select value={resp.extras.role_fillers?.[role] || ""}
                    onChange={(e) => setExtra("role_fillers", { ...(resp.extras.role_fillers || {}), [role]: e.target.value })}>
                    <option value="">{section.filler_question}</option>
                    {section.filler_options.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
              ))}
            </div>
          )}
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" onClick={next} data-testid="bfg-ig-group-next">{group.next_label || "Continue"}</button>
        </>
      );
    }
    if (stepKey === "connect") {
      const places = dedupe([...(resp.first || []), ...(resp.guided.places || [])]);
      return (
        <>
          <h1>{section.connect_heading}</h1>
          <p className="bfg-note" style={{ marginTop: 8 }}>{section.connect_support}</p>
          {audiences.map((aud) => {
            const chosen = resp.extras.audience_places?.[aud] || [];
            return (
              <div className="bfg-ig-card" key={aud}>
                <strong>{aud}</strong>
                <div className="bfg-ig-chips">
                  {places.map((place) => {
                    const on = chosen.includes(place);
                    return <button type="button" key={place} className={`bfg-ig-tag ${on ? "on" : ""}`}
                      onClick={() => setExtra("audience_places", { ...(resp.extras.audience_places || {}), [aud]: on ? chosen.filter((p) => p !== place) : [...chosen, place] })}>{place}</button>;
                  })}
                </div>
              </div>
            );
          })}
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" onClick={next} data-testid="bfg-ig-connect-next">Continue</button>
        </>
      );
    }
    if (stepKey === "status") {
      const all = dedupe([...(resp.first || []), ...(resp.guided.materials || []), ...(resp.final || [])]);
      const existing = context.map((line) => norm(line));
      return (
        <>
          <h1>{section.status_heading}</h1>
          {all.map((mat) => (
            <div className="bfg-ig-progressrow" key={mat}>
              <span>{mat}</span>
              <select value={resp.extras.material_status?.[mat] || (existing.some((e) => e.includes(norm(mat)) || norm(mat).includes(e)) ? "" : "Need To Create")}
                onChange={(e) => setExtra("material_status", { ...(resp.extras.material_status || {}), [mat]: e.target.value })}>
                <option value="">Choose…</option>
                {section.status_options.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          ))}
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" onClick={next} data-testid="bfg-ig-status-next">Continue</button>
        </>
      );
    }
    if (stepKey.startsWith("stage:")) {
      const stage = section.stages.find((s) => `stage:${s.key}` === stepKey);
      const items = resp.stages[stage.key] || [];
      const timed = Boolean(section.timing_options);
      return (
        <>
          <p className="bfg-eyebrow">{stage.number}. {stage.label}</p>
          <h1>{stage.label}</h1>
          <p style={{ marginTop: 10 }}>{fill(stage.description)}</p>
          <h2 style={{ marginTop: 16 }}>{fill(stage.ask)}</h2>
          {stage.prompt && <p className="bfg-note" style={{ marginTop: 6 }}>{fill(stage.prompt)}</p>}
          <AddList items={items} setItems={(v) => setR({ stages: { ...resp.stages, [stage.key]: v } })}
            placeholder="Add an action" addLabel="Add Action" testId={`bfg-ig-stage-${stage.key}`} />
          {timed && items.length > 0 && items.map((action) => (
            <div className="bfg-ig-progressrow" key={action}>
              <span>{action}</span>
              <select value={resp.extras.action_timing?.[`${stage.key}|${action}`] || ""}
                onChange={(e) => setExtra("action_timing", { ...(resp.extras.action_timing || {}), [`${stage.key}|${action}`]: e.target.value })}>
                <option value="">{section.timing_question}</option>
                {section.timing_options.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          ))}
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" onClick={next} data-testid="bfg-ig-stage-next">Continue</button>
        </>
      );
    }
    if (stepKey === "final") {
      if (section.stages?.length) return (
        <>
          <h1>{section.final_heading}</h1>
          {section.stages.map((stage) => (
            <div className="bfg-ig-card" key={stage.key}>
              <strong>{stage.label}</strong>
              <AddList items={resp.stages[stage.key] || []} setItems={(v) => setR({ stages: { ...resp.stages, [stage.key]: v } })}
                placeholder="Add an action" addLabel="Add" testId={`bfg-ig-final-${stage.key}`} />
            </div>
          ))}
          {error && <p className="bfg-error">{error}</p>}
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" disabled={saving} onClick={complete} data-testid="bfg-ig-complete-btn">{section.complete_label}</button>
        </>
      );
      return (
        <>
          <h1>Your Final Ideas</h1>
          <div className="bfg-ig-card"><strong>You First Thought Of</strong>
            <div className="bfg-ig-chips">{resp.first.map((t, i) => <span className="bfg-ig-chip locked" key={i}>{t}</span>)}</div>
          </div>
          {section.groups.map((group) => (resp.guided[group.key] || []).length > 0 && (
            <div className="bfg-ig-card" key={group.key}><strong>After Thinking Deeper — {group.heading}</strong>
              <div className="bfg-ig-chips">{resp.guided[group.key].map((t, i) => <span className="bfg-ig-chip" key={i}>{t}</span>)}</div>
            </div>
          ))}
          {section.final_question && (
            <>
              <h2 style={{ marginTop: 20 }}>{section.final_heading || "Anything Else?"}</h2>
              <p style={{ marginTop: 6 }}>{fill(section.final_question)}</p>
            </>
          )}
          <AddList items={resp.final} setItems={(v) => setR({ final: v })} placeholder="Add another idea" addLabel="Add Idea" testId="bfg-ig-final" />
          {error && <p className="bfg-error">{error}</p>}
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" disabled={saving} onClick={complete} data-testid="bfg-ig-complete-btn">{section.complete_label}</button>
        </>
      );
    }
    // preferences steps
    const selected = resp.prefs.map((p) => p.option);
    const allOptions = section.groups.flatMap((g) => g.items.map((c) => c.text));
    if (stepKey === "choose") return (
      <>
        <h1>{section.choose_heading}</h1>
        <p className="bfg-note" style={{ marginTop: 8 }}>{section.choose_support}</p>
        {section.groups.map((group) => (
          <div key={group.key} style={{ marginTop: 18 }}>
            <p className="bfg-eyebrow">{group.heading}</p>
            <div className="bfg-ig-cards">
              {group.items.map((card) => {
                const on = selected.includes(card.text);
                return <button type="button" key={card.text} className={`bfg-ig-card selectable ${on ? "on" : ""}`}
                  onClick={() => setR({ prefs: on ? resp.prefs.filter((p) => p.option !== card.text) : [...resp.prefs, { option: card.text, note: "", involvement: "" }] })}
                  data-testid={`bfg-ig-pref-${norm(card.text).replace(/ /g, "-")}`}>
                  <strong>{card.text}</strong>
                </button>;
              })}
            </div>
          </div>
        ))}
        <button className="bfg-btn bfg-btn-primary bfg-ig-cta" disabled={resp.prefs.length === 0} onClick={next} data-testid="bfg-ig-choose-next">Continue</button>
      </>
    );
    if (stepKey === "details") return (
      <>
        <h1>{section.involvement_question ? "How Do You Want To Participate?" : "Tell Us More"}</h1>
        {resp.prefs.map((pref, i) => (
          <div className="bfg-ig-card" key={pref.option}>
            <strong>{pref.option}</strong>
            {section.involvement_options && (
              <select value={pref.involvement} style={{ marginTop: 10 }}
                onChange={(e) => setR({ prefs: resp.prefs.map((p, x) => x === i ? { ...p, involvement: e.target.value } : p) })}>
                <option value="">{section.involvement_question}</option>
                {section.involvement_options.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            )}
            <textarea rows={2} placeholder={section.note_question} value={pref.note} style={{ marginTop: 10 }}
              onChange={(e) => setR({ prefs: resp.prefs.map((p, x) => x === i ? { ...p, note: e.target.value } : p) })} />
          </div>
        ))}
        <button className="bfg-btn bfg-btn-primary bfg-ig-cta" onClick={next} data-testid="bfg-ig-details-next">Continue</button>
      </>
    );
    if (stepKey === "exclude") {
      const noneLabel = section.do_not_want_none;
      const toggle = (label) => {
        if (label === noneLabel) { setR({ doNotWant: resp.doNotWant.includes(noneLabel) ? [] : [noneLabel] }); return; }
        const cleared = resp.doNotWant.filter((t) => t !== noneLabel);
        setR({ doNotWant: cleared.includes(label) ? cleared.filter((t) => t !== label) : [...cleared, label] });
      };
      return (
        <>
          <h1>{section.do_not_want_heading}</h1>
          <p className="bfg-note" style={{ marginTop: 8 }}>{section.do_not_want_support}</p>
          <div className="bfg-ig-cards">
            {[...allOptions.filter((o) => o !== "Other"), noneLabel].map((label) => {
              const on = resp.doNotWant.includes(label);
              return <button type="button" key={label} className={`bfg-ig-card selectable ${on ? "on" : ""}`} onClick={() => toggle(label)}
                data-testid={`bfg-ig-dnw-${norm(label).replace(/ /g, "-")}`}><strong>{label}</strong></button>;
            })}
          </div>
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" onClick={next} data-testid="bfg-ig-exclude-next">Continue</button>
        </>
      );
    }
    if (stepKey === "review") {
      const exclusions = resp.doNotWant.filter((t) => t !== section.do_not_want_none);
      return (
        <>
          <h1>{section.review_heading}</h1>
          {resp.prefs.map((pref, i) => (
            <div className="bfg-ig-card" key={pref.option}>
              <div className="bfg-panel-head"><strong>{pref.option}</strong>
                <button type="button" className="bfg-btn bfg-btn-ghost bfg-btn-sm"
                  onClick={() => setR({ prefs: resp.prefs.filter((_, x) => x !== i) })}>Remove</button>
              </div>
              {pref.involvement && <p>{pref.involvement}</p>}
              {pref.note && <p className="bfg-note">{pref.note}</p>}
            </div>
          ))}
          {section.custom_question && (
            <>
              <h2 style={{ marginTop: 18 }}>{section.custom_question}</h2>
              <AddList items={resp.prefs.filter((p) => !allOptions.includes(p.option)).map((p) => p.option)}
                setItems={(v) => setR({ prefs: [...resp.prefs.filter((p) => allOptions.includes(p.option)), ...v.map((t) => ({ option: t, note: "", involvement: "" }))] })}
                placeholder="Another way you would like to help" addLabel="Add" testId="bfg-ig-custom" />
            </>
          )}
          {exclusions.length > 0 && (
            <div className="bfg-ig-card"><strong>Activities You Prefer Not To Do</strong>
              <div className="bfg-ig-chips">{exclusions.map((t) => <span className="bfg-ig-chip" key={t}>{t}</span>)}</div>
            </div>
          )}
          {error && <p className="bfg-error">{error}</p>}
          <button className="bfg-btn bfg-btn-primary bfg-ig-cta" disabled={saving} onClick={complete} data-testid="bfg-ig-complete-btn">{section.complete_label}</button>
        </>
      );
    }
    return null;
  };

  return (
    <div className="bfg bfg-ig"><Header />
      <main className="bfg-flow" data-testid="bfg-ig-section">
        <div className="bfg-card">
          {body()}
          <div className="bfg-form-actions">
            {step > 0 && <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => { setStep(step - 1); window.scrollTo({ top: 0 }); }} data-testid="bfg-ig-back-btn">Back</button>}
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={saving} onClick={saveExit} data-testid="bfg-ig-exit-btn">Save & Exit</button>
          </div>
        </div>
      </main>
    </div>
  );
}
