import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, LifeBuoy } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { SupportBox } from "@/member/CoursePages";
import { GameNightSection } from "./GameNightSection";
import { HostToolsSection } from "./HostToolsSection";
import { CompleteGameNightSection } from "./CompleteGameNightSection";
import { BoardMembersSection } from "./BoardMembersSection";
import { FinalOutputsSection } from "./MeetingOutputs";
import { BfgShell, formatDate, money } from "./gameShared";

const SUPPORT_TYPES = [
  "I have a question about this step",
  "I need help using the platform",
  "I need help executing this step",
  "I would like someone to help me complete this step",
];

const DashboardSection = ({ number, title, summary, status, children, defaultOpen = false, testId }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`bfg-panel bfg-machine-section ${open ? "is-open" : ""}`} data-testid={testId}>
      <button type="button" className="bfg-machine-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="bfg-machine-number">{String(number).padStart(2, "0")}</span>
        <span className="bfg-machine-title">
          <strong>{title}</strong>
          <small>{summary}</small>
        </span>
        <span className="bfg-machine-right">
          {status && <em>{status}</em>}
          <ChevronDown size={19} className={open ? "rotate" : ""}/>
        </span>
      </button>
      {open && <div className="bfg-machine-body">{children}</div>}
    </section>
  );
};

const GroupGameStage = () => {
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  useEffect(() => {
    memberApi.get("/game/group/overview").then((response) => setOverview(response.data)).catch(() => {});
  }, []);
  if (!overview) return <p className="bfg-note">Opening your Group Game…</p>;
  const session = overview.session;
  const completed = session?.status === "completed";
  const inProgress = session?.status === "in_progress";
  return (
    <div className="bfg-stage-stack">
      <div className="bfg-clean-stage">
        <h3>Bring The Board's Ideas Into One Room</h3>
        <p className="bfg-panel-sub">
          {completed
            ? "Your Board completed all nine decision screens. The final strategy is being built from the decisions the Board adopted."
            : inProgress
              ? "Your Group Game is in progress. Continue from the exact screen where the Board stopped."
              : "The Group Game brings together the founder's thinking, Board Member ideas, current fundraising reality and execution recommendations so the Board can decide what actually moves forward."}
        </p>
        <div className="bfg-night-summary" style={{ marginTop: 14 }}>
          <div className="bfg-summary-row"><span>Fundraising Goal</span><strong>{overview.goal_display || "Not set"}</strong></div>
          <div className="bfg-summary-row"><span>Individual Games Completed</span><strong>{overview.individual_completed || 0}</strong></div>
          <div className="bfg-summary-row"><span>Board Members</span><strong>{overview.board_member_count || 0}</strong></div>
          {session && <div className="bfg-summary-row"><span>Group Game</span><strong>{completed ? "Complete" : inProgress ? "In Progress" : "Prepared"}</strong></div>}
        </div>
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16 }} onClick={() => navigate("/game/group")}>
          {completed ? "OPEN GROUP GAME RESULTS" : inProgress ? "CONTINUE GROUP GAME" : "START GROUP GAME"}
        </button>
      </div>
      <HostToolsSection />
    </div>
  );
};

const DelegationReviewStage = ({ ready }) => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [preparing, setPreparing] = useState(false);

  const load = useCallback(async () => {
    if (!ready) return;
    try {
      const response = await memberApi.get("/game/portfolios");
      setData(response.data);
    } catch { /* final strategy may still be committing */ }
  }, [ready]);

  useEffect(() => {
    if (!ready) return;
    let live = true;
    const prepare = async () => {
      setPreparing(true);
      try { await memberApi.post("/game/portfolios/prepare"); } catch { /* existing drafts or final commit race */ }
      if (live) {
        await load();
        setPreparing(false);
      }
    };
    prepare();
    return () => { live = false; };
  }, [ready, load]);

  if (!ready) {
    return <p className="bfg-note">Complete the Group Game first. Proposed delegations are prepared after the final strategy is ready.</p>;
  }
  if (!data) return <p className="bfg-note">{preparing ? "Preparing each participant's proposed fundraising delegation…" : "Opening delegation review…"}</p>;

  const rows = data.portfolios || [];
  return (
    <div className="bfg-delegation-review" data-testid="bfg-delegation-review">
      <div className="bfg-clean-stage">
        <h3>Review What Will Be Delegated To Each Participant</h3>
        <p className="bfg-panel-sub">
          The platform combines each person's Individual Game, participation choices, Board decisions and meeting commitments. Review the proposed responsibility yourself before the strategy can be sent to that person.
        </p>
      </div>
      {!rows.length && <p className="bfg-note">No participant delegations are ready yet.</p>}
      {rows.map((row) => {
        const approved = ["ready_to_send", "sent", "approved", "materials_ready"].includes(row.status);
        return (
          <div className="bfg-delegation-row" key={row.portfolio_id} data-testid={`bfg-delegation-${row.portfolio_id}`}>
            <div>
              <strong>{row.member_name}</strong>
              <p>{row.system_count} system-building responsibilit{row.system_count === 1 ? "y" : "ies"} · {row.direct_count} direct fundraising activit{row.direct_count === 1 ? "y" : "ies"}</p>
            </div>
            <span className={approved ? "bfg-delegation-approved" : "bfg-delegation-review-needed"}>
              {approved ? "FOUNDER APPROVED" : "REVIEW REQUIRED"}
            </span>
            <button className={approved ? "bfg-btn bfg-btn-ghost bfg-btn-sm" : "bfg-btn bfg-btn-primary bfg-btn-sm"}
              onClick={() => navigate(`/game/portfolios/${row.portfolio_id}`)}>
              {approved ? "REVIEW DELEGATION" : "REVIEW & APPROVE"}
            </button>
          </div>
        );
      })}
      <p className="bfg-note" style={{ marginTop: 12 }}>
        Strategy delivery stays locked for a participant until their delegation is founder-approved.
      </p>
    </div>
  );
};

export default function GameDashboardPage() {
  const navigate = useNavigate();
  const { member, loading, logout } = useMemberAuth();
  const [data, setData] = useState(null);
  const [postgame, setPostgame] = useState(null);
  const [meeting, setMeeting] = useState(null);
  const [denied, setDenied] = useState(false);
  const [openingGame, setOpeningGame] = useState(false);
  const meetingPoller = useRef(null);

  useEffect(() => { document.title = "Board Fundraising Game Dashboard | Nonprofit Board Builder"; }, []);

  const loadMeeting = useCallback(async () => {
    try {
      const overview = (await memberApi.get("/game/meeting/overview")).data;
      setMeeting(overview);
      if (overview.final?.status === "done") {
        memberApi.get("/game/postgame/overview").then((response) => setPostgame(response.data)).catch(() => {});
      }
      clearInterval(meetingPoller.current);
      if (overview.group_completed && !["running", "done"].includes(overview.final?.status || "")) {
        try {
          await memberApi.post("/game/meeting/compile-final");
          const refreshed = (await memberApi.get("/game/meeting/overview")).data;
          setMeeting(refreshed);
          if (refreshed.final?.status === "done") {
            memberApi.get("/game/postgame/overview").then((response) => setPostgame(response.data)).catch(() => {});
          }
        } catch { /* Group decisions remain saved and can be retried. */ }
      }
      const state = overview.final?.status === "running" ? overview : null;
      if (state || overview.final?.status === "running") {
        meetingPoller.current = setInterval(async () => {
          try {
            const next = (await memberApi.get("/game/meeting/overview")).data;
            setMeeting(next);
            if (next.final?.status === "done") {
              memberApi.get("/game/postgame/overview").then((response) => setPostgame(response.data)).catch(() => {});
            }
            if (next.final?.status !== "running") clearInterval(meetingPoller.current);
          } catch { /* keep the last known state */ }
        }, 4000);
      }
    } catch { /* final-output stage stays available when data exists */ }
  }, []);

  useEffect(() => () => clearInterval(meetingPoller.current), []);

  const refreshDashboard = useCallback(async () => {
    try {
      const response = await memberApi.get("/game/dashboard");
      setData(response.data);
    } catch { /* the existing dashboard state remains visible */ }
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) {
      navigate(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`, { replace: true });
      return;
    }
    memberApi.get("/game/dashboard")
      .then((response) => setData(response.data))
      .catch((error) => {
        if (error.response?.status === 403) setDenied(true);
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
            <Link className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} to="/board-fundraising-game">Return To The Board Fundraising Game</Link>
          </div>
        </main>
      </BfgShell>
    );
  }

  const goalAmount = Number(data.goal?.amount || 0);
  const founderGameComplete = Boolean(data.situation_completed && data.individual_game_completed);
  const meetingReady = Boolean(data.game_night_ready);
  const boardReady = meetingReady && Number(data.board_participant_count || 0) > 0;

  const openIndividualGame = async () => {
    setOpeningGame(true);
    try {
      const situation = (await memberApi.get("/game/situation")).data;
      if (situation.completed) {
        const token = (await memberApi.post("/game/self-play")).data.token;
        navigate(`/play/${token}`);
      } else {
        navigate("/game/setup");
      }
    } catch {
      navigate("/game/setup");
    }
  };

  return (
    <BfgShell nav={
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={async () => { await logout(); navigate("/"); }} data-testid="bfg-logout-btn">Log Out</button>
    }>
      <main className="bfg-dash bfg-clean-dashboard" data-testid="bfg-dashboard">
        <header className="bfg-clean-dashboard-hero">
          <p className="bfg-eyebrow">NONPROFIT BOARD BUILDER</p>
          <h1>BOARD FUNDRAISING GAME</h1>
          <p>Build the fundraising strategy with your Board, agree the system required to execute it and give every Board Member a clear role in raising money and strengthening that system.</p>
          <div className="bfg-goal-chip">
            <span>Fundraising Goal</span>
            <strong>{goalAmount ? money(goalAmount) : "Not set yet"}</strong>
            {data.goal?.deadline && <small>Needed by {formatDate(data.goal.deadline)}</small>}
          </div>
        </header>

        <DashboardSection
          number={1}
          title="PLAY THE BOARD FUNDRAISING GAME"
          summary="Build your starting fundraising direction, document the fundraising system you already have and tell us how you want to participate."
          status={founderGameComplete ? "Complete" : "Start Here"}
          defaultOpen
          testId="bfg-dashboard-section-founder-game"
        >
          <div className="bfg-clean-stage">
            <h3>Your Thinking Comes First</h3>
            <p className="bfg-panel-sub">Answer each strategic question in your own words. The platform makes the idea actionable without replacing your thinking. You decide what becomes part of the strategy.</p>
            <button className="bfg-btn bfg-btn-primary" disabled={openingGame} onClick={openIndividualGame} data-testid="bfg-open-individual-game-btn">
              {openingGame ? "OPENING…" : founderGameComplete ? "REVIEW MY BOARD FUNDRAISING GAME" : "PLAY MY BOARD FUNDRAISING GAME"}
            </button>
          </div>
        </DashboardSection>

        <DashboardSection
          number={2}
          title="SET YOUR BOARD MEETING AND FUNDING DEADLINE"
          summary="Set the meeting your Board will use to make final decisions and tell us when the money is needed so the execution plan is built backward from the real deadline."
          status={!founderGameComplete ? "Locked" : meetingReady ? "Complete" : "Set Meeting"}
          testId="bfg-dashboard-section-meeting"
        >
          {founderGameComplete
            ? <GameNightSection onSaved={refreshDashboard} />
            : <p className="bfg-note">Complete your individual Board Fundraising Game first.</p>}
        </DashboardSection>

        <DashboardSection
          number={3}
          title="INVITE YOUR BOARD MEMBERS TO PLAY"
          summary="Add each Board Member, send their private Game invitation, resend when needed and use a person-specific call script for follow-up."
          status={!founderGameComplete ? "Locked" : meetingReady ? "Invite Board" : "Locked"}
          testId="bfg-dashboard-section-board"
        >
          {!founderGameComplete ? (
            <p className="bfg-note">Complete your individual Board Fundraising Game first.</p>
          ) : !meetingReady ? (
            <p className="bfg-note">Save the Board meeting date, time, timezone and funding deadline in Section 2 before inviting participants.</p>
          ) : (
            <BoardMembersSection onChanged={refreshDashboard} />
          )}
        </DashboardSection>

        <DashboardSection
          number={4}
          title="RUN THE GROUP BOARD FUNDRAISING GAME"
          summary="Discuss every idea together, choose what the Board agrees to, settle the execution system and capture the meeting discussion and delegation."
          status={meeting?.group_completed ? "Complete" : boardReady ? "Group Decision" : "Locked"}
          testId="bfg-dashboard-section-group"
        >
          {boardReady
            ? <GroupGameStage />
            : <p className="bfg-note">Save the Board meeting and add at least one Board participant before preparing the Group Game.</p>}
        </DashboardSection>

        <DashboardSection
          number={5}
          title="FINAL FUNDRAISING STRATEGY AND DELEGATION"
          summary="Turn the Board's adopted decisions into a concise execution strategy, then review the responsibility proposed for every participant before sharing it."
          status={meeting?.final?.status === "done" ? "Ready To Review" : meeting?.final?.status === "running" ? "Generating" : "Waiting For Group Game"}
          testId="bfg-dashboard-section-strategy"
        >
          <FinalOutputsSection overview={meeting} onRefresh={loadMeeting} compact />
          <DelegationReviewStage ready={meeting?.final?.status === "done"} />
        </DashboardSection>

        <DashboardSection
          number={6}
          title="SHARE THE STRATEGY AND MOVE INTO EXECUTION"
          summary="Send the final strategy, activate Board Fundraising Portfolios and give Board Members the execution tools and assistant support tied to their approved responsibilities."
          status={postgame?.adopted ? "Execution" : "Waiting For Strategy"}
          testId="bfg-dashboard-section-execution"
        >
          <CompleteGameNightSection overview={postgame} />
          {postgame?.adopted && (
            <div className="bfg-bm-actions" style={{ marginTop: 16 }}>
              <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => navigate("/game/portfolios")}>MANAGE BOARD FUNDRAISING PORTFOLIOS</button>
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => navigate("/game/complete?send=1")}>MANAGE STRATEGY DELIVERY</button>
            </div>
          )}
        </DashboardSection>

        <section className="bfg-persistent-support" data-testid="bfg-dashboard-support">
          <div className="bfg-support-head">
            <LifeBuoy size={28}/>
            <div>
              <p className="bfg-eyebrow">SUPPORT THROUGHOUT THE PROCESS</p>
              <h2>Need Help With Your Board Fundraising Game?</h2>
              <p>Tell us where you are stuck or what you need help executing. Your request stays connected to the Board Fundraising Game.</p>
            </div>
          </div>
          <SupportBox productKey="board_fundraising_game" moduleNumber={1} supportTypes={SUPPORT_TYPES} />
        </section>
      </main>
    </BfgShell>
  );
}
