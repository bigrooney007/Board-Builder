import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";

import { useFlowVideo } from "@/hooks/useFlowVideos";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, GameVideo } from "./gameShared";

export default function GameWelcomePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session_id") || "";
  const { member, loading, refresh } = useMemberAuth();
  const video = useFlowVideo("game_welcome");
  const [state, setState] = useState("checking");
  const [detail, setDetail] = useState("");
  const [password, setPassword] = useState({ password: "", confirm_password: "" });
  const [securing, setSecuring] = useState(false);
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

  const playGame = async () => {
    if (member?.account_status !== "free_game_guest") {
      navigate("/game/setup");
      return;
    }
    if (password.password.length < 8 || password.password !== password.confirm_password) {
      setDetail(password.password !== password.confirm_password ? "Passwords do not match." : "Use at least 8 characters for your password.");
      return;
    }
    setSecuring(true); setDetail("");
    try {
      await memberApi.post("/members/complete-guest-account", password);
      await refresh();
      navigate("/game/setup");
    } catch (err) {
      setDetail(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not secure your account. Please try again.");
      setSecuring(false);
    }
  };

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
            <Link className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} to={`/login?next=${encodeURIComponent(`/game/welcome?session_id=${sessionId}`)}`} data-testid="bfg-welcome-login-link">Log In</Link>
          </div>
        ) : state === "error" ? (
          <div className="bfg-card" style={{ textAlign: "center" }} data-testid="bfg-welcome-error">
            <h1>We Could Not Confirm Your Payment</h1>
            <p className="bfg-error" style={{ marginTop: 16 }}>{detail}</p>
            <Link className="bfg-btn bfg-btn-ghost" style={{ marginTop: 18 }} to="/board-fundraising-game">Back to My Board Fundraising Game</Link>
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
              {member?.account_status === "free_game_guest" && (
                <div className="bfg-card" style={{ maxWidth: 560, margin: "0 auto 24px", padding: 22, textAlign: "left" }} data-testid="bfg-secure-account">
                  <h2 style={{ textAlign: "center" }}>Secure Your Board Fundraising Game</h2>
                  <p style={{ marginTop: 10, textAlign: "center" }}>Create a password so you can return to your Game and dashboard from any device.</p>
                  <label className="bfg-field"><span>Password</span><input type="password" minLength={8} value={password.password}
                    onChange={(event) => setPassword({ ...password, password: event.target.value })} data-testid="bfg-welcome-password" /></label>
                  <label className="bfg-field"><span>Confirm password</span><input type="password" minLength={8} value={password.confirm_password}
                    onChange={(event) => setPassword({ ...password, confirm_password: event.target.value })} data-testid="bfg-welcome-confirm-password" /></label>
                </div>
              )}
              {detail && <p className="bfg-error" style={{ marginBottom: 14 }}>{detail}</p>}
              <button className="bfg-btn bfg-btn-primary" data-testid="bfg-play-game-btn"
                disabled={securing} onClick={playGame}>
                {securing ? "Securing My Account…" : "Play My Board Fundraising Game"}
              </button>
              <p style={{ fontSize: 13.5, marginTop: 14 }}>Next: play the game. When you finish, we will take you into your dashboard.</p>
            </div>
          </div>
        )}
      </main>
    </BfgShell>
  );
}
