import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";

let profileCompletedCache = null;
import { useFlowVideo } from "@/hooks/useFlowVideos";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, GameVideo } from "./gameShared";

export default function GameWelcomePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session_id") || "";
  const { member, loading } = useMemberAuth();
  const video = useFlowVideo("game_welcome");
  const [state, setState] = useState("checking");
  const [detail, setDetail] = useState("");
  const attempts = useRef(0);

  useEffect(() => { document.title = "Welcome | Board Fundraising Game"; }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { setState("login"); return; }
    let cancelled = false;
    const claim = async () => {
      try {
        await memberApi.post("/game/claim", { session_id: sessionId, origin_url: window.location.origin });
        if (!cancelled) setState("welcome");
      } catch (err) {
        if (cancelled) return;
        attempts.current += 1;
        if (err.response?.status === 402 && attempts.current < 10) {
          setState("waiting");
          setTimeout(claim, 3000);
        } else {
          setDetail(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not confirm your payment.");
          setState("error");
        }
      }
    };
    claim();
    return () => { cancelled = true; };
  }, [loading, member, sessionId]);

  return (
    <BfgShell>
      <main className="bfg-flow" data-testid="bfg-welcome-page" style={{ maxWidth: 860 }}>
        {state === "checking" || state === "waiting" ? (
          <div className="bfg-card" style={{ textAlign: "center" }} data-testid="bfg-welcome-verifying">
            <h1>Confirming Your Payment…</h1>
            <p style={{ marginTop: 12 }}>One moment while we unlock your Board Fundraising Game.</p>
          </div>
        ) : state === "login" ? (
          <div className="bfg-card" style={{ textAlign: "center" }} data-testid="bfg-welcome-login">
            <h1>Log In to Continue</h1>
            <p style={{ marginTop: 12 }}>Please log in to the account you created before payment to unlock your game.</p>
            <Link className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} to={`/game/signup?mode=login`} data-testid="bfg-welcome-login-link">Log In</Link>
          </div>
        ) : state === "error" ? (
          <div className="bfg-card" style={{ textAlign: "center" }} data-testid="bfg-welcome-error">
            <h1>We Could Not Confirm Your Payment</h1>
            <p className="bfg-error" style={{ marginTop: 16 }}>{detail}</p>
            <Link className="bfg-btn bfg-btn-ghost" style={{ marginTop: 18 }} to="/game/start">Back to My Game Profile</Link>
          </div>
        ) : (
          <div data-testid="bfg-welcome-content">
            <div style={{ textAlign: "center", marginBottom: 30 }}>
              <p className="bfg-eyebrow">Payment confirmed</p>
              <h1 style={{ fontSize: "clamp(28px, 4.5vw, 42px)" }}>Welcome To Your Board Fundraising Game</h1>
              <p style={{ maxWidth: 560, margin: "14px auto 0" }}>
                This tutorial explains how to use the platform, prepare your board and run the game. We have also emailed it to you so you can come back to it anytime.
              </p>
            </div>
            <GameVideo video={video} testId="bfg-welcome-video" />
            <div style={{ textAlign: "center", marginTop: 32 }}>
              <button className="bfg-btn bfg-btn-primary" data-testid="bfg-complete-setup-btn"
                onClick={async () => {
                  try {
                    if (profileCompletedCache === null) {
                      const response = await memberApi.get("/game/profile");
                      profileCompletedCache = !!response.data.profile?.profile_completed;
                    }
                  } catch { profileCompletedCache = true; }
                  navigate(profileCompletedCache ? "/game/setup" : "/game/start?edit=1");
                }}>
                Complete My Game Setup
              </button>
              <p style={{ fontSize: 13.5, marginTop: 14 }}>Next: review the fundraising strategy you created and tell us what your organization already has.</p>
            </div>
          </div>
        )}
      </main>
    </BfgShell>
  );
}
