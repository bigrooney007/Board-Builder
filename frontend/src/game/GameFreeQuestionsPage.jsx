import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, money } from "./gameShared";
import { FIVE_QUESTIONS, fiveQuestionText } from "./gameFiveQuestions";

export default function GameFreeQuestionsPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [context, setContext] = useState(null);
  const [answers, setAnswers] = useState({});
  const [question, setQuestion] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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
        else setQuestion(response.data.next_question || 1);
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

  return <BfgShell><main className="bfg-flow" style={{ maxWidth: 780, margin: "0 auto", padding: "36px 20px 90px", textAlign: "center" }} data-testid="bfg-free-questions">
    {!context ? <p>{error || "Opening your Board Fundraising Game…"}</p> : <>
      <p className="bfg-eyebrow">YOUR BOARD FUNDRAISING GAME • QUESTION {question} OF 5</p>
      <p style={{ margin: "10px auto 24px" }}><strong>{context.organization_name}</strong> • Fundraising goal: <strong>{money(context.goal_amount)}</strong></p>
      <h1 data-testid="bfg-free-question">{fiveQuestionText(question - 1, answers["1"])}</h1>
      {question === 1 && <p style={{ margin: "18px auto 0", maxWidth: 660 }}>{FIVE_QUESTIONS[0].hint}</p>}
      <textarea rows={7} maxLength={6000} value={answers[String(question)] || ""}
        onChange={(event) => setAnswers({ ...answers, [String(question)]: event.target.value })}
        placeholder="Tell us what you think, in your own words…" aria-label={`Answer to question ${question}`}
        data-testid="bfg-free-answer" style={{ width: "100%", marginTop: 24, padding: 18, border: "1px solid #cbd5e1", borderRadius: 12, fontSize: 17, lineHeight: 1.6 }} />
      <p style={{ marginTop: 10, fontSize: 14 }}>Your answer is saved exactly as you give it.</p>
      {error && <p className="bfg-error">{error}</p>}
      <div style={{ display: "flex", justifyContent: "center", gap: 12, marginTop: 22 }}>
        {question > 1 && <button className="bfg-btn bfg-btn-ghost" onClick={() => setQuestion(question - 1)} disabled={busy}>Back</button>}
        <button className="bfg-btn bfg-btn-primary" onClick={continueGame} disabled={busy || !(answers[String(question)] || "").trim()} data-testid="bfg-free-continue">{busy ? "SAVING…" : question === 5 ? "CONTINUE" : "NEXT QUESTION"}</button>
      </div>
    </>}
  </main></BfgShell>;
}
