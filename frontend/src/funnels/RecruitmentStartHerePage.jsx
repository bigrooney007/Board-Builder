import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, FileText, HelpCircle, Rocket, Zap } from "lucide-react";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { MemberShell } from "@/member/MemberShell";
import { usePageMeta } from "@/seo";
import { SITE_CONTENT, recruitmentStartHerePageText } from "@/content/siteContent";

const BLOCKS = [
  {
    icon: Eye,
    title: "Watch Me, Then Do What I Do",
    lines: ["Each step includes a video showing you what to do. Watch the video, then follow the instructions for your own organization."],
  },
  {
    icon: FileText,
    title: "Your Materials Are Created For Your Organization",
    lines: [
      "We use the information you provided about your organization and board to create the materials you need as you move through the Recruitment process.",
      "Review them, make any changes you want, and use them to execute.",
    ],
  },
  {
    icon: Rocket,
    title: "Take Action As You Go",
    lines: ["Do not wait until you finish every step before taking action.", "Complete each step and execute before moving forward."],
  },
  {
    icon: HelpCircle,
    title: "Ask For Help Anytime",
    lines: [
      "Every step includes:",
      "Need Help With This Step?",
      "Use it whenever you are stuck, need clarification, want help reviewing something or need support completing the step.",
    ],
  },
  {
    icon: Zap,
    title: "Start Immediately",
    lines: ["You can begin now and work toward launching your board recruitment campaign in the next 30 minutes."],
  },
];

export default function RecruitmentStartHerePage() {
  usePageMeta("Start Here | Nonprofit Board Builder", "How to use the Nonprofit Board Builder Recruitment platform.", true);
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !member) navigate("/login?next=/recruitment-start-here", { replace: true });
  }, [loading, member, navigate]);

  if (loading || !member) {
    return (
      <MemberShell>
        <main className="sh-page" data-testid="start-here-loading"><p className="sh-loading">Loading…</p></main>
      </MemberShell>
    );
  }

  return (
    <MemberShell>
      <main className="sh-page" data-testid="start-here-page">
        <section className="funnel-hero-banner brp-hero sh-hero" data-testid="start-here-hero">
          <h1 data-testid="start-here-headline">{SITE_CONTENT.recruitStartHere.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="start-here-subtitle">{recruitmentStartHerePageText.followTheProcessUseThe}</p>
          <i aria-hidden="true" />
        </section>

        <section className="sh-blocks" data-testid="start-here-instructions">
          {BLOCKS.map(({ icon: Icon, title, lines }) => (
            <article className="sh-block" key={title} data-testid={`start-here-block-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
              <span className="sh-block-icon"><Icon size={22} aria-hidden="true" /></span>
              <h2>{title}</h2>
              {lines.map((line) => <p key={line} className={line === "Need Help With This Step?" ? "sh-help-label" : ""}>{line}</p>)}
            </article>
          ))}
        </section>

        <section className="sh-cta" data-testid="start-here-cta-section">
          <Link className="button rwr-cta-button brp-cta-button" to="/app/recruitment/self-guided/module/2" data-testid="start-here-module1-button">{SITE_CONTENT.recruitStartHere.cta}</Link>
        </section>
      </main>
    </MemberShell>
  );
}
