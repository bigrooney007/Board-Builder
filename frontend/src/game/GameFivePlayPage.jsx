import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { BfgShell, money } from "./gameShared";
import { SpeakButton } from "./SpeakButton";
import { fiveQuestionText } from "./gameFiveQuestions";
import GuidedAudioButton from "./GuidedAudioButton";
import { useGuidedNarration } from "./useGuidedNarration";
import "./guided-flow.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function GameFivePlayPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [context, setContext] = useState(null);
  const [answers, setAnswers] = useState({});
  const [question, setQuestion] = useState(1);
  const [started, setStarted] = useState(false);
  const [involvement, setInvolvement] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const boardIntro = "Welcome to your individual Board Fundraising Game. Your ideas matter. Share what comes to mind across five short questions, then tell us what part you would be comfortable playing. There are no perfect answers. Your board will bring everyone's thinking together at the meeting. Let's start.";
  const participationPrompt = context?.member?.is_primary
    ? "Looking at the fundraising process you've laid out, how do you see yourself participating in it? What part of this process can you personally take responsibility for?"
    : "Looking at the ideas you shared, what part of the fundraising process would you feel comfortable helping with?";
  const narration = useGuidedNarration("fundraising-free", context && !done
    ? !started ? "fundraising-free-board-welcome" : question > 5 ? "fundraising-free-participation" : `fundraising-free-question-${question}` : "",
    !started ? boardIntro : question > 5 ? participationPrompt : fiveQuestionText(question - 1, answers["1"]));

  useEffect(() => {
    document.title = "Individual Board Fundraising Game";
    let active = true;
    Promise.all([axios.get(`${API}/game/play/${token}`), axios.get(`${API}/game/play/${token}/ideas`)])
      .then(([ctx, saved]) => {
        if (!active) return;
        setContext(ctx.data);
        setAnswers(saved.data.answers || {});
        setQuestion(saved.data.next_question || 1);
        if (ctx.data.member?.is_primary || (saved.data.next_question || 1) > 1) setStarted(true);
        setInvolvement(saved.data.involvement || "");
        if (saved.data.completed) {
          if (ctx.data.member?.is_primary) navigate("/game/setup", { replace: true });
          else setDone(true);
        }
      }).catch(() => { if (active) setError("This game link is not available."); });
    return () => { active = false; };
  }, [token, navigate]);

  const continueQuestion = async () => {
    const answer = answers[String(question)] || "";
    if (!answer.trim()) return;
    setBusy(true); setError("");
    try {
      await axios.put(`${API}/game/play/${token}/ideas/answer/${question}`, { answer });
      setQuestion(question + 1);
      window.scrollTo({ top: 0 });
    } catch (err) { setError(err.response?.data?.detail || "We could not save your answer."); }
    finally { setBusy(false); }
  };

  const complete = async () => {
    if (!involvement.trim()) return;
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/game/play/${token}/ideas/complete`, { involvement });
      if (context.member?.is_primary) navigate("/game/setup", { replace: true });
      else setDone(true);
    } catch (err) { setError(err.response?.data?.detail || "We could not save your participation answer."); }
    finally { setBusy(false); }
  };

  return <BfgShell><main className="guided-flow" data-testid="bfg-five-play">
    {!context ? <p>{error || "Opening your individual game…"}</p> : done ? <>
      <h1>Your Individual Board Fundraising Game Is Complete</h1>
      <p style={{ marginTop: 16 }}>Thank you. Your original ideas and participation choice are ready for the board's group discussion.</p>
      {context.game_night?.date_display && <p style={{ marginTop: 16 }}>Game Night: {context.game_night.date_display}</p>}
    </> : !started ? <section className="guided-welcome" data-testid="bfg-board-welcome">
      <div className="guided-audio-position"><GuidedAudioButton narration={narration} /></div>
      <p className="guided-kicker">YOUR INDIVIDUAL BOARD FUNDRAISING GAME</p>
      <h1>Your ideas will help shape your board's fundraising strategy.</h1>
      <div className="guided-goal"><span>YOUR ORGANIZATION'S FUNDRAISING GOAL</span><strong>{context.goal_display || money(0)}</strong></div>
      <p className="guided-lead">Share your own thinking. Your board will bring everyone's ideas together at the meeting.</p>
      <p className="guided-instruction">Say what comes to mind. You don't need polished answers. After five questions, tell us where you can help.</p>
      <button type="button" className="bfg-btn bfg-btn-primary guided-action" onClick={() => { narration.stop(); setStarted(true); }} data-testid="bfg-board-start">START MY GAME</button>
    </section> : <section className="guided-question">
      <div className="guided-question-top"><span>{question <= 5 ? `QUESTION ${question} OF 5` : "YOUR PARTICIPATION"}</span><GuidedAudioButton narration={narration} /></div>
      {question <= 5 ? <>
        <h1 data-testid="bfg-five-question">{fiveQuestionText(question - 1, answers["1"])}</h1>
        <label className="guided-answer-label" htmlFor="bfg-five-answer">Your answer</label>
        <textarea id="bfg-five-answer" rows={7} maxLength={6000} value={answers[String(question)] || ""}
          onChange={(event) => setAnswers({ ...answers, [String(question)]: event.target.value })}
          placeholder="Say it as it comes to mind…" aria-label={`Answer to question ${question}`}
          data-testid="bfg-five-answer" />
        <SpeakButton value={answers[String(question)] || ""} onChange={(value) => setAnswers((current) => ({ ...current, [String(question)]: value }))} />
        {error && <p className="bfg-error">{error}</p>}
        <div className="guided-actions">
          {question > 1 && <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => setQuestion(question - 1)}>Back</button>}
          <button className="bfg-btn bfg-btn-primary" disabled={busy || !(answers[String(question)] || "").trim()} onClick={continueQuestion} data-testid="bfg-five-continue">{busy ? "SAVING…" : "NEXT QUESTION"}</button>
        </div>
      </> : <>
        <h1>{participationPrompt}</h1>
        {context.member?.is_primary && <div className="guided-process-summary">
          <strong>The process you described</strong>
          <p>{answers["5"]}</p>
        </div>}
        <label className="guided-answer-label" htmlFor="bfg-five-involvement">Your answer</label>
        <textarea id="bfg-five-involvement" rows={7} maxLength={6000} value={involvement} onChange={(event) => setInvolvement(event.target.value)}
          placeholder="I would be comfortable helping by…" data-testid="bfg-five-involvement"
          />
        <SpeakButton value={involvement} onChange={setInvolvement} />
        {error && <p className="bfg-error">{error}</p>}
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy || !involvement.trim()} onClick={complete} data-testid="bfg-five-complete">{busy ? "SAVING…" : "COMPLETE MY INDIVIDUAL GAME"}</button>
      </>}
    </section>}
  </main></BfgShell>;
}
