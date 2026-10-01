import { useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import GuidedAudioButton from "@/game/GuidedAudioButton";
import { useGuidedNarration } from "@/game/useGuidedNarration";
import { SpeakButton } from "@/game/SpeakButton";
import { memberApi } from "./api";
import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;
const INTRO = "Welcome. In six questions, tell me about your mission, the board you have now and the support you need. Say what is true for your organization, in your own words. We will use your answers to recommend the board members you should recruit. Ready? Let's begin.";

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
  const [started, setStarted] = useState(!publicToken);
  const [desiredCount, setDesiredCount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const activeQuestion = QUESTIONS[step];
  const narration = useGuidedNarration("recruitment", assessment ? started ? activeQuestion?.audio : "rct_welcome" : "", started ? activeQuestion?.question : INTRO);

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
      if (first > 0 || first < 0) setStarted(true);
    }).catch((e) => setError(e.response?.data?.detail || "We could not open your six Recruitment Questions."));
  }, [publicToken]);

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

  if (!started && publicToken) return <section className="sgr-public-question-welcome" data-testid="recruitment-questions-welcome">
    <div className="sgr-question-topline"><span>YOUR BOARD RECRUITMENT</span><GuidedAudioButton narration={narration} /></div>
    <h1>Let's identify the board members your organization needs.</h1>
    <p>Six questions will help us understand your mission, your current board, the people you believe you need and where you need their support.</p>
    <p>Speak or type as the answers come to mind. You don't need to sound formal. We will use your own thinking to recommend the board members to recruit.</p>
    <button type="button" className="button" onClick={() => { narration.stop(); setStarted(true); }} data-testid="recruitment-start-six">START MY SIX QUESTIONS</button>
  </section>;

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
        <GuidedAudioButton narration={narration} />
      </div>
      <div className="sgr-question-progress" aria-hidden="true">
        {QUESTIONS.map((_, index) => <span key={index} className={index <= step ? "active" : ""} />)}
      </div>
      <div className="sgr-question-copy">
        <h1>{question.question}</h1>
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
        <SpeakButton value={currentValue} onChange={(value) => setAnswers((current) => ({ ...current, [question.key]: value }))} testId={`recruitment-question-${step + 1}-speak`} />
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
