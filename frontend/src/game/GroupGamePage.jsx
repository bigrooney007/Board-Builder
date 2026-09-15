import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { RoundProgress, RoundResults } from "./groupShared";

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
            <Link className="bfg-btn bfg-btn-primary bfg-btn-sm" to="/game/strategy/priorities" data-testid="bfg-gg-results-generate-strategy-btn">
              Generate Board-Prioritized Strategy
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
  const [confirmClose, setConfirmClose] = useState(false);
  const [showPrevious, setShowPrevious] = useState(false);
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

  const closeVoting = () => {
    if (round && round.submitted_count < (session?.joined_count || 0)) { setConfirmClose(true); return; }
    run("close", () => memberApi.post("/game/group/close-round", { round_number: round.round_number }));
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
                <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} disabled={busy === "start"}
                  onClick={() => run("start", () => memberApi.post("/game/group/start"))} data-testid="bfg-gg-start-btn">
                  {busy === "start" ? "Starting…" : "Start Review Game"}
                </button>
              </div>
            )}

            {status === "in_progress" && round && (
              <div className="bfg-panel" data-testid="bfg-gg-host-round">
                <RoundProgress current={round.round_number} total={session.total_rounds} />
                <h2>{round.title}</h2>
                <p className="bfg-panel-sub">{round.instruction}</p>
                {round.status === "open" && (
                  <>
                    <p className="bfg-note" style={{ marginTop: 14 }} data-testid="bfg-gg-host-submit-count">
                      {round.submitted_count} of {session.joined_count} rankings submitted
                    </p>
                    <div className="bfg-gg-playerlist">
                      {session.players.filter((player) => player.joined).map((player) => (
                        <div key={player.name} className="bfg-summary-row">
                          <span>{player.name}</span>
                          <strong className={player.submitted ? "bfg-success" : ""}>{player.submitted ? "Submitted" : "Waiting"}</strong>
                        </div>
                      ))}
                    </div>
                    {round.idea_count === 0 && (
                      <p className="bfg-note" style={{ marginTop: 12 }}>No ideas were contributed for this strategy area. You can close this round and continue.</p>
                    )}
                    {confirmClose ? (
                      <div className="bfg-error" style={{ marginTop: 16 }} data-testid="bfg-gg-close-confirm">
                        Not everyone has submitted their ranking. Do you want to close voting anyway?
                        <div className="bfg-bm-actions">
                          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setConfirmClose(false)} data-testid="bfg-gg-keep-voting-btn">Keep Voting Open</button>
                          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" data-testid="bfg-gg-close-anyway-btn"
                            onClick={() => { setConfirmClose(false); run("close", () => memberApi.post("/game/group/close-round", { round_number: round.round_number })); }}>
                            Close Voting
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} disabled={busy === "close"}
                        onClick={closeVoting} data-testid="bfg-gg-close-voting-btn">
                        {busy === "close" ? "Closing…" : "Close Voting & Show Results"}
                      </button>
                    )}
                  </>
                )}
                {round.status === "closed" && (
                  <>
                    <h3 style={{ marginTop: 20, fontSize: 18 }}>Your Board's Priorities</h3>
                    <RoundResults results={round.results || []} />
                    <p className="bfg-note" style={{ marginTop: 14 }}>
                      These are the ideas your board collectively prioritized. The remaining ideas have been saved and can still be considered when your fundraising strategy is created.
                    </p>
                    <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16 }} disabled={busy === "next"}
                      onClick={() => run("next", () => memberApi.post("/game/group/next-round"))} data-testid="bfg-gg-next-round-btn">
                      {busy === "next" ? "Please wait…" : round.round_number >= session.total_rounds ? "Finish Review Game" : "Continue To Next Round"}
                    </button>
                  </>
                )}
              </div>
            )}

            {status === "in_progress" && session?.closed_rounds?.length > 0 && (
              <div className="bfg-panel" data-testid="bfg-gg-previous-rounds">
                <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setShowPrevious(!showPrevious)} data-testid="bfg-gg-previous-toggle">
                  {showPrevious ? "Hide Previous Rounds" : "Previous Rounds"}
                </button>
                {showPrevious && session.closed_rounds.map((item) => (
                  <div key={item.round_number} style={{ marginTop: 16 }}>
                    <h3 style={{ fontSize: 16 }}>{item.title}</h3>
                    <RoundResults results={item.results} compact />
                  </div>
                ))}
              </div>
            )}

            {status === "completed" && (
              <div className="bfg-panel" style={{ textAlign: "center" }} data-testid="bfg-gg-host-complete">
                <h2>Your Board Review Is Complete</h2>
                <p className="bfg-panel-sub" style={{ marginTop: 12 }}>
                  Your board has reviewed the ideas contributed before Game Night and identified its strongest fundraising priorities.
                  {" "}The prioritized ideas and additional board ideas have been saved and are ready to be used to build your Board-Prioritized Fundraising Strategy.
                </p>
                <p style={{ marginTop: 14, fontWeight: 700, color: "#059669" }}>8 of 8 Review Rounds Completed</p>
                <div className="bfg-panel" style={{ marginTop: 18, textAlign: "center" }}>
                  <h3 style={{ fontSize: 17 }}>Generate Board-Prioritized Strategy</h3>
                  <p className="bfg-panel-sub" style={{ marginTop: 8 }}>Turn your board's priorities and ideas into a complete fundraising strategy for your board to review together.</p>
                  <Link className="bfg-btn bfg-btn-primary" style={{ marginTop: 14 }} to="/game/strategy/priorities" data-testid="bfg-gg-generate-strategy-btn">
                    Generate Board-Prioritized Strategy
                  </Link>
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
