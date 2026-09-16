import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { FineTuneReview } from "./FineTuneReview";

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
  const poller = useRef(null);

  useEffect(() => { document.title = "Complete Your Game Setup | Board Fundraising Game"; }, []);
  useEffect(() => () => clearInterval(poller.current), []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
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
        let selfToken = "";
        try { selfToken = (await memberApi.post("/game/self-play")).data.token; }
        catch { navigate("/game/start", { replace: true }); return; }
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

  const finishParticipation = async () => {
    setBusy(true); setError("");
    const participation = { build: part.build, build_other: part.buildOther, raise: part.raise, raise_other: part.raiseOther, time: part.time };
    try {
      await memberApi.put("/game/situation", { sections: { current_reality: reality, participation }, current_step: 6 });
      await memberApi.post("/game/situation/complete");
      try {
        await axios.post(`${API}/game/play/${token}/section/5/complete`, {
          first_response: [], final_response: [], first_move_locked: true, guided_selections: {}, additional_ideas: {},
          stage_responses: {}, preferences: [], do_not_want: [], group_game_ideas: [],
          extras: { build: part.build, build_other: part.buildOther, raise: part.raise, raise_other: part.raiseOther, time: part.time },
        });
      } catch { /* participation stored on the situation either way */ }
      setBusy(false);
      await startGeneration();
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
    const continueReality = async () => {
      setBusy(true); setError("");
      try {
        await memberApi.put("/game/situation", { sections: { current_reality: reality }, current_step: 5 });
        setPhase("participation"); window.scrollTo({ top: 0 });
      } catch { setError("We could not save your answers. Please try again."); }
      setBusy(false);
    };
    return shell(<>
      <h1 data-testid="bfg-reality-heading">{cr.heading}</h1>
      {String(cr.supporting || "").split("\n").filter((line) => line.trim()).map((line, i) => <p key={i} style={{ marginTop: 12 }}>{line}</p>)}
      <div style={{ marginTop: 10, textAlign: "left" }}>
        {questions.map((question) => (
          <div className="bfg-card" key={question.key} style={{ marginTop: 16, padding: 18 }}>
            <h3>{question.heading}</h3>
            <label className="bfg-field" style={{ marginTop: 8 }}>
              <span>{question.question}</span>
              <textarea rows={4} value={reality[question.key] || ""}
                onChange={(event) => setReality((current) => ({ ...current, [question.key]: event.target.value }))}
                data-testid={`bfg-reality-${question.key}`} />
            </label>
          </div>
        ))}
      </div>
      {error && <p className="bfg-error">{error}</p>}
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy} onClick={continueReality} data-testid="bfg-reality-continue">
        {busy ? "Saving…" : "Save & Continue"}
      </button>
    </>, "bfg-setup-reality");
  }

  if (phase === "participation") {
    const toggle = (listKey, option) => setPart((current) => ({
      ...current,
      [listKey]: current[listKey].includes(option) ? current[listKey].filter((item) => item !== option) : [...current[listKey], option],
    }));
    const checkList = (question, options, listKey, otherKey, otherPrompt, testId) => (
      <div style={{ marginTop: 24, textAlign: "left" }}>
        <h3>{question}</h3>
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
    return shell(<>
      <h1 data-testid="bfg-participation-heading">{pp.heading}</h1>
      {checkList(pp.build_question, pp.build_options || [], "build", "buildOther", pp.build_other_prompt, "bfg-setup-build")}
      {checkList(pp.raise_question, pp.raise_options || [], "raise", "raiseOther", pp.raise_other_prompt, "bfg-setup-raise")}
      <div style={{ marginTop: 24, textAlign: "left" }}>
        <h3>{pp.time_question}</h3>
        {(pp.time_options || []).map((option) => (
          <label key={option} className="bfg-ht-check"><input type="radio" name="bfg-setup-time" checked={part.time === option} onChange={() => setPart((current) => ({ ...current, time: option }))} /><span>{option}</span></label>
        ))}
      </div>
      {error && <p className="bfg-error">{error}</p>}
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy} onClick={finishParticipation} data-testid="bfg-setup-participation-submit">
        {busy ? "Saving…" : pr.generate_button}
      </button>
      <p style={{ marginTop: 12, fontSize: 14 }}>{pr.generate_text}</p>
    </>, "bfg-setup-participation");
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
