import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Copy, Mail, X } from "lucide-react";
import { memberApi } from "./api";
import { activationM2Text, activationModule2Text } from "../content/appContent";

const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const dialogStyle = { background: "#fff", maxWidth: 760, width: "100%", padding: "28px", borderRadius: 8, position: "relative" };

const Modal = ({ children, onClose, testId }) => (
  <div style={overlayStyle} data-testid={testId}>
    <div style={dialogStyle}>
      <button type="button" onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testId}-close`}><X size={20} /></button>
      {children}
    </div>
  </div>
);

const RESPONSE_SECTIONS = [
  ["Fundraising Goal / Priorities", ["goal_important", "goal_clarity"]],
  ["Potential Funding Audiences", ["funding_audiences", "audiences_why"]],
  ["Fundraising Opportunities", ["opportunities", "opportunity_priority"]],
  ["Relationships / Networks", ["network_categories", "specific_relationships"]],
  ["Fundraising Messaging Ideas", ["why_support", "talk_about"]],
  ["Outreach Ideas", ["outreach_methods", "outreach_add"]],
  ["Personal Participation", ["participation_activities"]],
  ["Areas of Ownership", ["ownership"]],
  ["Support Needed", ["support_needed"]],
  ["90-Day Priorities", ["ninety_day_priorities"]],
  ["Additional Ideas", ["fundraising_idea", "final_thoughts"]],
];

const LABELS = {
  goal_important: "Most important about what we are trying to fund", goal_clarity: "Where greater clarity is needed",
  funding_audiences: "Who we should build relationships with", audiences_why: "Why they may care about our work",
  opportunities: "Opportunities to explore or strengthen", opportunity_priority: "Greatest opportunity right now, and why",
  network_categories: "Relationships / networks they already have", specific_relationships: "Relationships they would be comfortable exploring",
  why_support: "What would make someone want to support us", talk_about: "What we should talk about more",
  outreach_methods: "Best ways to reach potential supporters", outreach_add: "What they would add or do differently",
  participation_activities: "Activities they are comfortable helping with",
  ownership: "What they would be willing to take responsibility for or help lead",
  support_needed: "What would help them participate more effectively",
  ninety_day_priorities: "Three fundraising things for the next 90 days",
  fundraising_idea: "Fundraising idea we should consider", final_thoughts: "Anything else to consider",
};

const ResponseView = ({ data }) => (
  <div data-testid="am2-response-view">
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

const FormPreview = ({ content }) => (
  <div data-testid="am2-form-preview" style={{ border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 14, maxHeight: 420, overflowY: "auto" }}>
    <h3 style={{ marginTop: 0 }}>{content.title}</h3>
    <p style={{ whiteSpace: "pre-wrap" }}>{content.introduction}</p>
    {content.goal_context && <p style={{ whiteSpace: "pre-wrap" }}><strong>{content.goal_context}</strong></p>}
    {content.sections.map((section) => (
      <div key={section.key} style={{ marginTop: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 6 }}>{section.title}</p>
        {section.questions.map((question) => (
          <p key={question.id} style={{ margin: "0 0 6px" }}>
            {question.prompt} {question.required ? "" : "(optional)"}
            {question.type === "multi" && <span style={{ display: "block", fontSize: "0.85rem", color: "#555" }}>Options: {question.options.join(" · ")}</span>}
          </p>
        ))}
      </div>
    ))}
  </div>
);

export default function ActivationModule2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editForm, setEditForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [response, setResponse] = useState(null);
  const [email, setEmail] = useState(null);
  const [emailBusy, setEmailBusy] = useState(false);
  const [copied, setCopied] = useState("");
  const pollRef = useRef(null);

  const load = useCallback(() => {
    memberApi.get("/activation/planning").then((res) => setData(res.data)).catch(() => setError("We could not load your fundraising planning workspace."));
  }, []);
  useEffect(load, [load]);

  useEffect(() => {
    if (data?.form?.status === "Generating" && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await memberApi.get("/activation/planning-form");
          if (res.data.status !== "Generating") {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setGenerating(false);
            load();
          }
        } catch { /* keep polling */ }
      }, 3000);
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [data?.form?.status, load]);

  const openResponse = useCallback((participantId) => {
    memberApi.get(`/activation/participants/${participantId}/response`).then((res) => setResponse(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const participantId = searchParams.get("participant");
    if (participantId && data) {
      openResponse(participantId);
      setSearchParams({}, { replace: true });
    }
  }, [data, searchParams, setSearchParams, openResponse]);

  const generate = async () => {
    if (!data?.has_intake) {
      window.location.href = "/board-activation-intake?bf=1";
      return;
    }
    const form = data?.form;
    if (form?.content && form.edited_since_generation) {
      const ok = window.confirm("You have manually edited this form. Regenerating will replace your edited content with a newly generated version. Do you want to continue?");
      if (!ok) return;
    } else if (form?.content) {
      const ok = window.confirm("This will replace the current form content with a newly generated version. Continue?");
      if (!ok) return;
    }
    setGenerating(true);
    try {
      await memberApi.post("/activation/planning-form/generate");
      load();
    } catch (err) {
      setGenerating(false);
      window.alert(err.response?.data?.detail || "Generation could not start. Please try again.");
    }
  };

  const openEdit = () => {
    const content = data.form.content;
    setEditForm({
      introduction: content.introduction,
      goal_context: content.goal_context,
      question_prompts: Object.fromEntries(content.sections.flatMap((s) => s.questions.map((q) => [q.id, q.prompt]))),
      prompt_list: content.sections.flatMap((s) => s.questions.map((q) => ({ id: q.id, section: s.title }))),
    });
    setShowEdit(true);
  };

  const saveEdit = async () => {
    setSaving(true);
    try {
      await memberApi.put("/activation/planning-form", {
        introduction: editForm.introduction, goal_context: editForm.goal_context,
        question_prompts: editForm.question_prompts,
      });
      setShowEdit(false);
      load();
    } catch { /* keep open */ }
    setSaving(false);
  };

  const approve = async () => {
    try { await memberApi.post("/activation/planning-form/approve"); load(); } catch { /* ignore */ }
  };

  const generateEmail = async () => {
    setEmailBusy(true);
    try {
      const res = await memberApi.get("/activation/planning-email");
      setEmail(res.data);
    } catch (err) {
      window.alert(err.response?.data?.detail || "The email could not be generated.");
    }
    setEmailBusy(false);
  };

  const copyText = async (text, key) => {
    try { await navigator.clipboard.writeText(text); } catch { window.prompt("Copy this text:", text); }
    setCopied(key);
    setTimeout(() => setCopied(""), 2500);
  };

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">{activationModule2Text.loadingYourFundraisingPlanningWorkspace}</p>;

  const form = data.form;
  const formApproved = form.status === "Approved";
  const respondents = data.participants.filter((p) => p.status === "COMPLETED");

  return (
    <div data-testid="activation-module2">
      {!data.has_intake && (
        <section className="member-card" data-testid="am2-intake-prerequisite">
          <h2>Complete Your Fundraising Information First</h2>
          <p><strong>Before we can build your Board Fundraising Planning Form, we need some information about your organization's fundraising goals and priorities.</strong></p>
          <a className="button" href="/board-activation-intake?bf=1" data-testid="am2-complete-intake-button">COMPLETE MY FUNDRAISING INFORMATION</a>
        </section>
      )}
      <section className="member-card" data-testid="am2-intro">
        <h2>{activationM2Text.h_buildThePlanWithYour}</h2>
        <p>{activationModule2Text.doNotCreateAFundraising}</p>
        <p>{activationModule2Text.getYourBoardInvolvedIn}</p>
        <p>{activationModule2Text.theirIdeasProfessionalExperienceRelationships}</p>
        <p>{activationModule2Text.whenPeopleParticipateInBuilding}</p>
      </section>

      <section className="member-card" data-testid="am2-form-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2 style={{ margin: 0 }}>{activationModule2Text.boardFundraisingPlanningForm}</h2>
          <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid="am2-form-status">
            {form.status === "NONE" ? "NOT GENERATED" : form.status.toUpperCase()}{formApproved ? ` · v${form.approved_version}` : ""}
          </span>
        </div>
        <p style={{ marginTop: 10 }}>{activationModule2Text.generateOneOrganizationSpecificPlanning}</p>
        {!data.has_intake && <p className="submit-error" data-testid="am2-no-intake">{activationModule2Text.yourActivationIntakeWasNot}</p>}
        {form.status === "Failed" && <p className="submit-error" data-testid="am2-generation-error">{activationModule2Text.generationFailedPleaseTryAgain}</p>}
        {form.status === "Generating" || generating ? (
          <p data-testid="am2-generating">{activationModule2Text.generatingYourBoardFundraisingPlanning}</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
            <button type="button" className="button" onClick={generate} data-testid="am2-generate-button">
              {form.content ? "REGENERATE" : "GENERATE MY BOARD FUNDRAISING PLANNING FORM"}
            </button>
            {form.content && (
              <>
                <button type="button" className="button button-outline" onClick={openEdit} data-testid="am2-edit-button">EDIT FORM</button>
                {!formApproved && <button type="button" className="button" onClick={approve} data-testid="am2-approve-button">APPROVE FORM</button>}
              </>
            )}
          </div>
        )}
        {form.content && form.status !== "Generating" && <FormPreview content={form.content} />}
        {form.content && !formApproved && <p className="eyebrow" style={{ marginTop: 10 }} data-testid="am2-approval-required">{activationModule2Text.theFormMustBeApproved}</p>}
      </section>

      <section className="member-card" data-testid="am2-email-card">
        <h2>{activationM2Text.h_sendThePlanningFormToYourBoard}</h2>
        <p>{activationM2Text.d_sendThePlanningFormToYourBoard}</p>
        {!formApproved && <p className="eyebrow" data-testid="am2-email-locked">{activationM2Text.n_approveFormToUnlockEmail}</p>}
        <button type="button" className="button" onClick={generateEmail} disabled={!formApproved || emailBusy} data-testid="am2-generate-email-button"><Mail size={15} /> {emailBusy ? "Generating…" : email ? "REGENERATE EMAIL" : "GENERATE EMAIL"}</button>
        {email && (
          <div style={{ marginTop: 14 }} data-testid="am2-email-preview">
            <p><strong>Subject:</strong> <span data-testid="am2-email-subject">{email.subject}</span></p>
            <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 320, overflowY: "auto" }} data-testid="am2-email-body">{email.body}</div>
            <p style={{ marginTop: 10 }}>{email.form_link
              ? (<><strong>Secure Form Link:</strong> <span style={{ wordBreak: "break-all" }} data-testid="am2-email-link">{email.form_link}</span></>)
              : (<span data-testid="am2-email-link">Each Board Member automatically receives their OWN secure form link in their individual email — no shared link is used.</span>)}</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              <button type="button" className="button" onClick={() => copyText(email.body, "body")} data-testid="am2-copy-email-button"><Copy size={15} /> {copied === "body" ? "Email Copied" : "COPY EMAIL"}</button>
              <button type="button" className="button button-outline" onClick={() => copyText(email.subject, "subject")} data-testid="am2-copy-subject-button"><Copy size={15} /> {copied === "subject" ? "Subject Copied" : "COPY SUBJECT"}</button>
            </div>
          </div>
        )}
      </section>

      <section className="member-card" data-testid="am2-progress-summary">
        <h2>{activationM2Text.h_responsesReceived}</h2>
        <p data-testid="am2-progress-counts"><strong>{data.progress.received}</strong> Response{data.progress.received === 1 ? "" : "s"} Received</p>
        <p>{activationM2Text.d_responsesReceived}</p>
        {respondents.map((participant) => (
          <div key={participant.participant_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #eee", flexWrap: "wrap", gap: 8 }} data-testid={`am2-respondent-${participant.participant_id}`}>
            <span><strong>{participant.name}</strong> · {participant.role || "Board Member"} · {participant.email}{participant.submitted_at && <span className="eyebrow"> — completed {new Date(participant.submitted_at).toLocaleDateString()}</span>}</span>
            <button type="button" className="button button-outline" onClick={() => openResponse(participant.participant_id)} data-testid={`am2-view-response-${participant.participant_id}`}>VIEW RESPONSE</button>
          </div>
        ))}
      </section>

      {showEdit && editForm && (
        <Modal onClose={() => setShowEdit(false)} testId="am2-edit-modal">
          <h2>{activationM2Text.h_editBoardFundraisingPlanningForm}</h2>
          <label className="field"><span>Introduction</span><textarea rows={7} value={editForm.introduction} onChange={(e) => setEditForm({ ...editForm, introduction: e.target.value })} data-testid="am2-edit-introduction" /></label>
          <label className="field"><span>{activationModule2Text.fundraisingGoalContextShownTo}</span><textarea rows={4} value={editForm.goal_context} onChange={(e) => setEditForm({ ...editForm, goal_context: e.target.value })} data-testid="am2-edit-goal-context" /></label>
          <h3 style={{ margin: "14px 0 6px" }}>{activationM2Text.h_questions}</h3>
          {editForm.prompt_list.map((entry) => (
            <label className="field" key={entry.id}><span className="eyebrow">{entry.section}</span>
              <input value={editForm.question_prompts[entry.id]} onChange={(e) => setEditForm({ ...editForm, question_prompts: { ...editForm.question_prompts, [entry.id]: e.target.value } })} data-testid={`am2-edit-question-${entry.id}`} />
            </label>
          ))}
          <button type="button" className="button" onClick={saveEdit} disabled={saving} data-testid="am2-save-button">{saving ? "Saving…" : "SAVE"}</button>
        </Modal>
      )}

      {response && (
        <Modal onClose={() => setResponse(null)} testId="am2-response-modal">
          <h2>{response.participant.name} — Fundraising Planning Response</h2>
          <ResponseView data={response} />
        </Modal>
      )}
    </div>
  );
}
