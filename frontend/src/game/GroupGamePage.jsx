import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { RoundProgress, RoundResults } from "./groupShared";
import { LiveMeetingRecorder } from "./MeetingOutputs";

const fmtDate = (raw) => {
  if (!raw) return "";
  const date = new Date(`${raw}T00:00:00`);
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
};

const ResultsSummary = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    memberApi.get("/game/group/results").then((r) => setData(r.data))
      .catch(() => setError("No Group Game results are available yet."));
  }, []);
  if (error) return <div className="bfg-panel"><p className="bfg-note">{error}</p></div>;
  if (!data) return <div className="bfg-panel"><p className="bfg-note">Loading results…</p></div>;
  return (
    <div data-testid="bfg-gg-results-summary">
      <div className="bfg-panel">
        <h2>Group Game Results</h2>
        <p className="bfg-panel-sub">{data.rounds_completed} of {data.total_rounds} rounds completed · {data.participants} board members participated</p>
        {data.status === "completed" && (
          <div style={{ marginTop: 14 }}>
            <Link className="bfg-btn bfg-btn-primary bfg-btn-sm" to="/game/dashboard" data-testid="bfg-gg-results-generate-strategy-btn">
              Return To Dashboard And Create Final Strategy
            </Link>
            <p className="bfg-note" style={{ marginTop: 8 }}>Turn your board's priorities and ideas into a complete fundraising strategy for your board to review together.</p>
          </div>
        )}
      </div>
      {data.areas.map((area) => (
        <div className="bfg-panel" key={area.round_number} data-testid={`bfg-gg-summary-${area.section_key}`}>
          <h2>{area.title.replace(/^Round \d+: /, "")}</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 10 }}>Board Priorities</p>
          {area.priorities.length === 0 && <p className="bfg-note">No prioritized ideas for this area.</p>}
          <RoundResults results={area.priorities} />
          {area.additional.length > 0 && (
            <>
              <p className="bfg-panel-sub" style={{ marginTop: 16 }}>Additional Board Ideas</p>
              <ul className="bfg-gg-additional-list">
                {area.additional.map((item) => <li key={item.idea_id}>{item.text}</li>)}
              </ul>
            </>
          )}
        </div>
      ))}
    </div>
  );
};

export default function GroupGamePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const showResults = searchParams.get("results") === "1";
  const { member, loading } = useMemberAuth();
  const [overview, setOverview] = useState(null);
  const [session, setSession] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [newAgreedIdea, setNewAgreedIdea] = useState("");
  const timer = useRef(null);

  useEffect(() => { document.title = "Group Review Game | Board Fundraising Game"; }, []);

  const loadOverview = useCallback(async () => {
    try { setOverview((await memberApi.get("/game/group/overview")).data); }
    catch (err) { if (err.response?.status === 403) navigate("/game/start", { replace: true }); }
  }, [navigate]);

  const loadSession = useCallback(async () => {
    try { setSession((await memberApi.get("/game/group/session")).data); }
    catch { setSession(null); }
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    loadOverview(); loadSession();
  }, [loading, member, navigate, loadOverview, loadSession]);

  useEffect(() => {
    timer.current = setInterval(() => { loadSession(); }, 3000);
    return () => clearInterval(timer.current);
  }, [loadSession]);

  const run = async (key, fn) => {
    setBusy(key); setError("");
    try { await fn(); await loadSession(); await loadOverview(); }
    catch (err) { setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Something went wrong. Please try again."); }
    setBusy("");
  };

  if (loading || !member) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const status = session?.session?.status || overview?.session?.status || "";
  const round = session?.current_round;
  const groupLink = session?.session?.token ? `${window.location.origin}/group-game/${session.session.token}` : "";

  const copyLink = async () => {
    try { await navigator.clipboard.writeText(groupLink); } catch { window.prompt("Copy this Group Game link:", groupLink); }
    setCopied(true); setTimeout(() => setCopied(false), 2500);
  };

  const saveDecision = async (selectedIds, additions = round?.additional_agreed_ideas || []) => {
    if (!round) return;
    await memberApi.post("/game/group/decision", {
      round_number: round.round_number,
      selected_idea_ids: selectedIds,
      additional_agreed_ideas: additions,
    });
    await loadSession();
  };

  const toggleIdea = async (ideaId) => {
    const current = round?.selected_idea_ids || [];
    const next = current.includes(ideaId) ? current.filter((id) => id !== ideaId) : [...current, ideaId];
    setBusy(`decision-${ideaId}`);
    setError("");
    try { await saveDecision(next); }
    catch (err) { setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save that Board decision."); }
    setBusy("");
  };

  const addDiscussionIdea = async () => {
    const text = newAgreedIdea.trim();
    if (!text || !round) return;
    const additions = [...(round.additional_agreed_ideas || []), text];
    setBusy("add-agreed-idea");
    setError("");
    try { await saveDecision(round.selected_idea_ids || [], additions); setNewAgreedIdea(""); }
    catch (err) { setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save that agreed idea."); }
    setBusy("");
  };

  const continueMeeting = async () => {
    await memberApi.post("/game/group/close-round", { round_number: round.round_number });
    await memberApi.post("/game/group/next-round");
    setNewAgreedIdea("");
  };
  const startMeeting = async () => {
    if (navigator.mediaDevices?.getUserMedia) {
      try { const stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(track=>track.stop()); }
      catch { /* The recorder shows the transcript alternatives when microphone access is unavailable. */ }
    }
    return memberApi.post("/game/group/start");
  };

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-gg-back-dashboard">Back to Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-group-game-page">
        <p className="bfg-eyebrow">Game Night</p>
        <h1 style={{ marginBottom: 20 }}>Board Fundraising Review Game</h1>

        {showResults ? <ResultsSummary /> : (
          <>
            {overview && !["waiting", "prepared", "in_progress", "completed"].includes(status) && (
              <div className="bfg-panel" data-testid="bfg-gg-overview">
                <div className="bfg-night-summary">
                  <div className="bfg-summary-row"><span>Fundraising Goal</span><strong>{overview.goal_display}</strong></div>
                  <div className="bfg-summary-row"><span>Game Night</span><strong>{fmtDate(overview.game_night_date) || "Not scheduled yet"}</strong></div>
                  <div className="bfg-summary-row"><span>Board Members</span><strong>{overview.board_member_count}</strong></div>
                  <div className="bfg-summary-row"><span>Individual Games Completed</span><strong>{overview.individual_completed}</strong></div>
                  <div className="bfg-summary-row"><span>Individual Games In Progress</span><strong>{overview.individual_in_progress}</strong></div>
                  <div className="bfg-summary-row"><span>Board Ideas Ready For Review</span><strong data-testid="bfg-gg-responses-ready">{overview.responses_ready} completed responses</strong></div>
                </div>
                {overview.individual_completed < overview.board_member_count && (
                  <p className="bfg-note" style={{ marginTop: 14 }}>
                    Some board members have not completed their Individual Game. Any completed sections they have submitted can still be included in tonight's review.
                  </p>
                )}
                <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} disabled={busy === "prepare"}
                  onClick={() => run("prepare", () => memberApi.post("/game/group/prepare"))} data-testid="bfg-gg-prepare-btn">
                  {busy === "prepare" ? "Preparing…" : "Prepare Group Game"}
                </button>
              </div>
            )}

            {(status === "waiting" || status === "prepared") && session && (
              <div className="bfg-panel" data-testid="bfg-gg-lobby">
                <h2>Your Group Game Is Ready</h2>
                <p className="bfg-panel-sub">Share this link with everyone participating in Game Night. They do not need to create an account or log in.</p>
                <div className="bfg-gg-linkbox">
                  <code data-testid="bfg-gg-link">{groupLink}</code>
                  <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={copyLink} data-testid="bfg-gg-copy-link-btn">
                    {copied ? "Link Copied" : "Copy Group Game Link"}
                  </button>
                </div>
                <h3 style={{ marginTop: 22, fontSize: 16 }}>Players Joined</h3>
                <p className="bfg-note" data-testid="bfg-gg-joined-count">{session.joined_count} of {session.board_member_count} Board Members Joined</p>
                <div className="bfg-gg-playerlist">
                  {session.players.map((player) => (
                    <div key={player.name} className="bfg-summary-row">
                      <span>{player.name}</span>
                      <strong className={player.joined ? "bfg-success" : ""}>{player.joined ? "Joined" : "Waiting"}</strong>
                    </div>
                  ))}
                </div>
                <h3 style={{ marginTop: 22, fontSize: 18 }}>Now Let's Bring The Board's Ideas Together</h3>
                <p className="bfg-panel-sub" style={{ marginTop: 8, textAlign: "left" }}>
                  Everyone has already shared their thinking individually. The host controls one shared review screen, and every participant sees the same ideas at the same time. Discuss what should move forward while the meeting transcript captures the board's actual decisions.
                </p>
                <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} disabled={busy === "start"}
                  onClick={() => run("start", startMeeting)} data-testid="bfg-gg-start-btn">
                  {busy === "start" ? "Starting…" : "Start Group Game"}
                </button>
              </div>
            )}

            {status === "in_progress" && round && (
              <>
              <LiveMeetingRecorder autoStart title="Transcribe The Complete Board Fundraising Meeting" startLabel="ALLOW MICROPHONE AND START TRANSCRIPTION" onFinished={() => { loadSession(); loadOverview(); }} />
              <div className="bfg-panel" data-testid="bfg-gg-host-round">
                <RoundProgress current={round.round_number} total={session.total_rounds} />
                <h2>{round.title}</h2>
                <p className="bfg-panel-sub">{round.instruction}</p>
                <p className="bfg-note" style={{ marginTop: 14 }}>
                  Discuss every idea. As the Board agrees, check every idea that should become part of the strategy. The checkboxes are the Board's explicit decision; the microphone transcript preserves the discussion, changes and delegation behind those choices.
                </p>
                <div className="bfg-gg-ideas" style={{ marginTop: 18 }}>
                  {(round.ideas || []).map((idea) => {
                    const selected=(round.selected_idea_ids||[]).includes(idea.idea_id);
                    return <label className={`bfg-gg-idea ${selected?"selected":""}`} key={idea.idea_id} style={{display:"flex",gap:12,alignItems:"flex-start",cursor:"pointer"}}>
                      <input type="checkbox" checked={selected} disabled={busy===`decision-${idea.idea_id}`} onChange={()=>toggleIdea(idea.idea_id)} style={{marginTop:4}}/>
                      <span style={{display:"block",flex:1}}><span className="bfg-gg-idea-text">{idea.text}</span><small>Source: {idea.suggested_by}{selected?" · BOARD AGREED":""}</small></span>
                    </label>;
                  })}
                  {!round.ideas?.length && <p className="bfg-note">No earlier information was supplied for this screen. Use the discussion to establish the Board's direction, then add the agreed idea below.</p>}
                </div>
                {(round.additional_agreed_ideas||[]).length>0&&<div className="bfg-panel" style={{marginTop:14,padding:14}}>
                  <strong>Agreed ideas added during this meeting</strong>
                  <ul>{round.additional_agreed_ideas.map((idea,index)=><li key={index}>{idea}</li>)}</ul>
                </div>}
                <div className="bfg-panel" style={{marginTop:14,padding:14}}>
                  <label className="bfg-field"><span>Add an idea the Board agreed during the discussion</span>
                    <textarea rows={3} value={newAgreedIdea} onChange={e=>setNewAgreedIdea(e.target.value)} placeholder="Type the Board's agreed wording as closely as possible."/>
                  </label>
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={!newAgreedIdea.trim()||busy==="add-agreed-idea"} onClick={addDiscussionIdea}>
                    {busy==="add-agreed-idea"?"SAVING…":"ADD AGREED IDEA"}
                  </button>
                </div>
                {round.status === "open" && (
                  <>
                    {round.round_number===5&&<p className="bfg-note" style={{ marginTop: 14 }}><strong>Team discussion:</strong> Confirm what each person already said they are willing to do, change it if the person changes their mind, identify any role nobody can take, and say the final delegation aloud so the transcript captures it.</p>}
                    <p className="bfg-note" style={{ marginTop: 14 }}>Continue only after the Board has checked at least one agreed idea or added its agreed wording from the discussion. Every participant screen will advance with yours.</p>
                    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} disabled={busy === "next"||(!(round.selected_idea_ids||[]).length&&!(round.additional_agreed_ideas||[]).length)}
                      onClick={() => run("next", continueMeeting)} data-testid="bfg-gg-next-round-btn">
                      {busy === "next" ? "Please wait…" : round.round_number >= session.total_rounds ? "ADOPT THESE DECISIONS & END GROUP GAME" : "ADOPT THESE DECISIONS & CONTINUE"}
                    </button>
                  </>
                )}
              </div>
              </>
            )}

            {status === "completed" && (
              <div className="bfg-panel" style={{ textAlign: "center" }} data-testid="bfg-gg-host-complete">
                <h2>The Group Game Is Complete</h2>
                <p className="bfg-panel-sub" style={{ marginTop: 12 }}>
                  Your board has now made explicit decisions across the complete fundraising strategy and execution system. The checked ideas, ideas added during discussion and the meeting transcript will now be combined into the Final Board Fundraising Strategy.
                </p>
                <p style={{ marginTop: 14, fontWeight: 700, color: "#059669" }}>{session?.total_rounds || 6} of {session?.total_rounds || 6} Review Rounds Completed</p>
                <div className="bfg-panel" style={{ marginTop: 18, textAlign: "center" }}>
                  <h3 style={{ fontSize: 17 }}>Create Your Final Fundraising Strategy</h3>
                  <p className="bfg-panel-sub" style={{ marginTop: 8 }}>The final strategy is created from the complete upward stream of organization information, board ideas and meeting decisions.</p>
                  <Link className="bfg-btn bfg-btn-primary" style={{ marginTop: 14 }} to="/game/dashboard" data-testid="bfg-gg-generate-strategy-btn">RETURN TO DASHBOARD</Link>
                </div>
                <div className="bfg-bm-actions" style={{ justifyContent: "center", marginTop: 18 }}>
                  <Link className="bfg-btn bfg-btn-ghost" to="/game/group?results=1" data-testid="bfg-gg-view-results-btn">View Group Game Results</Link>
                  <Link className="bfg-btn bfg-btn-primary" to="/game/dashboard" data-testid="bfg-gg-return-dashboard-btn">Return To Dashboard</Link>
                </div>
              </div>
            )}

            {error && <p className="bfg-error" data-testid="bfg-gg-host-error">{error}</p>}
          </>
        )}
      </main>
    </BfgShell>
  );
}
