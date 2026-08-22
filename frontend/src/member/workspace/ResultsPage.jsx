import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, ExternalLink, Mail, UserCheck, X } from "lucide-react";
import axios from "axios";
import { memberApi } from "../api";
import { useMemberAuth } from "../MemberAuthContext";
import { MemberShell } from "../MemberShell";
import { MaterialCard, downloadMaterialPdf } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";
import { useBranding } from "./ApplicantModules";
import { myBoardText, resultsPageText } from "../../content/appContent";

const CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard";
const PUBLIC_API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PortfolioActions = ({ application, portfolio, refresh }) => {
  const [email, setEmail] = useState(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const token = portfolio?.share_token;
  const applicationId = application.application_id;
  if (portfolio?.status !== "Approved" || !token) return null;
  const sent = portfolio.sent_at && portfolio.sent_version === portfolio.current_version;

  const downloadPdf = async () => {
    try {
      const response = await axios.get(`${PUBLIC_API}/portfolio/${token}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url; link.download = `Board-Member-Portfolio-${(application.profile_snapshot?.full_name || "Member").replace(/[^a-zA-Z0-9]+/g, "-")}.pdf`; link.click();
      URL.revokeObjectURL(url);
    } catch { setMessage("The PDF could not be downloaded."); }
  };

  const prepare = async () => {
    setBusy(true); setMessage("");
    try {
      const response = await memberApi.get(`/workspace/applications/${applicationId}/portfolio-email`);
      setEmail(response.data); setSubject(response.data.subject); setBody(response.data.body);
    } catch (err) { setMessage(err.response?.data?.detail || "The email could not be prepared."); }
    setBusy(false);
  };

  const send = async () => {
    setBusy(true); setMessage("");
    try {
      await memberApi.post(`/workspace/applications/${applicationId}/portfolio-email`, { subject, body });
      setEmail(null); setMessage("");
      await refresh();
    } catch (err) { setMessage(err.response?.data?.detail || "The email could not be sent."); }
    setBusy(false);
  };

  return (
    <div style={{ marginTop: 10 }} data-testid={`portfolio-actions-${applicationId}`}>
      <div className="material-actions">
        <a className="button button-back" href={`/portfolio/${token}`} target="_blank" rel="noreferrer" data-testid={`portfolio-view-online-${applicationId}`}><ExternalLink size={14} /> View Online</a>
        <button className="button button-back" onClick={downloadPdf} data-testid={`portfolio-pdf-${applicationId}`}><Download size={14} /> Download PDF</button>
        <button className="button button-back" disabled={busy} onClick={prepare} data-testid={`portfolio-prepare-email-${applicationId}`}><Mail size={14} /> Prepare Portfolio Email</button>
        {sent && <span className="blog-status-badge published" data-testid={`portfolio-sent-${applicationId}`}>Sent {new Date(portfolio.sent_at).toLocaleString()}</span>}
      </div>
      {message && <p className="submit-error" data-testid={`portfolio-actions-error-${applicationId}`}>{message}</p>}
      {email && (
        <div className="member-card" style={{ marginTop: 12 }} data-testid={`portfolio-email-modal-${applicationId}`}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h4 style={{ margin: 0 }}>Portfolio Email</h4>
            <button className="link-button" onClick={() => setEmail(null)} data-testid={`portfolio-email-close-${applicationId}`}><X size={16} /></button>
          </div>
          <p className="material-meta">To: {email.to_name} &lt;{email.to_email || "no email on record"}&gt;</p>
          <label className="field" style={{ display: "block", marginBottom: 10 }}>
            <span>Subject</span>
            <input value={subject} onChange={(event) => setSubject(event.target.value)} style={{ width: "100%" }} data-testid={`portfolio-email-subject-${applicationId}`} />
          </label>
          <label className="field" style={{ display: "block", marginBottom: 10 }}>
            <span>Message</span>
            <textarea rows="12" value={body} onChange={(event) => setBody(event.target.value)} style={{ width: "100%" }} data-testid={`portfolio-email-body-${applicationId}`} />
          </label>
          <p className="material-meta" data-testid={`portfolio-email-link-${applicationId}`}>Secure Portfolio link (inserted automatically): {email.portfolio_link}</p>
          <button className="button" disabled={busy} onClick={send} data-testid={`portfolio-email-send-${applicationId}`}>{busy ? "Sending…" : "SEND PORTFOLIO"}</button>
        </div>
      )}
    </div>
  );
};

const BoardMemberResultCard = ({ application, branding, onChanged }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const snapshot = application.profile_snapshot || {};
  const portfolio = byType.board_member_portfolio;
  const engagement = byType.board_member_engagement_guide;
  return (
    <div className="board-member-result" data-testid={`board-member-${application.application_id}`}>
      <h3><UserCheck size={17} /> {snapshot.full_name || application.applicant_email} <span className="blog-status-badge published">Board Member</span></h3>
      <p className="material-meta">{[snapshot.profession, snapshot.employer, snapshot.location].filter(Boolean).join(" · ")}{application.board_role ? ` · Role: ${application.board_role}` : ""}{application.formal_appointment_date ? ` · Joined ${new Date(application.formal_appointment_date).toLocaleDateString()}` : ""}</p>
      <MaterialCard type="board_member_engagement_guide" title={resultsPageText.boardMemberEngagementGuide} buttonLabel="Generate Engagement Guide"
        description="A one-page internal guide for you: where this member's expertise creates the most value, how to engage them, strong early responsibilities, relationships and fundraising, leadership alignment and their first 90 days. Built only from their application, CV and Board Member Profile — never from confidential references or background checks. This stays internal and is never sent to the member."
        applicationId={application.application_id} material={engagement} refresh={refresh} approvable
        extraActions={engagement ? (
          <button className="button button-back" onClick={() => downloadMaterialPdf(engagement)} data-testid={`engagement-pdf-${application.application_id}`}><Download size={14} /> Download Branded PDF</button>
        ) : null} />
      <MaterialCard type="board_member_portfolio" title={resultsPageText.boardMemberPortfolio} buttonLabel="Generate Board Member Portfolio"
        description="A professional portfolio built from this member's application, CV, profile form, skills, networks and board role. Confidential references, internal notes and internal evaluation material are never included. Generate it, edit anything you want changed, approve it, then share it with the member using the secure link, PDF or portfolio email."
        applicationId={application.application_id} material={portfolio} refresh={refresh} approvable />
      <PortfolioActions application={application} portfolio={portfolio} refresh={refresh} />
    </div>
  );
};

export default function RecruitmentResultsPage() {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [branding] = useBranding();
  const [applications, setApplications] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    memberApi.get("/workspace/applications").then((response) => setApplications(response.data.applications)).catch(() => setError("We could not load your recruitment results. Please refresh the page or try again shortly."));
  }, []);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login"); return; }
    load();
  }, [loading, member, navigate, load]);

  const list = applications || [];
  const joined = list.filter((a) => a.final_outcome === "Joined Board" || a.status === "Selected");
  const notSelected = list.filter((a) => !joined.includes(a) && (["Not Selected", "Not Moving Forward", "Withdrawn"].includes(a.status) || a.emails_sent?.after_interview_rejection || a.emails_sent?.general_rejection_email));
  const inProgress = list.filter((a) => !joined.includes(a) && !notSelected.includes(a));
  const interviewed = list.filter((a) => a.interview_completed).length;

  return (
    <MemberShell>
      <main className="member-page recruitment-results-page" data-testid="recruitment-results-page">
        <Link className="member-back-link" to="/app/recruitment/self-guided"><ArrowLeft size={15} />{resultsPageText.boardRecruitmentSelfGuidedSystem}</Link>
        <header className="member-page-heading">
          <p className="eyebrow">Your board</p>
          <h1>{myBoardText.h_myBoard}</h1>
        </header>
        {error && (
          <section className="workspace-panel" data-testid="results-error-state">
            <h2>{myBoardText.h_weCouldNotLoadYour}</h2>
            <p>{error}</p>
            <button className="button" onClick={() => { setError(""); load(); }} data-testid="results-retry-button">Try Again</button>
          </section>
        )}
        {!error && applications === null && <p className="workspace-note">{myBoardText.n_loadingYourRecruitmentResults}</p>}
        {!error && applications !== null && list.length === 0 && (
          <section className="workspace-panel" data-testid="results-empty-state">
            <h2>{myBoardText.h_yourRecruitmentResults}</h2>
            <p>{resultsPageText.yourRecruitmentResultsWillAppear}</p>
            <Link className="button" to="/app/recruitment/self-guided/module/3">{resultsPageText.goToYourRecruitmentCampaign}</Link>
          </section>
        )}
        {!error && applications !== null && list.length > 0 && (
          <>
            <section className="workspace-panel" data-testid="results-summary">
              <h2>{myBoardText.h_recruitmentSummary}</h2>
              <div className="results-summary-grid">
                {[["Applications Received", list.length, "results-count-applications"], ["Interviewed", interviewed, "results-count-interviewed"], ["Joined the Board", joined.length, "results-count-joined"], ["Not Selected", notSelected.length, "results-count-not-selected"], ["Still In Progress", inProgress.length, "results-count-in-progress"]].map(([label, value, testId]) => (
                  <div className="results-stat" key={label} data-testid={testId}><strong>{value}</strong><span>{label}</span></div>
                ))}
              </div>
            </section>
            <section className="workspace-panel" data-testid="results-joined-section">
              <h2>{myBoardText.h_myBoard}</h2>
              {joined.length === 0 && <p className="workspace-note">{myBoardText.n_boardMembersAppearHereAs}</p>}
              {joined.map((application) => <BoardMemberResultCard application={application} branding={branding} onChanged={load} key={application.application_id} />)}
            </section>
            {inProgress.length > 0 && (
              <section className="workspace-panel" data-testid="results-in-progress-section">
                <h2>{myBoardText.h_stillInProgress}</h2>
                <ul className="readiness-list">{inProgress.map((a) => <li key={a.application_id}>{a.profile_snapshot?.full_name || a.applicant_email} — {a.status}</li>)}</ul>
              </section>
            )}
            {notSelected.length > 0 && (
              <section className="workspace-panel" data-testid="results-not-selected-section">
                <h2>{myBoardText.h_notSelected}</h2>
                <ul className="readiness-list">{notSelected.map((a) => <li key={a.application_id}>{a.profile_snapshot?.full_name || a.applicant_email} — {a.status}</li>)}</ul>
              </section>
            )}
          </>
        )}
        <section className="workspace-panel results-support-panel" data-testid="results-support-cta">
          <h2>{myBoardText.h_needHelpMovingForward}</h2>
          <p>{resultsPageText.getHelpReviewingYourNew}</p>
          <a className="button" href={CALENDLY_URL} target="_blank" rel="noreferrer" data-testid="book-call-rooney-button">{resultsPageText.bookACallWithRooney}<ExternalLink size={15} /></a>
        </section>
      </main>
    </MemberShell>
  );
}
