import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, Eye, X } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { SupportBox } from "./CoursePages";
import { useFlowVideo } from "@/hooks/useFlowVideos";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RESPONSE_LABELS = {
  individuals_supporters: "Individuals who would support our mission",
  business_supporters: "Businesses or companies that could support us",
  foundation_supporters: "Foundations and grantmakers that may be a fit",
  where_to_find: "Where we can find and reach them",
  what_to_understand: "What supporters need to understand about our work",
  attract_engage: "How we can attract and engage supporters",
  build_trust: "How we can build relationship and trust",
  existing_relationships: "Relationships we should consider",
  priority_opportunities: "Fundraising opportunities to prioritize",
  priorities_explanation: "About the priorities selected",
  participation_willingness: "Fundraising support they are comfortable helping with",
  greater_responsibility_interest: "Open to discussing greater responsibility",
  greater_responsibility_detail: "Area and contribution they could make",
  support_needed: "Support that would help them participate",
  first_moves: "First things we should focus on",
  final_thoughts: "Anything else to consider",
};

const Modal = ({ children, onClose, testId }) => (
  <div className="modal-overlay" onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
    <div className="member-card" data-testid={testId} onClick={(e) => e.stopPropagation()} style={{ maxWidth: 760, width: "100%", maxHeight: "84vh", overflowY: "auto", position: "relative" }}>
      <button className="table-link" onClick={onClose} data-testid={`${testId}-close`} style={{ position: "absolute", top: 14, right: 14 }}><X size={18} /></button>
      {children}
    </div>
  </div>
);

const Section = ({ number, title, children, testId }) => (
  <section className="member-card" data-testid={testId} style={{ marginTop: 26 }}>
    <h2 style={{ marginTop: 0 }}>{number}. {title}</h2>
    {children}
  </section>
);

const EmailBlock = ({ email, testId }) => {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(`Subject: ${email.subject}\n\n${email.body}`); setCopied(true); setTimeout(() => setCopied(false), 2500); } catch { /* best effort */ }
  };
  return (
    <div data-testid={testId} style={{ border: "1px solid #d8ded9", borderRadius: 8, padding: 16, marginTop: 12, background: "#fafcfa" }}>
      <p><strong>Subject:</strong> {email.subject}</p>
      <p style={{ whiteSpace: "pre-wrap" }}>{email.body}</p>
      <button className="button button-small" onClick={copy} data-testid={`${testId}-copy`}>{copied ? "Copied!" : "COPY EMAIL"}</button>
    </div>
  );
};

const ResponseView = ({ data }) => (
  <div data-testid="fa-response-view">
    <h2 style={{ marginTop: 0 }}>{data.participant?.name}</h2>
    {Object.entries(RESPONSE_LABELS).map(([key, label]) => {
      const value = data.response?.[key];
      const text = Array.isArray(value) ? value.join(", ") : String(value || "").trim();
      if (!text) return null;
      return <p key={key} style={{ margin: "0 0 10px" }}><strong>{label}:</strong> {text}</p>;
    })}
    <p className="eyebrow">Submitted {data.submitted_at ? new Date(data.submitted_at).toLocaleString() : ""}</p>
  </div>
);

const errText = (err, fallback) => (typeof err?.response?.data?.detail === "string" ? err.response.data.detail : fallback);

export default function FundraisingActivationPage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const video = useFlowVideo("fundraising_activation");
  const [planning, setPlanning] = useState(null);
  const [strategy, setStrategy] = useState(null);
  const [adoption, setAdoption] = useState(null);
  const [board, setBoard] = useState(null);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState({});
  const [modal, setModal] = useState(null);
  const [planningEmail, setPlanningEmail] = useState(null);
  const [strategyEmail, setStrategyEmail] = useState(null);
  const [stepUp, setStepUp] = useState(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState(false);
  const [strategyDraft, setStrategyDraft] = useState("");
  const [editingFinal, setEditingFinal] = useState(false);
  const [finalDraft, setFinalDraft] = useState("");
  const [meeting, setMeeting] = useState({ meeting_date: "", meeting_time: "", meeting_link: "", meeting_notes: "" });
  const [meetingNotes, setMeetingNotes] = useState("");
  const [recordFile, setRecordFile] = useState(null);
  const pollRef = useRef();

  const setSectionNotice = (key, message) => setNotice((current) => ({ ...current, [key]: message }));

  const load = useCallback(async () => {
    try {
      const [p, s, a, b] = await Promise.all([
        memberApi.get("/activation/planning"), memberApi.get("/activation/strategy"),
        memberApi.get("/activation/adoption"), memberApi.get("/activation/my-board"),
      ]);
      setPlanning(p.data); setStrategy(s.data); setAdoption(a.data); setBoard(b.data);
      const ad = a.data.adoption || {};
      setMeeting({ meeting_date: ad.meeting_date || "", meeting_time: ad.meeting_time || "", meeting_link: ad.meeting_link || "", meeting_notes: ad.meeting_notes || "" });
      const generating = p.data.form?.status === "Generating" || s.data.strategy?.status === "Generating"
        || ad.guide_status === "Generating" || ad.revised_status === "Generating"
        || (b.data.members || []).some((m) => m.fp_status === "Generating");
      clearTimeout(pollRef.current);
      if (generating) pollRef.current = setTimeout(load, 5000);
    } catch { /* handled by page-level auth */ }
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login?next=/app/fundraising-activation"); return; }
    load();
    return () => clearTimeout(pollRef.current);
  }, [loading, member, navigate, load]);

  const allowed = member && (member.entitlements || []).some((e) => ["fundraising_board_builder", "activation_self_guided"].includes(e));
  const respondents = (planning?.participants || []).filter((p) => p.status === "COMPLETED");
  const boardMembers = (board?.members || []).filter((m) => m.status === "COMPLETED");
  const formStatus = planning?.form?.status || "NONE";
  const strategyStatus = strategy?.strategy?.status || "NONE";
  const ad = adoption?.adoption || {};

  const act = async (key, fn, errorFallback) => {
    setBusy(key); setSectionNotice(key, "");
    try { await fn(); } catch (err) { setSectionNotice(key, errText(err, errorFallback)); }
    setBusy("");
  };

  const copyFormLink = () => act("form", async () => {
    const r = await memberApi.get("/activation/planning-form/shared-link");
    await navigator.clipboard.writeText(r.data.form_link);
    setCopiedLink(true); setTimeout(() => setCopiedLink(false), 2500);
    load();
  }, "We could not create your form link.");

  const openResponse = (participantId) => act("responses", async () => {
    const r = await memberApi.get(`/activation/participants/${participantId}/response`);
    setModal({ type: "response", data: r.data });
  }, "We could not load this response.");

  const download = (path) => { window.open(`${API}${path}`, "_blank", "noopener"); };

  return (
    <MemberShell>
      <main className="member-page" data-testid="fbb-activation-page">
        <header className="member-page-heading">
          <p className="eyebrow">Fundraising Board Builder</p>
          <h1 data-testid="fbb-activation-heading">BOARD FUNDRAISING ACTIVATION</h1>
          <p><strong>Activate your present board members to start raising money and work with you to build your organization's fundraising system.</strong></p>
        </header>
        {member && !allowed && (
          <section className="member-card" data-testid="fbb-activation-forbidden"><p>Your account does not include access to this process.</p></section>
        )}
        {allowed && (
          <>
            {video?.youtube_id && (
              <div className="module-video" data-testid="fbb-activation-video">
                <iframe src={`https://www.youtube.com/embed/${video.youtube_id}`} title="Board Fundraising Activation" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
              </div>
            )}
            <section className="member-card" data-testid="fbb-activation-intro">
              <p>Your goal in this process is not to turn every board member into a professional fundraiser.</p>
              <p>Your goal is to lead your board through a process that gets them involved in planning how your organization will raise money, gives them ownership of the fundraising strategy, and helps each person participate based on how they can best support the organization.</p>
              <p><strong>Those that plan together execute together.</strong></p>
              <p>Follow the process below.</p>
            </section>

            <Section number={1} title="CREATE YOUR BOARD FUNDRAISING PLANNING FORM" testId="fa-section-form">
              <p>The first step is to collect the ideas, experience, networks and fundraising preferences of your board members.</p>
              <p>The Board Fundraising Planning Form allows each board member to tell you how they believe the organization can raise money and how they would personally like to support the process.</p>
              {formStatus === "Generating" ? (
                <p data-testid="fa-form-generating"><em>Generating your Board Fundraising Planning Form… this usually takes under a minute.</em></p>
              ) : formStatus === "NONE" || formStatus === "Failed" ? (
                <>
                  {formStatus === "Failed" && <p className="submit-error">The last generation failed. Please try again.</p>}
                  <button className="button" disabled={busy === "form"} data-testid="fa-generate-form"
                    onClick={() => act("form", async () => { await memberApi.post("/activation/planning-form/generate"); load(); }, "We could not start the generation.")}>
                    GENERATE BOARD FUNDRAISING PLANNING FORM
                  </button>
                </>
              ) : (
                <div data-testid="fa-form-ready">
                  <p><strong>YOUR BOARD FUNDRAISING PLANNING FORM IS READY</strong></p>
                  <p>Review the form before sending it to your board.</p>
                  <div className="material-actions" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <button className="button button-outline" onClick={() => setModal({ type: "form" })} data-testid="fa-view-form"><Eye size={15} /> VIEW FORM</button>
                    <button className="button" onClick={copyFormLink} disabled={busy === "form"} data-testid="fa-copy-form-link">{copiedLink ? "Link copied!" : "COPY FORM LINK"}</button>
                  </div>
                </div>
              )}
              {notice.form && <p className="submit-error">{notice.form}</p>}
            </Section>

            <Section number={2} title="SEND THE FORM TO YOUR BOARD" testId="fa-section-send">
              <p>When you are ready, reveal the email below.</p>
              <p>The email explains why you are asking your board members to complete the form and gives them the link they need.</p>
              {!planningEmail ? (
                <button className="button" disabled={busy === "send"} data-testid="fa-reveal-email"
                  onClick={() => act("send", async () => { const r = await memberApi.get("/activation/planning-email/shared"); setPlanningEmail(r.data); }, "Generate your planning form first.")}>
                  REVEAL EMAIL
                </button>
              ) : <EmailBlock email={planningEmail} testId="fa-planning-email" />}
              {notice.send && <p className="submit-error">{notice.send}</p>}
            </Section>

            <Section number={3} title="BOARD MEMBER RESPONSES" testId="fa-section-responses">
              <p>Everyone who completes your Board Fundraising Planning Form will appear below.</p>
              <p>You can view each response individually or download a copy.</p>
              {respondents.length === 0 && <p data-testid="fa-no-responses"><em>No responses yet. They will appear here automatically as your board members complete the form.</em></p>}
              {respondents.map((p) => (
                <div key={p.participant_id} data-testid={`fa-respondent-${p.participant_id}`} style={{ borderTop: "1px solid #e3e8e4", padding: "12px 0", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <div>
                    <strong>{p.name}</strong>
                    <p style={{ margin: 0, fontSize: "0.88rem" }}>Form completed: {(p.submitted_at || "").slice(0, 10)}</p>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="button button-small button-outline" onClick={() => openResponse(p.participant_id)} data-testid={`fa-view-response-${p.participant_id}`}><Eye size={14} /> VIEW RESPONSE</button>
                    <button className="button button-small button-outline" onClick={() => download(`/activation/participants/${p.participant_id}/response/pdf`)} data-testid={`fa-download-response-${p.participant_id}`}><Download size={14} /> DOWNLOAD</button>
                  </div>
                </div>
              ))}
              {notice.responses && <p className="submit-error">{notice.responses}</p>}
              <div style={{ marginTop: 22, borderTop: "1px solid #e3e8e4", paddingTop: 16 }} data-testid="fa-follow-up">
                <h3>NEED TO FOLLOW UP WITH A BOARD MEMBER?</h3>
                <p>You know your board better than we do.</p>
                <p>If there are board members who have not completed the form or who continue to avoid participating in the responsibilities of the board, use the tool below when you need it.</p>
                <p>It will help you have a clear conversation about whether they are willing to step up and participate or whether it may be time for them to step down from the board.</p>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button className="button button-outline" disabled={busy === "stepup"} data-testid="fa-stepup-email"
                    onClick={() => act("stepup", async () => { const r = await memberApi.get("/activation/step-up-resources"); setStepUp(r.data); setModal({ type: "stepup-email" }); }, "We could not load this resource.")}>
                    GENERATE STEP UP OR STEP DOWN EMAIL
                  </button>
                  <button className="button button-outline" disabled={busy === "stepup"} data-testid="fa-stepup-script"
                    onClick={() => act("stepup", async () => { const r = await memberApi.get("/activation/step-up-resources"); setStepUp(r.data); setModal({ type: "stepup-script" }); }, "We could not load this resource.")}>
                    GENERATE STEP UP OR STEP DOWN CALL SCRIPT
                  </button>
                </div>
                <p style={{ marginTop: 12 }}><strong>IMPORTANT:</strong> Generating these resources does not send anything automatically. Review them and decide who you want to use them with.</p>
                {notice.stepup && <p className="submit-error">{notice.stepup}</p>}
              </div>
            </Section>

            <Section number={4} title="GENERATE YOUR FUNDRAISING STRATEGY" testId="fa-section-strategy">
              <p>Once you are satisfied that you have received the feedback you want to include, generate your fundraising strategy.</p>
              <p>The strategy will use the information provided about your organization together with the responses received from your board members.</p>
              {strategyStatus === "Generating" ? (
                <p data-testid="fa-strategy-generating"><em>Generating your Fundraising Strategy… this can take a minute or two.</em></p>
              ) : strategyStatus === "NONE" || strategyStatus === "Failed" ? (
                <>
                  {strategyStatus === "Failed" && <p className="submit-error">The last generation failed. Please try again.</p>}
                  <button className="button" disabled={busy === "strategy"} data-testid="fa-generate-strategy"
                    onClick={() => act("strategy", async () => { await memberApi.post("/activation/strategy/generate"); load(); }, "We could not start the generation.")}>
                    GENERATE FUNDRAISING STRATEGY
                  </button>
                </>
              ) : (
                <div data-testid="fa-strategy-ready">
                  <p><strong>YOUR FUNDRAISING STRATEGY DRAFT</strong></p>
                  <p>Read through the strategy carefully. Make any edits you believe are necessary.</p>
                  <p>This is still a draft. Your board will have the opportunity to review it and make changes before it becomes the organization's final adopted fundraising strategy.</p>
                  {editingStrategy ? (
                    <>
                      <textarea rows={16} value={strategyDraft} onChange={(e) => setStrategyDraft(e.target.value)} data-testid="fa-strategy-editor" style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid #cfd6d2", fontFamily: "inherit" }} />
                      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="button button-small" disabled={busy === "strategy"} data-testid="fa-strategy-save"
                          onClick={() => act("strategy", async () => { await memberApi.put("/activation/strategy", { display_text: strategyDraft }); setEditingStrategy(false); load(); }, "We could not save your edits.")}>Save Edits</button>
                        <button className="button button-small button-outline" onClick={() => setEditingStrategy(false)} data-testid="fa-strategy-cancel">Cancel</button>
                      </div>
                    </>
                  ) : (
                    <div style={{ border: "1px solid #d8ded9", borderRadius: 8, padding: 16, maxHeight: 340, overflowY: "auto", whiteSpace: "pre-wrap", background: "#fafcfa" }} data-testid="fa-strategy-text">{strategy?.strategy?.display_text}</div>
                  )}
                  <div className="material-actions" style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
                    {!editingStrategy && <button className="button button-outline" onClick={() => { setStrategyDraft(strategy?.strategy?.display_text || ""); setEditingStrategy(true); }} data-testid="fa-edit-strategy">EDIT STRATEGY</button>}
                    <button className="button button-outline" disabled={busy === "strategy"} data-testid="fa-regenerate-strategy"
                      onClick={() => act("strategy", async () => { await memberApi.post("/activation/strategy/generate"); load(); }, "We could not start the regeneration.")}>REGENERATE STRATEGY</button>
                    {strategyStatus !== "Ready for Board Review" ? (
                      <button className="button" disabled={busy === "strategy"} data-testid="fa-approve-strategy"
                        onClick={() => act("strategy", async () => { await memberApi.post("/activation/strategy/approve-review"); load(); }, "We could not approve the draft.")}>APPROVE DRAFT</button>
                    ) : <span className="eyebrow" data-testid="fa-strategy-approved">Draft approved</span>}
                    <button className="button button-outline" onClick={() => download("/activation/strategy/pdf")} data-testid="fa-download-strategy"><Download size={15} /> DOWNLOAD BRANDED FUNDRAISING STRATEGY</button>
                  </div>
                </div>
              )}
              {notice.strategy && <p className="submit-error">{notice.strategy}</p>}
            </Section>

            <Section number={5} title="PREPARE TO SEND THE STRATEGY TO YOUR BOARD" testId="fa-section-meeting">
              <p>Before we generate the email, provide the details of the board meeting where the fundraising strategy will be reviewed.</p>
              <h3>MEETING DETAILS</h3>
              <label className="intake-field">Meeting Date<input type="date" value={meeting.meeting_date} onChange={(e) => setMeeting({ ...meeting, meeting_date: e.target.value })} data-testid="fa-meeting-date" /></label>
              <label className="intake-field">Meeting Time<input value={meeting.meeting_time} onChange={(e) => setMeeting({ ...meeting, meeting_time: e.target.value })} placeholder="e.g. 6:00 PM EST" data-testid="fa-meeting-time" /></label>
              <label className="intake-field">Meeting Location or Meeting Link<input value={meeting.meeting_link} onChange={(e) => setMeeting({ ...meeting, meeting_link: e.target.value })} data-testid="fa-meeting-link" /></label>
              <label className="intake-field">Any additional information you want included (optional)<textarea rows={2} value={meeting.meeting_notes} onChange={(e) => setMeeting({ ...meeting, meeting_notes: e.target.value })} data-testid="fa-meeting-notes" /></label>
              <button className="button" disabled={busy === "meeting"} data-testid="fa-save-meeting"
                onClick={() => act("meeting", async () => { await memberApi.put("/activation/adoption/meeting", meeting); setSectionNotice("meeting", "Meeting details saved."); load(); }, "We could not save the meeting details.")}>
                SAVE MEETING DETAILS
              </button>
              {notice.meeting && <p style={{ fontWeight: 700 }}>{notice.meeting}</p>}
            </Section>

            <Section number={6} title="SEND THE FUNDRAISING STRATEGY TO YOUR BOARD" testId="fa-section-strategy-email">
              <p>Your board members should have the opportunity to review the strategy before the meeting.</p>
              {!strategyEmail ? (
                <button className="button" disabled={busy === "strategyEmail"} data-testid="fa-reveal-strategy-email"
                  onClick={() => act("strategyEmail", async () => { const r = await memberApi.get("/activation/adoption/meeting-email"); setStrategyEmail(r.data); }, "Approve your strategy draft and save your meeting details first.")}>
                  REVEAL EMAIL
                </button>
              ) : <EmailBlock email={strategyEmail} testId="fa-strategy-email" />}
              {notice.strategyEmail && <p className="submit-error">{notice.strategyEmail}</p>}
            </Section>

            <Section number={7} title="PREPARE FOR YOUR FUNDRAISING STRATEGY ADOPTION MEETING" testId="fa-section-guide">
              <p>You will lead this meeting.</p>
              <p>We will give you the facilitation guide you need to walk your board through the strategy, discuss changes, secure agreement and determine the next steps.</p>
              {ad.guide_status === "Generating" ? (
                <p data-testid="fa-guide-generating"><em>Generating your facilitation guide…</em></p>
              ) : ad.guide_text ? (
                <div data-testid="fa-guide-ready">
                  <p><strong>YOUR ADOPTION MEETING FACILITATION GUIDE</strong></p>
                  <p>Use this guide during your board meeting. It will walk you through the conversation from beginning to end.</p>
                  <div className="material-actions" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <button className="button button-outline" onClick={() => setModal({ type: "guide" })} data-testid="fa-view-guide"><Eye size={15} /> VIEW GUIDE</button>
                    <button className="button button-outline" onClick={() => download("/activation/adoption/guide/pdf")} data-testid="fa-download-guide"><Download size={15} /> DOWNLOAD GUIDE</button>
                  </div>
                </div>
              ) : (
                <>
                  {ad.guide_status === "Failed" && <p className="submit-error">The last generation failed. Please try again.</p>}
                  <button className="button" disabled={busy === "guide"} data-testid="fa-generate-guide"
                    onClick={() => act("guide", async () => { await memberApi.post("/activation/adoption/guide/generate"); load(); }, "Approve your strategy draft first.")}>
                    GENERATE ADOPTION MEETING FACILITATION GUIDE
                  </button>
                </>
              )}
              {notice.guide && <p className="submit-error">{notice.guide}</p>}
            </Section>

            <Section number={8} title="AFTER THE BOARD MEETING" testId="fa-section-record">
              <p>Upload the transcript or audio recording from your fundraising strategy adoption meeting.</p>
              <p>We will use the meeting discussion, decisions and agreed changes to help you produce the final version of your fundraising strategy.</p>
              {ad.conclusion && (
                <p data-testid="fa-record-saved" style={{ fontWeight: 700 }}>
                  Meeting record saved{ad.meeting_record_filename ? ` (${ad.meeting_record_filename})` : ""}. You can replace it below at any time.
                </p>
              )}
              <input type="file" accept=".pdf,.doc,.docx,.txt,.mp3,.m4a,.wav,.webm,.mp4" onChange={(e) => setRecordFile(e.target.files?.[0] || null)} data-testid="fa-record-input" />
              {recordFile && (
                <p>Selected: <strong>{recordFile.name}</strong>{" "}
                  <button className="button button-small" disabled={busy === "record"} data-testid="fa-upload-record"
                    onClick={() => act("record", async () => {
                      const upload = new FormData();
                      upload.append("file", recordFile);
                      await memberApi.post("/activation/adoption/meeting-record", upload);
                      setRecordFile(null); setSectionNotice("record", "Your meeting record was saved."); load();
                    }, "We could not process this file.")}>
                    {busy === "record" ? "Processing… (audio can take a minute)" : "UPLOAD MEETING RECORD"}
                  </button>
                </p>
              )}
              <div style={{ marginTop: 16 }}>
                <p><strong>OPTIONAL ALTERNATIVE</strong></p>
                <p>If you do not have a transcript or audio recording, you can provide your meeting notes instead.</p>
                <textarea rows={5} value={meetingNotes} onChange={(e) => setMeetingNotes(e.target.value)} placeholder="Enter your meeting notes, decisions and agreed changes…" data-testid="fa-meeting-notes-text" style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid #cfd6d2", fontFamily: "inherit" }} />
                <button className="button button-outline" disabled={busy === "record" || !meetingNotes.trim()} data-testid="fa-save-notes" style={{ marginTop: 8 }}
                  onClick={() => act("record", async () => { await memberApi.put("/activation/adoption/conclusion", { text: meetingNotes }); setMeetingNotes(""); setSectionNotice("record", "Your meeting notes were saved."); load(); }, "We could not save your notes.")}>
                  SAVE MEETING NOTES
                </button>
              </div>
              {notice.record && <p style={{ fontWeight: 700 }}>{notice.record}</p>}
            </Section>

            <Section number={9} title="GENERATE YOUR FINAL FUNDRAISING STRATEGY" testId="fa-section-final">
              <p>Once the meeting information has been uploaded, generate the final strategy.</p>
              {ad.revised_status === "Generating" ? (
                <p data-testid="fa-final-generating"><em>Generating your Final Fundraising Strategy…</em></p>
              ) : ad.revised_text ? (
                <div data-testid="fa-final-ready">
                  <p><strong>YOUR FINAL FUNDRAISING STRATEGY</strong></p>
                  <p>Review the final version carefully and make any final edits required.</p>
                  {editingFinal ? (
                    <>
                      <textarea rows={16} value={finalDraft} onChange={(e) => setFinalDraft(e.target.value)} data-testid="fa-final-editor" style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid #cfd6d2", fontFamily: "inherit" }} />
                      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="button button-small" disabled={busy === "final"} data-testid="fa-final-save"
                          onClick={() => act("final", async () => { await memberApi.put("/activation/adoption/revised", { text: finalDraft }); setEditingFinal(false); load(); }, "We could not save your edits.")}>Save Edits</button>
                        <button className="button button-small button-outline" onClick={() => setEditingFinal(false)} data-testid="fa-final-cancel">Cancel</button>
                      </div>
                    </>
                  ) : (
                    <div style={{ border: "1px solid #d8ded9", borderRadius: 8, padding: 16, maxHeight: 340, overflowY: "auto", whiteSpace: "pre-wrap", background: "#fafcfa" }} data-testid="fa-final-text">{ad.revised_text}</div>
                  )}
                  <div className="material-actions" style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
                    {!editingFinal && <button className="button button-outline" onClick={() => { setFinalDraft(ad.revised_text || ""); setEditingFinal(true); }} data-testid="fa-edit-final">EDIT STRATEGY</button>}
                    <button className="button button-outline" disabled={busy === "final"} data-testid="fa-regenerate-final"
                      onClick={() => act("final", async () => { await memberApi.post("/activation/adoption/strategy/generate"); load(); }, "We could not start the regeneration.")}>REGENERATE</button>
                    <button className="button button-outline" onClick={() => download("/activation/adoption/revised/pdf")} data-testid="fa-download-final"><Download size={15} /> DOWNLOAD BRANDED FINAL STRATEGY</button>
                  </div>
                </div>
              ) : (
                <>
                  {ad.revised_status === "Failed" && <p className="submit-error">The last generation failed. Please try again.</p>}
                  <button className="button" disabled={busy === "final"} data-testid="fa-generate-final"
                    onClick={() => act("final", async () => { await memberApi.post("/activation/adoption/strategy/generate"); load(); }, "Approve your strategy draft and save your meeting record first.")}>
                    GENERATE FINAL FUNDRAISING STRATEGY
                  </button>
                </>
              )}
              {notice.final && <p className="submit-error">{notice.final}</p>}
            </Section>

            <Section number={10} title="CREATE YOUR BOARD MEMBERS' FUNDRAISING EXECUTION PORTFOLIOS" testId="fa-section-portfolios">
              <p>Now that your fundraising strategy has been developed and discussed with your board, you can create an individual fundraising execution portfolio for each board member who completed the planning process.</p>
              <p>Select a board member below.</p>
              {boardMembers.length === 0 && <p><em>Board members who complete the planning form will appear here.</em></p>}
              {boardMembers.map((m) => (
                <div key={m.participant_id} data-testid={`fa-portfolio-member-${m.participant_id}`} style={{ borderTop: "1px solid #e3e8e4", padding: "12px 0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                    <strong>{m.name}</strong>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {m.fp_status === "Generating" ? (
                        <em data-testid={`fa-fp-generating-${m.participant_id}`}>Generating portfolio…</em>
                      ) : m.fp_text ? (
                        <>
                          <button className="button button-small button-outline" onClick={() => setModal({ type: "portfolio", data: m })} data-testid={`fa-view-fp-${m.participant_id}`}><Eye size={14} /> VIEW PORTFOLIO</button>
                          <button className="button button-small button-outline" onClick={() => download(`/activation/members/${m.participant_id}/portfolio/pdf`)} data-testid={`fa-download-fp-${m.participant_id}`}><Download size={14} /> DOWNLOAD BRANDED PORTFOLIO</button>
                          <button className="button button-small button-outline" disabled={busy === `fp-${m.participant_id}`} data-testid={`fa-regenerate-fp-${m.participant_id}`}
                            onClick={() => act(`fp-${m.participant_id}`, async () => { await memberApi.post(`/activation/members/${m.participant_id}/portfolio/generate`); load(); }, "We could not start the generation.")}>Regenerate</button>
                        </>
                      ) : (
                        <button className="button button-small" disabled={busy === `fp-${m.participant_id}`} data-testid={`fa-generate-fp-${m.participant_id}`}
                          onClick={() => act(`fp-${m.participant_id}`, async () => { await memberApi.post(`/activation/members/${m.participant_id}/portfolio/generate`); load(); }, "Generate your Final Fundraising Strategy first.")}>
                          GENERATE FUNDRAISING EXECUTION PORTFOLIO
                        </button>
                      )}
                    </div>
                  </div>
                  {m.fp_error && <p className="submit-error">{m.fp_error}</p>}
                  {notice[`fp-${m.participant_id}`] && <p className="submit-error">{notice[`fp-${m.participant_id}`]}</p>}
                </div>
              ))}
            </Section>

            <section className="member-card" data-testid="fa-closing" style={{ marginTop: 26 }}>
              <h2>YOU HAVE BUILT THE FOUNDATION OF YOUR FUNDRAISING SYSTEM</h2>
              <p>Your board has contributed to your fundraising strategy.</p>
              <p>Your organization now has a working fundraising plan.</p>
              <p>Your participating board members know how they can support execution.</p>
              <p>Your next responsibility is to keep the strategy moving and continue building the people, materials and systems needed to execute it consistently.</p>
              <p><strong>Those that plan together execute together.</strong></p>
            </section>

            <SupportBox productKey="activation_self_guided" moduleNumber={1}
              supportTypes={["I have a question about this step", "I need help using the platform", "I need help executing this step", "I would like someone to help me complete this step"]} />
          </>
        )}

        {modal?.type === "response" && <Modal onClose={() => setModal(null)} testId="fa-response-modal"><ResponseView data={modal.data} /></Modal>}
        {modal?.type === "form" && (
          <Modal onClose={() => setModal(null)} testId="fa-form-modal">
            <h2 style={{ marginTop: 0 }}>{planning?.form?.content?.title || "Board Fundraising Planning Form"}</h2>
            <p style={{ whiteSpace: "pre-wrap" }}>{planning?.form?.content?.introduction}</p>
            {planning?.form?.content?.goal_context && <p style={{ whiteSpace: "pre-wrap" }}><strong>{planning.form.content.goal_context}</strong></p>}
            {(planning?.form?.content?.sections || []).map((section) => (
              <div key={section.key} style={{ marginTop: 14 }}>
                <p className="eyebrow" style={{ marginBottom: 6 }}>{section.title}</p>
                {section.questions.map((q) => <p key={q.id} style={{ margin: "0 0 6px" }}>{q.prompt}{q.required ? "" : " (optional)"}</p>)}
              </div>
            ))}
          </Modal>
        )}
        {modal?.type === "stepup-email" && stepUp && (
          <Modal onClose={() => setModal(null)} testId="fa-stepup-email-modal">
            <h2 style={{ marginTop: 0 }}>Step Up or Step Down Email</h2>
            <EmailBlock email={stepUp.email} testId="fa-stepup-email-content" />
          </Modal>
        )}
        {modal?.type === "stepup-script" && stepUp && (
          <Modal onClose={() => setModal(null)} testId="fa-stepup-script-modal">
            <h2 style={{ marginTop: 0 }}>Step Up or Step Down Call Script</h2>
            <p style={{ whiteSpace: "pre-wrap" }} data-testid="fa-stepup-script-text">{stepUp.call_script}</p>
            <button className="button button-small" data-testid="fa-stepup-script-copy" onClick={() => navigator.clipboard.writeText(stepUp.call_script).catch(() => {})}>COPY SCRIPT</button>
          </Modal>
        )}
        {modal?.type === "guide" && (
          <Modal onClose={() => setModal(null)} testId="fa-guide-modal">
            <h2 style={{ marginTop: 0 }}>Adoption Meeting Facilitation Guide</h2>
            <p style={{ whiteSpace: "pre-wrap" }} data-testid="fa-guide-text">{ad.guide_text}</p>
          </Modal>
        )}
        {modal?.type === "portfolio" && (
          <Modal onClose={() => setModal(null)} testId="fa-portfolio-modal">
            <h2 style={{ marginTop: 0 }}>Fundraising Execution Portfolio — {modal.data.name}</h2>
            <p style={{ whiteSpace: "pre-wrap" }} data-testid="fa-portfolio-text">{modal.data.fp_text}</p>
          </Modal>
        )}
      </main>
    </MemberShell>
  );
}
