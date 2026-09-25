import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { NarrationControl, isNarrationMuted, wasClipPlayed, markClipPlayed } from "./NarrationControl";
import { SpeakButton } from "./SpeakButton";
import { useWakeLock } from "./useWakeLock";
import "./game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE = process.env.REACT_APP_BACKEND_URL;
const EMPTY_AUDIENCE = { enabled: false, audience: "", reason: "", where: "", attraction: "", funding_ask: "", process: "" };

const QUESTIONS = {
  individuals: [
    ["audience", "Which type or group of people do you think have the strongest reason to give to our organization and help us reach our fundraising goal?"],
    ["reason", "Why do you think these people would give to our organization and this fundraising goal?"],
    ["where", "Where do you think we can find these people?"],
    ["attraction", "What valuable thing, information, experience or opportunity can we offer that would attract them, help them get to know us, or encourage them to share their contact details?"],
    ["funding_ask", "What should we ask these individuals to fund, and how much should we ask each person to give?"],
    ["process", "Since we should not ask for money the first time we meet them, what step-by-step process should take them from first learning about our organization to giving to our mission?"],
  ],
  businesses: [
    ["audience", "Which type or group of businesses do you think have the strongest reason to sponsor our organization, our programs, or the people we serve?"],
    ["reason", "Why do you think these businesses would support our organization and this fundraising goal?"],
    ["where", "Where do you think we can find these businesses and the people who make their sponsorship decisions?"],
    ["attraction", "What valuable opportunity, partnership benefit or evidence can we offer to attract these businesses and earn a conversation with them?"],
    ["funding_ask", "What should we ask these businesses to sponsor or fund, and how much should we ask each business to contribute?"],
    ["process", "What step-by-step process should we follow from first contact to securing and maintaining their sponsorship or support?"],
  ],
  grantors: [
    ["audience", "Which type of grantors do you think have the strongest reason to fund our mission, programs, or this fundraising goal?"],
    ["reason", "Why do you think these grantors would fund our organization and this goal?"],
    ["where", "Where can we find these grantors and their funding opportunities?"],
    ["attraction", "How can we demonstrate the relevance, evidence and credibility that would attract these grantors and strengthen our relationship with them?"],
    ["funding_ask", "What should we ask these grantors to fund, and how much should we request from each grantor?"],
    ["process", "Grant fundraising goes beyond submitting an application. What step-by-step process should we follow to build the relationship and strengthen our case before, during and after the application?"],
  ],
};

const audienceLabel = (key) => ({ individuals: "INDIVIDUAL DONORS", businesses: "BUSINESS SPONSORS", grantors: "GRANTORS" }[key]);

export default function GamePlayPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const reviewMode = new URLSearchParams(useLocation().search).get("review") === "1";
  const [ctx, setCtx] = useState(null);
  const [phase, setPhase] = useState("loading");
  const [audience, setAudience] = useState("individuals");
  const [questionIndex, setQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState({
    individuals: { ...EMPTY_AUDIENCE, enabled: true }, businesses: { ...EMPTY_AUDIENCE }, grantors: { ...EMPTY_AUDIENCE },
  });
  const [involvement, setInvolvement] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);
  useWakeLock(["welcome", "question", "gate", "involvement"].includes(phase));

  const clipId = useMemo(() => phase === "question"
    ? `audience_${audience}_${QUESTIONS[audience][questionIndex][0]}`
    : phase === "involvement" ? "audience_involvement" : phase === "gate" ? `audience_${audience}_gate` : "audience_opening",
  [phase, audience, questionIndex]);

  const playClip = useCallback((id, force = false) => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    const clip = clips[id];
    if (!clip?.ready || isNarrationMuted()) return;
    const playedKey = `${id}:${clip.url}`;
    if (!force && wasClipPlayed(playedKey)) return;
    const audio = new Audio(`${BASE}${clip.url}`);
    audioRef.current = audio;
    audio.play().then(() => markClipPlayed(playedKey)).catch(() => {});
  }, [clips]);

  useEffect(() => () => { if (audioRef.current) audioRef.current.pause(); }, []);
  useEffect(() => { if (clips[clipId]) playClip(clipId); }, [clipId, clips, playClip]);
  useEffect(() => { document.title = "Board Fundraising Game"; }, []);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [phase, audience, questionIndex]);

  useEffect(() => {
    (async () => {
      try {
        const [context, saved] = await Promise.all([
          axios.get(`${API}/game/play/${token}`),
          axios.get(`${API}/game/play/${token}/audience-response`),
        ]);
        setCtx(context.data);
        axios.get(`${API}/game/voice/manifest/${token}`).then((r) => setClips(r.data.clips || {})).catch(() => {});
        const record = saved.data.response || {};
        if (record.audiences) {
          setAnswers({
            individuals: { ...EMPTY_AUDIENCE, enabled: true, ...(record.audiences.individuals || {}) },
            businesses: { ...EMPTY_AUDIENCE, ...(record.audiences.businesses || {}) },
            grantors: { ...EMPTY_AUDIENCE, ...(record.audiences.grantors || {}) },
          });
          setInvolvement(record.involvement || "");
        }
        if (record.completed && !reviewMode) {
          if (context.data.member?.is_primary && context.data.paid) navigate("/game/setup", { replace: true });
          else setPhase("done");
        } else if (reviewMode) {
          setAudience("individuals"); setQuestionIndex(0); setPhase("question");
        } else if (record.current_audience) {
          const savedAudience = ["individuals", "businesses", "grantors"].includes(record.current_audience)
            ? record.current_audience : "individuals";
          const savedQuestion = Math.max(0, Number(record.current_question || 0));
          const savedAnswer = record.audiences?.[savedAudience] || {};
          setAudience(savedAudience);
          if (savedQuestion >= 6) {
            if (savedAudience === "individuals") { setAudience("businesses"); setPhase("gate"); }
            else if (savedAudience === "businesses") { setAudience("grantors"); setPhase("gate"); }
            else setPhase("involvement");
          } else if (savedAudience !== "individuals" && !savedAnswer.enabled) {
            setQuestionIndex(0); setPhase("gate");
          } else {
            setQuestionIndex(Math.min(savedQuestion, 5)); setPhase("question");
          }
        } else setPhase("welcome");
      } catch {
        setError("This game link is not valid."); setPhase("error");
      }
    })();
  }, [token, navigate, reviewMode]);

  const payload = (nextAudience = audience, nextQuestion = questionIndex) => ({
    audiences: answers, involvement, current_audience: nextAudience, current_question: nextQuestion,
  });
  const persist = async (nextAudience = audience, nextQuestion = questionIndex) => {
    await axios.put(`${API}/game/play/${token}/audience-response`, payload(nextAudience, nextQuestion));
  };
  const goAfterAudience = async () => {
    if (audience === "individuals") { setAudience("businesses"); setPhase("gate"); }
    else if (audience === "businesses") { setAudience("grantors"); setPhase("gate"); }
    else setPhase("involvement");
  };

  const continueQuestion = async () => {
    const [field] = QUESTIONS[audience][questionIndex];
    if (!String(answers[audience][field] || "").trim()) return;
    setBusy(true); setError("");
    try {
      if (questionIndex < QUESTIONS[audience].length - 1) {
        await persist(audience, questionIndex + 1); setQuestionIndex(questionIndex + 1);
      } else if (audience === "individuals") {
        await persist("businesses", 0); await goAfterAudience();
      } else if (audience === "businesses") {
        await persist("grantors", 0); await goAfterAudience();
      } else {
        await persist("grantors", 6); await goAfterAudience();
      }
    } catch { setError("We could not save your answer. Please try again."); }
    setBusy(false);
  };

  const answerGate = async (yes) => {
    const nextAnswers = { ...answers, [audience]: { ...answers[audience], enabled: yes } };
    setAnswers(nextAnswers); setBusy(true); setError("");
    try {
      const nextAudience = yes ? audience : "grantors";
      const nextQuestion = yes ? 0 : audience === "grantors" ? 6 : 0;
      await axios.put(`${API}/game/play/${token}/audience-response`, {
        audiences: nextAnswers, involvement, current_audience: nextAudience, current_question: nextQuestion,
      });
      if (yes) { setQuestionIndex(0); setPhase("question"); }
      else if (audience === "businesses") { setAudience("grantors"); setPhase("gate"); }
      else setPhase("involvement");
    } catch { setError("We could not save your choice. Please try again."); }
    setBusy(false);
  };

  const complete = async () => {
    if (!involvement.trim()) return;
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/game/play/${token}/audience-response/complete`, payload("individuals", 7));
      if (ctx.member?.is_primary && ctx.paid) navigate(reviewMode ? "/game/setup?review=1" : "/game/setup", { replace: true });
      else setPhase("done");
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not complete your game. Please try again.");
    }
    setBusy(false);
  };

  const shell = (children, testId = "bfg-play-page") => (
    <div className="bfg" style={{ minHeight: "100vh" }}>
      <main className="bfg-flow" style={{ maxWidth: 720, margin: "0 auto", padding: "34px 20px 90px", textAlign: "center" }} data-testid={testId}>
        {!["loading", "error", "done"].includes(phase) && <div style={{ position: "absolute", top: 14, right: 14 }}><NarrationControl audioRef={audioRef} onReplay={() => playClip(clipId, true)} /></div>}
        {children}
        {error && <p className="bfg-error" data-testid="bfg-play-error">{error}</p>}
      </main>
    </div>
  );

  if (phase === "loading") return <div className="bfg" style={{ minHeight: "100vh" }} />;
  if (phase === "error") return shell(null, "bfg-play-invalid");
  if (phase === "welcome") return shell(<>
    <p className="bfg-eyebrow">YOUR INDIVIDUAL BOARD FUNDRAISING GAME</p>
    <h1>Build Ideas Your Board Can Turn Into A Fundraising Strategy</h1>
    <p style={{ marginTop: 16, fontSize: 17 }}>You will think through individual donors first. If you also have ideas for businesses or grantors, the game will guide you through the same complete process for each audience.</p>
    <div className="bfg-card" style={{ marginTop: 22, padding: 22 }}><p style={{ fontWeight: 700 }}>HELP {(ctx?.organization_name || "YOUR ORGANIZATION").toUpperCase()} RAISE</p><p style={{ fontFamily: "Outfit", fontWeight: 800, fontSize: 40, marginTop: 6 }}>{ctx?.goal_display || ""}</p></div>
    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 26 }} onClick={() => { setAudience("individuals"); setQuestionIndex(0); setPhase("question"); }} data-testid="bfg-start-my-game-btn">START MY GAME</button>
  </>, "bfg-welcome");

  if (phase === "gate") {
    const business = audience === "businesses";
    return shell(<>
      <p className="bfg-eyebrow">OPTIONAL FUNDING AUDIENCE</p>
      <h1>{business ? "Do You Have Ideas For Business Sponsors Or Partners?" : "Do You Have Ideas For Grantors?"}</h1>
      <p style={{ marginTop: 16 }}>{business ? "Do you know a type or group of businesses that would have a strong reason to support this fundraising goal?" : "Do you know a type of foundation, government funder or other grantor that would have a strong reason to fund this mission or goal?"}</p>
      <div style={{ display: "flex", justifyContent: "center", gap: 12, marginTop: 26, flexWrap: "wrap" }}>
        <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={() => answerGate(true)} data-testid={`bfg-${audience}-yes`}>YES, I HAVE IDEAS</button>
        <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => answerGate(false)} data-testid={`bfg-${audience}-no`}>NOT RIGHT NOW</button>
      </div>
    </>, `bfg-${audience}-gate`);
  }

  if (phase === "question") {
    const [field, question] = QUESTIONS[audience][questionIndex];
    const value = answers[audience][field] || "";
    return shell(<>
      <p className="bfg-eyebrow">{audienceLabel(audience)} • QUESTION {questionIndex + 1} OF 6</p>
      <h1 data-testid="bfg-audience-question">{question}</h1>
      <textarea rows={8} style={{ width: "100%", marginTop: 22, padding: 16, border: "1px solid #d1d5db", borderRadius: 12, fontSize: 16, lineHeight: 1.6 }} placeholder="Share your idea in your own words..." value={value} onChange={(event) => setAnswers((current) => ({ ...current, [audience]: { ...current[audience], [field]: event.target.value } }))} data-testid={`bfg-${audience}-${field}`} />
      <SpeakButton value={value} onChange={(text) => setAnswers((current) => ({ ...current, [audience]: { ...current[audience], [field]: text } }))} testId={`bfg-${audience}-${field}-speak`} />
      <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 22 }}>
        {questionIndex > 0 && <button className="bfg-btn bfg-btn-ghost" onClick={() => setQuestionIndex(questionIndex - 1)}>Back</button>}
        <button className="bfg-btn bfg-btn-primary" disabled={busy || !value.trim()} onClick={continueQuestion} data-testid="bfg-audience-continue">{busy ? "SAVING…" : "CONTINUE"}</button>
      </div>
    </>, "bfg-audience-question-page");
  }

  if (phase === "involvement") return shell(<>
    <p className="bfg-eyebrow">YOUR ROLE</p>
    <h1>How Would You Like To Support Fundraising?</h1>
    <p style={{ marginTop: 16, fontSize: 17 }}>Based on the ideas you shared, how would you feel most comfortable and useful supporting {ctx?.organization_name || "the organization"} to raise money?</p>
    <textarea rows={8} style={{ width: "100%", marginTop: 22, padding: 16, border: "1px solid #d1d5db", borderRadius: 12, fontSize: 16, lineHeight: 1.6 }} placeholder="Describe the role, introductions, research, outreach, follow-up or other support you would be comfortable providing..." value={involvement} onChange={(event) => setInvolvement(event.target.value)} data-testid="bfg-involvement" />
    <SpeakButton value={involvement} onChange={setInvolvement} testId="bfg-involvement-speak" />
    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy || !involvement.trim()} onClick={complete} data-testid="bfg-complete-game">{busy ? "SAVING…" : "COMPLETE MY GAME"}</button>
  </>, "bfg-involvement-page");

  return shell(<>
    <h1>Your Individual Board Fundraising Game Is Complete</h1>
    <p style={{ marginTop: 16 }}>Thank you. Your ideas and the way you would like to support fundraising are ready for the Board's group discussion.</p>
    {ctx?.game_night?.date_display && <p style={{ marginTop: 18, fontWeight: 700 }}>Game Night: {ctx.game_night.date_display}{ctx.game_night.time_display ? ` at ${ctx.game_night.time_display}` : ""}</p>}
    <button className="bfg-btn bfg-btn-ghost" style={{ marginTop: 22 }} onClick={() => { setAudience("individuals"); setQuestionIndex(0); setPhase("question"); }}>Review My Responses</button>
  </>, "bfg-board-done");
}
