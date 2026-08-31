import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Copy } from "lucide-react";
import { MemberShell } from "@/member/MemberShell";
import { memberApi } from "@/member/api";
import { SITE_CONTENT } from "@/content/siteContent";

const QUESTIONS = [
  { name: "step_off", label: "Are there board members you already know need to step off the board?" },
  { name: "advisory", label: "Are there board members you would like to consider moving to the advisory board?" },
];

const NEXT_STEP_URL = "/app/reactivation/self-guided/module/1";

export default function BoardFixOrientationPage() {
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [selections, setSelections] = useState({ step_off: "", advisory: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [materials, setMaterials] = useState(null);
  const [copied, setCopied] = useState(false);
  const videoId = SITE_CONTENT.memberVideos.boardFixOrientation;

  useEffect(() => { document.title = "Welcome to Board Fix | Board Ultimate Fix Framework | Nonprofit Board Builder"; }, []);

  const loadEmail = async () => {
    try {
      const email = await memberApi.get("/reactivation/recommitment-email");
      setMaterials(email.data);
    } catch { /* form not approved yet — generate flow will handle it */ }
  };

  useEffect(() => {
    memberApi.get("/board-fix/orientation")
      .then((r) => {
        setState(r.data);
        if (r.data.selections?.step_off) setSelections({ step_off: r.data.selections.step_off, advisory: r.data.selections.advisory });
        if (r.data.recommitment_form_status === "Approved") loadEmail();
      })
      .catch((err) => {
        if (err.response?.status === 401) { window.location.replace(`/login?next=${encodeURIComponent("/board-fix-orientation")}`); return; }
        setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not load your orientation. Please log in and try again.");
      });
  }, []);

  const generate = async () => {
    setError("");
    if (!selections.step_off || !selections.advisory) {
      setError("Answer both questions first — Yes or No is all I need.");
      return;
    }
    setBusy(true);
    try {
      await memberApi.post("/board-fix/orientation", selections);
      await memberApi.post("/reactivation/recommitment-form/generate");
      await memberApi.post("/reactivation/recommitment-form/approve");
      const email = await memberApi.get("/reactivation/recommitment-email");
      setMaterials(email.data);
      setState((current) => ({ ...current, recommitment_form_status: "Approved" }));
    } catch {
      setError("We could not generate your materials. Please try again.");
    }
    setBusy(false);
  };

  const emailBody = materials
    ? (materials.body.includes(`[${materials.button_label}]`)
        ? materials.body.replace(`[${materials.button_label}]`, materials.form_link)
        : `${materials.body}\n\nComplete your form here: ${materials.form_link}`)
    : "";

  const copyEmail = async () => {
    try {
      await navigator.clipboard.writeText(`Subject: ${materials.subject}\n\n${emailBody}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch { /* clipboard unavailable — the text is on screen */ }
  };

  return (
    <MemberShell>
      <main className="member-page board-fix-roadmap" data-testid="board-fix-orientation-page">
        <header className="member-page-heading">
          <p className="eyebrow">Board Ultimate Fix Framework</p>
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
          <p>Their answers will tell us who is ready to step up, who needs a conversation, and where the gaps are. Everything after that — rebuilding, recruitment, fundraising — builds on what we learn here.</p>
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
                        onChange={() => setSelections((current) => ({ ...current, [question.name]: option }))}
                        data-testid={`board-fix-orientation-${question.name}-${option.toLowerCase()}`} />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <button className="button" type="button" disabled={busy} onClick={generate} data-testid="board-fix-orientation-generate">
              {busy ? "Generating…" : materials ? "Regenerate My Materials" : "Generate My Board Member Profile & Recommitment Form + Email"} <ArrowRight size={16} />
            </button>
          </section>
        )}
        {materials && (
          <section className="member-card" data-testid="board-fix-orientation-materials">
            <h2>Your Materials Are Ready</h2>
            <p>Your Board Member Profile &amp; Recommitment Form is live at the link below — the same link is already inside the email. Copy the email, open your inbox, and send it to each of your board members. You send it; the responses come back here.</p>
            <p data-testid="board-fix-orientation-form-link"><strong>Form link:</strong> <a href={materials.form_link} target="_blank" rel="noreferrer">{materials.form_link}</a></p>
            <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, background: "#fff", marginBottom: 12 }} data-testid="board-fix-orientation-email">
              <p style={{ margin: 0 }}><strong>Subject:</strong> {materials.subject}</p>
              <p style={{ whiteSpace: "pre-wrap", marginTop: 10 }}>{emailBody}</p>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button className="button button-outline" type="button" onClick={copyEmail} data-testid="board-fix-orientation-copy-email">
                <Copy size={15} /> {copied ? "Copied!" : "Copy the Email"}
              </button>
              <button className="button" type="button" onClick={() => navigate(NEXT_STEP_URL)} data-testid="board-fix-orientation-next-step">
                Next Step: Understand Your Board <ArrowRight size={16} />
              </button>
            </div>
          </section>
        )}
      </main>
    </MemberShell>
  );
}
