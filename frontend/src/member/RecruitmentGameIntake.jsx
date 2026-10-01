import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { NarrationControl, isNarrationMuted } from "@/game/NarrationControl";
import { memberApi } from "./api";
import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;

const QUESTIONS = [
  {
    key: "mission",
    audio: "rct_question_1",
    heading: "Tell Us Your Mission Statement",
    question: "What does your organization exist to achieve, who do you serve and what change are you trying to create?",
    helper: "Your mission helps us understand the kind of experience, credibility and relationships that belong around your board table.",
    type: "textarea",
  },
  {
    key: "current_board",
    audio: "rct_question_2",
    heading: "Tell Us About The Board Members You Have Today",
    question: "Who is presently on your board, and how does each person help the organization?",
    helper: "Tell us what each person actually brings: professional expertise, relationships, lived experience, fundraising, governance, community knowledge or another contribution. If you have no board members yet, say that.",
    type: "textarea",
  },
  {
    key: "desired_board_members",
    audio: "rct_question_3",
    heading: "What Board Members Do You Think You Need?",
    question: "What kind of people do you already believe your organization should recruit to the board?",
    helper: "Use your own judgment here. You may already be thinking about a fundraiser, accountant, lawyer, marketer, community leader, corporate executive or another kind of person. We will preserve your thinking and evaluate it together with the rest of your answers.",
    type: "textarea",
  },
  {
    audio: "rct_question_4",
    heading: "Where Is Your Organization Right Now?",
    question: "What is happening in your organization right now, and what are the most important things you want your board to help you accomplish next?",
    helper: "Tell us about your current situation and priorities in your own words. We will use this alongside the organization details you already gave us.",
    key: "board_type",
    type: "textarea",
  },
  {
    key: "support_needs",
    audio: "rct_question_5",
    heading: "Where Do You Need Their Support?",
    question: "How many new board members do you want to bring in, and in which areas does your organization need their support most?",
    helper: "You can change the number you gave us if your thinking has shifted. Think about leadership, relationships, fundraising, governance, and the work ahead.",
    type: "textarea",
  },
  {
    key: "why_join",
    audio: "rct_question_6",
    heading: "What Do You Already Have, And What Is Missing?",
    question: "Looking at your board and the people around your organization, what skills, experience, relationships or capabilities do you already have, and what is still missing?",
    helper: "Include strengths beyond the current board if they are available to your organization. This helps us avoid recommending more of what you already have.",
    type: "textarea",
  },
];

export const RecruitmentGameIntake = ({ onComplete, publicToken = "" }) => {
  const [assessment, setAssessment] = useState(null);
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(0);
  const [desiredCount, setDesiredCount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);

  useEffect(() => {
    const load = publicToken
      ? axios.get(`${BASE}/api/recruit/free/${encodeURIComponent(publicToken)}`)
      : memberApi.get("/recruit/free/member-assessment/current");
    load.then(({ data }) => {
      setAssessment(data);
      setDesiredCount(data.desired_count ? String(data.desired_count) : "not_sure");
      const loaded = data.answers || {};
      setAnswers(loaded);
      const first = QUESTIONS.findIndex(({ key }) => !String(loaded[key] || "").trim());
      setStep(first < 0 ? QUESTIONS.length : first);
    }).catch((e) => setError(e.response?.data?.detail || "We could not open your six Recruitment Questions."));
  }, [publicToken]);

  useEffect(() => {
    memberApi.get("/game/voice/tutorial/recruitment")
      .then(({ data }) => setClips(data.clips || {}))
      .catch(() => {});
    return () => { if (audioRef.current) audioRef.current.pause(); };
  }, []);

  const play = useCallback((id) => {
    if (audioRef.current) audioRef.current.pause();
    if (isNarrationMuted()) return;
    const clip = clips[id];
    if (!clip?.ready) return;
    const audio = new Audio(`${BASE}${clip.url}`);
    audioRef.current = audio;
    audio.play().catch(() => {});
  }, [clips]);

  useEffect(() => {
    if (step < 3) play(QUESTIONS[step].audio);
  }, [step, clips, play]);

  const effectiveAnswer = (question) => {
    return String(answers[question.key] || "").trim();
  };

  const save = async () => {
    const question = QUESTIONS[step];
    const text = effectiveAnswer(question);
    if (!text) return;
    setBusy(true); setError("");
    try {
      const payload = { question: step + 1, text, ...(step === 4 ? { desired_count: desiredCount || "not_sure" } : {}) };
      if (publicToken) await axios.put(`${BASE}/api/recruit/free/${encodeURIComponent(publicToken)}/answer`, payload);
      else await memberApi.put(`/recruit/free/${assessment.token}/answer`, payload);
      setAnswers((current) => ({
        ...current,
        [question.key]: text,
      }));
      if (step < QUESTIONS.length - 1) setStep(step + 1);
      else {
        setStep(QUESTIONS.length);
        onComplete?.();
      }
    } catch (e) {
      setError(e.response?.data?.detail || "We could not save this answer.");
    }
    setBusy(false);
  };

  if (!assessment) return <div className="sgr-question-loading">{error || "Opening your Recruitment Questions…"}</div>;

  if (step === QUESTIONS.length) return (
    <div className="sgr-question-complete" data-testid="recruitment-questions-complete">
      <CheckCircle2 size={52} />
      <p className="eyebrow">SIX QUESTIONS COMPLETE</p>
      <h2>Your Recruitment Assessment Is Complete</h2>
      <p>Your answers are saved. Unlock your campaign to see the exact board profiles recommended for your organization, review your materials, and launch recruitment.</p>
      <div className="sgr-row-actions">
        <button className="button button-outline" onClick={() => setStep(0)}>REVIEW MY ANSWERS</button>
        <button className="button" onClick={onComplete}>{publicToken ? "UNLOCK MY CAMPAIGN" : "CONTINUE TO CAMPAIGN"}</button>
      </div>
    </div>
  );

  const question = QUESTIONS[step];
  const currentValue = answers[question.key] || "";
  const canContinue = Boolean(effectiveAnswer(question));

  return (
    <div className="sgr-question-screen" data-testid={`recruitment-question-${step + 1}`}>
      <div className="sgr-question-topline">
        <span>QUESTION {step + 1} OF {QUESTIONS.length}</span>
        {step < 3 && <NarrationControl audioRef={audioRef} onReplay={() => play(question.audio)} />}
      </div>
      <div className="sgr-question-progress" aria-hidden="true">
        {QUESTIONS.map((_, index) => <span key={index} className={index <= step ? "active" : ""} />)}
      </div>
      <div className="sgr-question-copy">
        <h1>{question.heading}</h1>
        <p className="sgr-question-prompt">{question.question}</p>
        <p className="sgr-question-helper">{question.helper}</p>
      </div>

      <div className="sgr-question-answer">
        <textarea
            rows={7}
            value={currentValue}
            onChange={(event) => setAnswers({ ...answers, [question.key]: event.target.value })}
            placeholder="Type your answer in your own words…"
            data-testid={`recruitment-question-${step + 1}-input`}
          />
      </div>
      {step === 4 && <label className="field"><span>How many new Board Members do you want to recruit?</span>
        <select value={desiredCount} onChange={(event) => setDesiredCount(event.target.value)} data-testid="recruitment-desired-count">
          <option value="not_sure">I'm not sure yet</option>
          {Array.from({ length: 50 }, (_, index) => <option value={String(index + 1)} key={index + 1}>{index + 1}</option>)}
        </select>
      </label>}

      {error && <p className="submit-error">{error}</p>}
      <div className="sgr-question-actions">
        {step > 0 && <button className="button button-outline" onClick={() => setStep(step - 1)}>BACK</button>}
        <button className="button" disabled={busy || !canContinue} onClick={save}>
          {busy ? "SAVING…" : step === QUESTIONS.length - 1 ? "SAVE MY ANSWERS" : "NEXT QUESTION"}
        </button>
      </div>
    </div>
  );
};
