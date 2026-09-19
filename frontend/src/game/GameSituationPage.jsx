import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { NarrationControl, isNarrationMuted, wasClipPlayed, markClipPlayed } from "./NarrationControl";
import { FineTuneReview } from "./FineTuneReview";
import { SpeakButton } from "./SpeakButton";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function GameSituationPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [phase, setPhase] = useState("loading");
  const [token, setToken] = useState("");
  const [ctx, setCtx] = useState(null);
  const [ftArea, setFtArea] = useState(1);
  const [reality, setReality] = useState({});
  const [part, setPart] = useState({ build: [], buildOther: "", raise: [], raiseOther: "", time: "" });
  const [strategyId, setStrategyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [rIdx, setRIdx] = useState(-1);
  const [partStep, setPartStep] = useState(-1);
  const [anything, setAnything] = useState("");
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);
  const poller = useRef(null);

  const playClip = (id) => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    if (isNarrationMuted() || wasClipPlayed(id)) return null;
    const clip = clips[id];
    if (!clip?.ready) return null;
    const audio = new Audio(`${process.env.REACT_APP_BACKEND_URL}${clip.url}`);
    audioRef.current = audio;
    markClipPlayed(id);
    audio.play().catch(() => {});
    return audio;
  };
  useEffect(() => () => { if (audioRef.current) audioRef.current.pause(); }, []);
  useEffect(() => {
    if (!token) return;
    axios.get(`${API}/game/voice/manifest/${token}`).then((r) => setClips(r.data.clips || {})).catch(() => {});
  }, [token]);

  useEffect(() => { document.title = "Complete Your Game Setup | Board Fundraising Game"; }, []);
  useEffect(() => () => clearInterval(poller.current), []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`, { replace: true }); return; }
    (async () => {
      try {
        const situation = (await memberApi.get("/game/situation")).data;
        if (situation.completed) { navigate("/game/dashboard", { replace: true }); return; }
        setReality(situation.sections?.current_reality || {});
        const saved = situation.sections?.participation || {};
        setPart({
          build: saved.build || [], buildOther: saved.build_other || "",
          raise: saved.raise || [], raiseOther: saved.raise_other || "", time: saved.time || "",
        });
        setAnything(saved.anything_else || "");
        let selfToken = "";
        try { selfToken = (await memberApi.post("/game/self-play")).data.token; }
        catch { navigate("/board-fundraising-game", { replace: true }); return; }
        setToken(selfToken);
        const context = (await axios.get(`${API}/game/play/${selfToken}`)).data;
        setCtx(context);
        const playedAll = [1, 2, 3, 4].every((id) => context.progress?.[id]?.completed);
        if (!playedAll) { setPhase("play_first"); return; }
        const responses = {};
        for (const id of [1, 2, 3, 4]) {
          responses[id] = (await axios.get(`${API}/game/play/${selfToken}/section/${id}`)).data.response || {};
        }
        const ftPending = [1, 2, 3, 4].find((id) => !responses[id]?.fine_tuning?.completed);
        if (ftPending) { setFtArea(ftPending); setPhase("intro"); }
        else setPhase("reality");
      } catch (err) {
        if (err.response?.status === 403) { navigate("/game/start", { replace: true }); return; }
        setError("We could not load your game setup. Please refresh the page.");
      }
    })();
  }, [loading, member, navigate]);

  const startGeneration = async () => {
    setPhase("generating"); setError("");
    try { await memberApi.post("/game/strategy/generate", { mode: "working" }); }
    catch { setPhase("failed"); return; }
    clearInterval(poller.current);
    poller.current = setInterval(async () => {
      try {
        const status = (await memberApi.get("/game/strategy/status", { params: { mode: "working" } })).data;
        if (status.status === "done" && status.strategy_id) {
          clearInterval(poller.current);
          setStrategyId(status.strategy_id);
          setPhase("generated");
        } else if (status.status === "failed") {
          clearInterval(poller.current);
          setPhase("failed");
        }
      } catch { /* keep polling */ }
    }, 3000);
  };

  const REALITY_CLIP_BY_KEY = {
    current_individual_donors: "reality_donors", current_businesses: "reality_businesses",
    current_grantors: "reality_grantors", current_team: "reality_team", current_resources: "reality_resources",
  };
  const PART_CLIPS = ["part_build", "part_raise", "part_time", "part_anything"];

  useEffect(() => {
    if (phase === "reality") {
      if (rIdx === -1) { playClip("reality_intro"); return; }
      const key = (((ctx || {}).v3 || {}).current_reality || {}).questions?.[rIdx]?.key;
      const clip = REALITY_CLIP_BY_KEY[key];
      if (clip) playClip(clip);
      else if (audioRef.current) audioRef.current.pause();
    }
    else if (phase === "participation") playClip(partStep === -1 ? "part_intro" : PART_CLIPS[partStep]);
    else if (phase === "done") {
      const audio = playClip("lead_setup_complete");
      const go = () => navigate("/game/dashboard", { replace: true });
      if (audio) audio.onended = go;
      else setTimeout(go, 2500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, rIdx, partStep, clips]);

  const finishParticipation = async () => {
    setBusy(true); setError("");
    const participation = { build: part.build, build_other: part.buildOther, raise: part.raise, raise_other: part.raiseOther, time: part.time, anything_else: anything };
    try {
      await memberApi.put("/game/situation", { sections: { current_reality: reality, participation }, current_step: 6 });
      await memberApi.post("/game/situation/complete");
      try {
        await axios.post(`${API}/game/play/${token}/section/5/complete`, {
          first_response: [], final_response: [], first_move_locked: true, guided_selections: {}, additional_ideas: {},
          stage_responses: {}, preferences: [], do_not_want: [], group_game_ideas: [],
          extras: { build: part.build, build_other: part.buildOther, raise: part.raise, raise_other: part.raiseOther, time: part.time, additional_idea: anything },
        });
      } catch { /* participation stored on the situation either way */ }
      try { await memberApi.post("/game/strategy/generate", { mode: "working" }); }
      catch { /* the dashboard can start generation again */ }
      setBusy(false);
      setPhase("done");
      window.scrollTo({ top: 0 });
    } catch {
      setError("We could not save your answers. Please try again.");
      setBusy(false);
    }
  };

  if (loading || phase === "loading" || !ctx) {
    return (
      <BfgShell>
        <main className="bfg-flow" style={{ textAlign: "center" }} data-testid="bfg-situation-loading">
          {error ? <p className="bfg-error">{error}</p> : <p style={{ marginTop: 40 }}>Loading your game setup…</p>}
        </main>
      </BfgShell>
    );
  }

  const v3 = ctx.v3 || {};
  const pr = v3.primary_review || {};
  const ft = v3.fine_tuning || {};
  const cr = v3.current_reality || {};
  const pp = v3.participation || {};

  const shell = (children, testId) => (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 760, margin: "0 auto", padding: "30px 20px 80px", textAlign: "center" }} data-testid={testId}>
        {children}
      </main>
    </BfgShell>
  );

  if (phase === "play_first") {
    return shell(<>
      <h1>{pr.play_first_heading}</h1>
      <p style={{ marginTop: 14 }}>{pr.play_first_text}</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} onClick={() => navigate(`/play/${token}`)} data-testid="bfg-setup-play-first-btn">
        {pr.play_first_button}
      </button>
    </>, "bfg-setup-play-first");
  }

  if (phase === "intro") {
    return shell(<>
      <h1 data-testid="bfg-setup-review-heading">{pr.heading}</h1>
      <p style={{ marginTop: 14 }}>{pr.supporting}</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} onClick={() => setPhase("finetune")} data-testid="bfg-setup-start-review-btn">
        {pr.start_button}
      </button>
    </>, "bfg-setup-review-intro");
  }

  if (phase === "finetune") {
    const gft = (v3.guided || {}).finetune || {};
    return shell(<>
      <p className="bfg-eyebrow">STRATEGIC AREA {ftArea} OF 4</p>
      <h1>{gft.heading || ft.heading}</h1>
      <FineTuneReview token={token} sectionId={ftArea} copy={{ ...gft, refining: (v3.guided || {}).refining }}
        onDone={() => {
          if (ftArea < 4) setFtArea(ftArea + 1); else setPhase("reality");
          window.scrollTo({ top: 0 });
        }} />
    </>, "bfg-setup-finetune");
  }

  if (phase === "reality") {
    const questions = cr.questions || [];
    if (rIdx === -1) {
      return shell(<>
        <h1 data-testid="bfg-reality-intro-heading">NOW LET'S BUILD AROUND WHAT YOU ALREADY HAVE</h1>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26 }} onClick={() => { setRIdx(0); window.scrollTo({ top: 0 }); }} data-testid="bfg-reality-intro-continue">
          Continue
        </button>
      </>, "bfg-setup-reality-intro");
    }
    const question = questions[rIdx] || {};
    const last = rIdx === questions.length - 1;    const continueReality = async () => {
      if (!last) { setRIdx(rIdx + 1); window.scrollTo({ top: 0 }); return; }
      setBusy(true); setError("");
      try {
        await memberApi.put("/game/situation", { sections: { current_reality: reality }, current_step: 5 });
        setPhase("participation"); setPartStep(-1); window.scrollTo({ top: 0 });
      } catch { setError("We could not save your answers. Please try again."); }
      setBusy(false);
    };
    return shell(<>
      <div style={{ position: "absolute", top: 14, right: 14 }}><NarrationControl audioRef={audioRef} /></div>
      <p className="bfg-eyebrow">YOUR CURRENT REALITY — {rIdx + 1} OF {questions.length}</p>
      <h1 data-testid="bfg-reality-heading">{question.heading}</h1>
      <p style={{ marginTop: 18, fontWeight: 700, fontSize: 18 }} data-testid={`bfg-reality-question-${question.key}`}>{question.question}</p>
      {question.hint && <p style={{ marginTop: 8, fontSize: 14, color: "#6B7280" }}>{question.hint}</p>}
      <textarea rows={7} style={{ width: "100%", marginTop: 22, padding: 16, border: "1px solid #d1d5db", borderRadius: 12, fontSize: 15, lineHeight: 1.6 }}
        placeholder="Type your answer here..." value={reality[question.key] || ""}
        onChange={(event) => setReality((current) => ({ ...current, [question.key]: event.target.value }))}
        data-testid={`bfg-reality-${question.key}`} />
      <div><SpeakButton value={reality[question.key] || ""} onChange={(value) => setReality((current) => ({ ...current, [question.key]: value }))} testId={`bfg-reality-${question.key}-speak`} /></div>
      {error && <p className="bfg-error">{error}</p>}
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 22 }}>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" data-testid="bfg-reality-back"
          onClick={() => { if (audioRef.current) audioRef.current.pause(); setRIdx(rIdx - 1); window.scrollTo({ top: 0 }); }}>
          Back
        </button>
        <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={continueReality} data-testid="bfg-reality-continue">
          {busy ? "Saving…" : "Continue"}
        </button>
      </div>
    </>, "bfg-setup-reality");
  }

  if (phase === "participation") {
    const toggle = (listKey, option) => setPart((current) => ({
      ...current,
      [listKey]: current[listKey].includes(option) ? current[listKey].filter((item) => item !== option) : [...current[listKey], option],
    }));
    const checkList = (options, listKey, otherKey, otherPrompt, testId) => (
      <div style={{ marginTop: 20, textAlign: "left" }}>
        {options.map((option) => (
          <label key={option} className="bfg-ht-check" data-testid={`${testId}-${option.slice(0, 20).replace(/\s+/g, "-").toLowerCase()}`}>
            <input type="checkbox" checked={part[listKey].includes(option)} onChange={() => toggle(listKey, option)} /><span>{option}</span>
          </label>
        ))}
        {part[listKey].includes("Other") && (
          <label className="bfg-field">
            <span>{otherPrompt}</span>
            <textarea rows={3} value={part[otherKey]} onChange={(event) => setPart((current) => ({ ...current, [otherKey]: event.target.value }))} data-testid={`${testId}-other-input`} />
          </label>
        )}
      </div>
    );
    const screens = [
      { heading: "HOW DO YOU WANT TO HELP BUILD AND MANAGE THE FUNDRAISING SYSTEM?",
        body: checkList(pp.build_options || [], "build", "buildOther", pp.build_other_prompt, "bfg-setup-build"), can: true },
      { heading: "HOW DO YOU WANT TO HELP RAISE MONEY?",
        body: checkList(pp.raise_options || [], "raise", "raiseOther", pp.raise_other_prompt, "bfg-setup-raise"), can: true },
      { heading: "HOW MUCH TIME CAN YOU REALISTICALLY COMMIT EACH MONTH?",
        body: (
          <div style={{ marginTop: 20, textAlign: "left" }}>
            {(pp.time_options || []).map((option) => (
              <label key={option} className="bfg-ht-check"><input type="radio" name="bfg-setup-time" checked={part.time === option} onChange={() => setPart((current) => ({ ...current, time: option }))} /><span>{option}</span></label>
            ))}
          </div>), can: !!part.time },
      { heading: "IS THERE ANYTHING ELSE YOU WANT TO SHARE?",
        body: (<>
          <textarea rows={6} style={{ width: "100%", marginTop: 20, padding: 16, border: "1px solid #d1d5db", borderRadius: 12, fontSize: 15, lineHeight: 1.6 }}
            placeholder="Type your answer here..." value={anything}
            onChange={(event) => setAnything(event.target.value)} data-testid="bfg-setup-anything-input" />
          <div><SpeakButton value={anything} onChange={setAnything} testId="bfg-setup-anything-speak" /></div>
        </>), can: true },
    ];
    if (partStep === -1) {
      return shell(<>
        <h1 data-testid="bfg-participation-intro-heading">NOW LET'S TALK ABOUT YOU</h1>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26 }} onClick={() => { setPartStep(0); window.scrollTo({ top: 0 }); }} data-testid="bfg-participation-intro-continue">
          Continue
        </button>
      </>, "bfg-setup-participation-intro");
    }
    const screen = screens[partStep];
    const last = partStep === screens.length - 1;
    return shell(<>
      <h1 data-testid="bfg-participation-heading">{screen.heading}</h1>
      {screen.body}
      {error && <p className="bfg-error">{error}</p>}
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 22 }}>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" data-testid="bfg-participation-back"
          onClick={() => {
            if (audioRef.current) audioRef.current.pause();
            if (partStep === 0) { setPhase("reality"); setRIdx((cr.questions || []).length - 1); }
            else setPartStep(partStep - 1);
            window.scrollTo({ top: 0 });
          }}>
          Back
        </button>
        <button className="bfg-btn bfg-btn-primary" disabled={busy || !screen.can}
          onClick={() => { if (last) finishParticipation(); else { setPartStep(partStep + 1); window.scrollTo({ top: 0 }); } }}
          data-testid="bfg-setup-participation-submit">
          {busy ? "Saving…" : last ? "Continue" : "Continue"}
        </button>
      </div>
    </>, `bfg-setup-participation-${partStep}`);
  }

  if (phase === "done") {
    return shell(<>
      <h1 data-testid="bfg-setup-done-heading">Building Your Working Fundraising Strategy</h1>
      <p style={{ marginTop: 14 }}>We're taking you to your dashboard now. Your working strategy will be there as soon as it's ready.</p>
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 22 }}
        onClick={() => navigate("/game/dashboard", { replace: true })} data-testid="bfg-setup-done-dashboard">
        Go To My Dashboard
      </button>
    </>, "bfg-setup-done");
  }

  if (phase === "generating") {
    return shell(<>
      <h1>{pr.generate_heading}</h1>
      <p style={{ marginTop: 14 }}>{pr.generating_text}</p>
    </>, "bfg-setup-generating");
  }

  if (phase === "failed") {
    return shell(<>
      <h1>{pr.failed_heading}</h1>
      <p style={{ marginTop: 14 }}>{pr.failed_text}</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} onClick={startGeneration} data-testid="bfg-setup-generate-retry">{pr.try_again_button}</button>
      <div style={{ marginTop: 14 }}>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/dashboard")} data-testid="bfg-setup-failed-dashboard">Go To My Dashboard</button>
      </div>
    </>, "bfg-setup-failed");
  }

  return shell(<>
    <h1 data-testid="bfg-setup-generated-heading">{pr.generated_heading}</h1>
    <p style={{ marginTop: 14 }}>{pr.generated_text}</p>
    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} onClick={() => navigate(`/game/strategy/view/${strategyId}`)} data-testid="bfg-setup-view-strategy-btn">
      {pr.generated_button}
    </button>
    <div style={{ marginTop: 14 }}>
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/dashboard")} data-testid="bfg-setup-generated-dashboard">Go To My Dashboard</button>
    </div>
  </>, "bfg-setup-generated");
}
