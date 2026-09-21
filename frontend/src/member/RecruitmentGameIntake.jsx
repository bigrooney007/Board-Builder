import { useEffect, useState } from "react";
import { memberApi } from "./api";

const QUESTIONS = [
  ["mission", "Tell Us About Your Organization's Mission", "What does your organization exist to achieve, who do you serve and what change are you trying to create?"],
  ["current_board", "Tell Us About The Board You Have Today", "How many board members do you currently have, and how does each person presently help your organization?"],
  ["important_areas", "Identify What Moves Your Organization Forward", "List the areas your organization needs to do really well in order to grow, raise money and achieve its mission."],
  ["support_needs", "Identify Where New Board Members Must Support You", "Which areas do you specifically need new board members to help your organization with right now, and why?"],
];

export const RecruitmentGameIntake = ({ onComplete, returnOnComplete = false }) => {
  const [assessment, setAssessment] = useState(null);
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    memberApi.get("/recruit/free/member-assessment/current").then(({ data }) => {
      setAssessment(data); setAnswers(data.answers || {});
      const first = QUESTIONS.findIndex(([key]) => !(data.answers || {})[key]);
      setStep(first < 0 ? 4 : first);
    }).catch((e) => setError(e.response?.data?.detail || "We could not open your Recruitment Game."));
  }, []);
  const save = async () => {
    const [key] = QUESTIONS[step]; const text = String(answers[key] || "").trim();
    if (!text) return;
    setBusy(true); setError("");
    try {
      await memberApi.put(`/recruit/free/${assessment.token}/answer`, { question: step + 1, text });
      if (step < 3) setStep(step + 1);
      else {
        const response = await memberApi.post(`/recruit/free/${assessment.token}/result`);
        setAssessment({ ...assessment, result: response.data.result });
        if (returnOnComplete) onComplete?.(); else setStep(4);
      }
    } catch (e) { setError(e.response?.data?.detail || "We could not save this answer."); }
    setBusy(false);
  };
  if (!assessment) return <p>{error || "Opening your Recruitment Game…"}</p>;
  if (step === 4) return <div data-testid="recruitment-game-complete">
    <p className="member-success"><strong>Your Recruitment Game is complete.</strong> Your answers now power the board-member profiles and recruitment materials below.</p>
    {(assessment.result?.priority_roles || []).map((role, index) => <article className="sgr-result-item" key={index}><h3>{role.role_name}</h3><p>{role.why_this_person_is_important} {role.how_this_person_can_support}</p></article>)}
    <button className="button button-small button-outline" onClick={() => setStep(0)}>REVIEW MY ANSWERS</button>
  </div>;
  const [key, heading, question] = QUESTIONS[step];
  return <div data-testid={`recruitment-game-question-${step + 1}`}>
    <p className="eyebrow">QUESTION {step + 1} OF 4</p><h3>{heading}</h3><p><strong>{question}</strong></p>
    <textarea rows={7} value={answers[key] || ""} onChange={(e) => setAnswers({ ...answers, [key]: e.target.value })} placeholder="Type your answer in your own words…" />
    {error && <p className="submit-error">{error}</p>}
    <div className="sgr-row-actions">{step > 0 && <button className="button button-small button-outline" onClick={() => setStep(step - 1)}>BACK</button>}<button className="button button-small" disabled={busy || !String(answers[key] || "").trim()} onClick={save}>{busy ? "SAVING…" : step === 3 ? "SHOW ME WHO WE NEED TO RECRUIT" : "CONTINUE"}</button></div>
  </div>;
};
