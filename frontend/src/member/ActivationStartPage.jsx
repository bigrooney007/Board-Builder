import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { VideoBlock } from "./CoursePages";
import ActivationModule2 from "./ActivationModule2";
import { ActivationParticipantsPanel } from "./ActivationParticipantsPanel";

const ACTIVATION_VIDEO = { youtube_url: "https://youtu.be/Aw751ZtIIks", title: "Board Fundraising Activation" };
const err = (e, fallback) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : fallback);

const StatusLine = ({ label, value, testId }) => (
  <p style={{ margin: "0 0 8px" }} data-testid={testId}><strong>{label}:</strong> {value}</p>
);

const UnderwayView = ({ state, reload }) => {
  const { delivery, progress } = state;
  const dwr = delivery.engagement_type === "dwr";
  return (
    <>
      <header className="member-page-heading">
        <p className="eyebrow">Board Fundraising Activation</p>
        <h1 data-testid="activation-underway-heading">Your Board Fundraising Planning Process Is Underway</h1>
      </header>
      <section className="member-card" data-testid="activation-underway-status">
        <h2>Where Things Stand</h2>
        <StatusLine label="Responses expected" value={progress.expected} testId="underway-expected" />
        <StatusLine label="Responses received" value={progress.received} testId="underway-received" />
        <StatusLine label="Still outstanding" value={progress.outstanding} testId="underway-outstanding" />
        <StatusLine label="Next Board meeting" value={`${delivery.next_board_meeting_date}${delivery.meeting_time ? ` at ${delivery.meeting_time}` : ""}`} testId="underway-meeting" />
      </section>
      <section className="member-card" data-testid="activation-underway-next">
        {dwr ? (
          <>
            <h2>What Happens Next</h2>
            <p>We are tracking your Board Members' Fundraising Planning responses. You do not need to log back in to check progress.</p>
            <p><strong>Rooney will continue working with you by email</strong> — we will let you know when it is time for the next step, and Rooney will build your Fundraising Strategy with you from there.</p>
          </>
        ) : delivery.ready ? (
          <>
            <h2>Your Strategy Resources Are Ready</h2>
            <p>Your Board's planning responses are ready for the next step. Build and review your Fundraising Strategy, then take it to your Board.</p>
            <a className="button" href="/app/activation/resources" data-testid="underway-resources-button">GO TO MY FUNDRAISING STRATEGY RESOURCES</a>
          </>
        ) : (
          <>
            <h2>What Happens Next</h2>
            <p>We are tracking your Board Members' Fundraising Planning responses and will email you when action is needed. You do not need to log back in to check progress.</p>
            <p>When enough responses are in — or you tell us to proceed with what we have — we will email you a link to return and build your Fundraising Strategy, along with the Board communication and Adoption Guide you will need.</p>
          </>
        )}
        <button type="button" className="button button-outline" style={{ marginTop: 12 }} onClick={reload} data-testid="underway-refresh-button">REFRESH STATUS</button>
      </section>
    </>
  );
};

const SetupQuestions = ({ state, reload }) => {
  const { delivery } = state;
  const [form, setForm] = useState({
    expected_planning_responses: delivery.expected_planning_responses || "",
    next_board_meeting_date: delivery.next_board_meeting_date || "",
    meeting_time: delivery.meeting_time || "",
  });
  const [message, setMessage] = useState("");
  const [saved, setSaved] = useState(Boolean(delivery.expected_planning_responses && delivery.next_board_meeting_date));

  const save = async (event) => {
    event.preventDefault();
    setMessage("");
    try {
      await memberApi.put("/activation/delivery/setup", {
        expected_planning_responses: Number(form.expected_planning_responses),
        next_board_meeting_date: form.next_board_meeting_date,
        meeting_time: form.meeting_time,
      });
      setSaved(true);
      setMessage("Saved.");
      reload();
    } catch (e) { setSaved(false); setMessage(err(e, "We could not save your answers.")); }
  };

  return (
    <section className="member-card" data-testid="activation-setup-questions">
      <h2>Two Important Questions</h2>
      <form onSubmit={save}>
        <label className="field"><span>How many Board Members need to complete the Fundraising Planning Form? <b>*</b></span>
          <input type="number" min="1" max="300" value={form.expected_planning_responses} onChange={(e) => setForm({ ...form, expected_planning_responses: e.target.value })} required style={{ maxWidth: 140 }} data-testid="setup-expected-responses" />
        </label>
        <label className="field"><span>When is your next Board meeting? <b>*</b></span>
          <input type="date" value={form.next_board_meeting_date} onChange={(e) => setForm({ ...form, next_board_meeting_date: e.target.value })} required style={{ maxWidth: 220 }} data-testid="setup-meeting-date" />
        </label>
        <label className="field"><span>Meeting time (optional)</span>
          <input value={form.meeting_time} onChange={(e) => setForm({ ...form, meeting_time: e.target.value })} placeholder="e.g. 6:00 PM Eastern" style={{ maxWidth: 260 }} data-testid="setup-meeting-time" />
        </label>
        <button type="submit" className="button" data-testid="setup-save-button">SAVE MY ANSWERS</button>
        {message && <span className="eyebrow" style={{ marginLeft: 10 }} data-testid="setup-save-message">{message}</span>}
      </form>
      {saved && <p className="eyebrow" style={{ marginTop: 10 }} data-testid="setup-saved-note">Saved — we will track responses against these answers.</p>}
    </section>
  );
};

export default function ActivationStartPage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [error, setError] = useState("");
  const [launchError, setLaunchError] = useState("");
  const [launching, setLaunching] = useState(false);

  const load = useCallback(() => {
    memberApi.get("/activation/delivery").then((res) => setState(res.data)).catch((e) => {
      if (e.response?.status === 401) navigate(`/login?next=${encodeURIComponent("/app/activation/start")}`);
      else if (e.response?.status === 403) setError("Your account does not include Board Fundraising Activation.");
      else setError("We could not load your Activation workspace.");
    });
  }, [navigate]);

  useEffect(() => { document.title = "Board Fundraising Activation | Nonprofit Board Builder"; }, []);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent("/app/activation/start")}`); return; }
    load();
  }, [loading, member, navigate, load]);

  const launch = async () => {
    setLaunching(true);
    setLaunchError("");
    try { await memberApi.post("/activation/delivery/launch"); load(); } catch (e) { setLaunchError(err(e, "We could not start the tracking process.")); }
    setLaunching(false);
  };

  return (
    <MemberShell>
      <main className="member-page" data-testid="activation-start-page">
        {error && <p className="submit-error" data-testid="activation-start-error">{error}</p>}
        {!state && !error && <p className="sh-loading">Loading…</p>}
        {state && state.delivery.launched_at && <UnderwayView state={state} reload={load} />}
        {state && !state.delivery.launched_at && (
          <>
            <header className="member-page-heading">
              <p className="eyebrow">Board Fundraising Activation</p>
              <h1 data-testid="activation-start-heading">Start Your Board Fundraising Planning Process</h1>
            </header>
            <VideoBlock module={ACTIVATION_VIDEO} testPrefix="activation-start" placeholderTitle="Board Fundraising Activation Video" />
            <section className="member-card" data-testid="activation-start-process">
              <h2>How This Works</h2>
              <p>You only need to complete this setup once. Watch Rooney's orientation above, then:</p>
              <p>1. Generate, review and approve your <strong>Board Fundraising Planning Form</strong>. 2. Add the Board Members who need to complete it — each gets their own secure link. 3. Answer two quick questions below. 4. Send the form and start tracking.</p>
              <p><strong>After that, everything continues by email.</strong> We track the responses and email you when it is time for the next step — no need to log back in to check progress.</p>
            </section>
            {!state.has_intake && (
              <section className="member-card" data-testid="activation-start-intake">
                <h2>First Step: Complete Your Fundraising Information</h2>
                <p>Everything below unlocks once we know your organization's fundraising goals and priorities.</p>
              </section>
            )}
            <ActivationModule2 />
            <ActivationParticipantsPanel />
            <SetupQuestions state={state} reload={load} />
            <section className="member-card" data-testid="activation-launch-card">
              <h2>Start Tracking Responses</h2>
              <p>Once your Planning Form is approved, your Board Members have been sent their secure links and your two answers above are saved, start the tracking process. From that point we take over the follow-up by email.</p>
              {launchError && <p className="submit-error" data-testid="activation-launch-error">{launchError}</p>}
              <button type="button" className="button" disabled={launching} onClick={launch} data-testid="activation-launch-button">
                {launching ? "Starting…" : "MY PLANNING FORM IS OUT — START TRACKING RESPONSES"}
              </button>
            </section>
          </>
        )}
      </main>
    </MemberShell>
  );
}
