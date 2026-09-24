import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { memberApi, storeMemberToken } from "@/member/api";
import { BfgShell } from "./gameShared";
import "./game.css";

export default function GameResumePage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    const resume = async () => {
      try {
        const response = await memberApi.post(`/members/game-resume/${token}`);
        if (!live) return;
        if (response.data.token) storeMemberToken(response.data.token);
        window.location.replace("/game/demonstration");
      } catch (err) {
        if (!live) return;
        if (err.response?.status === 409) {
          navigate("/login?next=" + encodeURIComponent("/game/demonstration"), { replace: true });
          return;
        }
        setError(err.response?.data?.detail || "This Board Fundraising Game return link is not available.");
      }
    };
    resume();
    return () => { live = false; };
  }, [token, navigate]);

  return (
    <BfgShell>
      <main className="bfg-flow" style={{ maxWidth: 700, margin: "0 auto", padding: "60px 20px", textAlign: "center" }}>
        <p className="bfg-eyebrow">BOARD FUNDRAISING GAME</p>
        <h1>{error ? "We Could Not Reopen Your Journey" : "Reopening Your Board Fundraising Game…"}</h1>
        {error && (
          <>
            <p className="bfg-error" style={{ marginTop: 18 }}>{error}</p>
            <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} onClick={() => navigate("/board-fundraising-game")}>
              RETURN TO THE BOARD FUNDRAISING GAME
            </button>
          </>
        )}
      </main>
    </BfgShell>
  );
}
