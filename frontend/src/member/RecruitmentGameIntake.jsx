import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { NarrationControl, isNarrationMuted } from "@/game/NarrationControl";
import { memberApi } from "./api";

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
    key: "support_needs",
    audio: "rct_question_4",
    heading: "Where Does Your Organization Need More Board Support?",
    question: "What areas need stronger support, experience, relationships or leadership, and why?",
    helper: "Think about where the organization is struggling, where leadership capacity is thin, what relationships are missing and what expertise would help the organization move forward.",
    type: "textarea",
  },
  {
    key: "board_type",
    audio: "rct_question_5",
    heading: "What Kind Of Board Do You Want To Build?",
    question: "Choose the option that best describes how you want your board to function.",
    helper: "This helps us recommend people who fit the way you actually want the board to work.",
    type: "select",
    options: [
      "Working Board",
      "Governance Board",
      "Advisory Board",
      "Hybrid Working + Governance Board",
      "I am not sure yet",
      "Other",
    ],
  },
  {
    key: "why_join",
    audio: "rct_question_6",
    heading: "Why Should Anybody Join Your Board?",
    question: "What would make serving on your board meaningful or valuable to the right person?",
    helper: "Think about the mission they can help advance, what they can help build, the influence they can have, the people they can serve, the relationships they can develop or the leadership experience they can gain.",
    type: "textarea",
  },
];

export const RecruitmentGameIntake = ({ onComplete }) => {
  const [assessment, setAssessment] = useState(null);
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(0);
  const [otherBoardType, setOtherBoardType] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);

  useEffect(() => {
    memberApi.get("/recruit/free/member-assessment/current").then(({ data }) => {
      setAssessment(data);
      const loaded = data.answers || {};
      setAnswers(loaded);
      const first = QUESTIONS.findIndex(({ key }) => !String(loaded[key] || "").trim());
      setStep(first < 0 ? QUESTIONS.length : first);
      if (loaded.board_type && !QUESTIONS[4].options.includes(loaded.board_type)) {
        setAnswers((current) => ({ ...current, board_type: "Other" }));
        setOtherBoardType(loaded.board_type);
      }
    }).catch((e) => setError(e.response?.data?.detail || "We could not open your six Recruitment Questions."));
  }, []);

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
    if (step < QUESTIONS.length) play(QUESTIONS[step].audio);
  }, [step, clips, play]);

  const effectiveAnswer = (question) => {
    if (question.key === "board_type" && answers.board_type === "Other") return otherBoardType.trim();
    return String(answers[question.key] || "").trim();
  };

  const save = async () => {
    const question = QUESTIONS[step];
    const text = effectiveAnswer(question);
    if (!text) return;
    setBusy(true); setError("");
    try {
      await memberApi.put(`/recruit/free/${assessment.token}/answer`, { question: step + 1, text });
      setAnswers((current) => ({
        ...current,
        [question.key]: question.key === "board_type" && current.board_type === "Other" ? "Other" : text,
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
      <h2>Your Recruitment Context Is Saved</h2>
      <p>We are already using your answers to identify the exact board members your organization needs. You can return to the dashboard while that work continues underneath.</p>
      <div className="sgr-row-actions">
        <button className="button button-outline" onClick={() => setStep(0)}>REVIEW MY ANSWERS</button>
        <button className="button" onClick={onComplete}>RETURN TO DASHBOARD</button>
      </div>
    </div>
  );

  const question = QUESTIONS[step];
  const currentValue = question.key === "board_type" ? answers.board_type || "" : answers[question.key] || "";
  const canContinue = Boolean(effectiveAnswer(question));

  return (
    <div className="sgr-question-screen" data-testid={`recruitment-question-${step + 1}`}>
      <div className="sgr-question-topline">
        <span>QUESTION {step + 1} OF {QUESTIONS.length}</span>
        <NarrationControl audioRef={audioRef} onReplay={() => play(question.audio)} />
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
        {question.type === "select" ? (
          <>
            <div className="sgr-board-type-grid">
              {question.options.map((option) => (
                <button
                  type="button"
                  key={option}
                  className={`sgr-choice-card ${currentValue === option ? "selected" : ""}`}
                  onClick={() => setAnswers({ ...answers, board_type: option })}
                >
                  {option}
                </button>
              ))}
            </div>
            {currentValue === "Other" && (
              <input
                autoFocus
                value={otherBoardType}
                onChange={(event) => setOtherBoardType(event.target.value)}
                placeholder="Describe the kind of board you want to build"
                data-testid="recruitment-question-5-other"
              />
            )}
          </>
        ) : (
          <textarea
            rows={7}
            value={currentValue}
            onChange={(event) => setAnswers({ ...answers, [question.key]: event.target.value })}
            placeholder="Type your answer in your own words…"
            data-testid={`recruitment-question-${step + 1}-input`}
          />
        )}
      </div>

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
