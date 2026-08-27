import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, ClipboardList } from "lucide-react";
import { MemberShell } from "@/member/MemberShell";
import { memberApi } from "@/member/api";

const STAGE_META = {
  orientation: {
    route: () => "/board-fix-orientation",
    text: "Watch the welcome video, answer two quick questions, and generate the Board Member Profile & Recommitment Form you will send to your current board members.",
  },
  understand: {
    route: (stage) => `/app/reactivation/self-guided/module/${stage.current_module || 1}`,
    text: "Send the Recommitment Form to every current board member, collect their responses, and let the system help you understand what each person — and your board as a whole — is telling you.",
  },
  reactivate: {
    route: (stage) => `/app/reactivation/self-guided/module/${stage.current_module || 4}`,
    text: "Have the conversations your board summary points to. Recommit the people ready to step up, move the right people to advisory roles, and let others step off gracefully.",
  },
  recruit: {
    route: () => "/app/recruitment/self-guided",
    intakeRoute: "/board-recruitment-intake?bf=1",
    text: "Identify the professionals your board is missing, generate your recruitment materials, launch your campaign, and select, interview and onboard the board members you need.",
  },
  activate: {
    route: () => "/app/activation/self-guided",
    intakeRoute: "/board-activation-intake?bf=1",
    text: "Bring your board into the fundraising planning process, build the strategy together, and equip every board member to execute their part.",
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
          <p className="eyebrow">Complete Board Fix</p>
          <h1 data-testid="board-fix-roadmap-headline">Your Board Fix Roadmap</h1>
        </header>
        <section className="member-card" data-testid="board-fix-roadmap-instructions">
          <h2>How the Complete Board Fix System Works</h2>
          <p>We fix your board in a specific order: <strong>Orientation → Understand Your Board → Reactivate / Transition Your Current Board → Recruit the Board You Need → Activate Your Board Around Fundraising.</strong></p>
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
