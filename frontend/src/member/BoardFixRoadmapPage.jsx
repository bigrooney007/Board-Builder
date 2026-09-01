import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, ClipboardList } from "lucide-react";
import { MemberShell } from "@/member/MemberShell";
import { memberApi } from "@/member/api";

const STAGE_META = {
  orientation: {
    route: () => "/board-fix-orientation",
    text: "Watch the welcome video, generate the Board Member Profile & Recommitment Form and the email you will send, then send the form to your current board members and track their responses as they come in.",
  },
  understand: {
    route: (stage) => `/app/reactivation/self-guided/module/${stage.current_module || 3}`,
    text: "Every board member who completes the Recommitment Form appears here. Understand each person's situation, generate the conversation script you need, have the conversation and record the outcome, send the right follow-up communication, and get the summary of your entire board.",
  },
  identify: {
    route: (stage) => `/app/recruitment/self-guided/module/${stage.current_module || 2}`,
    text: "No new intake here — we already have what we need. Compare your present board, including you, against the board your mission needs. The gap becomes the board members you need to recruit.",
  },
  launch: {
    route: () => "/app/recruitment/self-guided/module/3",
    text: "Generate your recruitment resources, review and approve them, and launch your board recruitment campaign.",
  },
  select: {
    route: () => "/app/recruitment/self-guided/module/4",
    text: "Applicants appear here automatically as they apply. Review them, invite the strongest to interview, and decide who moves forward. You make every selection decision.",
  },
  references: {
    route: () => "/app/recruitment/self-guided/module/5",
    text: "Run references and background checks: generate the reference emails, contact referees yourself, and prepare conditional appointments where you choose to move ahead.",
  },
  onboard: {
    route: () => "/app/recruitment/self-guided/module/6",
    text: "Onboard your new board members with the onboarding guide, agreements and profile forms — and send each new member their Final Board Appointment Email.",
  },
  fundraising_planning: {
    route: (stage) => `/app/activation/self-guided/module/${stage.current_module || 2}`,
    intakeRoute: "/board-activation-intake?bf=1",
    text: "Bring your whole board — current and newly recruited — into fundraising planning. Send every member the Fundraising Planning Form and complete your own.",
  },
  create_strategy: {
    route: () => "/app/activation/self-guided/module/3",
    text: "Build your Fundraising Strategy Plan from everyone's ideas, relationships and capabilities — combined with your own planning response.",
  },
  adopt_strategy: {
    route: () => "/app/activation/self-guided/module/4",
    text: "Take the completed strategy to your board, work through it together in your board meeting, and adopt the plan you will carry as one board.",
  },
  execute_strategy: {
    route: () => "/app/activation/self-guided/module/5",
    text: "Equip every board member — including you — with their fundraising portfolio, scripts and resources, and start executing the plan together.",
  },
};

export default function BoardFixRoadmapPage() {
  const [roadmap, setRoadmap] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Your Board Fix Roadmap | Nonprofit Board Builder"; }, []);

  useEffect(() => {
    memberApi.get("/board-fix/roadmap")
      .then((r) => setRoadmap(r.data))
      .catch((err) => {
        if (err.response?.status === 401) { window.location.replace(`/login?next=${encodeURIComponent("/board-fix-roadmap")}`); return; }
        setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not load your roadmap. Please log in and try again.");
      });
  }, []);

  const currentIndex = roadmap ? roadmap.journey.findIndex((stage) => !stage.done) : -1;

  return (
    <MemberShell>
      <main className="member-page board-fix-roadmap" data-testid="board-fix-roadmap-page">
        <header className="member-page-heading">
          <p className="eyebrow">Board Ultimate Fix Framework</p>
          <h1 data-testid="board-fix-roadmap-headline">Your Board Fix Dashboard</h1>
        </header>
        <section className="member-card" data-testid="board-fix-roadmap-instructions">
          <h2>How the Board Ultimate Fix Framework Works</h2>
          <p>The BUF Framework fixes your board in a specific order: <strong>Welcome to Board Fix → Understand the Situation → Identify the Board Members You Need → Launch Your Recruitment Campaign → Select and Interview Your Applicants → Complete References and Background Checks → Onboard Your New Board Members → Build the Fundraising Plan With Your Board → Build Your Fundraising Strategy → Review and Adopt the Fundraising Strategy → Equip Your Board to Execute.</strong></p>
          <p>Work through the stages below in order. You can leave and come back any time — your progress is always saved, and this roadmap will always show you exactly where you are and what comes next.</p>
        </section>
        {error && <p className="submit-error" data-testid="board-fix-roadmap-error">{error}</p>}
        {!roadmap && !error && <p data-testid="board-fix-roadmap-loading">Loading your roadmap…</p>}
        {roadmap && (
          <div className="board-fix-pathways">
            {roadmap.journey.map((stage, index) => {
              const meta = STAGE_META[stage.key];
              const isCurrent = index === currentIndex;
              const target = stage.needs_intake && meta.intakeRoute ? meta.intakeRoute : meta.route(stage);
              return (
                <section className="member-card board-fix-pathway" key={stage.key} data-testid={`board-fix-stage-card-${stage.key}`}
                  style={isCurrent ? { borderLeft: "4px solid #1d3a2f" } : undefined}>
                  <p className="eyebrow">Stage {index + 1}{stage.done ? " — Completed" : isCurrent ? " — You Are Here" : ""}</p>
                  <h2>{stage.label}</h2>
                  <p>{meta.text}</p>
                  <p className="board-fix-pathway-status" data-testid={`board-fix-status-${stage.key}`}>
                    {stage.done ? "Completed" : stage.started ? `${stage.percent}% complete` : "Not started yet"}
                  </p>
                  {!stage.done && stage.current_step && (
                    <p data-testid={`board-fix-current-step-${stage.key}`}>
                      <strong>Current step:</strong> {stage.current_step}
                      {stage.next_step ? <> — <strong>Next step:</strong> {stage.next_step}</> : null}
                    </p>
                  )}
                  {stage.completed_steps.length > 0 && (
                    <p className="board-fix-completed-steps" data-testid={`board-fix-completed-${stage.key}`}>
                      <CheckCircle2 size={14} /> Completed: {stage.completed_steps.join("; ")}
                    </p>
                  )}
                  {stage.needs_intake && meta.intakeRoute ? (
                    <>
                      <p data-testid={`board-fix-intake-note-${stage.key}`}>This stage needs a few details your master intake did not cover. Your answers are prefilled — you only complete what is missing.</p>
                      <Link className="button" to={target} data-testid={`board-fix-start-${stage.key}`}>
                        <ClipboardList size={16} /> Complete the Short Intake and Begin
                      </Link>
                    </>
                  ) : (
                    <Link className="button" to={target} data-testid={`board-fix-start-${stage.key}`}>
                      {stage.done ? "Review" : stage.started ? "Continue" : "Begin"} <ArrowRight size={16} />
                    </Link>
                  )}
                </section>
              );
            })}
          </div>
        )}
      </main>
    </MemberShell>
  );
}
