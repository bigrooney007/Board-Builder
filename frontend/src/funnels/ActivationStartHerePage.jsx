import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { MemberShell } from "@/member/MemberShell";
import { usePageMeta } from "@/seo";
import { SITE_CONTENT } from "@/content/siteContent";

export default function ActivationStartHerePage() {
  usePageMeta("Start Here: Activate Your Board | Nonprofit Board Builder", "How to use the Nonprofit Board Builder Fundraising Activation platform.", true);
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !member) navigate("/login?next=/activation-start-here", { replace: true });
  }, [loading, member, navigate]);

  if (loading || !member) {
    return (
      <MemberShell>
        <main className="sh-page" data-testid="activation-start-here-loading"><p className="sh-loading">Loading…</p></main>
      </MemberShell>
    );
  }

  return (
    <MemberShell>
      <main className="sh-page" data-testid="activation-start-here-page">
        <section className="funnel-hero-banner brp-hero sh-hero" data-testid="activation-start-here-hero">
          <h1 data-testid="activation-start-here-headline">{SITE_CONTENT.activationStartHere.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="activation-start-here-subtitle">You are about to take your Board through a process that gets them involved in building the fundraising plan, agreeing how the Board will help carry it, and equipping members to begin taking action.</p>
          <i aria-hidden="true" />
        </section>

        <section className="sh-blocks" data-testid="activation-start-here-copy">
          <article className="sh-block">
            <p>Do not simply tell your Board to raise money.</p>
            <p>Build the plan with them.</p>
            <p><strong>People who plan together execute together.</strong></p>
          </article>
        </section>

        <section className="sh-cta" data-testid="activation-start-here-cta-section">
          <Link className="button rwr-cta-button brp-cta-button" to="/app/activation/self-guided/module/1" data-testid="activation-start-here-module1-button">{SITE_CONTENT.activationStartHere.cta}</Link>
        </section>
      </main>
    </MemberShell>
  );
}
