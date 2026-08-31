import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Download, FileText, Mail, RefreshCw, Users, X } from "lucide-react";
import { memberApi } from "./api";
import { reactivationContent, reactivationStep5Text } from "../content/appContent";

const D = reactivationContent.dashboard;

const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;
const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const Modal = ({ children, onClose, testId, wide }) => (
  <div style={overlayStyle} data-testid={testId}>
    <div style={{ background: "#fff", maxWidth: wide ? 860 : 700, width: "100%", padding: 28, borderRadius: 8, position: "relative" }}>
      <button type="button" onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testId}-close`}><X size={20} /></button>
      {children}
    </div>
  </div>
);

const PortfolioWorkflow = ({ row, reload }) => {
  const id = row.member_record_id;
  const [busy, setBusy] = useState("");
  const [material, setMaterial] = useState(null);
  const [mode, setMode] = useState("");
  const [draftText, setDraftText] = useState("");
  const [emailDraft, setEmailDraft] = useState(null);
  const status = material
    ? (material.status === "Approved" ? (material.sent_at ? "SENT" : "APPROVED") : "DRAFT")
    : row.portfolio ? row.portfolio.status.toUpperCase() : "NOT GENERATED";
  const materialId = material?.material_id || row.portfolio?.material_id;

  const loadMaterial = useCallback(async () => {
    if (!materialId) return null;
    const res = await memberApi.get(`/reactivation/materials/${materialId}`);
    const merged = { ...res.data, share_token: row.portfolio?.share_token, sent_at: row.portfolio?.status === "SENT" ? row.portfolio.sent_at : "" };
    setMaterial(merged);
    return merged;
  }, [materialId, row.portfolio]);

  const generate = async () => {
    setBusy("generate");
    try {
      const res = await memberApi.post(`/reactivation/board-members/${id}/portfolio`);
      setMaterial(res.data);
      reload();
    } catch (err) {
      window.alert(err.response?.data?.detail || "Generation failed. Please try again.");
    }
    setBusy("");
  };

  const openEdit = async () => { const m = material?.display_text ? material : await loadMaterial(); if (m) { setDraftText(m.display_text); setMode("edit"); } };
  const openView = async () => { const m = material?.display_text ? material : await loadMaterial(); if (m) setMode("view"); };

  const saveEdit = async () => {
    setBusy("save");
    await memberApi.put(`/reactivation/materials/${materialId}`, { display_text: draftText });
    setMaterial((m) => ({ ...m, display_text: draftText, status: "Draft", sent_at: "" }));
    setMode("");
    setBusy("");
    reload();
  };

  const approve = async () => {
    setBusy("approve");
    await memberApi.post(`/reactivation/materials/${materialId}/approve-portfolio`);
    setBusy("");
    reload();
  };

  const download = async () => {
    const token = row.portfolio?.share_token || material?.share_token;
    if (token) { window.open(`${API_BASE}/portfolio/${token}/pdf`, "_blank"); return; }
    const res = await memberApi.get(`/reactivation/materials/${materialId}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `Board-Member-Portfolio-${row.name.replace(/[^a-zA-Z0-9]+/g, "-")}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const prepareEmail = async () => {
    try {
      const res = await memberApi.get(`/reactivation/board-members/${id}/portfolio-email`);
      setEmailDraft(res.data);
      setMode("email");
    } catch (err) {
      window.alert(err.response?.data?.detail || "Approve this Portfolio before preparing the email.");
    }
  };

  const sendEmail = async () => {
    setBusy("send");
    try {
      await memberApi.post(`/reactivation/board-members/${id}/portfolio-email`, { subject: emailDraft.subject, body: emailDraft.body });
      setMode("");
      reload();
    } catch (err) {
      window.alert(err.response?.data?.detail || "The email could not be sent.");
    }
    setBusy("");
  };

  return (
    <div style={{ marginTop: 12 }}>
      <p className="eyebrow" data-testid={`myboard-portfolio-status-${id}`}>Portfolio: {status}{row.portfolio?.sent_at ? ` · sent ${new Date(row.portfolio.sent_at).toLocaleString()}` : ""}</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <button type="button" className="button" onClick={generate} disabled={busy === "generate"} data-testid={`myboard-generate-portfolio-${id}`}>
          {busy === "generate" ? "Generating…" : status === "NOT GENERATED" ? <><FileText size={15} />{reactivationStep5Text.generateBoardMemberPortfolio}</> : <><RefreshCw size={15} /> REGENERATE</>}
        </button>
        {status !== "NOT GENERATED" && (
          <>
            <button type="button" className="button button-outline" onClick={openEdit} data-testid={`myboard-edit-${id}`}>EDIT</button>
            <button type="button" className="button button-outline" onClick={approve} disabled={busy === "approve" || status !== "DRAFT"} data-testid={`myboard-approve-${id}`}>{status === "DRAFT" ? "APPROVE PORTFOLIO" : "APPROVED"}</button>
            {row.portfolio?.share_token ? (
              <a className="button button-outline" href={`/portfolio/${row.portfolio.share_token}`} target="_blank" rel="noreferrer" data-testid={`myboard-view-online-${id}`}>VIEW ONLINE</a>
            ) : (
              <button type="button" className="button button-outline" onClick={openView} data-testid={`myboard-view-draft-${id}`}>VIEW DRAFT</button>
            )}
            <button type="button" className="button button-outline" onClick={download} data-testid={`myboard-download-${id}`}><Download size={15} /> DOWNLOAD PDF</button>
            {status !== "DRAFT" && (
              <button type="button" className="button" onClick={prepareEmail} data-testid={`myboard-prepare-email-${id}`}><Mail size={15} /> PREPARE PORTFOLIO EMAIL</button>
            )}
          </>
        )}
      </div>
      {mode === "view" && material && (
        <Modal onClose={() => setMode("")} testId={`myboard-view-modal-${id}`} wide>
          <h2>{material.title} — {row.name}</h2>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 18, maxHeight: 520, overflowY: "auto" }}>{material.display_text}</div>
        </Modal>
      )}
      {mode === "edit" && (
        <Modal onClose={() => setMode("")} testId={`myboard-edit-modal-${id}`} wide>
          <h2>Edit Portfolio</h2>
          <textarea rows={22} value={draftText} onChange={(e) => setDraftText(e.target.value)} style={{ width: "100%" }} data-testid={`myboard-edit-text-${id}`} />
          <button type="button" className="button" onClick={saveEdit} disabled={busy === "save"} data-testid={`myboard-save-edit-${id}`}>{busy === "save" ? "Saving…" : "SAVE"}</button>
        </Modal>
      )}
      {mode === "email" && emailDraft && (
        <Modal onClose={() => setMode("")} testId={`myboard-email-modal-${id}`} wide>
          <h2>Review Portfolio Email</h2>
          <p><strong>To:</strong> {emailDraft.to_name} &lt;{emailDraft.to_email}&gt;</p>
          <label className="field"><span>Subject</span><input value={emailDraft.subject} onChange={(e) => setEmailDraft({ ...emailDraft, subject: e.target.value })} data-testid={`myboard-email-subject-${id}`} /></label>
          <label className="field"><span>Email Body</span><textarea rows={12} value={emailDraft.body} onChange={(e) => setEmailDraft({ ...emailDraft, body: e.target.value })} data-testid={`myboard-email-body-${id}`} /></label>
          <p><strong>{reactivationStep5Text.portfolioLinkInsertedAutomatically}</strong> <span style={{ wordBreak: "break-all" }} data-testid={`myboard-email-link-${id}`}>{emailDraft.portfolio_link}</span></p>
          <button type="button" className="button" onClick={sendEmail} disabled={busy === "send"} data-testid={`myboard-send-email-${id}`}>{busy === "send" ? "Sending…" : "SEND PORTFOLIO"}</button>
        </Modal>
      )}
    </div>
  );
};

const OutcomeEmailWorkflow = ({ row, label, reload }) => {
  const id = row.member_record_id;
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState(null);
  const [mode, setMode] = useState("");
  const [draft, setDraft] = useState("");
  const [copied, setCopied] = useState(false);
  const exists = Boolean(row.outcome_email || email);

  const generate = async () => {
    setBusy(true);
    try {
      const res = await memberApi.post(`/reactivation/board-members/${id}/outcome-email`);
      setEmail(res.data);
      setMode("view");
      reload();
    } catch (err) { window.alert(err.response?.data?.detail || "Generation failed. Please try again."); }
    setBusy(false);
  };
  const open = async () => {
    const res = email || (await memberApi.get(`/reactivation/board-members/${id}/outcome-email`)).data;
    setEmail(res);
    setMode("view");
  };
  const saveEdit = async () => {
    await memberApi.put(`/reactivation/materials/${email.material_id}`, { display_text: draft });
    setEmail({ ...email, display_text: draft });
    setMode("view");
    reload();
  };
  const copy = async () => {
    try { await navigator.clipboard.writeText(email.display_text); } catch { window.prompt("Copy:", email.display_text); }
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div style={{ marginTop: 12 }} data-testid={`outcome-email-${id}`}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <button type="button" className="button" onClick={generate} disabled={busy} data-testid={`outcome-email-generate-${id}`}>
          <Mail size={15} /> {busy ? "Generating…" : exists ? D.regenerateEmailButton : label}
        </button>
        {exists && <button type="button" className="button button-outline" onClick={open} data-testid={`outcome-email-view-${id}`}>{D.viewEmailButton}</button>}
      </div>
      {exists && <p className="eyebrow" style={{ marginTop: 6 }}>{D.emailReadyLabel}</p>}
      {mode && email && (
        <Modal onClose={() => setMode("")} testId={`outcome-email-modal-${id}`} wide>
          <h2>{row.name} — Prepared Email</h2>
          <p><strong>To:</strong> {email.to_name} &lt;{email.to_email}&gt;</p>
          {mode === "view" ? (
            <>
              <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 16, borderRadius: 6, maxHeight: 480, overflowY: "auto" }} data-testid={`outcome-email-text-${id}`}>{email.display_text}</div>
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <button type="button" className="button" onClick={copy} data-testid={`outcome-email-copy-${id}`}><Copy size={15} /> {copied ? "Copied!" : D.copyEmailButton}</button>
                <button type="button" className="button button-outline" onClick={() => { setDraft(email.display_text); setMode("edit"); }} data-testid={`outcome-email-edit-${id}`}>EDIT</button>
              </div>
            </>
          ) : (
            <>
              <textarea rows={18} value={draft} onChange={(e) => setDraft(e.target.value)} style={{ width: "100%" }} data-testid={`outcome-email-edit-text-${id}`} />
              <button type="button" className="button" onClick={saveEdit} data-testid={`outcome-email-save-${id}`}>SAVE</button>
            </>
          )}
        </Modal>
      )}
    </div>
  );
};

const MemberCard = ({ row, withPortfolio, reload, badge, extra = null }) => (
  <article className="member-card" data-testid={`myboard-member-${row.member_record_id}`}>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <div>
        <h3 style={{ margin: 0 }}>{row.name}</h3>
        <p style={{ margin: "4px 0 0" }}>
          {row.role || "Board Member"}
          {row.professional_role && <> · {row.professional_role}{row.employer ? `, ${row.employer}` : ""}</>}
        </p>
      </div>
      <span className="eyebrow" style={{ alignSelf: "flex-start", padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }}>{badge}</span>
    </div>
    {row.contribution_interests?.length > 0 && <p style={{ margin: "10px 0 0" }}><strong>Primary Contribution:</strong> {row.contribution_interests.slice(0, 3).join(", ")}</p>}
    {row.expertise?.length > 0 && <p style={{ margin: "6px 0 0" }}><strong>Expertise:</strong> {row.expertise.slice(0, 6).join(", ")}</p>}
    {withPortfolio && <PortfolioWorkflow row={row} reload={reload} />}
    {extra}
  </article>
);

export default function ReactivationStep5() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    memberApi.get("/reactivation/my-board").then((res) => setData(res.data)).catch(() => setError("We could not load My Board."));
  }, []);
  useEffect(load, [load]);

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">Loading your Board…</p>;
  const { groups, summary } = data;
  const processed = summary.active + summary.advisory + summary.support + summary.stepping_down;

  return (
    <div data-testid="reactivation-myboard">
      <section className="member-card" data-testid="myboard-intro">
        <h2><Users size={20} aria-hidden="true" /> Your Reactivated Board</h2>
        <p>{reactivationStep5Text.youNowHaveAClearer}</p>
        <p>{reactivationStep5Text.thisIsTheBoardYou}</p>
      </section>

      <section className="member-card" data-testid="myboard-summary">
        <h2 style={{ marginTop: 0 }}>{D.heading}</h2>
        {D.intro.map((p) => <p key={p}>{p}</p>)}
        {(() => {
          const rows = Object.values(groups).flat();
          const stats = [
            [D.pipelineLabels.responded, rows.filter((r) => r.status === "COMPLETED").length],
            [D.pipelineLabels.analyzed, rows.filter((r) => r.analyzed).length],
            [D.pipelineLabels.conversations, rows.filter((r) => r.conversation_outcome && (r.conversation_conclusion || "").trim()).length],
            [D.pipelineLabels.steppedUp, summary.active],
            [D.pipelineLabels.advisory, summary.advisory],
            [D.pipelineLabels.steppedDown, summary.stepping_down],
            [D.pipelineLabels.portfolios, summary.portfolios_approved],
          ];
          return (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10, marginTop: 12 }} data-testid="myboard-pipeline">
              {stats.map(([label, count]) => (
                <div key={label} style={{ border: "1px solid #ddd", borderRadius: 8, padding: "12px 10px", textAlign: "center", background: count > 0 ? "#fafaf6" : "#fff" }} data-testid={`myboard-stat-${label.replace(/\s+/g, "-").toLowerCase()}`}>
                  <div style={{ fontSize: "1.5rem", fontWeight: 800 }}>{count}</div>
                  <div className="eyebrow" style={{ margin: 0 }}>{label}</div>
                </div>
              ))}
            </div>
          );
        })()}
        <p data-testid="myboard-summary-counts" style={{ marginTop: 12 }}>
          <strong>{summary.reviewed}</strong> Board Member{summary.reviewed === 1 ? "" : "s"} Reviewed
          {summary.active > 0 && <> · <strong>{summary.active}</strong> Continuing Active</>}
          {summary.advisory > 0 && <> · <strong>{summary.advisory}</strong> Advisory</>}
          {summary.support > 0 && <> · <strong>{summary.support}</strong> Support Role</>}
          {summary.stepping_down > 0 && <> · <strong>{summary.stepping_down}</strong> Stepping Down</>}
          {summary.follow_up > 0 && <> · <strong>{summary.follow_up}</strong> Follow-Up Needed</>}
          {summary.waiting > 0 && <> · <strong>{summary.waiting}</strong>{reactivationStep5Text.waitingForRecommitmentForm}</>}
          {summary.portfolios_approved > 0 && <> · <strong>{summary.portfolios_approved}</strong> Portfolio{summary.portfolios_approved === 1 ? "" : "s"} Approved</>}
        </p>
      </section>

      {processed > 0 && (
        <section className="member-card" data-testid="myboard-completion">
          <h2>{reactivationStep5Text.youHaveReactivatedYourBoard}</h2>
          <p>{reactivationStep5Text.youNowKnowWhoIs}</p>
          <p>{reactivationStep5Text.yourNextJobIsTo}</p>
        </section>
      )}

      {groups.active.length > 0 && (
        <section data-testid="myboard-active-section">
          <h2 style={{ margin: "24px 0 10px" }}>Active Board Members</h2>
          {groups.active.map((row) => <MemberCard key={row.member_record_id} row={row} withPortfolio reload={load} badge="ACTIVE — RECOMMITTED"
            extra={<OutcomeEmailWorkflow row={row} label={D.recommitmentEmailButton} reload={load} />} />)}
        </section>
      )}
      {groups.advisory.length > 0 && (
        <section data-testid="myboard-advisory-section">
          <h2 style={{ margin: "24px 0 10px" }}>{reactivationStep5Text.advisoryBoardAdvisoryMembers}</h2>
          {groups.advisory.map((row) => <MemberCard key={row.member_record_id} row={row} withPortfolio reload={load} badge="ADVISORY"
            extra={<OutcomeEmailWorkflow row={row} label={D.advisoryEmailButton} reload={load} />} />)}
        </section>
      )}
      {groups.support.length > 0 && (
        <section data-testid="myboard-support-section">
          <h2 style={{ margin: "24px 0 10px" }}>Support Roles</h2>
          {groups.support.map((row) => <MemberCard key={row.member_record_id} row={row} withPortfolio reload={load} badge="SUPPORT ROLE" />)}
        </section>
      )}
      {groups.stepping_down.length > 0 && (
        <section data-testid="myboard-transitions-section">
          <h2 style={{ margin: "24px 0 10px" }}>Board Transitions</h2>
          {groups.stepping_down.map((row) => <MemberCard key={row.member_record_id} row={row} withPortfolio={false} reload={load} badge="STEPPING DOWN"
            extra={<OutcomeEmailWorkflow row={row} label={D.followUpEmailButton} reload={load} />} />)}
        </section>
      )}
      {groups.follow_up.length > 0 && (
        <section data-testid="myboard-followup-section">
          <h2 style={{ margin: "24px 0 10px" }}>{reactivationStep5Text.followUpStillNeeded}</h2>
          {groups.follow_up.map((row) => <MemberCard key={row.member_record_id} row={row} withPortfolio={false} reload={load} badge="FOLLOW-UP NEEDED" />)}
          <Link className="button button-outline" to="/app/reactivation/self-guided/module/4" data-testid="myboard-return-step3">{reactivationStep5Text.returnToStep4Have}</Link>
        </section>
      )}
      {groups.waiting.length > 0 && (
        <section data-testid="myboard-waiting-section">
          <h2 style={{ margin: "24px 0 10px" }}>{reactivationStep5Text.waitingForRecommitmentForm2}</h2>
          {groups.waiting.map((row) => <MemberCard key={row.member_record_id} row={row} withPortfolio={false} reload={load} badge="WAITING" />)}
        </section>
      )}
      {summary.reviewed === 0 && (
        <section className="member-card" data-testid="myboard-empty">
          <p>{reactivationStep5Text.noReactivatedBoardMembersTo}</p>
          <Link className="button" to="/app/reactivation/self-guided/module/2">{reactivationStep5Text.goToStep2}</Link>
        </section>
      )}

      <section style={{ marginTop: 34 }} data-testid="myboard-crosssell">
        <div className="ar-offer-grid">
          <article className="ar-offer-card" data-testid="myboard-recruit-cta">
            <h3>{reactivationStep5Text.stillMissingTheRightPeople}</h3>
            <p className="ar-offer-copy">{reactivationStep5Text.reactivatingYourCurrentBoardShows}</p>
            <Link className="button" to="/recruit-your-board-yourself" data-testid="myboard-recruit-button">{reactivationStep5Text.recruitNewBoardMembers}</Link>
          </article>
          <article className="ar-offer-card" data-testid="myboard-activate-cta">
            <h3>{reactivationStep5Text.yourBoardIsBackAt}</h3>
            <p className="ar-offer-copy">{reactivationStep5Text.theNextStepIsTo}</p>
            <Link className="button" to="/activate-your-board-yourself" data-testid="myboard-activate-button">ACTIVATE MY BOARD</Link>
          </article>
        </div>
      </section>
    </div>
  );
}
