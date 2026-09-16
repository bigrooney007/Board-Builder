import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { FineTuneReview } from "./FineTuneReview";
import "./game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE = process.env.REACT_APP_BACKEND_URL;
const EMPTY_PAYLOAD = {
  first_response: [], final_response: [], first_move_locked: false, guided_selections: {},
  additional_ideas: {}, stage_responses: {}, preferences: [], do_not_want: [], group_game_ideas: [], extras: {},
};

export default function GamePlayPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [ctx, setCtx] = useState(null);
  const [phase, setPhase] = useState("loading");
  const [sec, setSec] = useState(1);
  const [stage, setStage] = useState("intro");
  const [pIdx, setPIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [state, setState] = useState({
    firsts: { 1: "", 2: "", 3: "", 4: "" }, seconds: { 1: "", 2: "", 3: "", 4: "" },
    approved: { 1: [], 2: [], 3: [], 4: [] }, displays: { 1: "", 2: "", 3: "", 4: "" },
    build: [], buildOther: "", raise: [], raiseOther: "", time: "", additional: "",
  });
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);
  const set = (patch) => setState((current) => ({ ...current, ...patch }));

  const playClip = useCallback((id) => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    const clip = clips[id];
    if (!clip?.ready) return;
    const audio = new Audio(`${BASE}${clip.url}`);
    audioRef.current = audio;
    audio.play().catch(() => {});
  }, [clips]);
  useEffect(() => () => { if (audioRef.current) audioRef.current.pause(); }, []);

  const load = useCallback(async () => {
    try {
      const context = (await axios.get(`${API}/game/play/${token}`)).data;
      const sections = {};
      for (const id of [1, 2, 3, 4, 5]) {
        sections[id] = (await axios.get(`${API}/game/play/${token}/section/${id}`)).data.response || {};
      }
      setCtx(context);
      axios.get(`${API}/game/voice/manifest/${token}`).then((r) => setClips(r.data.clips || {})).catch(() => {});
      const secondOf = (doc) => String(doc.extras?.second_response || (doc.final_response || []).join("\n") || "");
      setState({
        firsts: { 1: (sections[1].first_response || [])[0] || "", 2: (sections[2].first_response || [])[0] || "", 3: (sections[3].first_response || [])[0] || "", 4: (sections[4].first_response || [])[0] || "" },
        seconds: { 1: secondOf(sections[1]), 2: secondOf(sections[2]), 3: secondOf(sections[3]), 4: secondOf(sections[4]) },
        approved: { 1: sections[1].approved_entries || [], 2: sections[2].approved_entries || [], 3: sections[3].approved_entries || [], 4: sections[4].approved_entries || [] },
        displays: { 1: sections[1].approved_display || "", 2: sections[2].approved_display || "", 3: sections[3].approved_display || "", 4: sections[4].approved_display || "" },
        build: sections[5].extras?.build || [], buildOther: sections[5].extras?.build_other || "",
        raise: sections[5].extras?.raise || [], raiseOther: sections[5].extras?.raise_other || "",
        time: sections[5].extras?.time || "", additional: sections[5].extras?.additional_idea || "",
      });
      for (let id = 1; id <= 4; id += 1) {
        const doc = sections[id];
        if (!doc.fine_tuning?.completed) {
          setSec(id);
          setStage(doc.completed ? "finetune" : doc.first_move_locked ? "deeper" : "intro");
          setPhase("section");
          return;
        }
      }
      if (context.member?.is_primary) {
        if (context.paid) { navigate("/game/setup", { replace: true }); return; }
        navigate("/game/upgrade", { replace: true }); return;
      } else if (sections[5].completed) setPhase("board_done");
      else { setPIdx(0); setPhase("participation"); }
    } catch { setError("This game link is not valid."); setPhase("error"); }
  }, [token, navigate]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { document.title = "Board Fundraising Game"; }, []);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [phase, sec, stage, pIdx]);

  useEffect(() => {
    if (phase === "section" && stage === "intro") playClip(`a${sec}_intro`);
    else if (phase === "section" && stage === "deeper") playClip(`a${sec}_deeper`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, sec, stage, clips]);

  if (phase === "loading") return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const v3 = ctx?.v3 || {};
  const g = v3.guided || {};
  const sdef = (g.sections || [])[sec - 1] || {};
  const ft = g.finetune || {};
  const isPrimary = ctx?.member?.is_primary;

  const shell = (children, testId) => (
    <div className="bfg" style={{ minHeight: "100vh" }}>
      <main className="bfg-flow" style={{ maxWidth: 640, margin: "0 auto", padding: "34px 20px 90px", textAlign: "center" }} data-testid={testId || "bfg-play-page"}>
        {phase === "section" && (
          <p className="bfg-eyebrow" data-testid="bfg-play-progress">STRATEGIC AREA {sec} OF 4</p>
        )}
        {children}
        {error && <p className="bfg-error" data-testid="bfg-play-error">{error}</p>}
      </main>
    </div>
  );

  const saveFirst = async () => {
    if (!state.firsts[sec].trim()) return;
    setBusy(true); setError("");
    try {
      await axios.put(`${API}/game/play/${token}/section/${sec}`, {
        ...EMPTY_PAYLOAD, first_response: [state.firsts[sec].trim()], first_move_locked: true,
      });
      setStage("deeper");
    } catch { setError("We could not save your answer. Please try again."); }
    setBusy(false);
  };

  const saveSecond = async () => {
    const text = state.seconds[sec].trim();
    if (!text) return;
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/game/play/${token}/section/${sec}/complete`, {
        ...EMPTY_PAYLOAD, first_response: [state.firsts[sec].trim()].filter(Boolean), first_move_locked: true,
        final_response: [text], extras: { second_response: text },
      });
      setStage("finetune");
    } catch { setError("We could not save your answer. Please try again."); }
    setBusy(false);
  };

  const afterApproval = (entries) => {
    if (audioRef.current) audioRef.current.pause();
    set({ approved: { ...state.approved, [sec]: entries } });
    if (sec < 4) { setSec(sec + 1); setStage("intro"); }
    else if (isPrimary) navigate(ctx.paid ? "/game/setup" : "/game/upgrade", { replace: true });
    else setPhase("direction");
  };

  const answerScreen = (question, label, value, onChange, onContinue, testPrefix) => (
    <>
      {label ? <p className="bfg-eyebrow" style={{ marginTop: 22 }}>{label}</p> : null}
      {!label && <h1 style={{ marginTop: 14 }} data-testid={`${testPrefix}-heading`}>{sdef.heading}</h1>}
      <p style={{ marginTop: 18, fontWeight: 700, fontSize: 18 }} data-testid={`${testPrefix}-question`}>{question}</p>
      <textarea rows={8} style={{ width: "100%", marginTop: 22, padding: 16, border: "1px solid #d1d5db", borderRadius: 12, fontSize: 15, lineHeight: 1.6 }}
        placeholder={g.placeholder || "Type your answer here..."} value={value}
        onChange={(event) => onChange(event.target.value)} data-testid={`${testPrefix}-input`} />
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy || !value.trim()} onClick={onContinue} data-testid={`${testPrefix}-continue`}>
        {busy ? "Saving…" : "Continue"}
      </button>
    </>
  );

  if (phase === "error") return shell(null, "bfg-play-invalid");

  if (phase === "section" && stage === "intro") {
    return shell(answerScreen(sdef.q1, "", state.firsts[sec],
      (value) => setState((c) => ({ ...c, firsts: { ...c.firsts, [sec]: value } })), saveFirst, `bfg-s${sec}-first`), `bfg-s${sec}-intro`);
  }

  if (phase === "section" && stage === "deeper") {
    return shell(answerScreen(sdef.q2, g.label_deeper || "THINK A LITTLE DEEPER", state.seconds[sec],
      (value) => setState((c) => ({ ...c, seconds: { ...c.seconds, [sec]: value } })), saveSecond, `bfg-s${sec}-second`), `bfg-s${sec}-deeper`);
  }

  if (phase === "section" && stage === "finetune") {
    return shell(<>
      <h1 style={{ marginTop: 14 }} data-testid="bfg-finetune-heading">{ft.heading}</h1>
      <FineTuneReview token={token} sectionId={sec} copy={{ ...ft, refining: g.refining }}
        onReady={() => playClip("approval_review")} onDone={afterApproval} />
    </>, `bfg-s${sec}-finetune`);
  }

  if (phase === "direction") {
    const d = g.direction || {};
    return shell(<>
      <h1 data-testid="bfg-direction-heading">{d.heading}</h1>
      {(d.lines || []).map((line, i) => <p key={i} style={{ marginTop: i === 0 ? 18 : 8, fontWeight: i === 0 ? 400 : 600 }}>{line}</p>)}
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26 }} data-testid="bfg-direction-continue"
        onClick={() => { if (isPrimary) { if (ctx.paid) navigate("/game/setup", { replace: true }); else setPhase("ready"); } else { setPIdx(0); setPhase("participation"); } }}>
        {d.cta || "CONTINUE"}
      </button>
    </>, "bfg-direction");
  }

  if (phase === "ready") {
    const r = v3.strategy_ready || {};
    return shell(<>
      <h1 data-testid="bfg-strategy-ready-heading">{r.heading}</h1>
      <p style={{ marginTop: 14 }}>{r.completed_intro}</p>
      <div style={{ maxWidth: 520, margin: "14px auto 0", textAlign: "left" }}>
        {(r.completed_areas || []).map((area, i) => <p key={i} style={{ marginTop: 8 }}>✓ {area}</p>)}
      </div>
      <h2 style={{ marginTop: 22 }}>{r.imagine_heading}</h2>
      <p style={{ marginTop: 10, fontWeight: 600 }}>{r.more_people_statement}</p>
      <div className="bfg-card" style={{ marginTop: 18, padding: 18, textAlign: "left" }}>
        {(r.locked_sections || []).map((line, i) => <p key={i} style={{ marginTop: 8 }}>🔒 {line}</p>)}
      </div>
      <h2 style={{ marginTop: 22 }}>{r.upgrade_heading}</h2>
      <p style={{ marginTop: 10 }}>{r.upgrade_supporting}</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} onClick={() => navigate("/game/upgrade")} data-testid="bfg-ready-upgrade-btn">{r.upgrade_cta}</button>
    </>, "bfg-ready");
  }

  if (phase === "participation") {
    const pp = v3.participation || {};
    const ps = g.participation_screens || {};
    const toggle = (listKey, option) => setState((c) => ({
      ...c, [listKey]: c[listKey].includes(option) ? c[listKey].filter((item) => item !== option) : [...c[listKey], option],
    }));
    const options = (list, listKey, otherKey, otherPrompt, testId) => (
      <div style={{ marginTop: 16, textAlign: "left" }}>
        {(list || []).map((option) => (
          <label key={option} className="bfg-ht-check" data-testid={`${testId}-${option.slice(0, 18).replace(/\s+/g, "-").toLowerCase()}`}>
            <input type="checkbox" checked={state[listKey].includes(option)} onChange={() => toggle(listKey, option)} /><span>{option}</span>
          </label>
        ))}
        {state[listKey].includes("Other") && (
          <label className="bfg-field"><span>{otherPrompt}</span>
            <textarea rows={3} value={state[otherKey]} onChange={(event) => set({ [otherKey]: event.target.value })} data-testid={`${testId}-other-input`} />
          </label>
        )}
      </div>
    );
    const completeGame = async () => {
      setBusy(true); setError("");
      try {
        await axios.post(`${API}/game/play/${token}/section/5/complete`, {
          ...EMPTY_PAYLOAD, first_move_locked: true,
          extras: { build: state.build, build_other: state.buildOther, raise: state.raise, raise_other: state.raiseOther, time: state.time, additional_idea: state.additional || "" },
        });
        setPhase("ministrategy");
      } catch { setError("We could not save your answers. Please try again."); }
      setBusy(false);
    };
    const screens = [
      { heading: ps.build_heading, body: options(pp.build_options, "build", "buildOther", pp.build_other_prompt, "bfg-part-build"), can: true },
      { heading: ps.raise_heading, body: options(pp.raise_options, "raise", "raiseOther", pp.raise_other_prompt, "bfg-part-raise"), can: true },
      { heading: ps.time_heading, body: (
        <div style={{ marginTop: 16, textAlign: "left" }}>
          {(pp.time_options || []).map((option) => (
            <label key={option} className="bfg-ht-check"><input type="radio" name="bfg-time" checked={state.time === option} onChange={() => set({ time: option })} /><span>{option}</span></label>
          ))}
        </div>), can: !!state.time },
      { heading: ps.share_heading, body: (
        <div style={{ marginTop: 16 }}>
          <p style={{ fontSize: 14 }}>{ps.share_supporting}</p>
          <textarea rows={5} style={{ width: "100%", marginTop: 12, padding: 14, border: "1px solid #d1d5db", borderRadius: 12 }}
            placeholder={g.placeholder || "Type your answer here..."} value={state.additional}
            onChange={(event) => set({ additional: event.target.value })} data-testid="bfg-part-additional-input" />
        </div>), can: true },
    ];
    const screen = screens[pIdx];
    const last = pIdx === screens.length - 1;
    return shell(<>
      <h1 data-testid={`bfg-part-heading-${pIdx}`}>{screen.heading}</h1>
      {screen.body}
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy || !screen.can}
        onClick={() => last ? completeGame() : setPIdx(pIdx + 1)} data-testid="bfg-part-continue">
        {busy ? "Saving…" : last ? (ps.complete_button || "COMPLETE MY GAME") : "Continue"}
      </button>
    </>, `bfg-participation-${pIdx}`);
  }

  if (phase === "ministrategy") {
    const ms = v3.mini_strategy || {};
    const ap = state.approved;
    const displayFor = (id) => state.displays[id] || (ap[id] || []).map((entry) => entry.text).join("\n");
    const Section = ({ heading, id }) => (
      <div className="bfg-card" style={{ marginTop: 16, padding: 18, textAlign: "left" }}>
        <h3>{heading}</h3>
        <p style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{displayFor(id) || "No ideas added for this area."}</p>
      </div>
    );
    return shell(<>
      <h1 data-testid="bfg-ministrategy-heading">{ms.heading}</h1>
      <p style={{ marginTop: 12 }}>{String(ms.supporting || "").split("{organization}").join(ctx.organization_name || "your organization")}</p>
      <Section heading={ms.people_heading} id={1} />
      <Section heading={ms.find_heading} id={2} />
      <Section heading={ms.attract_heading} id={3} />
      <Section heading={ms.process_heading} id={4} />
      <div className="bfg-card" style={{ marginTop: 16, padding: 18, textAlign: "left" }}>
        <h3>{ms.build_heading}</h3>
        <p style={{ marginTop: 8 }}>{[...state.build.filter((option) => option !== "Other"), state.buildOther].filter(Boolean).join(", ") || "Not specified"}</p>
        <h3 style={{ marginTop: 14 }}>{ms.raise_heading}</h3>
        <p style={{ marginTop: 8 }}>{[...state.raise.filter((option) => option !== "Other"), state.raiseOther].filter(Boolean).join(", ") || "Not specified"}</p>
        <h3 style={{ marginTop: 14 }}>{ms.time_heading}</h3>
        <p style={{ marginTop: 8, fontWeight: 600 }}>{state.time || "Not specified"}</p>
      </div>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} onClick={() => setPhase("board_done")} data-testid="bfg-ministrategy-continue">{ms.continue_button || "Continue"}</button>
    </>, "bfg-ministrategy");
  }

  const b = v3.board_completion || {};
  return shell(<>
    <h1 data-testid="bfg-board-done-heading">{b.heading}</h1>
    <p style={{ marginTop: 12 }}>{b.supporting}</p>
    <p style={{ marginTop: 14, fontWeight: 600 }}>{b.more_people_statement}</p>
    <p style={{ marginTop: 14 }}>{b.game_night_text}</p>
    {ctx.game_night?.date_display && (
      <p style={{ marginTop: 14, fontWeight: 700 }}>Game Night: {ctx.game_night.date_display}{ctx.game_night.time_display ? ` at ${ctx.game_night.time_display}` : ""}</p>
    )}
    <button className="bfg-btn bfg-btn-ghost" style={{ marginTop: 20 }} onClick={() => setPhase("ministrategy")} data-testid="bfg-view-ministrategy-btn">
      View My Personal Fundraising Strategy
    </button>
  </>, "bfg-board-done");
}
