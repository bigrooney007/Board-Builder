import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { FineTuneReview } from "./FineTuneReview";
import { NarrationControl, isNarrationMuted, wasClipPlayed, markClipPlayed } from "./NarrationControl";
import { SpeakButton } from "./SpeakButton";
import { useWakeLock } from "./useWakeLock";
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
  const reviewMode = new URLSearchParams(useLocation().search).get("review") === "1";
  const [ctx, setCtx] = useState(null);
  const [phase, setPhase] = useState("loading");
  useWakeLock(["welcome", "section", "direction", "participation", "ministrategy"].includes(phase));
  const [sec, setSec] = useState(1);
  const [stage, setStage] = useState("first");
  const [pIdx, setPIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [state, setState] = useState({
    firsts: { 1: "", 2: "", 3: "", 4: "" }, seconds: { 1: "", 2: "", 3: "", 4: "" },
    approved: { 1: [], 2: [], 3: [], 4: [] }, displays: { 1: "", 2: "", 3: "", 4: "" },
    raise: [], raiseOther: "", time: "", additional: "",
  });
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);
  const set = (patch) => setState((current) => ({ ...current, ...patch }));

  const playClip = useCallback((id, force = false) => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    const clip = clips[id];
    if (!clip?.ready) return;
    const playedKey = `${id}:${clip.url}`;
    if (isNarrationMuted() || (!force && wasClipPlayed(playedKey))) return;
    const audio = new Audio(`${BASE}${clip.url}`);
    audioRef.current = audio;
    audio.play().then(() => markClipPlayed(playedKey)).catch(() => {});
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
        raise: sections[5].extras?.raise || [], raiseOther: sections[5].extras?.raise_other || "",
        time: sections[5].extras?.time || "", additional: sections[5].extras?.additional_idea || "",
      });
      if (reviewMode && context.member?.is_primary && context.paid) {
        setSec(1);
        setStage("first");
        setPhase("section");
        return;
      }
      const freshGame = !sections[1].first_move_locked && !(sections[1].first_response || []).length && !sections[1].completed;
      if (freshGame) {
        setSec(1); setStage("first"); setPhase("welcome"); return;
      }
      for (let id = 1; id <= 4; id += 1) {
        const doc = sections[id];
        if (!doc.fine_tuning?.completed) {
          setSec(id);
          setStage(doc.completed ? "finetune" : "first");
          setPhase("section");
          return;
        }
      }
      if (context.member?.is_primary) {
        if (context.paid) { navigate("/game/setup", { replace: true }); return; }
        navigate("/game/demonstration", { replace: true }); return;
      } else if (sections[5].completed) setPhase("board_done");
      else { setPIdx(0); setPhase("participation"); }
    } catch { setError("This game link is not valid."); setPhase("error"); }
  }, [token, navigate, reviewMode]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { document.title = "Board Fundraising Game"; }, []);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [phase, sec, stage, pIdx]);

  useEffect(() => {
    if (phase === "welcome") {
      const role = ctx?.member?.participant_role || "board_member";
      playClip(ctx?.member?.is_primary ? "lead_opening" : role === "board_member" ? "board_opening" : "");
    }
    else if (phase === "section" && stage === "first") playClip(`a${sec}_deeper`);
    else if (phase === "lead_done") playClip("lead_free_complete");
    else if (phase === "board_done") playClip((ctx?.member?.participant_role || "board_member") === "board_member" ? "board_complete" : "");
    else if (phase === "participation") playClip(["part_raise", "part_time", "part_anything"][pIdx]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, sec, stage, pIdx, clips]);

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
    const text = state.firsts[sec].trim();
    if (!text) return;
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/game/play/${token}/section/${sec}/complete`, {
        ...EMPTY_PAYLOAD,
        first_response: [text],
        first_move_locked: true,
        final_response: [text],
        extras: {},
      });
      setStage("finetune");
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your answer. Please try again.");
    }
    setBusy(false);
  };

  const afterApproval = (entries) => {
    if (audioRef.current) audioRef.current.pause();
    set({ approved: { ...state.approved, [sec]: entries } });
    if (sec < 4) { setSec(sec + 1); setStage("first"); }
    else if (isPrimary) {
      if (ctx.paid) navigate(reviewMode ? "/game/setup?review=1" : "/game/setup", { replace: true });
      else setPhase("lead_done");
    } else setPhase("direction");
  };

  const answerScreen = (question, label, value, onChange, onContinue, testPrefix) => (
    <>
      <h1 style={{ marginTop: 14 }} data-testid={`${testPrefix}-heading`}>{sdef.heading}</h1>
      {label ? <p className="bfg-eyebrow" style={{ marginTop: 16 }}>{label}</p> : null}
      <p style={{ marginTop: 18, fontWeight: 700, fontSize: 18 }} data-testid={`${testPrefix}-question`}>{question}</p>
      <textarea rows={8} style={{ width: "100%", marginTop: 22, padding: 16, border: "1px solid #d1d5db", borderRadius: 12, fontSize: 15, lineHeight: 1.6 }}
        placeholder={g.placeholder || "Type your answer here..."} value={value}
        onChange={(event) => onChange(event.target.value)} data-testid={`${testPrefix}-input`} />
      <div><SpeakButton value={value} onChange={onChange} testId={`${testPrefix}-speak`} /></div>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy || !value.trim()} onClick={onContinue} data-testid={`${testPrefix}-continue`}>
        {busy ? "Saving…" : "Continue"}
      </button>
    </>
  );

  if (phase === "error") return shell(null, "bfg-play-invalid");

  if (phase === "welcome") {
    return shell(<>
      <div style={{ position: "absolute", top: 14, right: 14 }}>
        <NarrationControl audioRef={audioRef} onReplay={() => playClip(isPrimary ? "lead_opening" : (ctx?.member?.participant_role || "board_member") === "board_member" ? "board_opening" : "", true)} />
      </div>
      <h1 style={{ marginTop: 10 }} data-testid="bfg-welcome-heading">WELCOME TO THE BOARD FUNDRAISING GAME</h1>
      {isPrimary ? (
        <p style={{ marginTop: 16, fontSize: 17 }}>Let's build your organization's fundraising strategy.</p>
      ) : (
        <p style={{ marginTop: 16, fontSize: 17 }}>Help {ctx.organization_name || "your organization"} build the fundraising strategy to raise:</p>
      )}
      <div className="bfg-card" style={{ marginTop: 22, padding: 22 }} data-testid="bfg-welcome-goal">
        {isPrimary && <p style={{ fontWeight: 700, letterSpacing: 1, fontSize: 13 }}>HELP {(ctx.organization_name || "YOUR ORGANIZATION").toUpperCase()} RAISE</p>}
        <p style={{ fontFamily: "Outfit", fontWeight: 800, fontSize: 40, color: "#111827", marginTop: 6 }}>{ctx.goal_display || ""}</p>
      </div>
      {!isPrimary && (ctx.member?.participant_role || "board_member") === "board_member" && (
        <p style={{ marginTop: 12, fontSize: 14, color: "#6B7280" }} data-testid="bfg-board-responsibility-note">
          Helping ensure your organization is adequately funded is part of your responsibility as a board member.
        </p>
      )}
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26 }} data-testid="bfg-start-my-game-btn"
        onClick={() => { playClip(isPrimary ? "lead_opening" : (ctx?.member?.participant_role || "board_member") === "board_member" ? "board_opening" : "", true); setStage("first"); setPhase("section"); }}>
        START MY GAME
      </button>
    </>, "bfg-welcome");
  }

  if (phase === "lead_done") {
    return shell(<>
      <div style={{ position: "absolute", top: 14, right: 14 }}><NarrationControl audioRef={audioRef} onReplay={() => playClip("lead_free_complete", true)} /></div>
      <h1 style={{ marginTop: 10 }} data-testid="bfg-lead-done-heading">You Built The Foundation Of Your Fundraising Strategy</h1>
      <p style={{ marginTop: 16 }}>Now, let's bring your board into the game.</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26 }} data-testid="bfg-lead-done-continue"
        onClick={() => { if (audioRef.current) audioRef.current.pause(); navigate("/game/demonstration", { replace: true }); }}>
        CONTINUE
      </button>
    </>, "bfg-lead-done");
  }

  if (phase === "section" && stage === "first") {
    return shell(<>
      <div style={{ position: "absolute", top: 14, right: 14 }}><NarrationControl audioRef={audioRef} onReplay={() => playClip(`a${sec}_deeper`, true)} /></div>
      {answerScreen(sdef.q1, sdef.label1 || "YOUR IDEA", state.firsts[sec],
        (value) => setState((current) => ({ ...current, firsts: { ...current.firsts, [sec]: value } })), saveFirst, `bfg-s${sec}-first`)}
    </>, `bfg-s${sec}-first`);
  }

  if (phase === "section" && stage === "finetune") {
    return shell(<>
      <div style={{ position: "absolute", top: 14, right: 14 }}><NarrationControl audioRef={audioRef} onReplay={() => playClip("approval_review", true)} /></div>
      <h1 style={{ marginTop: 14 }} data-testid="bfg-finetune-heading">{ft.heading}</h1>
      <FineTuneReview token={token} sectionId={sec} copy={{ ...ft, refining: g.refining }}
        onReady={() => playClip("approval_review")} onDone={afterApproval}
        onEdit={(message) => { setError(message || "Edit your answer, then continue."); setStage("first"); }} />
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
          extras: { raise: state.raise, raise_other: state.raiseOther, time: state.time, additional_idea: state.additional || "" },
        });
        setPhase("ministrategy");
      } catch { setError("We could not save your answers. Please try again."); }
      setBusy(false);
    };
    const screens = [
      { heading: ps.raise_heading, body: options(pp.raise_options, "raise", "raiseOther", pp.raise_other_prompt, "bfg-part-raise"),
        can: state.raise.length > 0 && (!state.raise.includes("Other") || Boolean(state.raiseOther.trim())) },
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
          <SpeakButton value={state.additional} onChange={(value) => set({ additional: value })} testId="bfg-part-additional-speak" />
        </div>), can: true },
    ];
    const screen = screens[pIdx];
    const last = pIdx === screens.length - 1;
    return shell(<>
      <div style={{ position: "absolute", top: 14, right: 14 }}><NarrationControl audioRef={audioRef} onReplay={() => playClip(["part_raise", "part_time", "part_anything"][pIdx], true)} /></div>
      <h1 data-testid={`bfg-part-heading-${pIdx}`}>{screen.heading}</h1>
      {screen.body}
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 22 }}>
        {pIdx > 0 && (
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setPIdx(pIdx - 1)} data-testid="bfg-part-back">
            Back
          </button>
        )}
        <button className="bfg-btn bfg-btn-primary" disabled={busy || !screen.can}
          onClick={() => last ? completeGame() : setPIdx(pIdx + 1)} data-testid="bfg-part-continue">
          {busy ? "Saving…" : last ? (ps.complete_button || "COMPLETE MY GAME") : "Continue"}
        </button>
      </div>
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
        <h3>{ms.raise_heading}</h3>
        <p style={{ marginTop: 8 }}>{[...state.raise.filter((option) => option !== "Other"), state.raiseOther].filter(Boolean).join(", ") || "Not specified"}</p>
        <h3 style={{ marginTop: 14 }}>{ms.time_heading}</h3>
        <p style={{ marginTop: 8, fontWeight: 600 }}>{state.time || "Not specified"}</p>
      </div>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} onClick={() => setPhase("board_done")} data-testid="bfg-ministrategy-continue">{ms.continue_button || "Continue"}</button>
    </>, "bfg-ministrategy");
  }

  const b = v3.board_completion || {};
  const nonBoard = (ctx.member?.participant_role || "board_member") !== "board_member";
  return shell(<>
    <h1 data-testid="bfg-board-done-heading">{b.heading}</h1>
    {nonBoard ? (
      <>
        <p style={{ marginTop: 12 }}>Thank you for contributing your ideas.</p>
        <p style={{ marginTop: 10 }}>Your responses will now become part of the fundraising strategy being built for {ctx.organization_name || "your organization"}.</p>
      </>
    ) : (
      <p style={{ marginTop: 12 }}>{b.supporting}</p>
    )}
    {!nonBoard && <p style={{ marginTop: 14, fontWeight: 600 }}>{b.more_people_statement}</p>}
    <p style={{ marginTop: 14 }}>{b.game_night_text}</p>
    {ctx.game_night?.date_display && (
      <p style={{ marginTop: 14, fontWeight: 700 }}>Game Night: {ctx.game_night.date_display}{ctx.game_night.time_display ? ` at ${ctx.game_night.time_display}` : ""}</p>
    )}
    <button className="bfg-btn bfg-btn-ghost" style={{ marginTop: 20 }} onClick={() => setPhase("ministrategy")} data-testid="bfg-view-ministrategy-btn">
      View My Personal Fundraising Strategy
    </button>
  </>, "bfg-board-done");
}
