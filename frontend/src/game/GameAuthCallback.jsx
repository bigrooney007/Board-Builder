import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { memberApi, storeMemberToken } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import "./game.css";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function GameAuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setMember } = useMemberAuth();
  const hasProcessed = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const match = (location.hash || "").match(/session_id=([^&]+)/);
    const sessionId = match ? match[1] : "";
    if (!sessionId) { navigate("/game/signup", { replace: true }); return; }
    (async () => {
      try {
        const response = await memberApi.post("/members/google/session", { session_id: sessionId });
        storeMemberToken(response.data.token);
        setMember(response.data.member);
        window.history.replaceState(null, "", window.location.pathname);
        navigate("/game/start", { replace: true, state: { user: response.data.member } });
      } catch (err) {
        setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Google sign-in failed. Please try again.");
      }
    })();
  }, [location.hash, navigate, setMember]);

  return (
    <div className="bfg" style={{ minHeight: "100vh", display: "grid", placeItems: "center" }} data-testid="bfg-auth-callback">
      {error ? (
        <div className="bfg-card" style={{ maxWidth: 420, textAlign: "center" }}>
          <p className="bfg-error" data-testid="bfg-auth-callback-error">{error}</p>
          <button className="bfg-btn bfg-btn-primary" onClick={() => navigate("/game/signup")} data-testid="bfg-auth-callback-retry">Back to Sign Up</button>
        </div>
      ) : (
        <p style={{ color: "#6B7280" }}>Signing you in…</p>
      )}
    </div>
  );
}
