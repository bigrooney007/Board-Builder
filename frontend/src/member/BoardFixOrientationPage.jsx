import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { MemberShell } from "@/member/MemberShell";
import { memberApi } from "@/member/api";

const QUESTIONS = [
  { name: "step_off", label: "Are there board members you already know need to step off the board?" },
  { name: "advisory", label: "Are there board members you would like to consider moving to the advisory board?" },
];

export default function BoardFixOrientationPage() {
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [selections, setSelections] = useState({ step_off: "", advisory: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { document.title = "Orientation | Complete Board Fix | Nonprofit Board Builder"; }, []);

  useEffect(() => {
    memberApi.get("/board-fix/orientation")
      .then((r) => {
        setState(r.data);
        if (r.data.selections?.step_off) setSelections({ step_off: r.data.selections.step_off, advisory: r.data.selections.advisory });
      })
      .catch((err) => {
        if (err.response?.status === 401) { window.location.replace(`/login?next=${encodeURIComponent("/board-fix-orientation")}`); return; }
        setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not load your orientation. Please log in and try again.");
      });
  }, []);

  const start = async () => {
    setError("");
    if (!selections.step_off || !selections.advisory) {
      setError("Answer both questions first — Yes or No is all I need.");
      return;
    }
    setBusy(true);
    try {
      const response = await memberApi.post("/board-fix/orientation", selections);
      navigate(response.data.next_url || "/app/reactivation/self-guided/module/2");
    } catch {
      setError("We could not save your answers. Please try again.");
      setBusy(false);
    }
  };

  return (
    <MemberShell>
      <main className="member-page board-fix-roadmap" data-testid="board-fix-orientation-page">
        <header className="member-page-heading">
          <p className="eyebrow">Complete Board Fix</p>
          <h1 data-testid="board-fix-orientation-headline">Welcome to the Complete Board Fix System</h1>
        </header>
        <div className="module-video" data-testid="board-fix-orientation-video">
          <div className="offer-video-placeholder"><p>Complete Board Fix Onboarding Video</p><span>Video coming soon</span></div>
        </div>
        <section className="member-card" data-testid="board-fix-orientation-intro">
          <h2>Here Is Where We Start</h2>
          <p>Before we recruit anyone new, we are going to understand the board you already have. You cannot fix a board you do not understand.</p>
          <p>The first thing you are going to do is gather information from your existing board members. You will send each of them a Board Member Profile &amp; Recommitment Form. It asks about their skills, their networks, their experience on your board, and the one question that matters most:</p>
          <p><strong>Are you ready to recommit and step up to your responsibilities as a board member?</strong></p>
          <p>Their answers will tell us who is ready to step up, who needs a conversation, and where the gaps are. Everything after that — reactivation, recruitment, fundraising — builds on what we learn here.</p>
        </section>
        {error && <p className="submit-error" data-testid="board-fix-orientation-error">{error}</p>}
        {state && (
          <section className="member-card" data-testid="board-fix-orientation-questions">
            <h2>Two Quick Questions Before You Generate the Form</h2>
            <p>Your answers decide which options appear on the form your board members receive. If you are not sure, answer No — you can always use the standard form.</p>
            {QUESTIONS.map((question) => (
              <fieldset className="field choice-field" key={question.name} data-testid={`board-fix-orientation-${question.name}`}>
                <legend>{question.label}</legend>
                <div style={{ display: "flex", gap: 10 }}>
                  {["Yes", "No"].map((option) => (
                    <label className={`choice ${selections[question.name] === option ? "selected" : ""}`} key={option}>
                      <input type="radio" checked={selections[question.name] === option}
                        onChange={() => setSelections((current) => ({ ...current, [question.name]: option }))}
                        data-testid={`board-fix-orientation-${question.name}-${option.toLowerCase()}`} />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <p>Whatever you choose here, the standard Board Member Profile &amp; Recommitment Form will always be available to you as well.</p>
            <button className="button" type="button" disabled={busy} onClick={start} data-testid="board-fix-orientation-generate">
              {busy ? "Saving…" : "Generate Your Board Member Profile & Recommitment Form"} <ArrowRight size={16} />
            </button>
            {state.recommitment_form_status !== "NONE" && (
              <p style={{ marginTop: 10 }} data-testid="board-fix-orientation-form-exists">You have already started your form ({state.recommitment_form_status}). Saving your answers here updates the options on it.</p>
            )}
          </section>
        )}
      </main>
    </MemberShell>
  );
}
