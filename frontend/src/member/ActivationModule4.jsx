import { useCallback, useEffect, useRef, useState } from "react";
import { Copy, Download, Mail, X } from "lucide-react";
import { memberApi } from "./api";
import { activationM4Text, activationModule4Text } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const dialogStyle = { background: "#fff", maxWidth: 780, width: "100%", padding: "28px", borderRadius: 8, position: "relative" };

const Modal = ({ children, onClose, testId }) => (
  <div style={overlayStyle} data-testid={testId}>
    <div style={dialogStyle}>
      <button type="button" onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testId}-close`}><X size={20} /></button>
      {children}
    </div>
  </div>
);

const PLAN_STATUSES = ["Adopted as Presented", "Adopted With Changes", "Further Review Needed"];

export default function ActivationModule4() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [generatingGuide, setGeneratingGuide] = useState(false);
  const [generatingRevised, setGeneratingRevised] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [conclusionSaved, setConclusionSaved] = useState(false);
  const [adoptedDraft, setAdoptedDraft] = useState("");
  const [meeting, setMeeting] = useState({ meeting_date: "", meeting_time: "", meeting_link: "", meeting_notes: "" });
  const [meetingSaved, setMeetingSaved] = useState(false);
  const [meetingEmail, setMeetingEmail] = useState(null);
  const [emailBusy, setEmailBusy] = useState(false);
  const [copied, setCopied] = useState("");
  const pollRef = useRef(null);

  const load = useCallback(() => {
    memberApi.get("/activation/adoption").then((res) => {
      setData(res.data);
      setConclusion(res.data.adoption.conclusion || "");
      setAdoptedDraft(res.data.adoption.draft_adopted_text || "");
      setMeeting({
        meeting_date: res.data.adoption.meeting_date || "",
        meeting_time: res.data.adoption.meeting_time || "",
        meeting_link: res.data.adoption.meeting_link || "",
        meeting_notes: res.data.adoption.meeting_notes || "",
      });
    }).catch(() => setError("We could not load your plan adoption workspace."));
  }, []);
  useEffect(load, [load]);

  const anyGenerating = data?.adoption?.guide_status === "Generating" || data?.adoption?.revised_status === "Generating";
  useEffect(() => {
    if (anyGenerating && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await memberApi.get("/activation/adoption/status");
          if (res.data.guide_status !== "Generating" && res.data.revised_status !== "Generating") {
            clearInterval(pollRef.current); pollRef.current = null;
            setGeneratingGuide(false); setGeneratingRevised(false); load();
          }
        } catch { /* keep polling */ }
      }, 3000);
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [anyGenerating, load]);

  const generateRevised = async () => {
    if (data?.adoption?.revised_text && !window.confirm("This will replace the current revised Fundraising Strategy Plan with a newly generated version built from the latest Board reviews. Continue?")) return;
    setGeneratingRevised(true);
    try { await memberApi.post("/activation/adoption/strategy/generate"); load(); } catch (err) {
      setGeneratingRevised(false);
      window.alert(err.response?.data?.detail || "Generation could not start.");
    }
  };

  const generateGuide = async () => {
    if (data?.adoption?.guide_text && !window.confirm("This will replace the current Facilitation Guide with a newly generated version. Continue?")) return;
    setGeneratingGuide(true);
    try { await memberApi.post("/activation/adoption/guide/generate"); load(); } catch (err) {
      setGeneratingGuide(false);
      window.alert(err.response?.data?.detail || "Generation could not start.");
    }
  };

  const saveGuide = async () => {
    try { await memberApi.put("/activation/adoption/guide", { text: editText }); setShowEdit(false); load(); } catch { /* keep open */ }
  };
  const approveGuide = async () => { try { await memberApi.post("/activation/adoption/guide/approve"); load(); } catch { /* ignore */ } };

  const saveMeeting = async () => {
    try {
      await memberApi.put("/activation/adoption/meeting", meeting);
      setMeetingSaved(true);
      setTimeout(() => setMeetingSaved(false), 2500);
      load();
    } catch (err) {
      window.alert(err.response?.data?.detail || "Could not save the meeting details.");
    }
  };

  const generateMeetingEmail = async () => {
    setEmailBusy(true);
    try {
      const res = await memberApi.get("/activation/adoption/meeting-email");
      setMeetingEmail(res.data);
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

  const saveConclusion = async () => {
    if (!conclusion.trim()) return;
    await memberApi.put("/activation/adoption/conclusion", { text: conclusion });
    setConclusionSaved(true);
    load();
  };

  const setPlanStatus = async (status) => {
    try { await memberApi.put("/activation/adoption/plan-status", { status }); load(); } catch (err) {
      window.alert(err.response?.data?.detail || "Could not save the plan status.");
    }
  };

  const saveAdoptedDraft = async () => { await memberApi.put("/activation/adoption/adopted-plan", { text: adoptedDraft }); load(); };
  const finalize = async () => {
    try { await memberApi.post("/activation/adoption/finalize"); load(); } catch (err) {
      window.alert(err.response?.data?.detail || "Could not finalize the plan.");
    }
  };

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">{activationModule4Text.loadingYourPlanAdoptionWorkspace}</p>;

  const adoption = data.adoption;
  const guideStatus = adoption.guide_status || "NONE";
  const revisedStatus = adoption.revised_status || "NONE";
  const meetingReady = Boolean(adoption.meeting_date && adoption.meeting_time);

  return (
    <div data-testid="activation-module4">
      <section className="member-card" data-testid="am4-intro">
        <h2>{activationM4Text.h_turnTheFundraisingStrategyInto}</h2>
        <p>{activationModule4Text.theBoardHasHelpedBuild}</p>
        <p>{activationModule4Text.theNextStepIsTo}</p>
        <p><strong>{activationModule4Text.thisIsWhereParticipationBecomes}</strong></p>
      </section>

      <section className="member-card" data-testid="am4-participants-card">
        <h2>{activationM4Text.h_boardReviewParticipants}</h2>
        <p>{activationM4Text.d_boardReviewParticipants}</p>
        <p data-testid="am4-context-line">Strategy: <strong>{data.strategy.status === "Ready for Board Review" ? `Ready for Board Review · v${data.strategy.review_version}` : data.strategy.status}</strong> · Board reviews received: <strong>{data.reviews.length}</strong></p>
        {!data.reviews.length && <p data-testid="am4-no-reviews">{activationM4Text.n_noReviewsYet}</p>}
        {data.reviews.map((review) => (
          <div key={review.name} style={{ borderLeft: "3px solid #000", paddingLeft: 12, margin: "14px 0" }} data-testid={`am4-review-${review.name.split(" ")[0].toLowerCase()}`}>
            <p style={{ margin: 0 }}><strong>{review.name}</strong> ({review.role}) — {review.position}</p>
            {review.discussion_points && <p style={{ margin: "4px 0 0" }}>To discuss: {review.discussion_points}</p>}
            {review.contribution && <p style={{ margin: "4px 0 0" }}>Contribution interest: {review.contribution}</p>}
            {review.support_needs && <p style={{ margin: "4px 0 0" }}>Support needs: {review.support_needs}</p>}
          </div>
        ))}
      </section>

      <section className="member-card" data-testid="am4-revised-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2 style={{ margin: 0 }}>{activationM4Text.h_revisedFundraisingStrategyPlan}</h2>
          <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid="am4-revised-status">{revisedStatus === "NONE" ? "NOT GENERATED" : revisedStatus.toUpperCase()}</span>
        </div>
        <p style={{ marginTop: 10 }}>{activationM4Text.d_revisedFundraisingStrategyPlan}</p>
        {revisedStatus === "Failed" && <p className="submit-error" data-testid="am4-revised-error">{activationModule4Text.generationFailedPleaseTryAgain}</p>}
        {revisedStatus === "Generating" || generatingRevised ? (
          <p data-testid="am4-revised-generating">{activationModule4Text.generatingTheRevisedFundraisingStrategy}</p>
        ) : (
          <button type="button" className="button" onClick={generateRevised} data-testid="am4-generate-revised-button">{adoption.revised_text ? "REGENERATE FUNDRAISING STRATEGY" : "GENERATE FUNDRAISING STRATEGY"}</button>
        )}
        {adoption.revised_text && revisedStatus !== "Generating" && (
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 14, maxHeight: 420, overflowY: "auto" }} data-testid="am4-revised-text">{adoption.revised_text}</div>
        )}
      </section>

      <section className="member-card" data-testid="am4-meeting-card">
        <h2>{activationM4Text.h_adoptionMeetingDetails}</h2>
        <p>{activationM4Text.d_adoptionMeetingDetails}</p>
        <div className="two-col-fields">
          <label className="field"><span>Adoption meeting date</span><input type="date" value={meeting.meeting_date} onChange={(e) => setMeeting({ ...meeting, meeting_date: e.target.value })} data-testid="am4-meeting-date" /></label>
          <label className="field"><span>Adoption meeting time</span><input type="time" value={meeting.meeting_time} onChange={(e) => setMeeting({ ...meeting, meeting_time: e.target.value })} data-testid="am4-meeting-time" /></label>
        </div>
        <label className="field"><span>{activationModule4Text.meetingLinkIfThereIs}</span><input value={meeting.meeting_link} onChange={(e) => setMeeting({ ...meeting, meeting_link: e.target.value })} data-testid="am4-meeting-link" /></label>
        <label className="field"><span>{activationModule4Text.anyOtherMeetingDetailsOptional}</span><textarea rows={3} value={meeting.meeting_notes} onChange={(e) => setMeeting({ ...meeting, meeting_notes: e.target.value })} data-testid="am4-meeting-notes" /></label>
        <button type="button" className="button" onClick={saveMeeting} data-testid="am4-save-meeting">{meetingSaved ? "Details Saved" : "SAVE MEETING DETAILS"}</button>
      </section>

      <section className="member-card" data-testid="am4-invite-card">
        <h2>{activationM4Text.h_adoptionMeetingInvitation}</h2>
        <p>{activationM4Text.d_adoptionMeetingInvitation}</p>
        {!meetingReady && <p className="eyebrow" data-testid="am4-invite-locked">{activationM4Text.n_saveMeetingToUnlockEmail}</p>}
        <button type="button" className="button" onClick={generateMeetingEmail} disabled={!meetingReady || emailBusy} data-testid="am4-generate-invite-button"><Mail size={15} /> {emailBusy ? "Generating…" : meetingEmail ? "REGENERATE ADOPTION MEETING EMAIL" : "GENERATE ADOPTION MEETING EMAIL"}</button>
        {meetingEmail && (
          <div style={{ marginTop: 14 }} data-testid="am4-invite-preview">
            <p><strong>Subject:</strong> <span data-testid="am4-invite-subject">{meetingEmail.subject}</span></p>
            <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 320, overflowY: "auto" }} data-testid="am4-invite-body">{meetingEmail.body}</div>
            <p style={{ marginTop: 10 }}><strong>Secure Plan Link:</strong> <span style={{ wordBreak: "break-all" }} data-testid="am4-invite-link">{meetingEmail.plan_link}</span></p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              <button type="button" className="button" onClick={() => copyText(meetingEmail.body, "invite-body")} data-testid="am4-copy-invite-button"><Copy size={15} /> {copied === "invite-body" ? "Email Copied" : "COPY EMAIL"}</button>
              <button type="button" className="button button-outline" onClick={() => copyText(meetingEmail.subject, "invite-subject")} data-testid="am4-copy-invite-subject-button"><Copy size={15} /> {copied === "invite-subject" ? "Subject Copied" : "COPY SUBJECT"}</button>
            </div>
          </div>
        )}
      </section>

      <section className="member-card" data-testid="am4-guide-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2 style={{ margin: 0 }}>{activationModule4Text.planAdoptionFacilitationGuide}</h2>
          <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid="am4-guide-status">{guideStatus === "NONE" ? "NOT GENERATED" : guideStatus.toUpperCase()}</span>
        </div>
        {adoption.guide_error && guideStatus === "Failed" && <p className="submit-error">{activationModule4Text.generationFailedPleaseTryAgain2}</p>}
        {guideStatus === "Generating" || generatingGuide ? (
          <p data-testid="am4-generating">{activationModule4Text.generatingYourFacilitationGuideFrom}</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
            <button type="button" className="button" onClick={generateGuide} data-testid="am4-generate-button">{adoption.guide_text ? "REGENERATE" : "GENERATE FACILITATION GUIDE"}</button>
            {adoption.guide_text && (
              <>
                <button type="button" className="button button-outline" onClick={() => { setEditText(adoption.guide_text); setShowEdit(true); }} data-testid="am4-edit-button">EDIT</button>
                {guideStatus !== "Approved" && <button type="button" className="button" onClick={approveGuide} data-testid="am4-approve-button">APPROVE</button>}
                <a className="button button-outline" href={`${API}/activation/adoption/guide/pdf`} target="_blank" rel="noreferrer" data-testid="am4-pdf-button"><Download size={15} /> DOWNLOAD PDF</a>
              </>
            )}
          </div>
        )}
        {adoption.guide_text && guideStatus !== "Generating" && (
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 14, maxHeight: 380, overflowY: "auto" }} data-testid="am4-guide-text">{adoption.guide_text}</div>
        )}
        <p className="eyebrow" style={{ marginTop: 10 }}>{activationModule4Text.thisGuideIsYourInternal}</p>
      </section>

      <section className="member-card" data-testid="am4-conclusion-card">
        <h2>{activationM4Text.h_planAdoptionConclusion}</h2>
        <p>{activationM4Text.d_planAdoptionConclusion}</p>
        <textarea rows={6} style={{ width: "100%" }} value={conclusion} onChange={(e) => { setConclusion(e.target.value); setConclusionSaved(false); }} data-testid="am4-conclusion-text" />
        <button type="button" className="button" onClick={saveConclusion} data-testid="am4-save-conclusion" style={{ marginTop: 10 }}>{conclusionSaved ? "Conclusion Saved" : "SAVE CONCLUSION"}</button>
      </section>

      <section className="member-card" data-testid="am4-plan-status-card">
        <h2>{activationM4Text.h_planStatus}</h2>
        <p>{activationModule4Text.recordTheBoardsAdoptionOutcome}</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {PLAN_STATUSES.map((status) => (
            <label className={`choice ${adoption.plan_status === status ? "selected" : ""}`} key={status}>
              <input type="radio" name="plan-status" checked={adoption.plan_status === status} onChange={() => setPlanStatus(status)} data-testid={`am4-plan-status-${status.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
              <span>{status}</span>
            </label>
          ))}
        </div>
        {adoption.plan_status === "Further Review Needed" && (
          <p className="submit-error" style={{ marginTop: 12 }} data-testid="am4-blocked-note">{activationModule4Text.theStrategyMustBeResolved}</p>
        )}
        {adoption.plan_status === "Adopted as Presented" && adoption.finalized && (
          <p style={{ marginTop: 12 }} data-testid="am4-adopted-note"><strong>{activationModule4Text.theStrategyVersionYourBoard}</strong></p>
        )}
        {adoption.plan_status === "Adopted With Changes" && (
          <div style={{ marginTop: 14 }} data-testid="am4-changes-area">
            <p>{activationModule4Text.editTheStrategyToReflect}</p>
            <textarea rows={14} style={{ width: "100%" }} value={adoptedDraft} onChange={(e) => setAdoptedDraft(e.target.value)} data-testid="am4-adopted-draft" />
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              <button type="button" className="button button-outline" onClick={saveAdoptedDraft} data-testid="am4-save-adopted-draft">SAVE EDITS</button>
              <button type="button" className="button" onClick={finalize} data-testid="am4-finalize-button">FINALIZE ADOPTED PLAN</button>
            </div>
            {adoption.finalized && <p style={{ marginTop: 10 }} data-testid="am4-finalized-note"><strong>Adopted plan finalized.</strong></p>}
          </div>
        )}
      </section>

      <section style={{ textAlign: "center", margin: "26px 0" }}>
        {data.module5_ready ? (
          <p className="eyebrow" data-testid="am4-module5-unlocked">{activationModule4Text.module5IsUnlockedUse}</p>
        ) : (
          <p className="eyebrow" data-testid="am4-module5-locked">{activationModule4Text.module5OpensOnceYour}</p>
        )}
      </section>

      {showEdit && (
        <Modal onClose={() => setShowEdit(false)} testId="am4-edit-modal">
          <h2>{activationM4Text.h_editFacilitationGuide}</h2>
          <textarea rows={22} style={{ width: "100%" }} value={editText} onChange={(e) => setEditText(e.target.value)} data-testid="am4-edit-text" />
          <button type="button" className="button" onClick={saveGuide} data-testid="am4-save-button">SAVE</button>
        </Modal>
      )}
    </div>
  );
}
