import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { STRATEGY_SECTIONS, SectionBody } from "./strategyRender";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SectionContent = ({ section }) => {
  const definition = STRATEGY_SECTIONS.find((item) => item.key === section.key);
  if (section.edit) return <p className="bfg-doc-text" style={{ whiteSpace: "pre-line", textAlign: "left" }}>{section.edit}</p>;
  return <div style={{ textAlign: "left" }}><SectionBody section={definition} data={section.data} mode={section.mode} /></div>;
};

const FeedbackBlock = ({ token, identity, section, myFeedback, onSubmitted }) => {
  const [choice, setChoice] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [changing, setChanging] = useState(false);

  useEffect(() => { setChoice(""); setComment(""); setChanging(false); setError(""); }, [section.key]);

  const submit = async (responseType, text = "") => {
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/game/group/play/${token}/review-feedback`, {
        slot_id: identity.slot_id, device_id: identity.device_id,
        section_key: section.key, response_type: responseType, comment: text,
      });
      setChoice(""); setComment(""); setChanging(false);
      onSubmitted();
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your response. Please try again.");
    }
    setBusy(false);
  };

  if (myFeedback && !changing) {
    const labels = { approve: "You approved this section.", suggest_change: "Your suggested change has been submitted.", needs_discussion: "Your discussion point has been submitted." };
    return (
      <div style={{ marginTop: 18 }} data-testid="bfg-gr-feedback-done">
        <p className="bfg-success" style={{ fontWeight: 700 }}>{labels[myFeedback.response_type]}</p>
        {myFeedback.comment && <p className="bfg-note" style={{ marginTop: 6 }}>{myFeedback.comment}</p>}
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 10 }} onClick={() => setChanging(true)} data-testid="bfg-gr-change-response-btn">
          Change My Response
        </button>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 18, textAlign: "left" }} data-testid="bfg-gr-feedback">
      <h2 style={{ fontSize: 18 }}>What Do You Think?</h2>
      <div className="bfg-gr-options">
        <button type="button" className={`bfg-gr-option ${choice === "approve" ? "selected" : ""}`}
          onClick={() => submit("approve")} disabled={busy} data-testid="bfg-gr-approve-btn">
          Approve This Section
        </button>
        <button type="button" className={`bfg-gr-option ${choice === "suggest_change" ? "selected" : ""}`}
          onClick={() => { setChoice("suggest_change"); setComment(""); }} disabled={busy} data-testid="bfg-gr-suggest-btn">
          I Have A Suggested Change
        </button>
        <button type="button" className={`bfg-gr-option ${choice === "needs_discussion" ? "selected" : ""}`}
          onClick={() => { setChoice("needs_discussion"); setComment(""); }} disabled={busy} data-testid="bfg-gr-discussion-btn">
          I Need More Discussion
        </button>
      </div>
      {choice === "suggest_change" && (
        <div style={{ marginTop: 12 }}>
          <label className="bfg-field" style={{ marginTop: 0 }}>
            <span>What would you change?</span>
            <textarea rows={4} value={comment} onChange={(event) => setComment(event.target.value)} data-testid="bfg-gr-suggest-text" />
          </label>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 10 }} disabled={!comment.trim() || busy}
            onClick={() => submit("suggest_change", comment.trim())} data-testid="bfg-gr-suggest-submit-btn">
            Submit Suggestion
          </button>
        </div>
      )}
      {choice === "needs_discussion" && (
        <div style={{ marginTop: 12 }}>
          <label className="bfg-field" style={{ marginTop: 0 }}>
            <span>What should the board discuss?</span>
            <textarea rows={4} value={comment} onChange={(event) => setComment(event.target.value)} data-testid="bfg-gr-discussion-text" />
          </label>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 10 }} disabled={!comment.trim() || busy}
            onClick={() => submit("needs_discussion", comment.trim())} data-testid="bfg-gr-discussion-submit-btn">
            Submit Discussion Point
          </button>
        </div>
      )}
      {error && <p className="bfg-error">{error}</p>}
    </div>
  );
};

const FinalResponseBlock = ({ token, identity, organizationName, myResponse, onSubmitted }) => {
  const [requesting, setRequesting] = useState(false);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (approvalStatus, text = "") => {
    setBusy(true); setError("");
    try {
      await axios.post(`${API}/game/group/play/${token}/final-response`, {
        slot_id: identity.slot_id, device_id: identity.device_id,
        approval_status: approvalStatus, change_request: text,
      });
      setRequesting(false); setComment("");
      onSubmitted();
    } catch { setError("We could not save your response. Please try again."); }
    setBusy(false);
  };

  if (myResponse) {
    return (
      <div style={{ marginTop: 18 }} data-testid="bfg-gr-final-done">
        <p className="bfg-success" style={{ fontWeight: 700 }}>
          {myResponse.approval_status === "approved" ? "You approved the final strategy." : "Your change request has been submitted."}
        </p>
        {myResponse.change_request && <p className="bfg-note" style={{ marginTop: 6 }}>{myResponse.change_request}</p>}
        <p className="bfg-note" style={{ marginTop: 10 }}>Waiting for the rest of the board and your host.</p>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 18, textAlign: "left" }} data-testid="bfg-gr-final-response">
      <p>You have reviewed {organizationName}'s Final Fundraising Strategy.</p>
      <h2 style={{ fontSize: 18, marginTop: 14 }}>Are you ready for the organization to adopt this strategy?</h2>
      {!requesting ? (
        <div className="bfg-gr-options">
          <button type="button" className="bfg-gr-option" onClick={() => submit("approved")} disabled={busy} data-testid="bfg-gr-approve-final-btn">
            Approve Final Strategy
          </button>
          <button type="button" className="bfg-gr-option" onClick={() => setRequesting(true)} disabled={busy} data-testid="bfg-gr-request-change-btn">
            Request A Change
          </button>
        </div>
      ) : (
        <div style={{ marginTop: 12 }}>
          <label className="bfg-field" style={{ marginTop: 0 }}>
            <span>What still needs to change?</span>
            <textarea rows={4} value={comment} onChange={(event) => setComment(event.target.value)} data-testid="bfg-gr-request-text" />
          </label>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 10 }} disabled={!comment.trim() || busy}
            onClick={() => submit("change_requested", comment.trim())} data-testid="bfg-gr-request-submit-btn">
            Submit Request
          </button>
        </div>
      )}
      {error && <p className="bfg-error">{error}</p>}
    </div>
  );
};

const PostGameComplete = ({ token, identity, organizationName }) => {
  const [info, setInfo] = useState(null);
  useEffect(() => {
    axios.get(`${API}/game/postgame/play/${token}`, { params: { slot: identity.slot_id } })
      .then((response) => setInfo(response.data))
      .catch(() => setInfo({ adopted: false }));
  }, [token, identity]);

  if (!info) return <div className="bfg-gg-card" style={{ textAlign: "center" }} />;

  if (!info.adopted) {
    return (
      <div className="bfg-gg-card" style={{ textAlign: "center" }} data-testid="bfg-gr-adopted">
        <p className="bfg-gg-eyebrow">Game Night</p>
        <h1>Your Fundraising Strategy Is Ready</h1>
        <p style={{ marginTop: 14 }}>{organizationName} has adopted its fundraising strategy.</p>
        <p className="bfg-gg-rule" style={{ marginTop: 14 }}>You will receive your personal Board Fundraising Portfolio when it is ready.</p>
      </div>
    );
  }

  return (
    <div className="bfg-gg-card" data-testid="bfg-postgame-complete">
      <p className="bfg-gg-eyebrow">Game Night</p>
      <h1>Your Board Fundraising Game Is Complete</h1>
      <p style={{ marginTop: 14 }}>{info.organization_name} has adopted the fundraising strategy your board built together.</p>
      <div style={{ marginTop: 16, textAlign: "left" }} data-testid="bfg-postgame-goal">
        <p><strong>Fundraising Goal:</strong> {info.goal_display}</p>
        {info.deadline_display && <p style={{ marginTop: 4 }}><strong>Goal Deadline:</strong> {info.deadline_display}</p>}
      </div>
      <a className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} href={`/strategy/${info.strategy_share_token}`}
        target="_blank" rel="noreferrer" data-testid="bfg-postgame-view-strategy-btn">
        View Our Adopted Fundraising Strategy
      </a>
      <div style={{ marginTop: 24, textAlign: "left" }}>
        <h2 style={{ fontSize: 18 }}>What Happens Next?</h2>
        <p style={{ marginTop: 10 }}>
          The strategy tells your organization what it plans to do. Your Board Fundraising Portfolio will show how you personally can help execute it.
        </p>
        <p style={{ marginTop: 12 }}>Your portfolio will combine:</p>
        <ul style={{ marginTop: 8, paddingLeft: 22 }}>
          <li>How you said you want to help build the fundraising system</li>
          <li>How you said you want to help raise money</li>
          <li>Commitments you made during Game Night</li>
          <li>Any final responsibilities agreed with the organization</li>
        </ul>
        {info.portfolio_state === "sent" && info.portfolio_token ? (
          <a className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }} href={`/board-portfolio/${info.portfolio_token}`}
            target="_blank" rel="noreferrer" data-testid="bfg-postgame-view-portfolio-btn">
            Review My Board Fundraising Portfolio
          </a>
        ) : (
          <p className="bfg-gg-rule" style={{ marginTop: 16 }} data-testid="bfg-postgame-portfolio-waiting">
            Your Board Fundraising Portfolio is being prepared. You will receive it when it is ready for review.
          </p>
        )}
      </div>
    </div>
  );
};

export const GroupReviewStage = ({ token, identity }) => {
  const [data, setData] = useState(null);

  const poll = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/game/group/play/${token}/review-state`, {
        params: { slot: identity.slot_id, device: identity.device_id } });
      setData(response.data);
    } catch { /* keep last state */ }
  }, [token, identity]);

  useEffect(() => {
    poll();
    const timer = setInterval(poll, 2500);
    return () => clearInterval(timer);
  }, [poll]);

  if (!data || !data.exists) {
    return (
      <div className="bfg-gg-card" style={{ textAlign: "center" }} data-testid="bfg-gg-complete">
        <p className="bfg-gg-eyebrow">Game Night</p>
        <h1>Review Game Complete</h1>
        <p style={{ marginTop: 14 }}>Your board has now identified the fundraising ideas it wants to prioritize.</p>
        <p style={{ marginTop: 10 }}>Stay with your board as you move into the next part of Game Night.</p>
      </div>
    );
  }

  if (data.status === "reviewing" && data.section) {
    return (
      <div className="bfg-gg-card" data-testid="bfg-gr-review-card">
        <p className="bfg-gg-eyebrow">Strategy Review</p>
        <p className="bfg-gg-rule" data-testid="bfg-gr-section-counter">Section {data.section.index + 1} of {data.total_sections}</p>
        <h1>{data.section.title}</h1>
        <div style={{ marginTop: 14 }} data-testid="bfg-gr-section-content">
          <SectionContent section={data.section} />
        </div>
        <FeedbackBlock token={token} identity={identity} section={data.section}
          myFeedback={data.my_feedback} onSubmitted={poll} />
      </div>
    );
  }

  if (data.status === "reviewing" || data.status === "review_complete" || data.status === "decisions_processed") {
    return (
      <div className="bfg-gg-card" style={{ textAlign: "center" }} data-testid="bfg-gr-waiting">
        <p className="bfg-gg-eyebrow">Strategy Review</p>
        <h1>Strategy Review Complete</h1>
        <p style={{ marginTop: 14 }}>
          Your board has reviewed the strategy together. {data.organization_name} is now turning the board's decisions into the Final Fundraising Strategy.
        </p>
        <p className="bfg-gg-rule" style={{ marginTop: 12 }}>Stay with your board — the final strategy is coming next.</p>
      </div>
    );
  }

  if (data.status === "final_strategy_created") {
    if (data.final_review_status === "reviewing" && data.section) {
      return (
        <div className="bfg-gg-card" data-testid="bfg-gr-final-review-card">
          <p className="bfg-gg-eyebrow">Final Strategy Review</p>
          <p className="bfg-gg-rule">Section {data.section.index + 1} of {data.total_sections}</p>
          <h1>{data.section.title}</h1>
          <div style={{ marginTop: 14 }} data-testid="bfg-gr-final-section-content">
            <SectionContent section={data.section} />
          </div>
          <p className="bfg-gg-rule" style={{ marginTop: 16 }}>Your host is walking the board through the final strategy.</p>
        </div>
      );
    }
    if (data.final_review_status === "response") {
      return (
        <div className="bfg-gg-card" data-testid="bfg-gr-final-response-card">
          <p className="bfg-gg-eyebrow">Final Strategy Review</p>
          <h1>Final Strategy Review</h1>
          <FinalResponseBlock token={token} identity={identity} organizationName={data.organization_name}
            myResponse={data.my_final_response} onSubmitted={poll} />
        </div>
      );
    }
    return (
      <div className="bfg-gg-card" style={{ textAlign: "center" }} data-testid="bfg-gr-final-waiting">
        <p className="bfg-gg-eyebrow">Final Strategy</p>
        <h1>The Final Strategy Is Ready</h1>
        <p style={{ marginTop: 14 }}>Waiting for your host to begin the final strategy review.</p>
      </div>
    );
  }

  if (data.status === "adopted") {
    return <PostGameComplete token={token} identity={identity} organizationName={data.organization_name} />;
  }

  return null;
};
