import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { MemberShell } from "@/member/MemberShell";
import { usePageMeta } from "@/seo";

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
          <h1 data-testid="reactivation-start-here-headline">Start Here: Reactivate Your Board</h1>
          <p className="funnel-hero-banner-supporting" data-testid="reactivation-start-here-subtitle">You are about to work through your Board one person at a time.</p>
          <i aria-hidden="true" />
        </section>

        <section className="sh-blocks" data-testid="reactivation-start-here-copy">
          <article className="sh-block">
            <p>The goal is to understand what caused the disengagement, find out who is willing and able to stand up, have the conversations that need to happen, and give the people who remain clear responsibility for helping move the organization forward.</p>
          </article>
        </section>

        <section className="sh-cta" data-testid="reactivation-start-here-cta-section">
          <Link className="button rwr-cta-button brp-cta-button" to="/app/reactivation/self-guided/module/1" data-testid="reactivation-start-here-step1-button">START REACTIVATING MY BOARD</Link>
        </section>
      </main>
    </MemberShell>
  );
}
