import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MemberShell } from "./MemberShell";
import { useMemberAuth } from "./MemberAuthContext";
import { memberApi } from "./api";
import { Module1Profile } from "./workspace/Module1Profile";
import { MaterialCard } from "./workspace/MaterialCard";
import { Module3Launch, useMaterials } from "./workspace/WorkspaceModules";
import "./sgr.css";

const ANSWER_KEYS = ["mission", "current_board", "desired_board_members", "board_type", "support_needs", "why_join"];
const ONBOARDING = [
  ["organization_overview", "Organization Overview"], ["board_manual", "Board Manual"],
  ["board_member_agreement", "Board Member Agreement"], ["confidentiality_agreement", "Confidentiality Agreement"],
  ["conflict_of_interest_agreement", "Conflict of Interest Agreement"], ["onboarding_agenda", "Onboarding Agenda"],
];
const COMMUNICATIONS = [
  ["general_interview_invitation", "Reusable Interview Invitation"],
  ["recruitment_communications", "Decision, Check And Offer Communications"],
];

export default function RecruitCampaignSetupPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const { byType, refresh } = useMaterials();
  const [assessment, setAssessment] = useState(null);
  const [opportunity, setOpportunity] = useState(null);
  const [readiness, setReadiness] = useState({});
  const [preparation, setPreparation] = useState({});
  const [schedule, setSchedule] = useState({ method: "", scheduling_link: "", availability: "" });
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    const [a, o, s] = await Promise.all([
      memberApi.get("/recruit/free/member-assessment/current"),
      memberApi.get("/workspace/opportunity"),
      memberApi.get("/workspace/interview-scheduling"),
    ]);
    setAssessment(a.data);
    setOpportunity(o.data.opportunity);
    setReadiness(o.data.readiness || {});
    setPreparation(o.data.preparation || {});
    setSchedule((old) => old.method ? old : (s.data.scheduling || old));
    await refresh();
    return a.data;
  }, [refresh]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login?next=/app/board-recruitment/setup", { replace: true }); return; }
    let live = true;
    load().then(async (a) => {
      if (!live) return;
      if (ANSWER_KEYS.some((key) => !String(a.answers?.[key] || "").trim())) return;
      if (a.result) return;
      setBusy("profiles");
      try {
        await memberApi.post(`/recruit/free/${a.token}/result`);
        if (live) await load();
      } catch (err) { if (live) setError(err.response?.data?.detail || "We could not prepare your board profiles. Try again below."); }
      if (live) setBusy("");
    }).catch((err) => { if (live) setError(err.response?.data?.detail || "We could not open your campaign. Please try again."); });
    return () => { live = false; };
  }, [member, loading, navigate, load]);

  useEffect(() => {
    if (!member || opportunity?.status === "Published" || opportunity?.status === "Closed") return undefined;
    const timer = window.setInterval(() => { load().catch(() => {}); }, 6000);
    return () => window.clearInterval(timer);
  }, [member, opportunity?.status, load]);

  const saveSchedule = async () => {
    setBusy("schedule"); setError(""); setMessage("");
    try {
      await memberApi.put("/workspace/interview-scheduling", schedule);
      setMessage("Interview scheduling saved. The invitation will include these details for each applicant.");
      await load();
    } catch (err) { setError(err.response?.data?.detail || "Could not save interview scheduling."); }
    setBusy("");
  };

  if (loading || !member) return null;
  const complete = assessment && ANSWER_KEYS.every((key) => String(assessment.answers?.[key] || "").trim());
  const launched = ["Published", "Closed"].includes(opportunity?.status);
  return <MemberShell><main className="member-page sgr sgr-recruitment-machine" data-testid="recruitment-campaign-setup">
    <header className="sgr-dashboard-hero"><p className="eyebrow">YOUR RECRUITMENT CAMPAIGN</p>
      <h1>Launch Your Board Recruitment Campaign</h1>
      <p>Your answers are saved. Review who your organization needs, choose how applicants arrange interviews, approve the materials and launch.</p>
    </header>
    {error && <p className="submit-error" role="alert">{error}</p>}
    {message && <p className="member-success">{message}</p>}
    {!complete && <section className="member-card"><h2>Complete your six recruitment answers</h2><button className="button" onClick={() => navigate("/app/board-recruitment/questions")}>CONTINUE QUESTIONS</button></section>}
    {complete && !assessment?.result && <section className="member-card"><h2>Preparing Your Exact Board Profiles</h2><p>We are comparing your priorities with your current board and the support you said is missing.</p>
      <button className="button" disabled={busy === "profiles"} onClick={async () => { setBusy("profiles"); setError(""); try { await memberApi.post(`/recruit/free/${assessment.token}/result`); await load(); } catch (err) { setError(err.response?.data?.detail || "Please try again."); } setBusy(""); }}>{busy === "profiles" ? "PREPARING…" : "PREPARE MY BOARD PROFILES"}</button></section>}
    {complete && assessment?.result && <>
      <section className="member-card"><p className="eyebrow">STEP 1 · BOARD PROFILES</p><Module1Profile onConfirmed={() => load().catch(() => {})} /></section>
      {readiness.profiles_approved && <section className="member-card" data-testid="interview-scheduling-setup">
        <p className="eyebrow">STEP 2 · INTERVIEW SCHEDULING</p><h2>How should candidates arrange an interview?</h2>
        <div className="material-actions"><label><input type="radio" name="interview-method" checked={schedule.method === "link"} onChange={() => setSchedule({ ...schedule, method: "link" })} /> I have a scheduling link</label>
          <label><input type="radio" name="interview-method" checked={schedule.method === "availability"} onChange={() => setSchedule({ ...schedule, method: "availability" })} /> I will give candidates available times</label></div>
        {schedule.method === "link" && <label className="field"><span>Calendly or another scheduling URL</span><input type="url" value={schedule.scheduling_link || ""} onChange={(e) => setSchedule({ ...schedule, scheduling_link: e.target.value })} placeholder="https://…" /></label>}
        {schedule.method === "availability" && <label className="field"><span>Your available interview dates and times</span><textarea rows="3" value={schedule.availability || ""} onChange={(e) => setSchedule({ ...schedule, availability: e.target.value })} placeholder="Tuesday 10 AM to 1 PM; Thursday 2 PM to 5 PM" /></label>}
        <button className="button" disabled={!schedule.method || busy === "schedule"} onClick={saveSchedule}>{busy === "schedule" ? "SAVING…" : "SAVE INTERVIEW SCHEDULING"}</button>
      </section>}
      {readiness.profiles_approved && readiness.scheduling_saved && <>
        <section className="member-card"><p className="eyebrow">STEP 3 · REVIEW CAMPAIGN MATERIALS</p><h2>Your Application And Recruitment Copy</h2>
          <p>These drafts use your approved board profiles and application link. Edit and approve each before launch. Preparation: {preparation.status || "queued"}{preparation.stage ? ` (${preparation.stage})` : ""}.</p><Module3Launch mode="materials" /></section>
        <section className="member-card"><h2>Organization Overview, Manual And Agreements</h2><p>These are reusable for everyone joining your board. Review and approve the organization-level drafts now.</p>
          {ONBOARDING.map(([type, title]) => <MaterialCard key={type} type={type} title={title} buttonLabel={`Generate ${title}`} description={`Review the ${title.toLowerCase()} for your organization.`} material={byType[type]} refresh={refresh} approvable />)}
          <p>The Board Member Profile Form is already hosted. You will send each new board member their individual link during onboarding.</p>
        </section>
        <section className="member-card"><h2>Interview, Check And Offer Communications</h2>
          <p>Review these reusable drafts now. When you choose an actual candidate, the platform prepares their individual email with their details and the correct onboarding links.</p>
          {COMMUNICATIONS.map(([type, title]) => <MaterialCard key={type} type={type} title={title} buttonLabel={`Generate ${title}`}
            description={type === "general_interview_invitation" ? "Uses the interview scheduling method you saved." : "Includes rejection, references, background check and both board offer paths."}
            material={byType[type]} refresh={refresh} approvable />)}
        </section>
        <section className="member-card"><p className="eyebrow">STEP 4 · LAUNCH</p><h2>Publish Your Board Opportunity</h2>
          <p>{readiness.materials_approved_count || 0}/{readiness.materials_total || 5} campaign materials, {readiness.onboarding_approved_count || 0}/{readiness.onboarding_total || 6} onboarding documents and {readiness.support_approved_count || 0}/{readiness.support_total || 2} communication resources approved.</p>
          <Module3Launch mode="launch" onLaunched={() => navigate("/app/board-recruitment#br-section-applicants")} />
        </section>
      </>}
    </>}
    {launched && <button className="button" onClick={() => navigate("/app/board-recruitment")}>OPEN MY RECRUITMENT DASHBOARD</button>}
  </main></MemberShell>;
}
