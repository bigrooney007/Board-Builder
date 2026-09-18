import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { BfgShell } from "@/game/gameShared";
import RecruitmentHomePage from "@/funnels/RecruitmentHomePage";
import "@/game/game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE = process.env.REACT_APP_BACKEND_URL;

const QUESTIONS = [
  { key: "mission", clip: "recruitment-free-question-1-mission", progress: "QUESTION 1 OF 4",
    heading: "Tell Us About Your Organization's Mission.",
    question: "What does your organization exist to achieve, who do you serve and what change are you trying to create?",
    helper: ["Tell us in your own words. You don't need to make it sound formal."], button: "CONTINUE" },
  { key: "current_board", clip: "recruitment-free-question-2-current-board", progress: "QUESTION 2 OF 4",
    heading: "Tell Us About The Board You Have Today.",
    question: "How many board members do you currently have, and how does each person presently help your organization?",
    helper: ["You can tell us their roles, skills, experience or the areas they normally help with.",
      "Example:", "\u201c5 board members. One is an accountant and helps with finance. One works in education and helps with programs. One has strong community relationships. The other two mainly provide general support.\u201d",
      "If you do not currently have board members, simply tell us that."], button: "CONTINUE" },
  { key: "important_areas", clip: "recruitment-free-question-3-important-areas", progress: "QUESTION 3 OF 4",
    heading: "What Are The Most Important Areas That Help Move Your Organization Forward?",
    question: "List the areas your organization needs to do really well in order to grow, raise money and achieve its mission.",
    helper: ["Think about the functions that genuinely matter to the success of your organization.",
      "For example:", "Fundraising", "Marketing", "Sales", "Partnerships", "Community engagement", "Programs", "Finance", "Operations", "Technology", "Legal", "Government relations", "Volunteer management", "Corporate relationships", "Grant development", "Communications", "Lived experience",
      "Add whatever is important to your organization."], button: "CONTINUE" },
  { key: "support_needs", clip: "recruitment-free-question-4-support-needed", progress: "QUESTION 4 OF 4",
    heading: "Where Do You Need New Board Members To Support You Right Now?",
    question: "Which areas do you specifically need new board members to help your organization with right now, and why?",
    helper: ["Think about the areas you just identified as important.", "Which ones need stronger board-level support?",
      "Where are you currently struggling?", "What experience, relationships or leadership are you hoping new board members will bring?"],
    button: "SHOW ME WHO I NEED TO RECRUIT" },
];

export default function RecruitFreePage() {
  const navigate = useNavigate();
  const [stage, setStage] = useState("landing"); // landing | q0..q3 | generating | result
  const [lead, setLead] = useState({ name: "", email: "", organization: "", count: "", notSure: false });
  const [assessment, setAssessment] = useState(null);
  const [answers, setAnswers] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);

  useEffect(() => { document.title = "Board Recruitment | Nonprofit Board Builder"; }, []);
  useEffect(() => {
    axios.get(`${API}/game/voice/tutorial/recruitment-free`).then((r) => setClips(r.data.clips || {})).catch(() => {});
    return () => { if (audioRef.current) audioRef.current.pause(); };
  }, []);

  const play = useCallback((id) => {
    if (audioRef.current) audioRef.current.pause();
    const clip = clips[id];
    if (!clip?.ready) return;
    const audio = new Audio(`${BASE}${clip.url}`);
    audioRef.current = audio;
    audio.play().catch(() => {});
  }, [clips]);

  const resumeFrom = useCallback((doc) => {
    setAssessment(doc);
    setAnswers(doc.answers || {});
    if (doc.result) { setStage("result"); return; }
    const idx = QUESTIONS.findIndex((q) => !(doc.answers || {})[q.key]);
    setStage(idx === -1 ? "generating" : `q${idx}`);
  }, []);

  // The public recruitment homepage always starts clean. A previous person's
  // assessment on this browser must never hijack a new visitor's journey.
  useEffect(() => { localStorage.removeItem("recruitFreeToken"); }, []);

  useEffect(() => {
    if (stage === "landing") play("recruitment-free-entry");
    else if (stage.startsWith("q")) play(QUESTIONS[Number(stage.slice(1))].clip);
    else if (stage === "result") play("recruitment-free-result");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, clips]);

  const start = async () => {
    localStorage.removeItem("recruitFreeToken");
    if (!lead.name.trim() || !lead.email.trim() || !lead.organization.trim() || (!lead.count.trim() && !lead.notSure)) {
      setError("Please complete every field, or choose I'M NOT SURE YET."); return;
    }
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/recruit/free/start`, {
        name: lead.name.trim(), email: lead.email.trim(), organization: lead.organization.trim(),
        desired_count: lead.notSure ? "not_sure" : lead.count.trim(),
      });
      localStorage.setItem("recruitFreeToken", response.data.token);
      resumeFrom(response.data);
    } catch { setError("We could not start your assessment. Please check your details and try again."); }
    setBusy(false);
  };

  const saveAnswer = async (index) => {
    const q = QUESTIONS[index];
    const text = (answers[q.key] || "").trim();
    if (!text) return;
    setBusy(true); setError("");
    try {
      await axios.put(`${API}/recruit/free/${assessment.token}/answer`, { question: index + 1, text });
      if (index < 3) setStage(`q${index + 1}`);
      else {
        setStage("generating");
        const response = await axios.post(`${API}/recruit/free/${assessment.token}/result`);
        setAssessment((current) => ({ ...current, result: response.data.result }));
        setStage("result");
      }
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your answer. Please try again.");
      if (index === 3) setStage("q3");
    }
    setBusy(false);
  };

  const field = { width: "100%", marginTop: 10, padding: 14, border: "1px solid #d1d5db", borderRadius: 12, fontSize: 15 };
  const shell = (children, testId) => (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 680, margin: "0 auto", padding: "40px 20px 90px" }} data-testid={testId}>
        {children}
        {error && <p className="bfg-error" data-testid="recruit-free-error">{error}</p>}
      </main>
    </BfgShell>
  );

  if (stage === "landing") {
    const leadForm = (
      <div data-testid="recruit-free-landing" style={{ textAlign: "center" }}>
        <h3 style={{ marginTop: 0, fontSize: 22, lineHeight: 1.3 }} data-testid="recruit-free-heading">Answer 4 Questions To Identify The Exact Board Members Your Nonprofit Needs To Recruit</h3>
        <p style={{ marginTop: 14 }}>Tell us about your mission, the board you have today, what your organization needs to move forward and where you need board support.</p>
        <p style={{ marginTop: 10 }}>We will show you the exact type of people you should recruit and then show you how to recruit them yourself.</p>
        <input style={field} placeholder="Your Name" value={lead.name} onChange={(e) => setLead({ ...lead, name: e.target.value })} data-testid="recruit-free-name" />
        <input style={field} placeholder="Email Address" type="email" value={lead.email} onChange={(e) => setLead({ ...lead, email: e.target.value })} data-testid="recruit-free-email" />
        <input style={field} placeholder="Organization Name" value={lead.organization} onChange={(e) => setLead({ ...lead, organization: e.target.value })} data-testid="recruit-free-org" />
        <p style={{ marginTop: 16, fontWeight: 700, color: "#111827" }}>How many new board members do you want to recruit?</p>
        <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
          <input style={{ ...field, width: 140, marginTop: 8 }} inputMode="numeric" placeholder="Number" disabled={lead.notSure}
            value={lead.count} onChange={(e) => setLead({ ...lead, count: e.target.value.replace(/[^0-9]/g, "") })} data-testid="recruit-free-count" />
          <button className={`bfg-btn bfg-btn-sm ${lead.notSure ? "bfg-btn-primary" : "bfg-btn-ghost"}`} style={{ marginTop: 8 }}
            onClick={() => setLead({ ...lead, notSure: !lead.notSure, count: "" })} data-testid="recruit-free-not-sure">
            I'M NOT SURE YET
          </button>
        </div>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 24 }} disabled={busy} onClick={start} data-testid="recruit-free-start-btn">
          {busy ? "Starting…" : "ANSWER THE 4 QUESTIONS"}
        </button>
        {error && <p className="bfg-error" data-testid="recruit-free-error">{error}</p>}
      </div>
    );
    return <RecruitmentHomePage form={leadForm} />;
  }

  if (stage.startsWith("q")) {
    const index = Number(stage.slice(1));
    const q = QUESTIONS[index];
    return shell(<>
      <p className="bfg-eyebrow" data-testid="recruit-free-progress">{q.progress}</p>
      <h1 style={{ marginTop: 12 }} data-testid={`recruit-free-q${index + 1}-heading`}>{q.heading}</h1>
      <p style={{ marginTop: 16, fontWeight: 700, fontSize: 17, color: "#111827" }}>{q.question}</p>
      <details className="recruit-question-guidance" data-testid={`recruit-free-q${index + 1}-guidance`}>
        <summary>Read the guidance</summary>
        <div>
          {q.helper.map((line, i) => <p key={i} style={{ marginTop: i === 0 ? 12 : 4, fontSize: 14 }}>{line}</p>)}
        </div>
      </details>
      <textarea rows={7} style={{ ...field, marginTop: 18, lineHeight: 1.6 }} placeholder="Type your answer here..."
        value={answers[q.key] || ""} onChange={(e) => setAnswers({ ...answers, [q.key]: e.target.value })}
        data-testid={`recruit-free-q${index + 1}-input`} />
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 20 }}>
        {index > 0 && (
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setStage(`q${index - 1}`)} data-testid="recruit-free-back-btn">Back</button>
        )}
        <button className="bfg-btn bfg-btn-primary" disabled={busy || !(answers[q.key] || "").trim()}
          onClick={() => saveAnswer(index)} data-testid={`recruit-free-q${index + 1}-continue`}>
          {busy ? "Saving…" : q.button}
        </button>
      </div>
    </>, `recruit-free-q${index + 1}`);
  }

  if (stage === "generating") {
    return shell(<>
      <h1 data-testid="recruit-free-generating">Preparing Your Board Recruitment Result…</h1>
      <p style={{ marginTop: 14 }}>We are comparing what your organization needs with what your present board already brings.</p>
    </>, "recruit-free-generating");
  }

  const result = assessment?.result || {};
  const covered = (result.present_board_capability_map || []).filter((r) => r.representation_status !== "NOT REPRESENTED");
  const gaps = result.board_gap || [];
  const profiles = result.priority_roles || [];
  const desired = assessment?.desired_count;

  return shell(<>
    <p className="bfg-eyebrow">YOUR BOARD RECRUITMENT RESULT</p>
    <h1 style={{ marginTop: 12 }} data-testid="recruit-free-result-heading">Here Are The Board Members We Recommend You Recruit</h1>
    <p style={{ marginTop: 16 }}>Based on what you told us about {assessment?.organization}, the board you already have, the areas that are important to moving your organization forward and the areas where you specifically need board support, here's what we found.</p>
    <h2 style={{ marginTop: 28, fontSize: 17, letterSpacing: 1 }}>YOUR PRESENT BOARD ALREADY GIVES YOU SUPPORT IN:</h2>
    <ul style={{ marginTop: 10, paddingLeft: 22, color: "#4B5563", lineHeight: 1.7 }} data-testid="recruit-free-covered">
      {covered.length ? covered.map((row, i) => <li key={i}>{row.capability}</li>) : <li>No areas of existing board support were identified from your answers.</li>}
    </ul>
    <h2 style={{ marginTop: 24, fontSize: 17, letterSpacing: 1 }}>THE BIGGEST GAPS WE IDENTIFIED ARE:</h2>
    <ul style={{ marginTop: 10, paddingLeft: 22, color: "#4B5563", lineHeight: 1.7 }} data-testid="recruit-free-gaps">
      {gaps.map((row, i) => <li key={i}>{row.gap}</li>)}
    </ul>
    {desired ? (
      <>
        <h2 style={{ marginTop: 26, fontSize: 18 }}>YOU TOLD US YOU WANT TO RECRUIT {desired} NEW BOARD MEMBERS.</h2>
        <p style={{ marginTop: 8 }}>So we have organized these needs into {desired} board-member profiles.</p>
      </>
    ) : (
      result.recommended_count_statement ? <p style={{ marginTop: 26, fontWeight: 700, color: "#111827" }}>{result.recommended_count_statement}</p> : null
    )}
    <div data-testid="recruit-free-profiles">
      {profiles.map((role, i) => (
        <div key={i} style={{ marginTop: 20, border: "1px solid #E5E7EB", borderRadius: 16, padding: 22, background: "#fff" }} data-testid={`recruit-free-profile-${i + 1}`}>
          <h3 style={{ margin: 0, fontSize: 18 }}>{i + 1}. {role.role_name}</h3>
          <p style={{ marginTop: 12, fontWeight: 700, fontSize: 13, letterSpacing: 1, color: "#4f46e5" }}>LOOK FOR SOMEONE WITH EXPERIENCE IN:</p>
          <ul style={{ marginTop: 6, paddingLeft: 22, color: "#4B5563", lineHeight: 1.7 }}>
            {(role.what_to_look_for || []).slice(0, 3).map((skill, j) => <li key={j}>{skill}</li>)}
          </ul>
          <p style={{ marginTop: 12, fontWeight: 700, fontSize: 13, letterSpacing: 1, color: "#111827" }}>WHY YOUR ORGANIZATION NEEDS THIS PERSON</p>
          <p style={{ marginTop: 6 }}>{[role.why_this_person_is_important, role.how_this_person_can_support].filter(Boolean).join(" ")}</p>
        </div>
      ))}
    </div>
    <h2 style={{ marginTop: 36 }}>Now You Know Who You Need To Recruit.</h2>
    <p style={{ marginTop: 12 }}>The next question is:</p>
    <p style={{ marginTop: 8 }}>How do you actually find these people, get them interested in your mission, take them through a professional recruitment process and successfully bring them onto your board?</p>
    <p style={{ marginTop: 8 }}>We've built the Self-Guided Board Recruitment System to help you do exactly that yourself.</p>
    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} data-testid="recruit-free-see-how-btn"
      onClick={() => { if (audioRef.current) audioRef.current.pause(); navigate("/recruit/walkthrough"); }}>
      SEE HOW TO RECRUIT THESE BOARD MEMBERS YOURSELF
    </button>
    <p style={{ marginTop: 10, fontSize: 13 }}>Watch the short walkthrough and see the complete process.</p>
  </>, "recruit-free-result");
}
