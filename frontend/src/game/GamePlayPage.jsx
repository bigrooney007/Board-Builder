import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { FineTuneReview } from "./FineTuneReview";
import "./game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const speakText = (text) => {
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
};

const AudioControls = ({ text }) => (
  <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 10 }} className="bfg-no-print">
    <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => speakText(text)} data-testid="bfg-play-audio">Play Audio</button>
    <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => window.speechSynthesis.pause()} data-testid="bfg-pause-audio">Pause</button>
    <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => speakText(text)} data-testid="bfg-replay-audio">Replay</button>
  </div>
);

const useVoice = () => {
  const recRef = useRef(null);
  const [listening, setListening] = useState(false);
  const start = (onText) => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.continuous = false; rec.interimResults = false; rec.lang = "en-US";
    rec.onresult = (event) => onText(event.results[0][0].transcript);
    rec.onend = () => setListening(false);
    recRef.current = rec; setListening(true); rec.start();
  };
  const supported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  return { start, listening, supported };
};

const VoiceArea = ({ label, value, onChange, testId }) => {
  const { start, listening, supported } = useVoice();
  return (
    <label className="bfg-field" data-testid={testId}>
      <span>{label}</span>
      <textarea rows={4} value={value} onChange={(event) => onChange(event.target.value)} data-testid={`${testId}-input`} />
      {supported && (
        <button type="button" className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 6 }}
          onClick={() => start((text) => onChange(`${value ? value + " " : ""}${text}`))} data-testid={`${testId}-voice`}>
          {listening ? "Listening…" : "Speak My Answer"}
        </button>
      )}
    </label>
  );
};

const ItemList = ({ label, addLabel, items, setItems, testId }) => {
  const { start, listening, supported } = useVoice();
  return (
    <div style={{ marginTop: 14, textAlign: "left" }} data-testid={testId}>
      <p style={{ fontWeight: 700 }}>{label}</p>
      {items.map((item, index) => (
        <div key={index} style={{ display: "flex", gap: 6, marginTop: 6 }}>
          <input className="bfg-item-input" style={{ flex: 1, border: "1px solid #d1d5db", borderRadius: 8, padding: "8px 10px" }}
            value={item} onChange={(event) => setItems(items.map((v, i) => i === index ? event.target.value : v))}
            data-testid={`${testId}-item-${index}`} />
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setItems(items.filter((_, i) => i !== index))}>✕</button>
        </div>
      ))}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setItems([...items, ""])} data-testid={`${testId}-add`}>{addLabel}</button>
        {supported && (
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => start((text) => setItems([...items, text]))}>
            {listening ? "Listening…" : "Speak My Answer"}
          </button>
        )}
      </div>
    </div>
  );
};

const Paras = ({ text }) => String(text || "").split("\n").filter((line) => line.trim()).map((line, i) => <p key={i} style={{ marginTop: 10 }}>{line}</p>);

export default function GamePlayPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [ctx, setCtx] = useState(null);
  const [phase, setPhase] = useState("intro");
  const [roundIndex, setRoundIndex] = useState(0);
  const [ftArea, setFtArea] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [state, setState] = useState({});

  useEffect(() => { document.title = "Play | Board Fundraising Game"; }, []);

  const load = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/game/play/${token}`);
      const context = response.data;
      const sections = {};
      for (const id of [1, 2, 3, 4, 5]) {
        const sec = await axios.get(`${API}/game/play/${token}/section/${id}`);
        sections[id] = sec.data.response || {};
      }
      setCtx({ ...context, saved: sections });
      const firstIncomplete = [1, 2, 3, 4].find((id) => !sections[id]?.completed);
      const isPrimary = context.member?.is_primary;
      const ftPending = [1, 2, 3, 4].find((id) => !sections[id]?.fine_tuning?.completed);
      if (!firstIncomplete) {
        if (isPrimary) {
          if (context.paid) { navigate("/game/setup", { replace: true }); return; }
          setPhase("ready");
        } else if (context.paid && ftPending) {
          setFtArea(ftPending); setPhase("finetune");
        } else if (sections[5]?.completed) setPhase("board_done");
        else setPhase("participation");
      } else if (firstIncomplete > 1 || sections[1]?.first_response?.length) {
        setPhase("round"); setRoundIndex(firstIncomplete - 1);
      }
      const s1 = sections[1]?.extras || {};
      setState({
        approved: { 1: sections[1]?.approved_entries || [], 2: sections[2]?.approved_entries || [], 3: sections[3]?.approved_entries || [], 4: sections[4]?.approved_entries || [] },
        first: { 1: (sections[1]?.first_response || [])[0] || "", 2: (sections[2]?.first_response || [])[0] || "", 3: (sections[3]?.first_response || [])[0] || "", 4: (sections[4]?.first_response || [])[0] || "" },
        people: s1.people || [], businesses: s1.businesses || [], grantors: s1.grantors || [],
        places: sections[2]?.extras?.places || {}, ideas: sections[3]?.extras?.ideas || {},
        process: (sections[4]?.final_response || [])[0] || "", byAudience: sections[4]?.extras?.by_audience || {},
        build: sections[5]?.extras?.build || [], buildOther: sections[5]?.extras?.build_other || "",
        raise: sections[5]?.extras?.raise || [], raiseOther: sections[5]?.extras?.raise_other || "",
        time: sections[5]?.extras?.time || "",
      });
    } catch { setError("This game link is not valid."); }
  }, [token, navigate]);
  useEffect(() => { load(); }, [load]);

  if (error) return <div className="bfg" style={{ minHeight: "100vh", padding: 40, textAlign: "center" }}><p>{error}</p></div>;
  if (!ctx) return <div className="bfg" style={{ minHeight: "100vh" }} />;
  const v3 = ctx.v3;
  const isPrimary = ctx.member?.is_primary;
  const set = (patch) => setState((current) => ({ ...current, ...patch }));
  const audiences = [
    ...state.people.filter(Boolean).map((name) => ({ name, type: "person" })),
    ...state.businesses.filter(Boolean).map((name) => ({ name, type: "business" })),
    ...state.grantors.filter(Boolean).map((name) => ({ name, type: "grantor" })),
  ];
  const exampleAudience = audiences[0]?.name || "one of your audiences";

  const completeRound = async (id, payload) => {
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/game/play/${token}/section/${id}/complete`, payload);
      if (id < 4) { setRoundIndex(id); window.scrollTo({ top: 0 }); }
      else if (id === 4) {
        if (isPrimary) {
          if (ctx.paid) { navigate("/game/setup", { replace: true }); return; }
          setPhase("ready");
        } else if (ctx.paid) { setFtArea(1); setPhase("finetune"); }
        else setPhase("participation");
        window.scrollTo({ top: 0 });
      }
      else { setPhase("ministrategy"); window.scrollTo({ top: 0 }); }
    } catch { setError("We could not save your answers. Please try again."); }
    setBusy(false);
  };

  const roundPayload = (id) => {
    const base = { first_response: [state.first[id] || ""], first_move_locked: true, guided_selections: {}, additional_ideas: {}, stage_responses: {}, preferences: [], do_not_want: [], group_game_ideas: [] };
    if (id === 1) return { ...base, final_response: [...state.people, ...state.businesses, ...state.grantors].filter(Boolean), extras: { people: state.people.filter(Boolean), businesses: state.businesses.filter(Boolean), grantors: state.grantors.filter(Boolean) } };
    if (id === 2) return { ...base, final_response: audiences.flatMap((a) => (state.places[a.name] || []).filter(Boolean).map((p) => `${a.name} — ${p}`)), extras: { places: state.places } };
    if (id === 3) return { ...base, final_response: audiences.flatMap((a) => (state.ideas[a.name] || []).filter(Boolean).map((p) => `${a.name} — ${p}`)), extras: { ideas: state.ideas } };
    return { ...base, final_response: [state.process, ...Object.entries(state.byAudience).map(([a, v]) => v ? `${a} — ${v}` : "")].filter(Boolean), extras: { by_audience: state.byAudience } };
  };

  const shell = (children) => (
    <div className="bfg" style={{ minHeight: "100vh" }}>
      <main style={{ maxWidth: 760, margin: "0 auto", padding: "30px 20px 80px", textAlign: "center" }} data-testid="bfg-play-v3">
        {children}
      </main>
    </div>
  );

  if (phase === "intro") {
    const audioText = [...v3.intro.paragraphs, v3.intro.strategy_heading, v3.intro.completion_text].join(" ");
    return shell(<>
      <h1>{v3.intro.heading}</h1>
      {v3.intro.paragraphs.map((p, i) => <p key={i} style={{ marginTop: 14 }}>{p}</p>)}
      <h2 style={{ marginTop: 18 }}>{v3.intro.strategy_heading}</h2>
      <p style={{ marginTop: 12 }}>{v3.intro.completion_text}</p>
      <div className="bfg-goal-highlight" style={{ maxWidth: 420, margin: "20px auto 0" }}>
        <span>{v3.intro.goal_label}</span><strong>{ctx.goal_display}</strong>
        {ctx.deadline_display && <span>By {ctx.deadline_display}</span>}
      </div>
      <AudioControls text={audioText} />
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} onClick={() => setPhase("round")} data-testid="bfg-v3-get-started">{v3.intro.cta}</button>
    </>);
  }

  if (phase === "ready") {
    const r = v3.strategy_ready;
    return shell(<>
      <h1 data-testid="bfg-strategy-ready-heading">{r.heading}</h1>
      <p style={{ marginTop: 14, fontWeight: 700 }}>{r.completed_intro}</p>
      {r.completed_areas.map((a) => <p key={a} style={{ marginTop: 8 }}><span style={{ color: "#059669", fontWeight: 700 }}>✓</span> {a}</p>)}
      <h2 style={{ marginTop: 24 }}>{r.imagine_heading}</h2>
      <p style={{ marginTop: 12, fontWeight: 600 }}>{r.more_people_statement}</p>
      <div style={{ marginTop: 20 }}>
        {r.locked_sections.map((s) => (
          <div className="bfg-card" key={s} style={{ marginTop: 10, textAlign: "center", padding: 16 }}>🔒 {s}</div>
        ))}
      </div>
      <h2 style={{ marginTop: 24 }}>{r.upgrade_heading}</h2>
      <p style={{ marginTop: 12 }}>{r.upgrade_supporting}</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} onClick={() => navigate("/game/upgrade")} data-testid="bfg-v3-unlock-cta">{r.upgrade_cta}</button>
    </>);
  }

  if (phase === "finetune") {
    const ft = v3.fine_tuning;
    return shell(<>
      <p className="bfg-eyebrow">STRATEGIC AREA {ftArea} OF 4</p>
      <h1 data-testid="bfg-finetune-heading">{ft.heading}</h1>
      <p style={{ marginTop: 12 }}>{ft.supporting}</p>
      <FineTuneReview token={token} sectionId={ftArea} copy={ft} areaTitle={(ft.area_titles || [])[ftArea - 1]}
        onDone={(entries) => {
          set({ approved: { ...(state.approved || {}), [ftArea]: entries } });
          if (ftArea < 4) setFtArea(ftArea + 1); else setPhase("participation");
          window.scrollTo({ top: 0 });
        }} />
    </>);
  }

  if (phase === "ministrategy") {
    const ms = v3.mini_strategy;
    const ap = state.approved || {};
    const fromApproved = (sectionId) => (ap[sectionId] || []).map((entry) => entry.text).filter(Boolean);
    const a1 = ap[1] || [];
    const typed = (audienceType) => a1.filter((entry) => entry.audience_type === audienceType).map((entry) => entry.text);
    const individuals = a1.length ? typed("individual") : state.people.filter(Boolean);
    const businessesList = a1.length ? typed("business") : state.businesses.filter(Boolean);
    const grantorsList = a1.length ? typed("grantor") : state.grantors.filter(Boolean);
    const find = ap[2]?.length ? fromApproved(2) : audiences.flatMap((a) => (state.places[a.name] || []).filter(Boolean).map((p) => `${a.name} — ${p}`));
    const attract = ap[3]?.length ? fromApproved(3) : audiences.flatMap((a) => (state.ideas[a.name] || []).filter(Boolean).map((p) => `${a.name} — ${p}`));
    const processList = ap[4]?.length ? fromApproved(4) : [state.process, ...Object.entries(state.byAudience).map(([a, v]) => v ? `${a} — ${v}` : "")].filter(Boolean);
    const List = ({ items, testId }) => items.length
      ? <ul style={{ marginTop: 8, paddingLeft: 20, textAlign: "left" }} data-testid={testId}>{items.map((item, i) => <li key={i} style={{ marginTop: 6 }}>{item}</li>)}</ul>
      : <p style={{ marginTop: 8, fontSize: 14, color: "#6B7280" }}>No ideas added for this area.</p>;
    const Section = ({ heading, children }) => (
      <div className="bfg-card" style={{ marginTop: 16, padding: 18, textAlign: "left" }}>
        <h3>{heading}</h3>
        {children}
      </div>
    );
    return shell(<>
      <h1 data-testid="bfg-ministrategy-heading">{ms.heading}</h1>
      <p style={{ marginTop: 12 }}>{String(ms.supporting || "").split("{organization}").join(ctx.organization_name || "your organization")}</p>
      <Section heading={ms.people_heading}>
        <p style={{ fontWeight: 700, marginTop: 8, textAlign: "left" }}>{ms.individuals_label}</p><List items={individuals} testId="bfg-ms-individuals" />
        <p style={{ fontWeight: 700, marginTop: 12, textAlign: "left" }}>{ms.businesses_label}</p><List items={businessesList} testId="bfg-ms-businesses" />
        <p style={{ fontWeight: 700, marginTop: 12, textAlign: "left" }}>{ms.grantors_label}</p><List items={grantorsList} testId="bfg-ms-grantors" />
      </Section>
      <Section heading={ms.find_heading}><List items={find} testId="bfg-ms-find" /></Section>
      <Section heading={ms.attract_heading}><List items={attract} testId="bfg-ms-attract" /></Section>
      <Section heading={ms.process_heading}><List items={processList} testId="bfg-ms-process" /></Section>
      <Section heading={ms.build_heading}><List items={[...state.build.filter((option) => option !== "Other"), state.buildOther].filter(Boolean)} testId="bfg-ms-build" /></Section>
      <Section heading={ms.raise_heading}><List items={[...state.raise.filter((option) => option !== "Other"), state.raiseOther].filter(Boolean)} testId="bfg-ms-raise" /></Section>
      <Section heading={ms.time_heading}><p style={{ marginTop: 8, fontWeight: 600, textAlign: "left" }}>{state.time || "Not specified"}</p></Section>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} onClick={() => { setPhase("board_done"); window.scrollTo({ top: 0 }); }} data-testid="bfg-ministrategy-continue">{ms.continue_button}</button>
    </>);
  }

  if (phase === "board_done") {
    const b = v3.board_completion;
    return shell(<>
      <h1 data-testid="bfg-board-done-heading">{b.heading}</h1>
      <p style={{ marginTop: 12 }}>{b.supporting}</p>
      <p style={{ marginTop: 14, fontWeight: 600 }}>{b.more_people_statement}</p>
      <p style={{ marginTop: 14 }}>{b.game_night_text}</p>
      {ctx.game_night?.date_display && (
        <p style={{ marginTop: 14, fontWeight: 700 }}>Game Night: {ctx.game_night.date_display}{ctx.game_night.time_display ? ` at ${ctx.game_night.time_display}` : ""}</p>
      )}
      <button className="bfg-btn bfg-btn-ghost" style={{ marginTop: 20 }} onClick={() => { setPhase("ministrategy"); window.scrollTo({ top: 0 }); }} data-testid="bfg-view-ministrategy-btn">
        View My Personal Fundraising Strategy
      </button>
    </>);
  }

  if (phase === "participation") {
    const p = v3.participation;
    const toggle = (listKey, option) => set({ [listKey]: state[listKey].includes(option) ? state[listKey].filter((o) => o !== option) : [...state[listKey], option] });
    const checkList = (question, options, listKey, otherKey, otherPrompt, testId) => (
      <div style={{ marginTop: 24, textAlign: "left" }}>
        <h3>{question}</h3>
        {options.map((option) => (
          <label key={option} className="bfg-ht-check" data-testid={`${testId}-${option.slice(0, 20).replace(/\s+/g, "-").toLowerCase()}`}>
            <input type="checkbox" checked={state[listKey].includes(option)} onChange={() => toggle(listKey, option)} /><span>{option}</span>
          </label>
        ))}
        {state[listKey].includes("Other") && (
          <VoiceArea label={otherPrompt} value={state[otherKey]} onChange={(value) => set({ [otherKey]: value })} testId={`${testId}-other`} />
        )}
      </div>
    );
    return shell(<>
      <h1>{p.heading}</h1>
      {checkList(p.build_question, p.build_options, "build", "buildOther", p.build_other_prompt, "bfg-v3-build")}
      {checkList(p.raise_question, p.raise_options, "raise", "raiseOther", p.raise_other_prompt, "bfg-v3-raise")}
      <div style={{ marginTop: 24, textAlign: "left" }}>
        <h3>{p.time_question}</h3>
        {p.time_options.map((option) => (
          <label key={option} className="bfg-ht-check"><input type="radio" name="time" checked={state.time === option} onChange={() => set({ time: option })} /><span>{option}</span></label>
        ))}
      </div>
      {error && <p className="bfg-error">{error}</p>}
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} disabled={busy}
        onClick={() => completeRound(5, { first_response: [], final_response: [], first_move_locked: true, guided_selections: {}, additional_ideas: {}, stage_responses: {}, preferences: [], do_not_want: [], group_game_ideas: [], extras: { build: state.build, build_other: state.buildOther, raise: state.raise, raise_other: state.raiseOther, time: state.time } })}
        data-testid="bfg-v3-participation-submit">
        {busy ? "Saving…" : "Complete My Fundraising Game"}
      </button>
    </>);
  }

  const round = v3.rounds[roundIndex];
  const id = roundIndex + 1;
  const perAudience = (mapKey, promptFor, inputLabel, addLabel) => (
    <div style={{ marginTop: 16, textAlign: "left" }}>
      {audiences.map((a) => (
        <div className="bfg-card" key={a.name} style={{ marginTop: 12, padding: 16 }}>
          <h4>{a.name}</h4>
          <p style={{ marginTop: 6, fontSize: 14 }}>{promptFor(a)}</p>
          <ItemList label={inputLabel} addLabel={addLabel}
            items={state[mapKey][a.name] || [""]}
            setItems={(items) => set({ [mapKey]: { ...state[mapKey], [a.name]: items } })}
            testId={`bfg-v3-${mapKey}-${a.name.slice(0, 16).replace(/\s+/g, "-").toLowerCase()}`} />
        </div>
      ))}
    </div>
  );

  const canContinue = id === 1
    ? [...state.people, ...state.businesses, ...state.grantors].some((v) => v.trim())
    : id === 2 ? Object.values(state.places).some((list) => (list || []).some((v) => v.trim()))
    : id === 3 ? Object.values(state.ideas).some((list) => (list || []).some((v) => v.trim()))
    : !!state.process.trim();

  return shell(<>
    <p className="bfg-eyebrow">{round.label}</p>
    <h1>{round.heading}</h1>
    <Paras text={round.teaching} />
    <AudioControls text={round.teaching.replace(/\n/g, " ")} />

    <div style={{ marginTop: 24, textAlign: "left" }}>
      <VoiceArea label={`${round.first_label} — ${round.first_question}`} value={state.first[id] || ""}
        onChange={(value) => set({ first: { ...state.first, [id]: value } })} testId={`bfg-v3-first-${id}`} />
    </div>

    {id === 1 && round.guides.map((guide) => (
      <div className="bfg-card" key={guide.heading} style={{ marginTop: 16, textAlign: "left", padding: 18 }}>
        <h3>{guide.heading}</h3>
        <AudioControls text={`${guide.heading}. ${guide.items.join(" ")} ${guide.note}`} />
        <ul style={{ marginTop: 8, paddingLeft: 20 }}>{guide.items.map((item) => <li key={item} style={{ marginTop: 6 }}>{item}</li>)}</ul>
        <p style={{ marginTop: 10, fontWeight: 600 }}>{guide.note}</p>
      </div>
    ))}
    {id === 1 && (
      <div style={{ marginTop: 20, textAlign: "left" }}>
        <h3>{round.final_label}</h3>
        <p style={{ marginTop: 6 }}>{round.final_question}</p>
        <ItemList label="People" addLabel="+ Add A Type Of Person" items={state.people.length ? state.people : [""]} setItems={(items) => set({ people: items })} testId="bfg-v3-people" />
        <ItemList label="Businesses" addLabel="+ Add A Type Of Business" items={state.businesses.length ? state.businesses : [""]} setItems={(items) => set({ businesses: items })} testId="bfg-v3-businesses" />
        <ItemList label="Grantors" addLabel="+ Add A Type Of Grantor" items={state.grantors.length ? state.grantors : [""]} setItems={(items) => set({ grantors: items })} testId="bfg-v3-grantors" />
      </div>
    )}

    {id === 2 && (<>
      {perAudience("places", (a) => a.type === "person" ? `Where Does ${a.name} Congregate? ${round.person_prompt}` : a.type === "business" ? `Where Can You Consistently Find ${a.name}? ${round.business_prompt}` : `Where Can You Consistently Find ${a.name}? ${round.grantor_prompt}`, round.final_input_label, "+ Add Another Place")}
      <p style={{ marginTop: 14, fontWeight: 600 }}>{round.teaching_note}</p>
    </>)}

    {id === 3 && (<>
      <div className="bfg-card" style={{ marginTop: 16, padding: 18 }}>
        <h3>For Example</h3>
        <p style={{ marginTop: 8 }}>{round.example_text.split("[AUDIENCE NAME]").join(exampleAudience)}</p>
        <ul style={{ marginTop: 10, paddingLeft: 20, textAlign: "left" }}>{round.examples.map((example) => <li key={example} style={{ marginTop: 4 }}>{example}</li>)}</ul>
        <Paras text={round.teaching_note} />
      </div>
      {perAudience("ideas", () => round.final_input_label, round.final_input_label, "+ Add Another Idea")}
    </>)}

    {id === 4 && (<>
      <div className="bfg-card" style={{ marginTop: 16, padding: 18, textAlign: "left" }}>
        <h3 style={{ textAlign: "center" }}>{round.process_heading}</h3>
        <p style={{ textAlign: "center", fontWeight: 800, marginTop: 8 }}>{round.process_line}</p>
        {round.process_steps.map((step) => (
          <div key={step.key} style={{ marginTop: 12 }}><strong>{step.key}</strong><p style={{ marginTop: 4 }}>{step.text}</p></div>
        ))}
        <h4 style={{ marginTop: 16 }}>Example</h4>
        <Paras text={round.example_text.split("[AUDIENCE NAME]").join(exampleAudience)} />
        <p style={{ marginTop: 12, fontWeight: 600 }}>{round.teaching_note}</p>
      </div>
      <div style={{ marginTop: 18, textAlign: "left" }}>
        <h3>{round.final_label}</h3>
        <VoiceArea label={round.final_question} value={state.process} onChange={(value) => set({ process: value })} testId="bfg-v3-process" />
        {audiences.map((a) => (
          <VoiceArea key={a.name} label={`Optional ideas for ${a.name}`} value={state.byAudience[a.name] || ""}
            onChange={(value) => set({ byAudience: { ...state.byAudience, [a.name]: value } })}
            testId={`bfg-v3-process-${a.name.slice(0, 16).replace(/\s+/g, "-").toLowerCase()}`} />
        ))}
      </div>
    </>)}

    {error && <p className="bfg-error">{error}</p>}
    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy || !canContinue}
      onClick={() => completeRound(id, roundPayload(id))} data-testid={`bfg-v3-round-${id}-continue`}>
      {busy ? "Saving…" : round.cta}
    </button>
  </>);
}
