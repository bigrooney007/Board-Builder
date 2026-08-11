import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, ExternalLink, UserCheck } from "lucide-react";
import { memberApi } from "../api";
import { useMemberAuth } from "../MemberAuthContext";
import { MemberShell } from "../MemberShell";
import { MaterialCard, SendMaterialButton, currentVersion, printBranded } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";
import { useBranding } from "./ApplicantModules";

const CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard";

const BoardMemberResultCard = ({ application, branding, onChanged }) => {
  const { byType, refresh } = useMaterials(application.application_id);
  const snapshot = application.profile_snapshot || {};
  const portfolio = byType.board_member_portfolio;
  const version = currentVersion(portfolio);
  return (
    <div className="board-member-result" data-testid={`board-member-${application.application_id}`}>
      <h3><UserCheck size={17} /> {snapshot.full_name || application.applicant_email} <span className="blog-status-badge published">Board Member</span></h3>
      <p className="material-meta">{[snapshot.profession, snapshot.employer].filter(Boolean).join(" · ")}{application.board_role ? ` · Role: ${application.board_role}` : ""}{application.formal_appointment_date ? ` · Appointed ${new Date(application.formal_appointment_date).toLocaleDateString()}` : ""}</p>
      <MaterialCard type="board_member_portfolio" title="Board Member Portfolio" buttonLabel="Generate Board Member Portfolio"
        description="A professional portfolio built from this member's application, CV, profile form, skills, networks and board role. Confidential references, internal notes and internal evaluation material are never included."
        applicationId={application.application_id} material={portfolio} refresh={refresh} approvable
        extraActions={portfolio?.status === "Approved" && version ? (
          <button className="button button-back" onClick={() => printBranded("Board Member Portfolio", version.display_text, branding)} data-testid={`portfolio-pdf-${application.application_id}`}><Download size={14} /> Create Portfolio PDF</button>
        ) : null} />
      {portfolio?.status === "Approved" && (
        <MaterialCard type="portfolio_email" title="Email to Board Member" buttonLabel="Generate Portfolio Email"
          description="A short professional email sharing the completed portfolio with this board member."
          applicationId={application.application_id} material={byType.portfolio_email} refresh={refresh} approvable
          extraActions={byType.portfolio_email?.status === "Approved" ? (
            <SendMaterialButton type="portfolio_email" applicationId={application.application_id}
              label={application.emails_sent?.portfolio_email ? "Send Updated" : `Send to ${application.applicant_email || "member"}`}
              sentAt={application.emails_sent?.portfolio_email} onSent={onChanged} />
          ) : null} />
      )}
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
        <Link className="member-back-link" to="/app/recruitment/self-guided"><ArrowLeft size={15} /> Board Recruitment — $497 Self-Guided System</Link>
        <header className="member-page-heading">
          <p className="eyebrow">Recruitment complete</p>
          <h1>Your Recruitment Results</h1>
        </header>
        {error && (
          <section className="workspace-panel" data-testid="results-error-state">
            <h2>We Could Not Load Your Results</h2>
            <p>{error}</p>
            <button className="button" onClick={() => { setError(""); load(); }} data-testid="results-retry-button">Try Again</button>
          </section>
        )}
        {!error && applications === null && <p className="workspace-note">Loading your recruitment results…</p>}
        {!error && applications !== null && list.length === 0 && (
          <section className="workspace-panel" data-testid="results-empty-state">
            <h2>Your Recruitment Results</h2>
            <p>Your recruitment results will appear here as applicants move through the recruitment process.</p>
            <Link className="button" to="/app/recruitment/self-guided/module/3">Go to Your Recruitment Campaign</Link>
          </section>
        )}
        {!error && applications !== null && list.length > 0 && (
          <>
            <section className="workspace-panel" data-testid="results-summary">
              <h2>Recruitment Summary</h2>
              <div className="results-summary-grid">
                {[["Applications Received", list.length, "results-count-applications"], ["Interviewed", interviewed, "results-count-interviewed"], ["Joined the Board", joined.length, "results-count-joined"], ["Not Selected", notSelected.length, "results-count-not-selected"], ["Still In Progress", inProgress.length, "results-count-in-progress"]].map(([label, value, testId]) => (
                  <div className="results-stat" key={label} data-testid={testId}><strong>{value}</strong><span>{label}</span></div>
                ))}
              </div>
            </section>
            <section className="workspace-panel" data-testid="results-joined-section">
              <h2>Joined the Board</h2>
              {joined.length === 0 && <p className="workspace-note">Formally appointed board members will appear here.</p>}
              {joined.map((application) => <BoardMemberResultCard application={application} branding={branding} onChanged={load} key={application.application_id} />)}
            </section>
            {inProgress.length > 0 && (
              <section className="workspace-panel" data-testid="results-in-progress-section">
                <h2>Still In Progress</h2>
                <ul className="readiness-list">{inProgress.map((a) => <li key={a.application_id}>{a.profile_snapshot?.full_name || a.applicant_email} — {a.status}</li>)}</ul>
              </section>
            )}
            {notSelected.length > 0 && (
              <section className="workspace-panel" data-testid="results-not-selected-section">
                <h2>Not Selected</h2>
                <ul className="readiness-list">{notSelected.map((a) => <li key={a.application_id}>{a.profile_snapshot?.full_name || a.applicant_email} — {a.status}</li>)}</ul>
              </section>
            )}
          </>
        )}
        <section className="workspace-panel results-support-panel" data-testid="results-support-cta">
          <h2>Need Help Moving Forward?</h2>
          <p>Get help reviewing your new board, preparing for your first meeting or helping your board start strongly.</p>
          <a className="button" href={CALENDLY_URL} target="_blank" rel="noreferrer" data-testid="book-call-rooney-button">Book a Call With Rooney <ExternalLink size={15} /></a>
        </section>
      </main>
    </MemberShell>
  );
}
