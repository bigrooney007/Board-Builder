import { useCallback, useEffect, useState } from "react";
import { Copy, Mail, Sparkles } from "lucide-react";
import { memberApi } from "./api";
import { reactivationContent, reactivationStep2Text } from "../content/appContent";

const C = reactivationContent.step2;

// Response labels/sections are shared with later steps.
export const RESPONSE_SECTIONS = [
  ["Professional Profile", ["full_name", "preferred_name", "email", "phone", "city_state", "linkedin", "current_position", "employer", "industry", "years_experience"]],
  ["Professional Expertise", ["expertise", "expertise_other"]],
  ["Networks", ["networks"]],
  ["Experience on the Board", ["why_joined", "how_recruited", "original_role_expectation", "role_clarity", "clarity_help", "board_experience", "participation_barriers", "board_improvement", "strategic_clarity", "planning_participation", "planning_involvement_desire"]],
  ["Areas of Contribution", ["contribution_interests", "ownership_areas", "leadership_interest"]],
  ["Fundraising Participation", ["fundraising_comfort"]],
  ["Availability", ["monthly_availability", "meeting_participation", "constraints"]],
  ["Support Needed", ["support_needed"]],
  ["Additional Comments", ["meaningful_service", "anything_else"]],
];

export const LABELS = {
  full_name: "Full Name", preferred_name: "Preferred Name", email: "Email", phone: "Phone", city_state: "City / State / Region", linkedin: "LinkedIn",
  current_position: "Current Professional Position", employer: "Organization / Employer", industry: "Industry / Professional Field", years_experience: "Years of Professional Experience",
  expertise: "Professional skills, experience or expertise", expertise_other: "Other expertise", networks: "Relationships / professional networks",
  why_joined: "What originally interested them in serving", how_recruited: "How they originally became involved", original_role_expectation: "What they understood their role to be",
  role_clarity: "Role clarity today", clarity_help: "What would give greater clarity", board_experience: "Experience serving on the Board", participation_barriers: "What has made participation difficult",
  board_improvement: "What would help the Board work more effectively", strategic_clarity: "Clarity about organization direction", planning_participation: "Strategic planning participation",
  planning_involvement_desire: "Desired planning involvement", contribution_interests: "Where they would most like to contribute", ownership_areas: "Responsibility they would take ownership of",
  leadership_interest: "Leadership interest", fundraising_comfort: "Fundraising activities they are comfortable with", monthly_availability: "Monthly availability",
  meeting_participation: "Meeting participation", constraints: "Availability / circumstances to understand", support_needed: "Support, information or resources needed",
  meaningful_service: "What would make Board service meaningful", anything_else: "Anything else",
};

export const ResponseView = ({ data, testPrefix = "step2" }) => (
  <div data-testid={`${testPrefix}-response-view`}>
    <div className="member-card" style={{ borderLeft: "4px solid #000", marginBottom: 18 }} data-testid={`${testPrefix}-recommitment-answer`}>
      <p className="eyebrow">Recommitment Response</p>
      <p style={{ fontSize: "1.05rem", fontWeight: 700, margin: 0 }}>{data.response.recommitment}</p>
      {data.response.advisory_openness && <p style={{ margin: "8px 0 0" }}>{reactivationStep2Text.openToAnAdvisoryRole}<strong>{data.response.advisory_openness}</strong></p>}
      {data.response.support_role_openness && <p style={{ margin: "8px 0 0" }}>{reactivationStep2Text.openToAnotherSupportRole}<strong>{data.response.support_role_openness}</strong></p>}
      {data.response.step_off_openness && <p style={{ margin: "8px 0 0" }}>Remain or transition off the board: <strong>{data.response.step_off_openness}</strong></p>}
    </div>
    {RESPONSE_SECTIONS.map(([section, keys]) => {
      const rows = keys.filter((key) => {
        const value = data.response[key];
        return Array.isArray(value) ? value.length : String(value || "").trim();
      });
      if (!rows.length) return null;
      return (
        <div key={section} style={{ marginBottom: 18 }}>
          <h3 style={{ marginBottom: 8 }}>{section}</h3>
          {rows.map((key) => {
            const value = data.response[key];
            return (
              <p key={key} style={{ margin: "0 0 8px" }}>
                <strong>{LABELS[key] || key}:</strong> {Array.isArray(value) ? value.join(", ") : value}
              </p>
            );
          })}
        </div>
      );
    })}
    <p className="eyebrow">Submitted {data.submitted_at ? new Date(data.submitted_at).toLocaleString() : ""}</p>
  </div>
);

export default function ReactivationStep2() {
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [email, setEmail] = useState(null);
  const [copied, setCopied] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    memberApi.get("/reactivation/recommitment-form").then((res) => setForm(res.data)).catch(() => setError(C.errors.load));
  }, []);
  useEffect(load, [load]);

  const act = async (fn) => {
    setBusy(true); setError("");
    try { await fn(); load(); } catch (err) { setError(err.response?.data?.detail || C.errors.action); }
    setBusy(false);
  };

  const copy = async (text, tag) => {
    try { await navigator.clipboard.writeText(text); } catch { window.prompt("Copy:", text); }
    setCopied(tag);
    setTimeout(() => setCopied(""), 2500);
  };

  if (error && !form) return <p className="submit-error">{error}</p>;
  if (!form) return <p className="sh-loading">Loading…</p>;
  const link = form.generic_token ? `${window.location.origin}/board-recommitment/${form.generic_token}` : "";

  return (
    <div data-testid="reactivation-step2">
      <section className="member-card" data-testid="step2-intro">
        <h2>{C.heading}</h2>
        {C.intro.map((p) => <p key={p}>{p}</p>)}
      </section>
      {error && <p className="submit-error" data-testid="step2-error">{error}</p>}

      {form.status === "NONE" && (
        <section className="member-card" data-testid="step2-generate-form">
          <p>{C.frameworkNote}</p>
          <button type="button" className="button" disabled={busy} onClick={() => act(() => memberApi.post("/reactivation/recommitment-form/generate"))} data-testid="step2-generate-form-button">
            <Sparkles size={16} /> {busy ? "Generating…" : C.generateFormButton}
          </button>
        </section>
      )}

      {form.status === "Draft" && (
        <section className="member-card" data-testid="step2-form-draft">
          <h2>{reactivationStep2Text.reviewYourRecommitmentForm}</h2>
          <p>{C.formReadyNote}</p>
          {editing ? (
            <>
              <textarea rows={12} value={draft} onChange={(e) => setDraft(e.target.value)} style={{ width: "100%" }} data-testid="step2-form-editor" />
              <button type="button" className="button" disabled={busy} onClick={() => act(async () => { await memberApi.put("/reactivation/recommitment-form", { text: draft }); setEditing(false); })} data-testid="step2-form-save">{C.saveButton}</button>
            </>
          ) : (
            <>
              <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6 }} data-testid="step2-form-intro-text">{form.intro_text}</div>
              <p style={{ marginTop: 10 }}>{C.frameworkNote}</p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                <button type="button" className="button button-outline" onClick={() => { setDraft(form.intro_text); setEditing(true); }} data-testid="step2-form-edit">{C.editButton}</button>
                <button type="button" className="button" disabled={busy} onClick={() => act(() => memberApi.post("/reactivation/recommitment-form/approve"))} data-testid="step2-form-approve">{C.approveButton}</button>
              </div>
            </>
          )}
        </section>
      )}

      {form.status === "Approved" && (
        <section className="member-card" data-testid="step2-form-approved">
          <h2>{reactivationStep2Text.yourRecommitmentFormIsLive}</h2>
          <p>{C.approvedNote}</p>
          <p><strong>{C.formLinkLabel}:</strong> <span style={{ wordBreak: "break-all" }} data-testid="step2-form-link">{link}</span></p>
          {form.transition_enabled && (
            <p data-testid="step2-standard-form-link">
              <strong>Standard version (no transition questions):</strong> <span style={{ wordBreak: "break-all" }}>{`${link}?general=1`}</span>{" "}
              <button type="button" className="table-link" onClick={() => copy(`${link}?general=1`, "general")} data-testid="step2-copy-standard-link">{copied === "general" ? C.copiedLabel : "Copy Standard Link"}</button>
            </p>
          )}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" className="button button-outline" onClick={() => copy(link, "link")} data-testid="step2-copy-link"><Copy size={15} /> {copied === "link" ? C.copiedLabel : C.copyLinkButton}</button>
            {!email && (
              <button type="button" className="button" onClick={() => memberApi.get("/reactivation/recommitment-email").then((res) => setEmail(res.data)).catch(() => setError(C.errors.action))} data-testid="step2-generate-email">
                <Mail size={15} /> {C.generateEmailButton}
              </button>
            )}
            <button type="button" className="button button-outline" onClick={() => { setDraft(form.intro_text); setEditing(true); act(() => memberApi.put("/reactivation/recommitment-form", { text: form.intro_text })); }} data-testid="step2-reopen-form">{C.editButton}</button>
          </div>
          {email && (
            <div style={{ marginTop: 16 }} data-testid="step2-email-block">
              <h3>{C.emailLabel}</h3>
              <p><strong>Subject:</strong> <span data-testid="step2-email-subject">{email.subject}</span></p>
              <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 320, overflowY: "auto" }} data-testid="step2-email-body">{email.body}</div>
              <button type="button" className="button" style={{ marginTop: 10 }} onClick={() => copy(`Subject: ${email.subject}\n\n${email.body.replace(/\[[^\]]+\]/, email.form_link)}`, "email")} data-testid="step2-copy-email">
                <Copy size={15} /> {copied === "email" ? C.copiedLabel : C.copyEmailButton}
              </button>
            </div>
          )}
          <p className="eyebrow" style={{ marginTop: 14 }} data-testid="step2-responses-count">{C.responsesLabel(form.responses_received)}</p>
        </section>
      )}
    </div>
  );
}
