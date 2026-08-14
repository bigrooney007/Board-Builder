import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Mail, X } from "lucide-react";
import { memberApi } from "./api";

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

export default function ActivationModule3() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState("");
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(null);
  const [sending, setSending] = useState(false);
  const [review, setReview] = useState(null);
  const pollRef = useRef(null);

  const load = useCallback(() => {
    memberApi.get("/activation/strategy").then((res) => setData(res.data)).catch(() => setError("We could not load your strategy workspace."));
  }, []);
  useEffect(load, [load]);

  useEffect(() => {
    if (data?.strategy?.status === "Generating" && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await memberApi.get("/activation/strategy/status");
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
  }, [data?.strategy?.status, load]);

  const openReview = useCallback((participantId) => {
    memberApi.get(`/activation/reviewers/${participantId}/review`).then((res) => setReview(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const reviewerId = searchParams.get("reviewer");
    if (reviewerId && data) {
      openReview(reviewerId);
      setSearchParams({}, { replace: true });
    }
  }, [data, searchParams, setSearchParams, openReview]);

  const generate = async () => {
    const strategy = data?.strategy;
    if (strategy?.display_text) {
      const ok = window.confirm("This will create a new version of your Fundraising Strategy Plan using the responses currently received. Your previous approved review version and any Board reviews already attached to it are preserved. Continue?");
      if (!ok) return;
    }
    setGenerating(true);
    try { await memberApi.post("/activation/strategy/generate"); load(); } catch (err) {
      setGenerating(false);
      window.alert(err.response?.data?.detail || "Generation could not start.");
    }
  };

  const saveEdit = async () => {
    setSaving(true);
    try { await memberApi.put("/activation/strategy", { display_text: editText }); setShowEdit(false); load(); } catch { /* keep open */ }
    setSaving(false);
  };

  const approve = async () => {
    try { await memberApi.post("/activation/strategy/approve-review"); load(); } catch { /* ignore */ }
  };

  const openPreview = (participant, type) => {
    memberApi.get(`/activation/reviewers/${participant.participant_id}/email-preview`, { params: { type } })
      .then((res) => setPreview({ ...res.data, participant, type }))
      .catch(() => {});
  };

  const sendEmail = async () => {
    setSending(true);
    try {
      await memberApi.post(`/activation/reviewers/${preview.participant.participant_id}/send`, { type: preview.type });
      setPreview(null);
      load();
    } catch (err) { window.alert(err.response?.data?.detail || "The email could not be sent."); }
    setSending(false);
  };

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">Loading your strategy workspace…</p>;

  const strategy = data.strategy;
  const ready = strategy.status === "Ready for Board Review";

  return (
    <div data-testid="activation-module3">
      <section className="member-card" data-testid="am3-intro">
        <h2>Turn the Board's Ideas Into One Fundraising Strategy</h2>
        <p>Your Board has now contributed ideas about who the organization should build relationships with, which fundraising opportunities to prioritize, what relationships already exist around the Board, how members are willing to participate, and what they believe should happen first.</p>
        <p>The next step is to combine those ideas with the organization's goals and direction and build one Fundraising Strategy Plan the Board can review together.</p>
      </section>

      <section className="member-card" data-testid="am3-planning-counts">
        <h2>Board Planning Responses</h2>
        <p data-testid="am3-planning-count-line">
          <strong>{data.planning.invited}</strong> Board Members Invited · <strong>{data.planning.received}</strong> Responses Received · <strong>{data.planning.waiting}</strong> Waiting · <strong>{data.planning.included}</strong> Responses That Will Be Included
        </p>
        {data.planning.waiting > 0 && (
          <p data-testid="am3-incomplete-note">The strategy will use the responses currently received. Responses that arrive later remain saved and can be included only by intentionally regenerating the plan.</p>
        )}
      </section>

      <section className="member-card" data-testid="am3-strategy-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2 style={{ margin: 0 }}>Fundraising Strategy Plan</h2>
          <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid="am3-strategy-status">
            {strategy.status === "NONE" ? "NOT BUILT" : strategy.status === "Ready for Board Review" ? `READY FOR BOARD REVIEW · v${strategy.review_version}` : strategy.status.toUpperCase()}
          </span>
        </div>
        {strategy.status === "Failed" && <p className="submit-error" data-testid="am3-generation-error">Generation failed. Please try again.</p>}
        {strategy.status === "Generating" || generating ? (
          <p data-testid="am3-generating">Building your Fundraising Strategy Plan from your intake and the Board's responses… This can take a minute or two. It will appear here automatically.</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
            <button type="button" className="button" onClick={generate} data-testid="am3-generate-button">
              {strategy.display_text ? "REGENERATE WITH LATEST RESPONSES" : "BUILD MY FUNDRAISING STRATEGY PLAN"}
            </button>
            {strategy.display_text && (
              <>
                <button type="button" className="button button-outline" onClick={() => { setEditText(strategy.display_text); setShowEdit(true); }} data-testid="am3-edit-button">EDIT PLAN</button>
                {!ready && <button type="button" className="button" onClick={approve} data-testid="am3-approve-button">APPROVE FOR BOARD REVIEW</button>}
              </>
            )}
          </div>
        )}
        {strategy.display_text && strategy.status !== "Generating" && (
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 14, maxHeight: 420, overflowY: "auto" }} data-testid="am3-strategy-text">{strategy.display_text}</div>
        )}
        {strategy.display_text && !ready && <p className="eyebrow" style={{ marginTop: 10 }} data-testid="am3-approval-required">Approve the plan for Board review before sending review links.</p>}
      </section>

      <section className="member-card" data-testid="am3-review-summary">
        <h2>Board Fundraising Strategy Review</h2>
        <p data-testid="am3-review-counts">
          <strong>{data.review_progress.invited}</strong> Invited · <strong>{data.review_progress.received}</strong> Review{data.review_progress.received === 1 ? "" : "s"} Received · <strong>{data.review_progress.waiting}</strong> Waiting
        </p>
        {data.review_progress.invited > 0 && data.review_progress.received < data.review_progress.invited && (
          <p data-testid="am3-review-warning">You have received {data.review_progress.received} of {data.review_progress.invited} Board reviews. You can continue to the plan-adoption stage now, or wait for additional reviews. Any review received later will remain saved.</p>
        )}
        {!data.reviewers.length && <p data-testid="am3-no-reviewers">Your Module 2 participants will appear here so you can send them the plan for review.</p>}
        {data.reviewers.map((reviewer) => (
          <article key={reviewer.participant_id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 16 }} data-testid={`am3-reviewer-card-${reviewer.participant_id}`}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
              <div>
                <h3 style={{ margin: 0 }}>{reviewer.name}</h3>
                <p style={{ margin: "4px 0 0" }}>{reviewer.role || "Board Member"} · {reviewer.email}</p>
              </div>
              <span className="eyebrow" style={{ alignSelf: "flex-start", padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid={`am3-review-status-${reviewer.participant_id}`}>{reviewer.review_status}</span>
            </div>
            <p className="eyebrow" style={{ marginTop: 10 }}>
              {reviewer.review_position && <>Position: {reviewer.review_position} · </>}
              {reviewer.last_review_sent_at && <>Plan sent {new Date(reviewer.last_review_sent_at).toLocaleDateString()} · </>}
              {reviewer.review_submitted_at && <>Reviewed {new Date(reviewer.review_submitted_at).toLocaleDateString()} · </>}
              {reviewer.last_review_reminder_at && <>Last reminder {new Date(reviewer.last_review_reminder_at).toLocaleDateString()}</>}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
              {reviewer.review_status === "NOT SENT" && (
                <button type="button" className="button" onClick={() => openPreview(reviewer, "initial")} disabled={!ready} data-testid={`am3-send-review-${reviewer.participant_id}`}><Mail size={15} /> SEND FOR REVIEW</button>
              )}
              {reviewer.review_status === "SENT" && (
                <button type="button" className="button button-outline" onClick={() => openPreview(reviewer, "reminder")} data-testid={`am3-send-reminder-${reviewer.participant_id}`}><Mail size={15} /> SEND REVIEW REMINDER</button>
              )}
              {reviewer.review_status === "REVIEWED" && (
                <button type="button" className="button" onClick={() => openReview(reviewer.participant_id)} data-testid={`am3-view-review-${reviewer.participant_id}`}>VIEW REVIEW</button>
              )}
            </div>
          </article>
        ))}
      </section>

      <section style={{ textAlign: "center", margin: "26px 0" }}>
        <Link className="button rwr-cta-button" to="/app/activation/self-guided/module/4" data-testid="am3-continue-module4">CONTINUE TO MODULE 4 — FACILITATE PLAN ADOPTION</Link>
      </section>

      {showEdit && (
        <Modal onClose={() => setShowEdit(false)} testId="am3-edit-modal">
          <h2>Edit Fundraising Strategy Plan</h2>
          <textarea rows={22} style={{ width: "100%" }} value={editText} onChange={(e) => setEditText(e.target.value)} data-testid="am3-edit-text" />
          <button type="button" className="button" onClick={saveEdit} disabled={saving} data-testid="am3-save-button">{saving ? "Saving…" : "SAVE"}</button>
        </Modal>
      )}

      {preview && (
        <Modal onClose={() => setPreview(null)} testId="am3-send-modal">
          <h2>{preview.type === "reminder" ? "Review Reminder Email" : "Review Strategy Review Email"}</h2>
          <p><strong>To:</strong> {preview.to_name} &lt;{preview.to_email}&gt;</p>
          <p><strong>Subject:</strong> <span data-testid="am3-email-subject">{preview.subject}</span></p>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 320, overflowY: "auto" }} data-testid="am3-email-body">{preview.body}</div>
          <p style={{ marginTop: 10 }}><strong>Secure Review Link:</strong> <span style={{ wordBreak: "break-all" }} data-testid="am3-email-link">{preview.form_link}</span></p>
          <button type="button" className="button" onClick={sendEmail} disabled={sending} data-testid="am3-send-confirm">{sending ? "Sending…" : "SEND"}</button>
        </Modal>
      )}

      {review && (
        <Modal onClose={() => setReview(null)} testId="am3-review-modal">
          <h2>{review.participant.name} — Plan Review</h2>
          <div className="member-card" style={{ borderLeft: "4px solid #000", marginBottom: 14 }}>
            <p className="eyebrow">Review Position</p>
            <p style={{ fontWeight: 700, margin: 0 }} data-testid="am3-review-position">{review.review.position}</p>
          </div>
          {review.review.discussion_points && <p data-testid="am3-review-discussion"><strong>Suggestions / concerns to discuss:</strong> {review.review.discussion_points}</p>}
          <p data-testid="am3-review-contribution"><strong>Where they see themselves contributing:</strong> {review.review.contribution}</p>
          {review.review.support_needs && <p data-testid="am3-review-support"><strong>Support or resources that would help:</strong> {review.review.support_needs}</p>}
          <p className="eyebrow">Submitted {review.review_submitted_at ? new Date(review.review_submitted_at).toLocaleString() : ""} · Plan version {review.review_version}</p>
        </Modal>
      )}
    </div>
  );
}
