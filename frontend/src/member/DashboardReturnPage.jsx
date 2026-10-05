import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { memberApi, storeMemberToken } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";

export default function DashboardReturnPage() {
  const { token } = useParams();
  const { refresh } = useMemberAuth();
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    // Remove the bearer link from browser history as soon as the exchange begins.
    window.history.replaceState({}, "", "/return");
    memberApi.post(`/members/dashboard-return/${encodeURIComponent(token)}`)
      .then(async ({ data }) => {
        if (!active) return;
        storeMemberToken(data.token);
        await refresh();
        window.location.replace(data.dashboard_url);
      })
      .catch(() => { if (active) setError("This private link could not open your dashboard. Log in to continue."); });
    return () => { active = false; };
  }, [token, refresh]);
  return <MemberShell><main className="member-auth-page"><section className="member-auth-card">
    <h1>{error ? "Dashboard Link Unavailable" : "Opening Your Dashboard"}</h1>
    <p>{error || "Connecting your private link to your workspace…"}</p>
    {error && <a className="button" href="/login">LOG IN</a>}
  </section></main></MemberShell>;
}
