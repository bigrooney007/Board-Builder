import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import { RoundProgress } from "./groupShared";
import { GroupReviewStage } from "./GroupReviewStage";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const deviceKey = (token) => `bfgGroup:${token}`;
const readIdentity = (token) => {
  try { return JSON.parse(localStorage.getItem(deviceKey(token)) || "null"); } catch { return null; }
};

export default function GroupPlayPage() {
  const { token } = useParams();
  const [entry, setEntry] = useState(null);
  const [identity, setIdentity] = useState(() => readIdentity(token));
  const [selectedSlot, setSelectedSlot] = useState("");
  const [state, setState] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const lastRound = useRef(0);

  useEffect(() => { document.title = "Game Night | Board Fundraising Game"; }, []);

  const loadEntry = useCallback(async () => {
    try { setEntry((await axios.get(`${API}/game/group/play/${token}`)).data); }
    catch { setNotFound(true); }
  }, [token]);
  useEffect(() => { loadEntry(); }, [loadEntry]);

  const poll = useCallback(async () => {
    if (!identity) return;
    try {
      const response = await axios.get(`${API}/game/group/play/${token}/state`, {
        params: { slot: identity.slot_id, device: identity.device_id } });
      setState(response.data);
      const roundNumber = response.data.current_round?.round_number || 0;
      if (roundNumber !== lastRound.current) lastRound.current = roundNumber;
    } catch { /* keep last state */ }
  }, [identity, token]);

  useEffect(() => {
    if (!identity) return undefined;
    poll();
    const timer = setInterval(poll, 2500);
    return () => clearInterval(timer);
  }, [identity, poll]);

  const join = async () => {
    if (!selectedSlot) return;
    setBusy(true); setError("");
    const existing = readIdentity(token);
    const device_id = existing?.device_id || `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    try {
      await axios.post(`${API}/game/group/play/${token}/join`, { slot_id: selectedSlot, device_id });
      const next = { slot_id: selectedSlot, device_id };
      localStorage.setItem(deviceKey(token), JSON.stringify(next));
      setIdentity(next);
    } catch (err) {
      setError(err.response?.status === 409
        ? "That name has already joined on another device. If this is you, use the device you joined with."
        : "We could not join the game. Please try again.");
    }
    setBusy(false);
  };

  if (notFound) {
    return (
      <div className="bfg bfg-gg" style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
        <div className="bfg-gg-card" style={{ maxWidth: 420, textAlign: "center" }} data-testid="bfg-gg-invalid">
          <h2>This Group Game Link Is Not Valid</h2>
          <p>Please ask your host to share the current Game Night link.</p>
        </div>
      </div>
    );
  }
  if (!entry) return <div className="bfg bfg-gg" style={{ minHeight: "100vh" }} />;

  const round = state?.current_round;
  const myName = identity ? (entry.players.find((player) => player.slot_id === identity.slot_id)?.name || "") : "";

  return (
    <div className="bfg bfg-gg" style={{ minHeight: "100vh" }}>
      <header className="bfg-gg-nav">
        <span><strong>Nonprofit Board Builder</strong> · Board Fundraising Game</span>
        {myName && <span className="bfg-gg-me">{myName}</span>}
      </header>
      <main className="bfg-gg-main" data-testid="bfg-group-play-page">

        {!identity && (
          <div className="bfg-gg-card" data-testid="bfg-gg-entry">
            <p className="bfg-gg-eyebrow">Game Night</p>
            <h1>Welcome To Game Night</h1>
            <p style={{ marginTop: 12 }}>
              {entry.organization_name} is working toward a fundraising goal of {entry.goal_display}.
              {" "}Tonight, your board will review the complete set of ideas together and agree on the direction for your fundraising strategy.
            </p>
            <h2 style={{ marginTop: 24 }}>Who Are You?</h2>
            <div className="bfg-gg-names">
              {entry.players.map((player) => (
                <button key={player.slot_id} type="button"
                  className={`bfg-gg-name ${selectedSlot === player.slot_id ? "selected" : ""} ${player.joined ? "joined" : ""}`}
                  disabled={player.joined}
                  onClick={() => setSelectedSlot(player.slot_id)}
                  data-testid={`bfg-gg-name-${player.name.toLowerCase()}`}>
                  {player.name}
                  {player.joined && <small>Already Joined</small>}
                </button>
              ))}
            </div>
            {error && <p className="bfg-error">{error}</p>}
            <button className="bfg-btn bfg-btn-primary" style={{ width: "100%", marginTop: 18 }}
              disabled={!selectedSlot || busy} onClick={join} data-testid="bfg-gg-join-btn">
              {busy ? "Joining…" : "Join The Game"}
            </button>
          </div>
        )}

        {identity && state && state.status !== "in_progress" && state.status !== "completed" && (
          <div className="bfg-gg-card" style={{ textAlign: "center" }} data-testid="bfg-gg-waiting">
            <p className="bfg-gg-eyebrow">Game Night</p>
            <h1>You're In</h1>
            <p style={{ marginTop: 12 }}>Waiting for {state.host_first_name} to start the Board Fundraising Review Game.</p>
            <p className="bfg-gg-goal" style={{ marginTop: 16 }}>Fundraising Goal: {state.goal_display}</p>
            <p style={{ marginTop: 14 }}>
              The host controls the meeting. Your screen will automatically show the same section and ideas the host is discussing.
            </p>
          </div>
        )}

        {identity && state?.status === "in_progress" && round && (
          <>
            <RoundProgress current={round.round_number} total={state.total_rounds} />
            {round.status === "open" && (
              <div className="bfg-gg-card" data-testid="bfg-gg-shared-review">
                <h1>{round.title}</h1>
                <p style={{ marginTop: 10 }}>{round.instruction}</p>
                <div className="bfg-gg-ideas" style={{ marginTop: 18 }}>
                  {(round.ideas || []).map((idea) => {
                    const selected=(round.selected_idea_ids||[]).includes(idea.idea_id);
                    return <div className={`bfg-gg-idea ${selected?"selected":""}`} key={idea.idea_id} style={selected?{border:"2px solid #4f46e5"}:{}}>
                      <span className="bfg-gg-idea-text">{idea.text}</span>
                      <small>Source: {idea.suggested_by}{selected?" · BOARD AGREED":""}</small>
                    </div>;
                  })}
                </div>
                {(round.additional_agreed_ideas||[]).length>0&&<div className="bfg-gg-card" style={{marginTop:14,padding:14}}><strong>Agreed during this discussion</strong><ul>{round.additional_agreed_ideas.map((idea,index)=><li key={index}>{idea}</li>)}</ul></div>}
                {!round.ideas?.length && !(round.additional_agreed_ideas||[]).length && <p style={{ marginTop: 16 }}>No earlier information was supplied for this screen. Join the discussion so the Board can establish its direction.</p>}
                <p className="bfg-gg-rule">Discuss this screen with the Board. The Lead User will check the ideas the Board agrees with, and your screen will update automatically.</p>
              </div>
            )}
            {round.status === "closed" && (
              <div className="bfg-gg-card" data-testid="bfg-gg-advancing">
                <h1>Moving To The Next Review</h1><p>The host is advancing the board to the next screen.</p>
              </div>
            )}
          </>
        )}

        {identity && state?.status === "completed" && (
          <GroupReviewStage token={token} identity={identity} />
        )}
      </main>
    </div>
  );
}
