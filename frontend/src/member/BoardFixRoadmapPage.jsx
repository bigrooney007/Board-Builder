import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, ClipboardList } from "lucide-react";
import { MemberShell } from "@/member/MemberShell";
import { memberApi } from "@/member/api";

const PATHWAY_META = {
  recruitment: {
    label: "BOARD RECRUITMENT", route: "/app/recruitment/self-guided", intakeRoute: "/board-recruitment-intake?bf=1",
    text: "The complete process for recruiting the board members the organization needs.",
  },
  reactivation: {
    label: "BOARD REACTIVATION", route: "/app/reactivation/self-guided", intakeRoute: "/board-reactivation-intake?bf=1",
    text: "The complete process for getting existing board members to step up, recommit, take responsibility, or transition gracefully.",
  },
  activation: {
    label: "BOARD FUNDRAISING ACTIVATION", route: "/app/activation/self-guided", intakeRoute: "/board-activation-intake?bf=1",
    text: "The complete process for activating the board around fundraising and helping build the organization's fundraising system.",
  },
};

export default function BoardFixRoadmapPage() {
  const [roadmap, setRoadmap] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Your Board Fix Roadmap | Nonprofit Board Builder"; }, []);

  useEffect(() => {
    memberApi.get("/board-fix/roadmap")
      .then((r) => setRoadmap(r.data))
      .catch((err) => setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not load your roadmap. Please log in and try again."));
  }, []);

  return (
    <MemberShell>
      <main className="member-page board-fix-roadmap" data-testid="board-fix-roadmap-page">
        <header className="member-page-heading">
          <p className="eyebrow">Complete Board Fix</p>
          <h1 data-testid="board-fix-roadmap-headline">Your Board Fix Roadmap</h1>
        </header>
        <div className="module-video" data-testid="board-fix-onboarding-video">
          <div className="offer-video-placeholder"><p>Complete Board Fix Onboarding Video</p><span>Video coming soon</span></div>
        </div>
        <section className="member-card" data-testid="board-fix-roadmap-instructions">
          <h2>How the Complete Board Fix System Works</h2>
          <p>Your Complete Board Fix system contains the three execution pathways below. Each pathway gives you the process, tools, materials and resources for that area of your board.</p>
          <p><strong>Start with the area that is most pressing for your organization right now.</strong> You do not have to begin with a predetermined step, and you can return to this roadmap at any time to continue another pathway. Your progress is always saved.</p>
        </section>
        {error && <p className="submit-error" data-testid="board-fix-roadmap-error">{error}</p>}
        {!roadmap && !error && <p data-testid="board-fix-roadmap-loading">Loading your roadmap…</p>}
        {roadmap && (
          <div className="board-fix-pathways">
            {roadmap.pathways.map((pathway) => {
              const meta = PATHWAY_META[pathway.key];
              return (
                <section className="member-card board-fix-pathway" key={pathway.key} data-testid={`board-fix-pathway-${pathway.key}`}>
                  <h2>{meta.label}</h2>
                  <p>{meta.text}</p>
                  <p className="board-fix-pathway-status" data-testid={`board-fix-status-${pathway.key}`}>
                    {pathway.done ? "Completed" : pathway.started ? `${pathway.percent}% complete` : "Not started yet"}
                  </p>
                  {!pathway.done && (
                    <p data-testid={`board-fix-current-step-${pathway.key}`}>
                      <strong>Current step:</strong> {pathway.current_step}
                      {pathway.next_step ? <> — <strong>Next step:</strong> {pathway.next_step}</> : null}
                    </p>
                  )}
                  {pathway.completed_steps.length > 0 && (
                    <p className="board-fix-completed-steps" data-testid={`board-fix-completed-${pathway.key}`}>
                      <CheckCircle2 size={14} /> Completed: {pathway.completed_steps.join("; ")}
                    </p>
                  )}
                  {pathway.needs_intake ? (
                    <>
                      <p data-testid={`board-fix-intake-note-${pathway.key}`}>This pathway needs a few details your master intake did not cover. Your answers are prefilled — you only complete what is missing.</p>
                      <Link className="button" to={meta.intakeRoute} data-testid={`board-fix-start-${pathway.key}`}>
                        <ClipboardList size={16} /> Complete the Short Intake and Begin
                      </Link>
                    </>
                  ) : (
                    <Link className="button" to={meta.route} data-testid={`board-fix-start-${pathway.key}`}>
                      {pathway.done ? "Review" : pathway.started ? "Continue" : "Begin"} <ArrowRight size={16} />
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
