import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Plus, Trash2 } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import SpeakButton from "@/game/SpeakButton";
import "./guided-products.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const RECOMMITMENT = [
  { key: "mission", title: "Start with your mission", prompt: "What is your organization's mission statement?", help: "Use the words you already use to describe why your organization exists." },
  { key: "why_recommit", title: "Why now", prompt: "Why do you need your board members to recommit and step up now?", help: "Tell us what has changed, where the board has become quiet, and why this matters now." },
  { key: "board_help_accomplish", title: "What the board can help build", prompt: "What do you need these board members to help the organization accomplish?", help: "Think about the work and outcomes you need people to take real responsibility for." },
  { key: "need_by", title: "Your deadline", prompt: "By when do you need the board to recommit and begin operating in these roles?", help: "Choose the date that will guide the conversations with your board.", type: "date" },
];
const STRATEGIC = [
  { key: "mission", title: "Mission", prompt: "What is your organization's mission statement?", help: "Give us the mission as it stands today. Your board can review it together later." },
  { key: "goals", title: "Goals", prompt: "What is your organization trying to achieve over the next one to two years?", help: "Tell us what you want to change, grow or make possible." },
  { key: "objectives", title: "Objectives", prompt: "What specific results are you working toward to reach those goals?", help: "Share the milestones you have in mind, even if the plan is not yet perfect." },
  { key: "program_details", title: "Programs", type: "programs", prompt: "Tell us about this program or service.", help: "Each program will have its own place in your board's planning conversation." },
  { key: "team_building", title: "Team and leadership", prompt: "Who is helping you carry the work, and where do you need more leadership capacity?", help: "Include your staff, volunteers, board members, contractors and the work you still carry yourself." },
  { key: "technology", title: "Technology", prompt: "What tools help you run the organization, and what still slows you down?", help: "Tell us about the systems you use today and what you need them to do better." },
  { key: "marketing", title: "Marketing", prompt: "How are people finding and hearing about your organization today?", help: "Who are you trying to reach, and where could your visibility grow?" },
  { key: "partnerships", title: "Partnerships", prompt: "Which relationships are helping you now, and which partners do you need next?", help: "Think about organizations, businesses, institutions and people you want to work alongside." },
  { key: "fundraising", title: "Fundraising", prompt: "How are you raising money now, and what needs to change?", help: "Tell us what has worked, what has been difficult and what you want to build with your board." },
  { key: "budget", title: "Budget", prompt: "What does it cost to run and grow this organization?", help: "Share the numbers you know and say where you are still estimating. You do not need to invent figures." },
  { key: "action_planning", title: "Action plan", prompt: "What do you want to do in the next few months and over the next few years?", help: "Tell us the actions already on your mind. Your board will help turn them into an agreed plan." },
];
const blankProgram = () => ({ name: "", description: "", present_work: "" });
const firstMissing = (steps, answers) => {
  const found = steps.findIndex((step) => step.type === "programs"
    ? !(answers.program_details?.[step.programIndex]?.name || "").trim()
    : !String(answers[step.key] || "").trim());
  return found < 0 ? steps.length - 1 : found;
};

export default function GuidedPrepaymentQuestionsPage({ product }) {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") || localStorage.getItem(`guidedLead:${product}`) || "";
  const [lead, setLead] = useState(null);
  const [answers, setAnswers] = useState({ program_details: [blankProgram()] });
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [spokenDate, setSpokenDate] = useState("");
  const ready = useRef(false);
  const saveChain = useRef(Promise.resolve());
  const isStrategic = product === "strategic-planning";
  const base = isStrategic ? STRATEGIC : RECOMMITMENT;
  const steps = useMemo(() => base.flatMap((step) => step.type === "programs"
    ? (answers.program_details || [blankProgram()]).map((_, programIndex) => ({ ...step, programIndex }))
    : [step]), [base, answers.program_details]);
  const persist = useCallback((draft) => {
    const next = saveChain.current.catch(() => {}).then(() => axios.put(`${API}/guided/context/${token}/answers`, { answers: draft }));
    saveChain.current = next;
    return next;
  }, [token]);

  useEffect(() => {
    document.title = `${isStrategic ? "Your Strategic Planning" : "Your Board Recommitment"} Questions | Nonprofit Board Builder`;
    if (!token) { navigate(`/${product}`, { replace: true }); return; }
    localStorage.setItem(`guidedLead:${product}`, token);
    axios.get(`${API}/guided/context/${token}`).then(({ data }) => {
      if (data.product !== product) throw new Error("This link belongs to another process.");
      setLead(data);
      const saved = data.prepayment_answers || {};
      let latest = saved;
      try {
        const draft = JSON.parse(localStorage.getItem(`guidedDraft:${product}:${token}`) || "null");
        if (draft?.updated_at > (data.updated_at || "") && draft.answers) latest = draft.answers;
      } catch { /* the server copy is still available */ }
      const restored = { ...latest, program_details: latest.program_details?.length ? latest.program_details : [blankProgram()] };
      setAnswers(restored);
      const initialSteps = base.flatMap((step) => step.type === "programs"
        ? restored.program_details.map((_, programIndex) => ({ ...step, programIndex })) : [step]);
      setIndex(firstMissing(initialSteps, restored));
      ready.current = true;
    }).catch(() => setError("We could not open your saved answers. Please use the link from your email."))
      .finally(() => setLoading(false));
  }, [token, product, navigate, isStrategic, base]);

  useEffect(() => {
    if (!ready.current || !lead) return undefined;
    localStorage.setItem(`guidedDraft:${product}:${token}`, JSON.stringify({ answers, updated_at: new Date().toISOString() }));
    const timer = setTimeout(() => {
      persist(answers).catch(() => {});
    }, 1200);
    return () => clearTimeout(timer);
  }, [answers, token, lead, product, persist]);

  const step = steps[index];
  const last = index === steps.length - 1;
  const currentValue = step?.type === "programs" ? answers.program_details?.[step.programIndex] : answers[step?.key];
  const valid = step?.type === "programs" ? Boolean(currentValue?.name?.trim()) : Boolean(String(currentValue || "").trim());
  const save = async () => {
    if (!valid) { setError(step?.type === "programs" ? "Give this program a name before continuing." : "Share your answer before continuing."); return; }
    setBusy(true); setError("");
    try {
      const result = await persist(answers);
      if (last) {
        if (!result.data.complete) throw new Error("Please complete every section before continuing.");
        navigate(lead?.facilitated_by_admin && isStrategic
          ? `/strategic-planning/facilitated-complete?token=${encodeURIComponent(token)}`
          : `/${product}/video?token=${encodeURIComponent(token)}`);
      } else {
        setIndex(index + 1);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    } catch (err) { setError(err.response?.data?.detail || err.message || "We could not save your answer. Please try again."); }
    setBusy(false);
  };
  const updateProgram = (field, value) => setAnswers((old) => ({ ...old, program_details: old.program_details.map((program, i) => i === step.programIndex ? { ...program, [field]: value } : program) }));
  const addProgram = async () => {
    if (!valid) { setError("Give this program a name before adding another."); return; }
    setBusy(true); setError("");
    try {
      await persist(answers);
      setAnswers((old) => ({ ...old, program_details: [...old.program_details, blankProgram()] }));
      setIndex(index + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch { setError("We could not save this program yet."); }
    setBusy(false);
  };
  const removeProgram = () => {
    if (answers.program_details.length <= 1) return;
    setAnswers((old) => ({ ...old, program_details: old.program_details.filter((_, i) => i !== step.programIndex) }));
    setIndex((old) => Math.max(0, old - 1));
  };
  const dateFromVoice = (speech) => {
    setSpokenDate(speech);
    const parsed = new Date(speech);
    if (!Number.isNaN(parsed.getTime())) setAnswers((old) => ({ ...old, need_by: `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}-${String(parsed.getDate()).padStart(2, "0")}` }));
  };

  return <BfgShell><main className="guided-preflow" data-testid={`${product}-prepayment-questions`}>
    {loading ? <p>Opening your saved process…</p> : !lead || !step ? <p role="alert">{error}</p> : <section className="guided-preflow-card">
      <p className="guided-preflow-kicker">{isStrategic ? "STRATEGIC PLANNING" : "BOARD RECOMMITMENT"} · {index + 1} OF {steps.length}</p>
      <div className="guided-preflow-progress" aria-hidden="true"><span style={{ width: `${((index + 1) / steps.length) * 100}%` }} /></div>
      <p className="guided-preflow-title">{step.type === "programs" ? `PROGRAM ${step.programIndex + 1}` : step.title}</p>
      <h1>{step.prompt}</h1>
      <p className="guided-preflow-help">{step.help}</p>
      {step.type === "programs" ? <div className="guided-preflow-fields">
        <label>Program or service name<input value={currentValue?.name || ""} onChange={(e) => updateProgram("name", e.target.value)} placeholder="What do you call this program?" /><SpeakButton value={currentValue?.name || ""} onChange={(value) => updateProgram("name", value)} /></label>
        <label>Who does it serve, and what does it do?<textarea rows="4" value={currentValue?.description || ""} onChange={(e) => updateProgram("description", e.target.value)} placeholder="Tell us in your own words." /><SpeakButton value={currentValue?.description || ""} onChange={(value) => updateProgram("description", value)} /></label>
        <label>What is happening in this program today?<textarea rows="4" value={currentValue?.present_work || ""} onChange={(e) => updateProgram("present_work", e.target.value)} placeholder="What is working, and what would you like to improve?" /><SpeakButton value={currentValue?.present_work || ""} onChange={(value) => updateProgram("present_work", value)} /></label>
        <div className="guided-preflow-program-actions"><button type="button" className="bfg-btn bfg-btn-ghost" disabled={busy || !valid || answers.program_details.length >= 20} onClick={addProgram}><Plus size={17} /> ADD ANOTHER PROGRAM</button>{answers.program_details.length > 1 && <button type="button" className="bfg-btn bfg-btn-ghost" onClick={removeProgram}><Trash2 size={16} /> REMOVE THIS PROGRAM</button>}</div>
      </div> : <div className="guided-preflow-fields"><label className="guided-preflow-answer-label">Your answer
        {step.type === "date" ? <input type="date" value={currentValue || ""} onChange={(e) => setAnswers((old) => ({ ...old, need_by: e.target.value }))} />
          : <textarea rows="8" value={currentValue || ""} onChange={(e) => setAnswers((old) => ({ ...old, [step.key]: e.target.value }))} placeholder="Say it as it comes to mind. You can refine it later." />}
      </label><SpeakButton value={step.type === "date" ? spokenDate : currentValue || ""} onChange={step.type === "date" ? dateFromVoice : (value) => setAnswers((old) => ({ ...old, [step.key]: value }))} />{step.type === "date" && spokenDate && <p>Heard: {spokenDate}. Check that the date above is right before continuing.</p>}</div>}
      <p className="guided-preflow-saved">Your answers are saved as you go. You can return through your personal link.</p>
      {error && <p className="bfg-error" role="alert">{error}</p>}
      <div className="guided-preflow-navigation"><button type="button" className="bfg-btn bfg-btn-ghost" onClick={() => index ? setIndex(index - 1) : navigate(`/${product}`)}><ArrowLeft size={17} /> BACK</button><button type="button" className="bfg-btn bfg-btn-primary" disabled={busy} onClick={save}>{busy ? "SAVING…" : last ? "SEE HOW WE MOVE FORWARD" : "SAVE AND CONTINUE"} <ArrowRight size={17} /></button></div>
    </section>}
  </main></BfgShell>;
}
