import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { MemberShell } from "@/member/MemberShell";
import { memberApi } from "@/member/api";
import ReactivationStep2 from "@/member/ReactivationStep2";
import { SITE_CONTENT } from "@/content/siteContent";

const QUESTIONS = [
  { name: "step_off", label: "Are there board members you already know need to step off the board?" },
  { name: "advisory", label: "Are there board members you would like to consider moving to the advisory board?" },
];

const NEXT_STEP_URL = "/app/reactivation/self-guided/module/3";

export default function BoardFixOrientationPage() {
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [selections, setSelections] = useState({ step_off: "", advisory: "" });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const videoId = SITE_CONTENT.memberVideos.boardFixOrientation;

  useEffect(() => { document.title = "Welcome to Board Fix | Board Ultimate Fix Framework | Nonprofit Board Builder"; }, []);

  useEffect(() => {
    memberApi.get("/board-fix/orientation")
      .then((r) => {
        setState(r.data);
        if (r.data.selections?.step_off) {
          setSelections({ step_off: r.data.selections.step_off, advisory: r.data.selections.advisory });
          setSaved(true);
        }
      })
      .catch((err) => {
        if (err.response?.status === 401) { window.location.replace(`/login?next=${encodeURIComponent("/board-fix-orientation")}`); return; }
        setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not load your orientation. Please log in and try again.");
      });
  }, []);

  const saveAnswers = async () => {
    setError("");
    if (!selections.step_off || !selections.advisory) {
      setError("Answer both questions first — Yes or No is all I need.");
      return;
    }
    setBusy(true);
    try {
      await memberApi.post("/board-fix/orientation", selections);
      setSaved(true);
    } catch {
      setError("We could not save your answers. Please try again.");
    }
    setBusy(false);
  };

  return (
    <MemberShell>
      <main className="member-page board-fix-roadmap" data-testid="board-fix-orientation-page">
        <header className="member-page-heading">
          <p className="eyebrow">Board Ultimate Fix Framework — Step 1</p>
          <h1 data-testid="board-fix-orientation-headline">Welcome to Board Fix</h1>
          <p>This is the beginning of your Board Ultimate Fix Framework journey. I am going to take you through it step by step — watch the video, then generate the first materials below.</p>
        </header>
        <div className="module-video" data-testid="board-fix-orientation-video">
          {videoId ? (
            <iframe src={`https://www.youtube.com/embed/${videoId}`} title="Welcome to Board Fix" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
          ) : (
            <div className="offer-video-placeholder"><p>Welcome to Board Fix Video</p><span>Video coming soon</span></div>
          )}
        </div>
        <section className="member-card" data-testid="board-fix-orientation-intro">
          <h2>Here Is Where We Start</h2>
          <p>Before we recruit anyone new, we are going to understand the board you already have. You cannot fix a board you do not understand.</p>
          <p>The first thing you are going to do is gather information from your existing board members. You will send each of them a Board Member Profile &amp; Recommitment Form. It asks about their skills, their networks, their experience on your board, and the one question that matters most:</p>
          <p><strong>Are you ready to recommit and step up to your responsibilities as a board member?</strong></p>
          <p>Their answers will tell us who is ready to step up, who needs a conversation, and where the gaps are. Everything after that — the conversations, recruitment, fundraising — builds on what we learn here.</p>
        </section>
        {error && <p className="submit-error" data-testid="board-fix-orientation-error">{error}</p>}
        {state && (
          <section className="member-card" data-testid="board-fix-orientation-questions">
            <h2>Two Quick Questions Before You Generate Your Materials</h2>
            <p>Your answers decide which options appear on the form your board members receive. If you are not sure, answer No — you can always use the standard form.</p>
            {QUESTIONS.map((question) => (
              <fieldset className="field choice-field" key={question.name} data-testid={`board-fix-orientation-${question.name}`}>
                <legend>{question.label}</legend>
                <div style={{ display: "flex", gap: 10 }}>
                  {["Yes", "No"].map((option) => (
                    <label className={`choice ${selections[question.name] === option ? "selected" : ""}`} key={option}>
                      <input type="radio" checked={selections[question.name] === option}
                        onChange={() => { setSelections((current) => ({ ...current, [question.name]: option })); setSaved(false); }}
                        data-testid={`board-fix-orientation-${question.name}-${option.toLowerCase()}`} />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <button className="button" type="button" disabled={busy || saved} onClick={saveAnswers} data-testid="board-fix-orientation-save-answers">
              {busy ? "Saving…" : saved ? "Answers Saved" : "Save My Answers"} <ArrowRight size={16} />
            </button>
          </section>
        )}
        {state && saved && (
          <div data-testid="board-fix-orientation-recommitment">
            <ReactivationStep2 />
            <div className="module-nav" data-testid="board-fix-orientation-navigation">
              <span />
              <button className="button" type="button" onClick={() => navigate(NEXT_STEP_URL)} data-testid="board-fix-orientation-next-step">
                Next Step: Understand the Situation <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}
      </main>
    </MemberShell>
  );
}
