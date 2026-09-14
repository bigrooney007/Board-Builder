import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import { RoundProgress, RoundResults } from "./groupShared";

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
  const [ranking, setRanking] = useState([]);
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
      if (roundNumber !== lastRound.current) { lastRound.current = roundNumber; setRanking([]); }
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

  const toggleRank = (ideaId) => {
    if (!round || round.status !== "open" || round.my_submitted) return;
    setRanking((current) => current.includes(ideaId)
      ? current.filter((id) => id !== ideaId)
      : current.length < round.required_rank ? [...current, ideaId] : current);
  };

  const submit = async () => {
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/game/group/play/${token}/submit`, {
        slot_id: identity.slot_id, device_id: identity.device_id,
        round_number: round.round_number, rankings: ranking,
      });
      await poll();
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not submit your ranking. Please try again.");
      await poll();
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
  const ideasById = Object.fromEntries((round?.ideas || []).map((idea) => [idea.idea_id, idea]));
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
              {" "}Tonight, your board will review the ideas contributed before Game Night and identify the strongest priorities for your fundraising strategy.
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
              Tonight you will review the ideas your board contributed and help identify the strongest priorities for your fundraising strategy.
            </p>
          </div>
        )}

        {identity && state?.status === "in_progress" && round && (
          <>
            <RoundProgress current={round.round_number} total={state.total_rounds} />
            {round.status === "open" && !round.my_submitted && (
              <div className="bfg-gg-card" data-testid="bfg-gg-ranking">
                <h1>{round.title}</h1>
                <p style={{ marginTop: 10 }}>{round.instruction}</p>
                {round.required_rank > 0 ? (
                  <>
                    <p className="bfg-gg-rule" data-testid="bfg-gg-rank-rule">Choose and rank your top {round.required_rank} ideas.</p>
                    {ranking.length > 0 && (
                      <div className="bfg-gg-myranking" data-testid="bfg-gg-my-ranking">
                        <p className="bfg-gg-eyebrow">Your Ranking</p>
                        {ranking.map((ideaId, index) => (
                          <button type="button" key={ideaId} className="bfg-gg-ranked" onClick={() => toggleRank(ideaId)}>
                            <span className="bfg-gg-pos">#{index + 1}</span> {ideasById[ideaId]?.text}
                            <span className="bfg-gg-remove">Remove</span>
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="bfg-gg-ideas">
                      {(round.ideas || []).map((idea) => {
                        const position = ranking.indexOf(idea.idea_id);
                        return (
                          <button type="button" key={idea.idea_id}
                            className={`bfg-gg-idea ${position >= 0 ? "ranked" : ""}`}
                            onClick={() => toggleRank(idea.idea_id)}
                            data-testid={`bfg-gg-idea-${idea.idea_id}`}>
                            {position >= 0 && <span className="bfg-gg-pos">#{position + 1}</span>}
                            <span className="bfg-gg-idea-text">{idea.text}</span>
                            <small>Suggested by: {idea.suggested_by}</small>
                          </button>
                        );
                      })}
                    </div>
                    {error && <p className="bfg-error">{error}</p>}
                    <button className="bfg-btn bfg-btn-primary" style={{ width: "100%", marginTop: 18 }}
                      disabled={ranking.length !== round.required_rank || busy}
                      onClick={submit} data-testid="bfg-gg-submit-btn">
                      {busy ? "Submitting…" : "Submit My Ranking"}
                    </button>
                  </>
                ) : (
                  <p style={{ marginTop: 16 }}>No ideas were contributed for this strategy area. Waiting for the host to continue.</p>
                )}
              </div>
            )}
            {round.status === "open" && round.my_submitted && (
              <div className="bfg-gg-card" style={{ textAlign: "center" }} data-testid="bfg-gg-submitted">
                <h1>Ranking Submitted</h1>
                <p style={{ marginTop: 12 }}>Waiting for the rest of the board.</p>
                <p className="bfg-gg-rule" data-testid="bfg-gg-submit-count">{round.submitted_count} of {state.joined_count} players have submitted.</p>
              </div>
            )}
            {round.status === "closed" && (
              <div className="bfg-gg-card" data-testid="bfg-gg-round-results">
                <h1>Your Board's Priorities</h1>
                <p style={{ marginTop: 8 }}>{round.title}</p>
                <RoundResults results={round.results || []} />
                <p style={{ marginTop: 16 }}>
                  These are the ideas your board collectively prioritised. The remaining ideas have been saved and can still be considered when your fundraising strategy is created.
                </p>
                <p className="bfg-gg-rule">Waiting for the host to continue.</p>
              </div>
            )}
          </>
        )}

        {identity && state?.status === "completed" && (
          <div className="bfg-gg-card" style={{ textAlign: "center" }} data-testid="bfg-gg-complete">
            <p className="bfg-gg-eyebrow">Game Night</p>
            <h1>Review Game Complete</h1>
            <p style={{ marginTop: 14 }}>Your board has now identified the fundraising ideas it wants to prioritise.</p>
            <p style={{ marginTop: 10 }}>Stay with your board as you move into the next part of Game Night.</p>
          </div>
        )}
      </main>
    </div>
  );
}
