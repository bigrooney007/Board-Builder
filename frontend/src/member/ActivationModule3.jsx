import { useCallback, useEffect, useRef, useState } from "react";
import { Copy, Mail, X } from "lucide-react";
import { memberApi } from "./api";
import { activationM3Text } from "../content/appContent";

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
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState("");
  const [saving, setSaving] = useState(false);
  const [email, setEmail] = useState(null);
  const [emailBusy, setEmailBusy] = useState(false);
  const [copied, setCopied] = useState("");
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

  const generateEmail = async () => {
    setEmailBusy(true);
    try {
      const res = await memberApi.get("/activation/strategy-review-email");
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
  if (!data) return <p className="sh-loading">Loading your strategy workspace…</p>;

  const strategy = data.strategy;
  const ready = strategy.status === "Ready for Board Review";

  return (
    <div data-testid="activation-module3">
      <section className="member-card" data-testid="am3-intro">
        <h2>{activationM3Text.h_turnTheBoardsIdeasInto}</h2>
        <p>Your Board has now contributed ideas about who the organization should build relationships with, which fundraising opportunities to prioritize, what relationships already exist around the Board, how members are willing to participate, and what they believe should happen first.</p>
        <p>The next step is to combine those ideas with the organization's goals and direction and build one Fundraising Strategy Plan the Board can review together.</p>
      </section>

      <section className="member-card" data-testid="am3-planning-counts">
        <h2>{activationM3Text.h_boardPlanningResponses}</h2>
        <p data-testid="am3-planning-count-line">
          <strong>{data.planning.received}</strong> Response{data.planning.received === 1 ? "" : "s"} Received · <strong>{data.planning.included}</strong> Response{data.planning.included === 1 ? "" : "s"} That Will Be Included
        </p>
        <p data-testid="am3-incomplete-note">The strategy uses the responses currently received. Responses that arrive later remain saved and can be included only by intentionally regenerating the plan.</p>
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
              {strategy.display_text ? "REGENERATE WITH LATEST RESPONSES" : "GENERATE FUNDRAISING STRATEGY PLAN"}
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
        {strategy.display_text && !ready && <p className="eyebrow" style={{ marginTop: 10 }} data-testid="am3-approval-required">Approve the plan for Board review before generating the review email.</p>}
      </section>

      <section className="member-card" data-testid="am3-email-card">
        <h2>{activationM3Text.h_sendThePlanForBoardReview}</h2>
        <p>{activationM3Text.d_sendThePlanForBoardReview}</p>
        {!ready && <p className="eyebrow" data-testid="am3-email-locked">{activationM3Text.n_approvePlanToUnlockEmail}</p>}
        <button type="button" className="button" onClick={generateEmail} disabled={!ready || emailBusy} data-testid="am3-generate-email-button"><Mail size={15} /> {emailBusy ? "Generating…" : email ? "REGENERATE EMAIL" : "GENERATE EMAIL"}</button>
        {email && (
          <div style={{ marginTop: 14 }} data-testid="am3-email-preview">
            <p><strong>Subject:</strong> <span data-testid="am3-email-subject">{email.subject}</span></p>
            <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 320, overflowY: "auto" }} data-testid="am3-email-body">{email.body}</div>
            <p style={{ marginTop: 10 }}><strong>Secure Review Link:</strong> <span style={{ wordBreak: "break-all" }} data-testid="am3-email-link">{email.review_link}</span></p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              <button type="button" className="button" onClick={() => copyText(email.body, "body")} data-testid="am3-copy-email-button"><Copy size={15} /> {copied === "body" ? "Email Copied" : "COPY EMAIL"}</button>
              <button type="button" className="button button-outline" onClick={() => copyText(email.subject, "subject")} data-testid="am3-copy-subject-button"><Copy size={15} /> {copied === "subject" ? "Subject Copied" : "COPY SUBJECT"}</button>
            </div>
          </div>
        )}
        <p className="eyebrow" style={{ marginTop: 12 }} data-testid="am3-reviews-note">{activationM3Text.n_reviewsAppearInModule4}</p>
      </section>

      {showEdit && (
        <Modal onClose={() => setShowEdit(false)} testId="am3-edit-modal">
          <h2>{activationM3Text.h_editFundraisingStrategyPlan}</h2>
          <textarea rows={22} style={{ width: "100%" }} value={editText} onChange={(e) => setEditText(e.target.value)} data-testid="am3-edit-text" />
          <button type="button" className="button" onClick={saveEdit} disabled={saving} data-testid="am3-save-button">{saving ? "Saving…" : "SAVE"}</button>
        </Modal>
      )}
    </div>
  );
}
