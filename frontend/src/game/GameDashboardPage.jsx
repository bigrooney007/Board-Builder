import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { SupportBox } from "@/member/CoursePages";
import { GameNightSection } from "./GameNightSection";
import { HostToolsSection } from "./HostToolsSection";
import { CompleteGameNightSection } from "./CompleteGameNightSection";
import { BoardMembersSection } from "./BoardMembersSection";
import { WorkingStrategyCard, StrategiesHistoryCard, AdoptedStrategyCard } from "./StrategyCards";
import { CompleteBoardMeetingSection, FinalOutputsSection } from "./MeetingOutputs";
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
          <h2>Group Review Game</h2>
          <p className="bfg-panel-sub">
            {completed
              ? "Completed — 8 of 8 rounds completed"
              : session?.status === "in_progress"
                ? "In progress — continue running your Board Fundraising Day/Night with your board."
                : session
                  ? "Ready — your Group Game link is prepared and waiting."
                  : "Bring your board together to review and rank the ideas contributed before your meeting."}
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
  const meetingPoller = useRef(null);

  useEffect(() => { document.title = "Your Game Dashboard | Board Fundraising Game"; }, []);

  const loadMeeting = useCallback(async () => {
    try {
      const overview = (await memberApi.get("/game/meeting/overview")).data;
      setMeeting(overview);
      clearInterval(meetingPoller.current);
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
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    memberApi.get("/game/dashboard")
      .then((response) => setData(response.data))
      .catch((err) => {
        if (err.response?.status === 403) setDenied(true);
        else navigate("/game/start", { replace: true });
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
            <Link className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} to="/game/start">Set Up & Unlock My Game</Link>
          </div>
        </main>
      </BfgShell>
    );
  }

  const goalAmount = Number(data.goal?.amount || 0);

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
          <Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/start?edit=1" data-testid="bfg-edit-game-profile-link">Edit Game Profile</Link>
        </div>

        <div data-tour="working-strategy">
          <WorkingStrategyCard />
        </div>

        <AdoptedStrategyCard goalDisplay={goalAmount ? money(goalAmount) : ""} />
        <CompleteGameNightSection overview={postgame} />

        <div className="bfg-dash-grid">
          <div className="bfg-dash-card" data-testid="bfg-dashboard-goal-card">
            <h3>Your Fundraising Goal</h3>
            <p className="bfg-big">{goalAmount ? money(goalAmount) : "Not set yet"}</p>
            {data.goal?.deadline && <p className="bfg-sub">by {formatDate(data.goal.deadline)}</p>}
            {data.organization?.name && <p className="bfg-sub">{data.organization.name}</p>}
          </div>
          <div className="bfg-dash-card" data-testid="bfg-dashboard-status-card">
            <h3>Game Status</h3>
            {data.situation_completed ? (
              <>
                <p className="bfg-big" style={{ fontSize: 22 }} data-testid="bfg-journey-status">{postgame?.journey_status || "Set Up Your Board Fundraising Game"}</p>
                <p className="bfg-sub">{{
                  "Setting Up": "Complete your setup and add the board members who will play.",
                  "Board Preparing": "Invitations are out and your board members are playing their Individual Games.",
                  "Ready For Game Night": "Your Board Fundraising Day/Night is scheduled and your board is preparing.",
                  "Game Night In Progress": "Your board is playing the Group Review Game together.",
                  "Strategy Review": "Your board is reviewing its fundraising strategy.",
                  "Strategy Adopted": "Your board has adopted its fundraising strategy.",
                  "Moving Into Execution": "Board Fundraising Portfolios are being prepared and sent.",
                  "Execution Ready": "Approved board members can now access their execution resources.",
                }[postgame?.journey_status] || "Your game setup is complete. Prepare your board for your Board Fundraising Day/Night."}</p>
              </>
            ) : (
              <>
                <p className="bfg-big" style={{ fontSize: 22 }}>Complete Your Game Setup</p>
                <p className="bfg-sub">Tell us about your current fundraising situation so your game fits your organization.</p>
                <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 14 }} onClick={() => navigate("/game/setup")} data-testid="bfg-dashboard-complete-setup-btn">
                  Complete My Game Setup
                </button>
              </>
            )}
          </div>
          <div className="bfg-dash-card" data-testid="bfg-dashboard-tutorial-card">
            <h3>Tutorial</h3>
            <p className="bfg-sub">Take a guided tour of your dashboard — how to prepare your board, run the meeting and build your strategy.</p>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 14 }} onClick={() => setShowTour(true)} data-testid="bfg-watch-tutorial-btn">
              Tutorial
            </button>
          </div>
        </div>

        <div data-tour="board-participation">
          <BoardMembersSection />
        </div>
        <div data-tour="prepare-meeting">
          <GameNightSection />
        </div>
        <div data-tour="meeting-resources">
          <HostToolsSection />
        </div>
        <GroupGameCard />
        <div data-tour="complete-meeting">
          <CompleteBoardMeetingSection overview={meeting} onRefresh={loadMeeting} />
        </div>
        <FinalOutputsSection overview={meeting} />
        <StrategiesHistoryCard />

        <SupportBox productKey="board_fundraising_game" moduleNumber={1} supportTypes={SUPPORT_TYPES} />
        {showTour && <DashboardTour onClose={() => setShowTour(false)} />}
      </main>
    </BfgShell>
  );
}
