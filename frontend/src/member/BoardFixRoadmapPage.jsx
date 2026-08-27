import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { MemberShell } from "@/member/MemberShell";
import { memberApi } from "@/member/api";

const PATHWAYS = [
  { key: "recruitment", label: "BOARD RECRUITMENT", endpoint: "/courses/recruitment/self-guided", route: "/app/recruitment/self-guided",
    text: "The complete process for recruiting the board members the organization needs." },
  { key: "reactivation", label: "BOARD REACTIVATION", endpoint: "/courses/reactivation/self-guided", route: "/app/reactivation/self-guided",
    text: "The complete process for getting existing board members to step up, recommit, take responsibility, or transition gracefully." },
  { key: "activation", label: "BOARD FUNDRAISING ACTIVATION", endpoint: "/courses/activation/self-guided", route: "/app/activation/self-guided",
    text: "The complete process for activating the board around fundraising and helping build the organization's fundraising system." },
];

export default function BoardFixRoadmapPage() {
  const [progress, setProgress] = useState({});

  useEffect(() => { document.title = "Your Board Fix Roadmap | Nonprofit Board Builder"; }, []);

  useEffect(() => {
    PATHWAYS.forEach((pathway) => {
      memberApi.get(pathway.endpoint).then((r) => {
        const modules = r.data.modules || [];
        const current = modules.find((m) => !m.completed && !m.locked);
        setProgress((prev) => ({ ...prev, [pathway.key]: {
          percent: r.data.percent_complete ?? 0,
          current: current ? current.title : "",
          started: modules.some((m) => m.viewed || m.completed),
        }}));
      }).catch(() => {});
    });
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
          <p><strong>Start with the area that is most pressing for your organization right now.</strong> You do not have to begin with a predetermined step, and you can return to this roadmap at any time to continue another pathway.</p>
        </section>
        <div className="board-fix-pathways">
          {PATHWAYS.map((pathway) => {
            const state = progress[pathway.key] || {};
            return (
              <section className="member-card board-fix-pathway" key={pathway.key} data-testid={`board-fix-pathway-${pathway.key}`}>
                <h2>{pathway.label}</h2>
                <p>{pathway.text}</p>
                <p className="board-fix-pathway-status" data-testid={`board-fix-status-${pathway.key}`}>
                  {state.started ? `${state.percent}% complete${state.current ? ` — Current step: ${state.current}` : " — Completed"}` : "Not started yet"}
                </p>
                <Link className="button" to={pathway.route} data-testid={`board-fix-start-${pathway.key}`}>
                  {state.started ? "Continue" : "Begin"} <ArrowRight size={16} />
                </Link>
              </section>
            );
          })}
        </div>
      </main>
    </MemberShell>
  );
}
