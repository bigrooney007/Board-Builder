import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, money } from "./gameShared";
import { FIVE_QUESTIONS, fiveQuestionText } from "./gameFiveQuestions";
import { SpeakButton } from "./SpeakButton";
import GuidedAudioButton from "./GuidedAudioButton";
import { useGuidedNarration } from "./useGuidedNarration";
import "./guided-flow.css";

const INTRO = "Welcome to your Board Fundraising Game. This is the fundraising goal you want to reach. Share your own thinking across five short questions. Say your answers as they come to mind. You don't have to edit them or sound perfect. When you complete the game, you can invite your board members to bring their ideas into the strategy too. Let's start.";

export default function GameFreeQuestionsPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [context, setContext] = useState(null);
  const [answers, setAnswers] = useState({});
  const [question, setQuestion] = useState(1);
  const [started, setStarted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const narrationId = started ? `fundraising-free-question-${question}` : "fundraising-free-welcome";
  const questionText = fiveQuestionText(question - 1, answers["1"]);
  const narration = useGuidedNarration("fundraising-free", context ? narrationId : "", started ? questionText : INTRO);

  useEffect(() => { document.title = "Play Your Board Fundraising Game"; }, []);
  useEffect(() => {
    if (loading) return;
    if (!member) {
      navigate(`/login?next=${encodeURIComponent("/game/questions")}`, { replace: true });
      return;
    }
    let active = true;
    const open = async () => {
      try {
        let response;
        try { response = await memberApi.get("/game/free"); }
        catch (err) {
          if (err.response?.status !== 409) throw err;
          const goal = Number(sessionStorage.getItem("bfgGoal") || 0);
          const organization = sessionStorage.getItem("bfgOrg") || "";
          const name = sessionStorage.getItem("bfgName") || "";
          if (!goal || !organization || !name) throw err;
          await memberApi.put("/game/profile", {
            organization: { name: organization },
            goal: { amount: goal, purpose: "Reach our fundraising goal" },
            primary_user: { full_name: name, email: member.email },
            homepage_capture: true,
          });
          response = await memberApi.get("/game/free");
        }
        if (!active) return;
        setContext(response.data);
        setAnswers(response.data.answers || {});
        if (response.data.complete) navigate(response.data.unlocked ? "/game/setup" : "/game/upgrade", { replace: true });
        else {
          setQuestion(response.data.next_question || 1);
          if ((response.data.next_question || 1) > 1) setStarted(true);
        }
      } catch { if (active) setError("We could not open your game. Return to the homepage to enter your goal and details."); }
    };
    open();
    return () => { active = false; };
  }, [loading, member, navigate]);

  const continueGame = async () => {
    const value = answers[String(question)] || "";
    if (!value.trim()) return;
    setBusy(true); setError("");
    try {
      await memberApi.put(`/game/free/${question}`, { answer: value });
      if (question === FIVE_QUESTIONS.length) navigate("/game/upgrade");
      else { setQuestion(question + 1); window.scrollTo({ top: 0 }); }
    } catch (err) { setError(err.response?.data?.detail || "We could not save your answer. Please try again."); }
    finally { setBusy(false); }
  };

  return <BfgShell><main className="guided-flow" data-testid="bfg-free-questions">
    {!context ? <p className="guided-loading">{error || "Opening your Board Fundraising Game…"}</p> : !started ? (
      <section className="guided-welcome" data-testid="bfg-free-welcome">
        <div className="guided-audio-position"><GuidedAudioButton narration={narration} /></div>
        <p className="guided-kicker">WELCOME TO YOUR BOARD FUNDRAISING GAME</p>
        <h1>Let's build a strategy to reach your fundraising goal.</h1>
        <div className="guided-goal"><span>YOUR FUNDRAISING GOAL</span><strong>{money(context.goal_amount)}</strong></div>
        <p className="guided-lead">By playing this game, you will start building the fundraising strategy your organization needs to reach this goal.</p>
        <p className="guided-instruction">Say what comes to mind. You don't need to edit your thinking or sound perfect. Finish the five questions, then invite your board to bring their ideas into the strategy.</p>
        <button type="button" className="bfg-btn bfg-btn-primary guided-action" onClick={() => { narration.stop(); setStarted(true); }} data-testid="bfg-free-start">START THE GAME</button>
      </section>
    ) : (
      <section className="guided-question" data-testid="bfg-free-question-page">
        <div className="guided-question-top"><span>QUESTION {question} OF {FIVE_QUESTIONS.length}</span><GuidedAudioButton narration={narration} /></div>
        <h1 data-testid="bfg-free-question">{questionText}</h1>
        <label className="guided-answer-label" htmlFor="bfg-free-answer">Your answer</label>
        <textarea id="bfg-free-answer" rows={6} maxLength={6000} value={answers[String(question)] || ""}
          onChange={(event) => setAnswers({ ...answers, [String(question)]: event.target.value })}
          placeholder="Say it as it comes to mind…" aria-label={`Answer to question ${question}`}
          data-testid="bfg-free-answer" />
        <SpeakButton value={answers[String(question)] || ""} onChange={(value) => setAnswers((current) => ({ ...current, [String(question)]: value }))} />
        {error && <p className="bfg-error" role="alert">{error}</p>}
        <div className="guided-actions">
          {question > 1 && <button type="button" className="bfg-btn bfg-btn-ghost" onClick={() => setQuestion(question - 1)} disabled={busy}>Back</button>}
          <button type="button" className="bfg-btn bfg-btn-primary" onClick={continueGame} disabled={busy || !(answers[String(question)] || "").trim()} data-testid="bfg-free-continue">{busy ? "SAVING…" : question === 5 ? "FINISH MY FIVE QUESTIONS" : "NEXT QUESTION"}</button>
        </div>
      </section>
    )}
  </main></BfgShell>;
}
