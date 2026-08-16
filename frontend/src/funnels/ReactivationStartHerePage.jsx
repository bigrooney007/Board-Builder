import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { MemberShell } from "@/member/MemberShell";
import { usePageMeta } from "@/seo";
import { SITE_CONTENT, reactivationStartHerePageText } from "@/content/siteContent";

export default function ReactivationStartHerePage() {
  usePageMeta("Start Here: Reactivate Your Board | Nonprofit Board Builder", "How to use the Nonprofit Board Builder Reactivation platform.", true);
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !member) navigate("/login?next=/reactivation-start-here", { replace: true });
  }, [loading, member, navigate]);

  if (loading || !member) {
    return (
      <MemberShell>
        <main className="sh-page" data-testid="reactivation-start-here-loading"><p className="sh-loading">Loading…</p></main>
      </MemberShell>
    );
  }

  return (
    <MemberShell>
      <main className="sh-page" data-testid="reactivation-start-here-page">
        <section className="funnel-hero-banner brp-hero sh-hero" data-testid="reactivation-start-here-hero">
          <h1 data-testid="reactivation-start-here-headline">{SITE_CONTENT.reactivationStartHere.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="reactivation-start-here-subtitle">{reactivationStartHerePageText.youAreAboutToWork}</p>
          <i aria-hidden="true" />
        </section>

        <section className="sh-blocks" data-testid="reactivation-start-here-copy">
          <article className="sh-block">
            <p>{reactivationStartHerePageText.theGoalIsToUnderstand}</p>
          </article>
        </section>

        <section className="sh-cta" data-testid="reactivation-start-here-cta-section">
          <Link className="button rwr-cta-button brp-cta-button" to="/app/reactivation/self-guided/module/1" data-testid="reactivation-start-here-step1-button">{SITE_CONTENT.reactivationStartHere.cta}</Link>
        </section>
      </main>
    </MemberShell>
  );
}
