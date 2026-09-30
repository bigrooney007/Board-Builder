import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { BfgShell, money } from "./gameShared";
import { SpeakButton } from "./SpeakButton";
import { FIVE_QUESTIONS, fiveQuestionText } from "./gameFiveQuestions";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function GameFivePlayPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [context, setContext] = useState(null);
  const [answers, setAnswers] = useState({});
  const [question, setQuestion] = useState(1);
  const [involvement, setInvolvement] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    document.title = "Individual Board Fundraising Game";
    let active = true;
    Promise.all([axios.get(`${API}/game/play/${token}`), axios.get(`${API}/game/play/${token}/ideas`)])
      .then(([ctx, saved]) => {
        if (!active) return;
        setContext(ctx.data);
        setAnswers(saved.data.answers || {});
        setQuestion(saved.data.next_question || 1);
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

  return <BfgShell><main className="bfg-flow" style={{ maxWidth: 780, margin: "0 auto", padding: "36px 20px 90px", textAlign: "center" }} data-testid="bfg-five-play">
    {!context ? <p>{error || "Opening your individual game…"}</p> : done ? <>
      <h1>Your Individual Board Fundraising Game Is Complete</h1>
      <p style={{ marginTop: 16 }}>Thank you. Your original ideas and participation choice are ready for the board's group discussion.</p>
      {context.game_night?.date_display && <p style={{ marginTop: 16 }}>Game Night: {context.game_night.date_display}</p>}
    </> : <>
      <p className="bfg-eyebrow">{context.member?.is_primary ? "YOUR BOARD FUNDRAISING GAME" : "YOUR INDIVIDUAL BOARD FUNDRAISING GAME"} • {question <= 5 ? `QUESTION ${question} OF 5` : "YOUR PARTICIPATION"}</p>
      <p style={{ margin: "10px auto 24px" }}><strong>{context.organization_name}</strong> • Fundraising goal: <strong>{context.goal_display || money(0)}</strong></p>
      {question <= 5 ? <>
        <h1 data-testid="bfg-five-question">{fiveQuestionText(question - 1, answers["1"])}</h1>
        {question === 1 && <p style={{ margin: "18px auto 0" }}>{FIVE_QUESTIONS[0].hint}</p>}
        <textarea rows={7} maxLength={6000} value={answers[String(question)] || ""}
          onChange={(event) => setAnswers({ ...answers, [String(question)]: event.target.value })}
          placeholder="Share your idea in your own words…" aria-label={`Answer to question ${question}`}
          data-testid="bfg-five-answer" style={{ width: "100%", marginTop: 24, padding: 18, border: "1px solid #cbd5e1", borderRadius: 12, fontSize: 17, lineHeight: 1.6 }} />
        <SpeakButton value={answers[String(question)] || ""} onChange={(value) => setAnswers({ ...answers, [String(question)]: value })} />
        <p style={{ marginTop: 10, fontSize: 14 }}>Your answer is saved in your own words.</p>
        {error && <p className="bfg-error">{error}</p>}
        <div style={{ display: "flex", justifyContent: "center", gap: 12, marginTop: 20 }}>
          {question > 1 && <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => setQuestion(question - 1)}>Back</button>}
          <button className="bfg-btn bfg-btn-primary" disabled={busy || !(answers[String(question)] || "").trim()} onClick={continueQuestion} data-testid="bfg-five-continue">{busy ? "SAVING…" : "NEXT"}</button>
        </div>
      </> : <>
        <h1>How Would You Be Comfortable Supporting Fundraising?</h1>
        <p style={{ margin: "18px auto 0" }}>You have shared your five ideas. Tell us how you would personally like to participate, including any relationships, introductions or actions you are comfortable taking.</p>
        <textarea rows={7} maxLength={6000} value={involvement} onChange={(event) => setInvolvement(event.target.value)}
          placeholder="I would be comfortable helping by…" data-testid="bfg-five-involvement"
          style={{ width: "100%", marginTop: 24, padding: 18, border: "1px solid #cbd5e1", borderRadius: 12, fontSize: 17, lineHeight: 1.6 }} />
        <SpeakButton value={involvement} onChange={setInvolvement} />
        {error && <p className="bfg-error">{error}</p>}
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy || !involvement.trim()} onClick={complete} data-testid="bfg-five-complete">{busy ? "SAVING…" : "COMPLETE MY INDIVIDUAL GAME"}</button>
      </>}
    </>}
  </main></BfgShell>;
}
