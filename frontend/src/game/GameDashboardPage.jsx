import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { SupportBox } from "@/member/CoursePages";
import { GameNightSection } from "./GameNightSection";
import { HostToolsSection } from "./HostToolsSection";
import { CompleteGameNightSection } from "./CompleteGameNightSection";
import { BoardMembersSection } from "./BoardMembersSection";
import { WorkingStrategyCard, StrategiesHistoryCard } from "./StrategyCards";
import { FinalOutputsSection } from "./MeetingOutputs";
import { DashboardTour } from "./DashboardTour";
import { BfgShell, formatDate, money } from "./gameShared";

const SUPPORT_TYPES = [
  "I have a question about this module",
  "I need help using the platform",
  "I need help executing this step",
  "I would like someone to help me complete this step",
];

const GroupGameCard = () => {
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  useEffect(() => {
    memberApi.get("/game/group/overview").then((r) => setOverview(r.data)).catch(() => {});
  }, []);
  if (!overview) return null;
  const session = overview.session;
  const completed = session?.status === "completed";
  return (
    <section className="bfg-panel" data-tour="group-game" data-testid="bfg-group-game-card">
      <div className="bfg-panel-head">
        <div>
          <><p className="bfg-eyebrow">STEP 6</p><h2>Group Review Game</h2></>
          <p className="bfg-panel-sub">
            {completed
              ? "Completed — 9 of 9 review screens completed"
              : session?.status === "in_progress"
                ? "In progress — continue running your Board Fundraising Day/Night with your board."
                : session
                  ? "Ready — your Group Game link is prepared and waiting."
                  : "Bring your board together on one shared screen to review every idea and agree on the complete fundraising system."}
          </p>
          {completed && <p className="bfg-note">{session.participants_joined} board members participated</p>}
        </div>
        <div className="bfg-bm-actions" style={{ marginTop: 0 }}>
          {completed ? (
            <>
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/group?results=1")} data-testid="bfg-view-group-results-btn">View Group Game Results</button>
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/group")} data-testid="bfg-open-group-game-btn">Open Group Game</button>
            </>
          ) : (
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => navigate("/game/group")} data-testid="bfg-start-group-game-btn">
              {session ? "Open Group Game" : "Start Group Game"}
            </button>
          )}
        </div>
      </div>
    </section>
  );
};

export default function GameDashboardPage() {
  const navigate = useNavigate();
  const { member, loading, logout } = useMemberAuth();
  const [data, setData] = useState(null);
  const [postgame, setPostgame] = useState(null);
  const [meeting, setMeeting] = useState(null);
  const [showTour, setShowTour] = useState(false);
  const [denied, setDenied] = useState(false);
  const [openingGame, setOpeningGame] = useState(false);
  const meetingPoller = useRef(null);

  useEffect(() => { document.title = "Your Game Dashboard | Board Fundraising Game"; }, []);

  const loadMeeting = useCallback(async () => {
    try {
      const overview = (await memberApi.get("/game/meeting/overview")).data;
      setMeeting(overview);
      clearInterval(meetingPoller.current);
      if (overview.group_completed && !["running", "done"].includes(overview.final?.status || "")) {
        try {
          await memberApi.post("/game/meeting/compile-final");
          const refreshed = (await memberApi.get("/game/meeting/overview")).data;
          setMeeting(refreshed);
          if (refreshed.final?.status === "running") {
            meetingPoller.current = setInterval(async () => {
              try {
                const next = (await memberApi.get("/game/meeting/overview")).data;
                setMeeting(next);
                if (next.final?.status !== "running") clearInterval(meetingPoller.current);
              } catch { /* keep polling */ }
            }, 5000);
          }
          return;
        } catch { /* the output cards will show the current state */ }
      }
      if (overview.final?.status === "running") {
        meetingPoller.current = setInterval(async () => {
          try {
            const next = (await memberApi.get("/game/meeting/overview")).data;
            setMeeting(next);
            if (next.final?.status !== "running") clearInterval(meetingPoller.current);
          } catch { /* keep polling */ }
        }, 5000);
      }
    } catch { /* section stays hidden */ }
  }, []);

  useEffect(() => () => clearInterval(meetingPoller.current), []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`, { replace: true }); return; }
    memberApi.get("/game/dashboard")
      .then((response) => setData(response.data))
      .catch((err) => {
        if (err.response?.status === 403) setDenied(true);
        else navigate("/board-fundraising-game", { replace: true });
      });
    memberApi.get("/game/postgame/overview").then((response) => setPostgame(response.data)).catch(() => {});
    loadMeeting();
  }, [loading, member, navigate, loadMeeting]);

  if (loading || (!data && !denied)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  if (denied) {
    return (
      <BfgShell>
        <main className="bfg-flow" data-testid="bfg-dashboard-denied">
          <div className="bfg-card" style={{ textAlign: "center" }}>
            <h1>Unlock Your Board Fundraising Game</h1>
            <p style={{ marginTop: 12 }}>Your account does not include the Board Fundraising Game yet.</p>
            <Link className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} to="/board-fundraising-game">Return To My Board Fundraising Game</Link>
          </div>
        </main>
      </BfgShell>
    );
  }

  const goalAmount = Number(data.goal?.amount || 0);
  const openIndividualGame = async () => {
    setOpeningGame(true);
    try {
      const situation = (await memberApi.get("/game/situation")).data;
      if (situation.completed) {
        const token = (await memberApi.post("/game/self-play")).data.token;
        navigate(`/play/${token}`);
      } else navigate("/game/setup");
    } catch { navigate("/game/setup"); }
  };

  return (
    <BfgShell nav={
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={async () => { await logout(); navigate("/"); }} data-testid="bfg-logout-btn">Log Out</button>
    }>
      <main className="bfg-dash" data-testid="bfg-dashboard">
        <div className="bfg-dash-head">
          <div>
            <p className="bfg-eyebrow">Your Board Fundraising Game</p>
            <h1 data-testid="bfg-dashboard-welcome">Welcome back, {data.first_name}</h1>
          </div>
          <Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/board-fundraising-game" data-testid="bfg-edit-game-profile-link">Edit Game Profile</Link>
        </div>

        <section className="bfg-panel bfg-tour-panel" data-testid="bfg-dashboard-tutorial-card">
          <div className="bfg-panel-head"><div><p className="bfg-eyebrow">START HERE</p><h2>Take A Guided Tour Of Your Dashboard</h2><p className="bfg-panel-sub">See how to play your individual game, prepare the Board, run the Group Game and move into execution.</p></div><button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => setShowTour(true)} data-testid="bfg-watch-tutorial-btn">START GUIDED TOUR</button></div>
        </section>

        <section className="bfg-panel" data-tour="play-individual-game" data-testid="bfg-play-individual-game">
          <div className="bfg-panel-head">
            <div>
              <p className="bfg-eyebrow">STEP 1</p>
              <h2>Play Your Board Fundraising Game</h2>
              <p className="bfg-panel-sub">Answer one strategic question at a time. After each answer, the platform makes your idea sharper and more actionable for you to approve before moving forward. Your game also captures your present fundraising reality and how you want to participate.</p>
            </div>
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" disabled={openingGame} onClick={openIndividualGame} data-testid="bfg-open-individual-game-btn">
              {openingGame ? "OPENING…" : "PLAY MY BOARD FUNDRAISING GAME"}
            </button>
          </div>
        </section>

        <div data-tour="working-strategy">
          <WorkingStrategyCard autoGenerate={data.situation_completed && data.individual_game_completed} />
        </div>


        <div data-tour="prepare-meeting">
          <GameNightSection />
        </div>
        <div data-tour="board-participation">
          <BoardMembersSection />
        </div>
        <div data-tour="meeting-resources">
          <HostToolsSection />
        </div>
        <GroupGameCard />
        <FinalOutputsSection overview={meeting} onRefresh={loadMeeting} />
        <CompleteGameNightSection overview={postgame} />

        <div className="bfg-dash-grid">
          <div className="bfg-dash-card" data-testid="bfg-dashboard-goal-card">
            <h3>Your Fundraising Goal</h3>
            <p className="bfg-big">{goalAmount ? money(goalAmount) : "Not set yet"}</p>
            {data.goal?.deadline && <p className="bfg-sub">by {formatDate(data.goal.deadline)}</p>}
            {data.organization?.name && <p className="bfg-sub">{data.organization.name}</p>}
          </div>
        </div>

        <StrategiesHistoryCard />

        <SupportBox productKey="board_fundraising_game" moduleNumber={1} supportTypes={SUPPORT_TYPES} />
        {showTour && <DashboardTour onClose={() => setShowTour(false)} />}
      </main>
    </BfgShell>
  );
}
