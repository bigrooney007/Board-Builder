import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import "./game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PortfolioItem = ({ item, involvement }) => (
  <div className="bfg-pf-item" data-testid={`bfg-bp-item-${item.item_id}`}>
    <strong>{item.label}</strong>
    {item.requires_confirmation && <span className="bfg-pe-badge">Requires Your Confirmation</span>}
    {involvement && <p className="bfg-pf-note">Your involvement: {involvement}</p>}
    {item.member_note && <p className="bfg-pf-note">How you said you would help: {item.member_note}</p>}
    {item.commitment && <p className="bfg-pf-note">Game Night Commitment: {item.commitment}</p>}
    {(item.audiences || []).length > 0 && <p className="bfg-pf-note">Priority audiences this may support: {item.audiences.join(", ")}</p>}
    {item.deadline && <p className="bfg-pf-note">Deadline: {item.deadline}</p>}
  </div>
);

export default function BoardPortfolioPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [showApprove, setShowApprove] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Your Board Fundraising Portfolio"; }, []);
  const load = useCallback(async () => {
    try {
      const result = (await axios.get(`${API}/board-portfolio/${token}`)).data;
      setData(result);
    } catch { setNotFound(true); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  if (notFound) {
    return (
      <div className="bfg-pf-page" style={{ display: "grid", placeItems: "center" }}>
        <div className="bfg-pf-doc" style={{ maxWidth: 440, textAlign: "center" }} data-testid="bfg-bp-invalid">
          <h2>This Portfolio Link Is Not Valid</h2>
          <p className="bfg-pf-sub">Please ask your organization to resend your Board Fundraising Portfolio link.</p>
        </div>
      </div>
    );
  }
  if (!data) return <div className="bfg-pf-page" />;

  const respond = async (action, text = "") => {
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/board-portfolio/${token}/respond`, { action, comment: text });
      setShowApprove(false); setRequesting(false); setComment("");
      await load();
      window.scrollTo({ top: 0 });
    } catch { setError("We could not save your response. Please try again."); }
    setBusy(false);
  };

  const approved = data.status === "approved" || data.status === "materials_ready";
  const reviewable = ["draft", "ready_to_send", "sent"].includes(data.status);
  const hasContent = data.system_roles.length > 0 || data.direct_activities.length > 0 || data.additional_commitments.length > 0;

  return (
    <div className="bfg-pf-page" data-testid="bfg-board-portfolio-page">
      <div className="bfg-pf-doc">
        <header className="bfg-pf-header">
          <p className="bfg-pf-eyebrow">{data.organization_name}</p>
          <h1>Your Board Fundraising Portfolio</h1>
          <p className="bfg-pf-sub" style={{ marginTop: 10 }}>
            {data.organization_name} is working toward a fundraising goal of <strong>{data.goal_display}</strong>
            {data.goal_deadline && <> by <strong>{data.goal_deadline}</strong></>}.
          </p>
          <p className="bfg-pf-sub">
            Your portfolio shows the role you agreed to play in helping the organization raise money toward this goal.
          </p>
          <div className="bfg-pf-actions bfg-no-print">
            {data.strategy_share_token && (
              <a className="bfg-pf-btn ghost" href={`/strategy/${data.strategy_share_token}`} target="_blank" rel="noreferrer"
                data-testid="bfg-bp-view-strategy">View Our Adopted Fundraising Strategy</a>
            )}
            {approved && (
              <button className="bfg-pf-btn ghost" onClick={() => window.print()} data-testid="bfg-bp-print-btn">Print / Save As PDF</button>
            )}
            {approved && <a className="bfg-pf-btn" href={`/board-assistant/${token}`} data-testid="bfg-bp-assistant-btn">Let's Help You Execute</a>}
          </div>
          {approved && (
            <p className="bfg-pf-note" style={{ marginTop: 12, color: "#059669", fontWeight: 700 }} data-testid="bfg-bp-approved-badge">
              Portfolio Approved{data.approved_at ? ` — ${new Date(data.approved_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}` : ""}
            </p>
          )}
        </header>

        {!hasContent && <p className="bfg-pf-sub" style={{ marginTop: 20, fontWeight: 700 }}>Participation Role Not Defined Yet</p>}

        {data.system_roles.length > 0 && (
          <section className="bfg-pf-section" data-testid="bfg-bp-system-section">
            <p className="bfg-pf-eyebrow">HOW I AGREED TO HELP</p>
            <h2>Your Role In Building Our Fundraising System</h2>
            <p className="bfg-pf-sub">
              These are the areas where you will help strengthen the people, processes, technology and resources required to execute our fundraising strategy.
            </p>
            {data.system_roles.map((role) => (
              <PortfolioItem key={role.item_id} item={role} involvement={role.involvement_display} />
            ))}
          </section>
        )}

        {data.direct_activities.length > 0 && (
          <section className="bfg-pf-section" data-testid="bfg-bp-direct-section">
            <h2>How You Will Help Us Raise Money</h2>
            <p className="bfg-pf-sub">
              These are the fundraising activities you agreed to support based on your interests, relationships and strengths.
            </p>
            {data.direct_activities.map((act) => <PortfolioItem key={act.item_id} item={act} />)}
          </section>
        )}

        {data.additional_commitments.length > 0 && (
          <section className="bfg-pf-section" data-testid="bfg-bp-commitments-section">
            <h2>Your Game Night Commitments</h2>
            {data.additional_commitments.map((item, index) => (
              <div className="bfg-pf-item" key={index}>
                <strong>{item.text}</strong>
                {item.deadline && <p className="bfg-pf-note">Deadline: {item.deadline}</p>}
              </div>
            ))}
          </section>
        )}

        {data.org_note && (
          <section className="bfg-pf-section" data-testid="bfg-bp-org-note">
            <h2>A Note From {data.organization_name}</h2>
            <p className="bfg-pf-sub" style={{ whiteSpace: "pre-line" }}>{data.org_note}</p>
          </section>
        )}

        {reviewable && (
          <section className="bfg-pf-section bfg-no-print" data-testid="bfg-bp-response">
            <h2>Does This Accurately Reflect How You Will Participate?</h2>
            {!requesting ? (
              <div className="bfg-pf-actions">
                <button className="bfg-pf-btn" disabled={busy} onClick={() => setShowApprove(true)} data-testid="bfg-bp-approve-btn">
                  Approve My Portfolio
                </button>
                <button className="bfg-pf-btn ghost" disabled={busy} onClick={() => setRequesting(true)} data-testid="bfg-bp-request-btn">
                  Request A Change
                </button>
              </div>
            ) : (
              <div style={{ marginTop: 12 }}>
                <p className="bfg-pf-sub" style={{ fontWeight: 700 }}>What Should We Change?</p>
                <textarea className="bfg-pf-textarea" value={comment} onChange={(event) => setComment(event.target.value)}
                  data-testid="bfg-bp-request-text" />
                <div className="bfg-pf-actions">
                  <button className="bfg-pf-btn" disabled={!comment.trim() || busy}
                    onClick={() => respond("request_change", comment.trim())} data-testid="bfg-bp-request-submit">
                    Send Change Request
                  </button>
                  <button className="bfg-pf-btn ghost" onClick={() => setRequesting(false)}>Cancel</button>
                </div>
              </div>
            )}
            {error && <p className="bfg-pf-note" style={{ color: "#dc2626" }}>{error}</p>}
          </section>
        )}

        {data.status === "change_requested" && (
          <section className="bfg-pf-section" data-testid="bfg-bp-change-sent">
            <h2>Change Request Sent</h2>
            <p className="bfg-pf-sub">Your change request has been sent to {data.organization_name}.</p>
            {data.change_request && <p className="bfg-pf-note" style={{ marginTop: 8 }}>{data.change_request}</p>}
          </section>
        )}

        {approved && (
          <section className="bfg-pf-section bfg-no-print" data-testid="bfg-bp-approved-section">
            <h2>Ready To Carry Out Your Role?</h2>
            <p className="bfg-pf-sub">Your Executive Assistant recommends the materials most useful for the responsibilities in this Portfolio. Create only what you need, when you need it, or ask the assistant for help with your next action.</p>
            <a className="bfg-pf-btn" style={{marginTop:12,display:"inline-block"}} href={`/board-assistant/${token}`} data-testid="bfg-bp-open-assistant">OPEN MY EXECUTIVE ASSISTANT</a>
          </section>
        )}

        {data.play_token && (
          <section className="bfg-pf-section bfg-no-print" data-testid="bfg-bp-relationship-section">
            <h2>Relationship Mapping</h2>
            <p className="bfg-pf-sub">
              Identify the people, businesses and grantors in your own network who match the funder profiles identified in {data.organization_name}'s fundraising strategy.
            </p>
            <a className="bfg-pf-btn" style={{ marginTop: 12, display: "inline-block" }}
              href={`/relationship-mapping/${data.play_token}`} data-testid="bfg-bp-relationship-link">
              Complete My Relationship Mapping
            </a>
          </section>
        )}
      </div>

      {showApprove && (
        <div className="bfg-pf-modal-overlay" data-testid="bfg-bp-approve-modal">
          <div className="bfg-pf-modal">
            <h2>Approve Your Board Fundraising Portfolio?</h2>
            <p className="bfg-pf-sub" style={{ marginTop: 10 }}>
              By approving, you are confirming that this portfolio accurately reflects how you currently intend to support {data.organization_name}'s fundraising strategy.
            </p>
            <div className="bfg-pf-actions" style={{ justifyContent: "flex-end" }}>
              <button className="bfg-pf-btn ghost" onClick={() => setShowApprove(false)} data-testid="bfg-bp-approve-cancel">Cancel</button>
              <button className="bfg-pf-btn" disabled={busy} onClick={() => respond("approve")} data-testid="bfg-bp-approve-confirm">
                {busy ? "Approving…" : "Approve Portfolio"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
