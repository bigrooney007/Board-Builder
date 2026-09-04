import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import ActivationModule3 from "./ActivationModule3";
import ActivationModule4 from "./ActivationModule4";

export default function ActivationResourcesPage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    memberApi.get("/activation/delivery").then((res) => setState(res.data)).catch((e) => {
      if (e.response?.status === 401) navigate(`/login?next=${encodeURIComponent("/app/activation/resources")}`);
      else if (e.response?.status === 403) setError("Your account does not include Board Fundraising Activation.");
      else setError("We could not load your strategy resources.");
    });
  }, [navigate]);

  useEffect(() => { document.title = "Your Board Fundraising Strategy | Nonprofit Board Builder"; }, []);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent("/app/activation/resources")}`); return; }
    load();
  }, [loading, member, navigate, load]);

  const ready = state && (state.delivery.ready || state.operator);
  const dwrCustomer = state && state.delivery.engagement_type === "dwr" && !state.operator;

  return (
    <MemberShell>
      <main className="member-page" data-testid="activation-resources-page">
        {error && <p className="submit-error" data-testid="activation-resources-error">{error}</p>}
        {!state && !error && <p className="sh-loading">Loading…</p>}
        {state && dwrCustomer && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">Board Fundraising Activation</p>
              <h1 data-testid="resources-dwr-heading">Your Board Fundraising Planning Process Is Underway</h1>
            </header>
            <section className="member-card" data-testid="resources-dwr-status">
              <p><strong>Responses expected:</strong> {state.progress.expected}</p>
              <p><strong>Responses received:</strong> {state.progress.received}</p>
              <p><strong>Next Board meeting:</strong> {state.delivery.next_board_meeting_date || "—"}</p>
              <p>Rooney is working on your Fundraising Strategy with you and will continue by email — you do not need to work through these resources yourself.</p>
            </section>
          </>
        )}
        {state && !dwrCustomer && !ready && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">Board Fundraising Activation</p>
              <h1 data-testid="resources-not-ready-heading">Your Strategy Resources Are Not Ready Yet</h1>
            </header>
            <section className="member-card" data-testid="resources-not-ready">
              {state.delivery.launched_at ? (
                <>
                  <p>We are still collecting your Board's Fundraising Planning responses ({state.progress.received} of {state.progress.expected} received).</p>
                  <p>We will email you the moment it is time to build your Fundraising Strategy — you do not need to keep checking here.</p>
                  <Link className="button button-outline" to="/app/activation/start" data-testid="resources-back-start">VIEW MY PLANNING STATUS</Link>
                </>
              ) : (
                <>
                  <p>Start your Board Fundraising Planning process first. Once your Board's responses are in, this page unlocks your Fundraising Strategy resources.</p>
                  <Link className="button" to="/app/activation/start" data-testid="resources-go-start">GO TO MY PLANNING SETUP</Link>
                </>
              )}
            </section>
          </>
        )}
        {state && !dwrCustomer && ready && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">Board Fundraising Activation</p>
              <h1 data-testid="resources-ready-heading">Your Board Fundraising Strategy</h1>
              <p>Build your strategy from your Board's planning input, send it to your Board, and lead the Review &amp; Adoption Meeting.</p>
            </header>
            <section data-testid="resources-strategy-section">
              <ActivationModule3 />
            </section>
            <section data-testid="resources-adoption-section" style={{ marginTop: 24 }}>
              <h2 style={{ marginBottom: 12 }}>Lead The Board Meeting</h2>
              <ActivationModule4 />
            </section>
          </>
        )}
      </main>
    </MemberShell>
  );
}
