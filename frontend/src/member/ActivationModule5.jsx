import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Download, Mail, X } from "lucide-react";
import { memberApi } from "./api";
import { ExecutionResourceCard } from "./ExecutionResourceCard";
import { activationM5Text, activationContent, activationModule5Text } from "../content/appContent";

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

export default function ActivationModule5() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState("");
  const [respEdits, setRespEdits] = useState({});
  const [savedResp, setSavedResp] = useState("");
  const [editFollowup, setEditFollowup] = useState(null);
  const [copied, setCopied] = useState("");
  const pollRef = useRef(null);

  const load = useCallback(() => {
    memberApi.get("/activation/toolkit").then((res) => setData(res.data)).catch(() => setError("We could not load your execution toolkit workspace."));
  }, []);
  useEffect(load, [load]);

  const anyGenerating = data?.toolkit?.status === "Generating" || data?.case?.status === "Generating" || data?.communication_system?.status === "Generating" || (data?.members || []).some((m) => m.followup_status === "Generating");
  useEffect(() => {
    if (anyGenerating && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await memberApi.get("/activation/toolkit");
          const stillGenerating = res.data.toolkit.status === "Generating" || res.data.case?.status === "Generating" || res.data.communication_system?.status === "Generating" || (res.data.members || []).some((m) => m.followup_status === "Generating");
          if (!stillGenerating) {
            clearInterval(pollRef.current); pollRef.current = null;
            setGenerating(false);
          }
          setData(res.data);
        } catch { /* keep polling */ }
      }, 3000);
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [anyGenerating]);

  const generate = async () => {
    if (data?.toolkit?.display_text && !window.confirm("This will replace the current Execution Toolkit with a newly generated version. Continue?")) return;
    setGenerating(true);
    try { await memberApi.post("/activation/toolkit/generate"); load(); } catch (err) {
      setGenerating(false);
      window.alert(err.response?.data?.detail || "Generation could not start.");
    }
  };

  const saveEdit = async () => {
    try { await memberApi.put("/activation/toolkit", { text: editText }); setShowEdit(false); load(); } catch { /* keep open */ }
  };
  const approve = async () => { try { await memberApi.post("/activation/toolkit/approve"); load(); } catch { /* ignore */ } };

  const saveResponsibility = async (member) => {
    const edit = respEdits[member.participant_id] || {};
    try {
      await memberApi.put(`/activation/participants/${member.participant_id}/responsibility`, {
        agreed_responsibility: edit.agreed_responsibility ?? member.agreed_responsibility,
        responsibility_status: edit.responsibility_status ?? member.responsibility_status,
      });
      setSavedResp(member.participant_id);
      setTimeout(() => setSavedResp(""), 2500);
      load();
    } catch (err) {
      window.alert(err.response?.data?.detail || "Could not save the responsibility.");
    }
  };

  const generateFollowup = async (member) => {
    if (member.followup_body && !window.confirm("This will replace this member's follow-up email with a newly generated version. Continue?")) return;
    try { await memberApi.post(`/activation/members/${member.participant_id}/followup-email/generate`); load(); } catch (err) {
      window.alert(err.response?.data?.detail || "Generation could not start.");
    }
  };

  const saveFollowup = async () => {
    try {
      await memberApi.put(`/activation/members/${editFollowup.participant_id}/followup-email`, { subject: editFollowup.subject, body: editFollowup.body });
      setEditFollowup(null);
      load();
    } catch (err) {
      window.alert(err.response?.data?.detail || "Could not save the email.");
    }
  };

  const copyText = async (text, key) => {
    try { await navigator.clipboard.writeText(text); } catch { window.prompt("Copy this text:", text); }
    setCopied(key);
    setTimeout(() => setCopied(""), 2500);
  };

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">{activationModule5Text.loadingYourExecutionToolkitWorkspace}</p>;

  const toolkit = data.toolkit;

  return (
    <div data-testid="activation-module5">
      <section className="member-card" data-testid="am5-intro">
        <h2>{activationM5Text.h_giveYourBoardTheTools}</h2>
        <p>{activationModule5Text.theBoardHasHelpedBuild}</p>
        <p>{activationModule5Text.nowGiveBoardMembersPractical}</p>
      </section>

      {!data.gate_open ? (
        <section className="member-card" data-testid="am5-locked">
          <h2>{activationM5Text.h_thePlanMustBeAdopted}</h2>
          <p>{activationModule5Text.theFundraisingStrategyPlanMust}</p>
          {data.plan_status === "Further Review Needed" && <p data-testid="am5-further-review-note">{activationModule5Text.yourRecordedPlanStatusIs}<strong>Further Review Needed</strong>{activationModule5Text.returnToModule4To}</p>}
          <Link className="button" to="/app/activation/self-guided/module/4" data-testid="am5-back-to-module4">{activationModule5Text.goToModule4Facilitate}</Link>
        </section>
      ) : (
        <>
          <section className="member-card" data-testid="am5-members-card">
            <h2>{activationM5Text.h_equipEachBoardMember}</h2>
            <p>{activationM5Text.d_equipEachBoardMember}</p>
            {data.members.map((member) => {
              const edit = respEdits[member.participant_id] || {};
              return (
                <article key={member.participant_id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 16 }} data-testid={`am5-member-${member.participant_id}`}>
                  <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                    <div>
                      <h3 style={{ margin: 0 }}>{member.name}</h3>
                      <p style={{ margin: "4px 0 0" }}>{member.role || "Board Member"} · {member.email}</p>
                    </div>
                    <span className="eyebrow" style={{ alignSelf: "flex-start", padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid={`am5-resp-status-${member.participant_id}`}>{member.responsibility_status}</span>
                  </div>
                  <label className="field" style={{ marginTop: 12 }}><span>{activationModule5Text.agreedFundraisingResponsibilityAreaThey}</span>
                    <textarea rows={3} value={edit.agreed_responsibility ?? member.agreed_responsibility} onChange={(e) => setRespEdits({ ...respEdits, [member.participant_id]: { ...edit, agreed_responsibility: e.target.value } })} data-testid={`am5-responsibility-${member.participant_id}`} />
                  </label>
                  <label className="field"><span>Responsibility Status</span>
                    <select value={edit.responsibility_status ?? member.responsibility_status} onChange={(e) => setRespEdits({ ...respEdits, [member.participant_id]: { ...edit, responsibility_status: e.target.value } })} data-testid={`am5-resp-status-select-${member.participant_id}`}>
                      {data.responsibility_statuses.map((status) => <option key={status}>{status}</option>)}
                    </select>
                  </label>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    <button type="button" className="button" onClick={() => saveResponsibility(member)} data-testid={`am5-save-resp-${member.participant_id}`}>{savedResp === member.participant_id ? "Saved" : "SAVE RESPONSIBILITY"}</button>
                    {member.followup_status === "Generating" ? (
                      <p style={{ margin: 0, alignSelf: "center" }} data-testid={`am5-followup-generating-${member.participant_id}`}>{activationModule5Text.generatingFollowUpEmail}</p>
                    ) : (
                      <button type="button" className="button button-outline" onClick={() => generateFollowup(member)} data-testid={`am5-generate-followup-${member.participant_id}`}><Mail size={15} /> {member.followup_body ? "REGENERATE FOLLOW-UP EMAIL" : "GENERATE FOLLOW-UP EMAIL"}</button>
                    )}
                  </div>
                  {member.followup_status === "Failed" && <p className="submit-error" data-testid={`am5-followup-error-${member.participant_id}`}>{activationModule5Text.generationFailedPleaseTryAgain}</p>}
                  {member.followup_body && member.followup_status !== "Generating" && (
                    <div style={{ marginTop: 12 }} data-testid={`am5-followup-preview-${member.participant_id}`}>
                      <p><strong>Subject:</strong> <span data-testid={`am5-followup-subject-${member.participant_id}`}>{member.followup_subject}</span></p>
                      <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 280, overflowY: "auto" }} data-testid={`am5-followup-body-${member.participant_id}`}>{member.followup_body}</div>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                        <button type="button" className="button" onClick={() => copyText(member.followup_body, member.participant_id)} data-testid={`am5-copy-followup-${member.participant_id}`}><Copy size={15} /> {copied === member.participant_id ? "Email Copied" : "COPY EMAIL"}</button>
                        <button type="button" className="button button-outline" onClick={() => setEditFollowup({ participant_id: member.participant_id, subject: member.followup_subject, body: member.followup_body })} data-testid={`am5-edit-followup-${member.participant_id}`}>EDIT</button>
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </section>

          <ExecutionResourceCard
            title="Case for Support"
            description="Your organization's external fundraising document. It helps a potential supporter understand the need, who you serve, the work, the funding priority, what support makes possible and how to take the next step. Once approved, it has one secure read-only link Board Members can share with potential supporters."
            resource={data.case}
            basePath="/activation/case-for-support"
            testPrefix="am5-case"
            generateLabel="GENERATE OUR CASE FOR SUPPORT"
            load={load}
          >
            {data.case?.share_link && (
              <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 14, marginTop: 12 }} data-testid="am5-case-share">
                <p style={{ margin: 0 }}><strong>Secure share link (approved version):</strong></p>
                <p style={{ margin: "6px 0", wordBreak: "break-all" }} data-testid="am5-case-share-link">{data.case.share_link}</p>
                <button type="button" className="button button-outline" onClick={() => copyText(data.case.share_link, "case-share")} data-testid="am5-case-copy-link"><Copy size={15} /> {copied === "case-share" ? "Link Copied" : "COPY SHARE LINK"}</button>
                {!data.case.share_is_current && <p style={{ marginTop: 8 }} data-testid="am5-case-share-outdated">This link still shows the previously approved version. Approve your edited draft to update what supporters see.</p>}
              </div>
            )}
          </ExecutionResourceCard>

          <ExecutionResourceCard
            title="Board Fundraising Communication System"
            description="The Board's reusable three-stage outreach sequence — Introduce Impact → Case for Support → Follow Up & Ask — with a complete email and call script at every stage for each major funding audience in your adopted strategy. This is internal Board execution material, not a prospect-facing document."
            resource={data.communication_system}
            basePath="/activation/communication-system"
            testPrefix="am5-comm"
            generateLabel="GENERATE OUR COMMUNICATION SYSTEM"
            load={load}
            disabled={!(data.case?.status === "Approved" && data.case?.share_link)}
            disabledNote="Approve your Case for Support first — the Stage 2 communications include its real secure link."
          />

          <section className="member-card" data-testid="am5-toolkit-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
              <h2 style={{ margin: 0 }}>{activationModule5Text.boardFundraisingExecutionToolkit}</h2>
              <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid="am5-toolkit-status">{toolkit.status === "NONE" ? "NOT GENERATED" : toolkit.status.toUpperCase()}</span>
            </div>
            <p style={{ marginTop: 10 }}>{activationModule5Text.oneOrganizationLevelSetOf}</p>
            {toolkit.status === "Failed" && <p className="submit-error">{activationModule5Text.generationFailedPleaseTryAgain2}</p>}
            {toolkit.status === "Generating" || generating ? (
              <p data-testid="am5-generating">{activationModule5Text.generatingYourBoardFundraisingExecution}</p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
                <button type="button" className="button" onClick={generate} data-testid="am5-generate-button">{toolkit.display_text ? "REGENERATE" : "GENERATE MY BOARD FUNDRAISING EXECUTION TOOLKIT"}</button>
                {toolkit.display_text && (
                  <>
                    <button type="button" className="button button-outline" onClick={() => { setEditText(toolkit.display_text); setShowEdit(true); }} data-testid="am5-edit-button">EDIT</button>
                    {toolkit.status !== "Approved" && <button type="button" className="button" onClick={approve} data-testid="am5-approve-button">APPROVE</button>}
                    <a className="button button-outline" href={`${API}/activation/toolkit/pdf`} target="_blank" rel="noreferrer" data-testid="am5-pdf-button"><Download size={15} /> DOWNLOAD PDF</a>
                  </>
                )}
              </div>
            )}
            {toolkit.display_text && toolkit.status !== "Generating" && (
              <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 14, maxHeight: 420, overflowY: "auto" }} data-testid="am5-toolkit-text">{toolkit.display_text}</div>
            )}
          </section>

          {toolkit.status === "Approved" && (
            <section className="member-card" style={{ textAlign: "center" }} data-testid="am5-completion">
              <h2>{activationM5Text.h_yourBoardIsReadyTo}</h2>
              <p>{activationModule5Text.yourBoardHelpedBuildThe}</p>
              <p>{activationModule5Text.theNextStepIsTo}</p>
            </section>
          )}
        </>
      )}

      {showEdit && (
        <Modal onClose={() => setShowEdit(false)} testId="am5-edit-modal">
          <h2>{activationM5Text.h_editExecutionToolkit}</h2>
          <textarea rows={22} style={{ width: "100%" }} value={editText} onChange={(e) => setEditText(e.target.value)} data-testid="am5-edit-text" />
          <button type="button" className="button" onClick={saveEdit} data-testid="am5-save-button">SAVE</button>
        </Modal>
      )}

      {editFollowup && (
        <Modal onClose={() => setEditFollowup(null)} testId="am5-followup-modal">
          <h2>{activationM5Text.h_editFollowUpEmail}</h2>
          <label className="field"><span>Subject</span><input value={editFollowup.subject} onChange={(e) => setEditFollowup({ ...editFollowup, subject: e.target.value })} data-testid="am5-followup-edit-subject" /></label>
          <label className="field"><span>Email</span><textarea rows={16} value={editFollowup.body} onChange={(e) => setEditFollowup({ ...editFollowup, body: e.target.value })} data-testid="am5-followup-edit-body" /></label>
          <button type="button" className="button" onClick={saveFollowup} data-testid="am5-followup-save-button">SAVE</button>
        </Modal>
      )}
    </div>
  );
}
