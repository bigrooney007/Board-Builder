import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell, GameProgress, formatDate, money, useGameContent } from "./gameShared";

const STEPS = ["About Your Organization", "Your Fundraising Goal", "About You", "Review"];
const ORG_TYPES = ["Charity / Nonprofit", "Foundation", "Association", "School / Education", "Faith-Based Organization", "Community Organization", "Other"];

const Field = ({ label, value, onChange, testId, required, type = "text", textarea, hint, options, readOnly }) => (
  <label className="bfg-field">
    <span>{label} {required && <b>*</b>}</span>
    {textarea ? (
      <textarea rows={3} value={value} onChange={(event) => onChange(event.target.value)} data-testid={testId} required={required} />
    ) : options ? (
      <select value={value} onChange={(event) => onChange(event.target.value)} data-testid={testId} required={required}>
        <option value="">Select one</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    ) : (
      <input type={type} value={value} readOnly={readOnly} onChange={(event) => onChange(event.target.value)} data-testid={testId} required={required} />
    )}
    {hint && <small>{hint}</small>}
  </label>
);

export default function GameProfilePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editMode = searchParams.get("edit") === "1";
  const { member, loading } = useMemberAuth();
  const content = useGameContent();
  const [step, setStep] = useState(0);
  const [saved, setSaved] = useState(false);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [org, setOrg] = useState({ name: "", website: "", org_type: "", location: "", mission: "", who_served: "" });
  const [goal, setGoal] = useState({ amount: "", deadline: "", purpose: "", why_now: "" });
  const [user, setUser] = useState({ full_name: "", job_title: "", email: "" });

  useEffect(() => { document.title = "Set Up Your Game | Board Fundraising Game"; }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup", { replace: true }); return; }
    memberApi.get("/game/profile").then((response) => {
      const { profile, unlocked } = response.data;
      if (unlocked && !editMode) {
        navigate(profile?.situation_completed ? "/game/dashboard" : "/game/welcome", { replace: true });
        return;
      }
      const storedGoal = sessionStorage.getItem("bfgGoal") || "";
      setOrg((current) => ({ ...current, ...(profile?.organization || {}) }));
      setGoal((current) => ({
        ...current, ...(profile?.goal || {}),
        amount: profile?.goal?.amount ? Number(profile.goal.amount).toLocaleString("en-US") : (storedGoal ? Number(storedGoal).toLocaleString("en-US") : ""),
      }));
      setUser((current) => ({
        full_name: profile?.primary_user?.full_name || `${member.first_name} ${member.last_name}`.trim(),
        job_title: profile?.primary_user?.job_title || "",
        email: member.email,
        ...current.full_name ? current : {},
      }));
      if (editMode && profile?.profile_completed) setStep(3);
      setReady(true);
    }).catch(() => setReady(true));
  }, [loading, member, navigate, editMode]);

  if (loading || !ready || !content) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const setField = (setter) => (key) => (value) => setter((current) => ({ ...current, [key]: value }));
  const setOrgField = setField(setOrg);
  const setGoalField = setField(setGoal);
  const setUserField = setField(setUser);
  const goalAmount = Number(String(goal.amount).replace(/[^0-9]/g, "")) || 0;

  const save = async (next) => {
    setError(""); setBusy(true);
    try {
      await memberApi.put("/game/profile", { organization: org, goal: { ...goal, amount: goalAmount }, primary_user: user });
      setStep(next);
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your answers. Please try again.");
    }
    setBusy(false);
  };

  const validators = [
    () => (org.name.trim() ? "" : "Please enter your organization's name."),
    () => (goalAmount > 0 ? (goal.purpose.trim() ? "" : "Please tell us what the money will be used for.") : "Please enter the amount you want to raise."),
    () => (user.full_name.trim() ? "" : "Please enter your full name."),
  ];

  const nextStep = () => {
    const problem = validators[step]();
    if (problem) { setError(problem); return; }
    save(step + 1);
  };

  const unlock = async () => {
    setError(""); setBusy(true);
    try {
      await memberApi.put("/game/profile", { organization: org, goal: { ...goal, amount: goalAmount }, primary_user: user });
      setSaved(true);
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your profile. Please try again.");
    }
    setBusy(false);
  };

  const pf = content.profile_flow || {};

  if (saved) {
    return (
      <BfgShell>
        <main className="bfg-flow" data-testid="bfg-profile-saved" style={{ maxWidth: 720, margin: "0 auto", padding: "40px 20px 80px", textAlign: "center" }}>
          <h1 data-testid="bfg-profile-saved-heading">{pf.saved_heading}</h1>
          <p style={{ marginTop: 12 }}>{pf.saved_supporting}</p>
          <div className="bfg-goal-highlight" style={{ maxWidth: 460, margin: "24px auto 0" }} data-testid="bfg-profile-saved-goal">
            <strong>{money(goalAmount)}</strong>
            {goal.deadline && <span>By {formatDate(goal.deadline)}</span>}
          </div>
          <h2 style={{ marginTop: 32 }}>{pf.next_heading}</h2>
          <p style={{ marginTop: 10, maxWidth: 600, marginLeft: "auto", marginRight: "auto" }}>{pf.next_supporting}</p>
          <div style={{ marginTop: 22, display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
            <button className="bfg-btn bfg-btn-primary" onClick={() => navigate("/game/upgrade")} data-testid="bfg-invite-board-cta">{pf.invite_cta}</button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => { setSaved(false); setStep(0); }} data-testid="bfg-edit-my-profile-btn">Edit My Profile</button>
          </div>
        </main>
      </BfgShell>
    );
  }

  return (
    <BfgShell>
      <main className="bfg-flow" data-testid="bfg-profile-page">
        <div style={{ textAlign: "center", marginBottom: 18 }}>
          <h1 style={{ fontSize: "clamp(24px, 3.6vw, 34px)" }} data-testid="bfg-profile-heading">{pf.heading}</h1>
          <p style={{ marginTop: 8 }}>{pf.supporting}</p>
        </div>
        <GameProgress steps={STEPS} current={step} />
        <div className="bfg-card">
          {step === 0 && (
            <div data-testid="bfg-profile-step-org">
              <p className="bfg-eyebrow">Step 1 of 4</p>
              <h2>{pf.step1_heading}</h2>
              <Field label="Organization name" value={org.name} onChange={setOrgField("name")} testId="bfg-org-name" required />
              <Field label="Website" value={org.website} onChange={setOrgField("website")} testId="bfg-org-website" hint="Optional" />
              <Field label="Organization type" value={org.org_type} onChange={setOrgField("org_type")} testId="bfg-org-type" options={ORG_TYPES} />
              <Field label="Location" value={org.location} onChange={setOrgField("location")} testId="bfg-org-location" hint="City, state or region" />
              <Field label="Mission" value={org.mission} onChange={setOrgField("mission")} testId="bfg-org-mission" textarea />
              <Field label="Who does your organization serve?" value={org.who_served} onChange={setOrgField("who_served")} testId="bfg-org-who-served" textarea />
            </div>
          )}
          {step === 1 && (
            <div data-testid="bfg-profile-step-goal">
              <p className="bfg-eyebrow">Step 2 of 4</p>
              <h2>{pf.step2_heading}</h2>
              <p style={{ marginTop: 10 }}>This goal is the centre of your Board Fundraising Game. Your board will build the strategy required to raise it.</p>
              <label className="bfg-field">
                <span>How much does your organization want to raise? <b>*</b></span>
                <div className="bfg-goal-input">
                  <span>$</span>
                  <input inputMode="numeric" value={goal.amount}
                    onChange={(event) => setGoalField("amount")(Number(event.target.value.replace(/[^0-9]/g, "") || 0) ? Number(event.target.value.replace(/[^0-9]/g, "")).toLocaleString("en-US") : "")}
                    data-testid="bfg-goal-amount" />
                </div>
              </label>
              <Field label="When do you want to reach this goal?" type="date" value={goal.deadline} onChange={setGoalField("deadline")} testId="bfg-goal-deadline" />
              <Field label="What will the money be used for?" value={goal.purpose} onChange={setGoalField("purpose")} testId="bfg-goal-purpose" textarea required />
              <Field label="Why does this fundraising goal matter right now?" value={goal.why_now} onChange={setGoalField("why_now")} testId="bfg-goal-why-now" textarea />
            </div>
          )}
          {step === 2 && (
            <div data-testid="bfg-profile-step-user">
              <p className="bfg-eyebrow">Step 3 of 4</p>
              <h2>{pf.step3_heading}</h2>
              <p style={{ marginTop: 10 }}>You will lead the Board Fundraising Game for {org.name || "your organization"}.</p>
              <Field label="Full name" value={user.full_name} onChange={setUserField("full_name")} testId="bfg-user-full-name" required />
              <Field label="Job title" value={user.job_title} onChange={setUserField("job_title")} testId="bfg-user-job-title" />
              <Field label="Email" type="email" value={user.email} onChange={() => {}} testId="bfg-user-email" readOnly hint="From your account" />
              <Field label="Organization name" value={org.name} onChange={setOrgField("name")} testId="bfg-user-org-name" hint="From Step 1" />
              <Field label="Organization website" value={org.website} onChange={setOrgField("website")} testId="bfg-user-org-website" hint="From Step 1" />
            </div>
          )}
          {step === 3 && (
            <div data-testid="bfg-profile-review">
              <p className="bfg-eyebrow">Step 4 of 4</p>
              <h2>{pf.review_heading}</h2>
              <p style={{ marginTop: 8 }}>{pf.review_supporting}</p>
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 14 }} onClick={() => setStep(0)} data-testid="bfg-edit-profile-btn">Edit Profile</button>
              <div className="bfg-goal-highlight" data-testid="bfg-review-goal">
                <span>Your Fundraising Goal</span>
                <strong>{money(goalAmount)}</strong>
                {goal.deadline && <span>By {formatDate(goal.deadline)}</span>}
              </div>
              <div className="bfg-summary-grid">
                <div className="bfg-summary-row"><span>Organization</span><strong data-testid="bfg-review-org">{org.name}</strong></div>
                {goal.purpose && <div className="bfg-summary-row"><span>Purpose</span><strong>{goal.purpose}</strong></div>}
                {org.mission && <div className="bfg-summary-row"><span>Mission</span><strong>{org.mission}</strong></div>}
                {org.who_served && <div className="bfg-summary-row"><span>Who We Serve</span><strong>{org.who_served}</strong></div>}
                {org.location && <div className="bfg-summary-row"><span>Location</span><strong>{org.location}</strong></div>}
                <div className="bfg-summary-row"><span>Primary User</span><strong>{user.full_name}{user.job_title ? ` — ${user.job_title}` : ""}</strong></div>
              </div>
              <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 24, width: "100%" }} onClick={unlock} disabled={busy} data-testid="bfg-save-profile-btn">
                {busy ? "Saving…" : pf.save_button}
              </button>
            </div>
          )}
          {error && <p className="bfg-error" data-testid="bfg-profile-error">{error}</p>}
          {step < 3 && (
            <div className="bfg-form-actions">
              {step > 0 ? (
                <button className="bfg-btn bfg-btn-ghost" onClick={() => setStep(step - 1)} data-testid="bfg-profile-back">Back</button>
              ) : <span />}
              <button className="bfg-btn bfg-btn-primary" onClick={nextStep} disabled={busy} data-testid="bfg-profile-next">
                {busy ? "Saving…" : step === 2 ? "Review My Fundraising Game" : "Continue"}
              </button>
            </div>
          )}
        </div>
      </main>
    </BfgShell>
  );
}
