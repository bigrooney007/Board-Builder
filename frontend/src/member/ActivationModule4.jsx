import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Download, X } from "lucide-react";
import { memberApi } from "./api";

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
const RESP_STATUSES = ["Responsibility Agreed", "Follow-Up Needed", "No Fundraising Responsibility Agreed Yet"];

export default function ActivationModule4() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [conclusionSaved, setConclusionSaved] = useState(false);
  const [adoptedDraft, setAdoptedDraft] = useState("");
  const [respEdits, setRespEdits] = useState({});
  const [savedResp, setSavedResp] = useState("");
  const pollRef = useRef(null);

  const load = useCallback(() => {
    memberApi.get("/activation/adoption").then((res) => {
      setData(res.data);
      setConclusion(res.data.adoption.conclusion || "");
      setAdoptedDraft(res.data.adoption.draft_adopted_text || "");
    }).catch(() => setError("We could not load your plan adoption workspace."));
  }, []);
  useEffect(load, [load]);

  useEffect(() => {
    if (data?.adoption?.guide_status === "Generating" && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await memberApi.get("/activation/adoption/status");
          if (res.data.guide_status !== "Generating") {
            clearInterval(pollRef.current); pollRef.current = null;
            setGenerating(false); load();
          }
        } catch { /* keep polling */ }
      }, 3000);
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [data?.adoption?.guide_status, load]);

  const generate = async () => {
    if (data?.adoption?.guide_text && !window.confirm("This will replace the current Facilitation Guide with a newly generated version. Continue?")) return;
    setGenerating(true);
    try { await memberApi.post("/activation/adoption/guide/generate"); load(); } catch (err) {
      setGenerating(false);
      window.alert(err.response?.data?.detail || "Generation could not start.");
    }
  };

  const saveGuide = async () => {
    try { await memberApi.put("/activation/adoption/guide", { text: editText }); setShowEdit(false); load(); } catch { /* keep open */ }
  };
  const approveGuide = async () => { try { await memberApi.post("/activation/adoption/guide/approve"); load(); } catch { /* ignore */ } };

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

  const saveResponsibility = async (member) => {
    const edit = respEdits[member.participant_id] || {};
    const body = {
      agreed_responsibility: edit.agreed_responsibility ?? member.agreed_responsibility,
      responsibility_status: edit.responsibility_status ?? member.responsibility_status,
    };
    await memberApi.put(`/activation/participants/${member.participant_id}/responsibility`, body);
    setSavedResp(member.participant_id);
    setTimeout(() => setSavedResp(""), 2500);
    load();
  };

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">Loading your plan adoption workspace…</p>;

  const adoption = data.adoption;
  const guideStatus = adoption.guide_status || "NONE";

  return (
    <div data-testid="activation-module4">
      <section className="member-card" data-testid="am4-intro">
        <h2>Turn the Fundraising Strategy Into a Board-Owned Plan</h2>
        <p>The Board has helped build the strategy and reviewed the plan.</p>
        <p>The next step is to bring everyone together, work through the feedback, agree on the direction and establish what the Board will actually help carry.</p>
        <p><strong>This is where participation becomes ownership.</strong></p>
      </section>

      <section className="member-card" data-testid="am4-context">
        <h2>Where Things Stand</h2>
        <p data-testid="am4-context-line">Strategy: <strong>{data.strategy.status === "Ready for Board Review" ? `Ready for Board Review · v${data.strategy.review_version}` : data.strategy.status}</strong> · Board reviews received: <strong>{data.reviews.length}</strong></p>
        {data.reviews.map((review) => (
          <div key={review.name} style={{ borderLeft: "3px solid #000", paddingLeft: 12, margin: "12px 0" }} data-testid={`am4-review-${review.name.split(" ")[0].toLowerCase()}`}>
            <p style={{ margin: 0 }}><strong>{review.name}</strong> ({review.role}) — {review.position}</p>
            {review.discussion_points && <p style={{ margin: "4px 0 0" }}>To discuss: {review.discussion_points}</p>}
            {review.contribution && <p style={{ margin: "4px 0 0" }}>Contribution interest: {review.contribution}</p>}
            {review.support_needs && <p style={{ margin: "4px 0 0" }}>Support needs: {review.support_needs}</p>}
          </div>
        ))}
      </section>

      <section className="member-card" data-testid="am4-guide-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h2 style={{ margin: 0 }}>Plan Adoption Facilitation Guide</h2>
          <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid="am4-guide-status">{guideStatus === "NONE" ? "NOT GENERATED" : guideStatus.toUpperCase()}</span>
        </div>
        {adoption.guide_error && guideStatus === "Failed" && <p className="submit-error">Generation failed. Please try again.</p>}
        {guideStatus === "Generating" || generating ? (
          <p data-testid="am4-generating">Generating your Facilitation Guide from the strategy and your Board's actual feedback… It will appear here automatically.</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
            <button type="button" className="button" onClick={generate} data-testid="am4-generate-button">{adoption.guide_text ? "REGENERATE" : "GENERATE MY PLAN ADOPTION FACILITATION GUIDE"}</button>
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
        <p className="eyebrow" style={{ marginTop: 10 }}>This guide is your internal facilitation resource. It is not sent to Board Members.</p>
      </section>

      <section className="member-card" data-testid="am4-conclusion-card">
        <h2>Plan Adoption Conclusion</h2>
        <p>After the Board discussion, record in your own words what happened, what was agreed, what changed and what still needs attention.</p>
        <textarea rows={6} style={{ width: "100%" }} value={conclusion} onChange={(e) => { setConclusion(e.target.value); setConclusionSaved(false); }} data-testid="am4-conclusion-text" />
        <button type="button" className="button" onClick={saveConclusion} data-testid="am4-save-conclusion" style={{ marginTop: 10 }}>{conclusionSaved ? "Conclusion Saved" : "SAVE CONCLUSION"}</button>
      </section>

      <section className="member-card" data-testid="am4-plan-status-card">
        <h2>Plan Status</h2>
        <p>Record the Board's adoption outcome. This is your recorded organizational outcome — it is not inferred from the reviews.</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {PLAN_STATUSES.map((status) => (
            <label className={`choice ${adoption.plan_status === status ? "selected" : ""}`} key={status}>
              <input type="radio" name="plan-status" checked={adoption.plan_status === status} onChange={() => setPlanStatus(status)} data-testid={`am4-plan-status-${status.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
              <span>{status}</span>
            </label>
          ))}
        </div>
        {adoption.plan_status === "Further Review Needed" && (
          <p className="submit-error" style={{ marginTop: 12 }} data-testid="am4-blocked-note">The strategy must be resolved and adopted before execution tools are generated. Module 5 remains locked. Your strategy and Board reviews are preserved.</p>
        )}
        {adoption.plan_status === "Adopted as Presented" && adoption.finalized && (
          <p style={{ marginTop: 12 }} data-testid="am4-adopted-note"><strong>The strategy version your Board reviewed is now the adopted strategy.</strong></p>
        )}
        {adoption.plan_status === "Adopted With Changes" && (
          <div style={{ marginTop: 14 }} data-testid="am4-changes-area">
            <p>Edit the strategy to reflect what was actually agreed during the adoption discussion, then finalize it. The version your Board reviewed and their reviews are preserved separately.</p>
            <textarea rows={14} style={{ width: "100%" }} value={adoptedDraft} onChange={(e) => setAdoptedDraft(e.target.value)} data-testid="am4-adopted-draft" />
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              <button type="button" className="button button-outline" onClick={saveAdoptedDraft} data-testid="am4-save-adopted-draft">SAVE EDITS</button>
              <button type="button" className="button" onClick={finalize} data-testid="am4-finalize-button">FINALIZE ADOPTED PLAN</button>
            </div>
            {adoption.finalized && <p style={{ marginTop: 10 }} data-testid="am4-finalized-note"><strong>Adopted plan finalized.</strong></p>}
          </div>
        )}
      </section>

      <section className="member-card" data-testid="am4-responsibilities">
        <h2>Board Member Responsibilities</h2>
        <p>Record what each Board Member actually agreed to carry during the adoption discussion. Nothing is assigned automatically.</p>
        {data.members.map((member) => {
          const edit = respEdits[member.participant_id] || {};
          return (
            <article key={member.participant_id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 16 }} data-testid={`am4-member-${member.participant_id}`}>
              <h3 style={{ margin: 0 }}>{member.name} <span className="eyebrow">({member.role})</span></h3>
              {member.participation_activities.length > 0 && <p style={{ margin: "6px 0 0" }}><strong>Willing to help with:</strong> {member.participation_activities.join(", ")}</p>}
              {member.ownership_interest && <p style={{ margin: "4px 0 0" }}><strong>Ownership interest:</strong> {member.ownership_interest}</p>}
              {member.review_contribution && <p style={{ margin: "4px 0 0" }}><strong>Review contribution interest:</strong> {member.review_contribution}</p>}
              {member.support_needed.length > 0 && <p style={{ margin: "4px 0 0" }}><strong>Support requested:</strong> {member.support_needed.join(", ")}</p>}
              <label className="field" style={{ marginTop: 12 }}><span>Agreed Fundraising Responsibility</span>
                <textarea rows={3} value={edit.agreed_responsibility ?? member.agreed_responsibility} onChange={(e) => setRespEdits({ ...respEdits, [member.participant_id]: { ...edit, agreed_responsibility: e.target.value } })} data-testid={`am4-responsibility-${member.participant_id}`} />
              </label>
              <label className="field"><span>Responsibility Status</span>
                <select value={edit.responsibility_status ?? member.responsibility_status} onChange={(e) => setRespEdits({ ...respEdits, [member.participant_id]: { ...edit, responsibility_status: e.target.value } })} data-testid={`am4-resp-status-${member.participant_id}`}>
                  {RESP_STATUSES.map((status) => <option key={status}>{status}</option>)}
                </select>
              </label>
              <button type="button" className="button" onClick={() => saveResponsibility(member)} data-testid={`am4-save-resp-${member.participant_id}`}>{savedResp === member.participant_id ? "Saved" : "SAVE RESPONSIBILITY"}</button>
            </article>
          );
        })}
      </section>

      <section style={{ textAlign: "center", margin: "26px 0" }}>
        {data.module5_ready ? (
          <Link className="button rwr-cta-button" to="/app/activation/self-guided/module/5" data-testid="am4-continue-module5">CONTINUE TO MODULE 5 — EQUIP THE BOARD TO EXECUTE</Link>
        ) : (
          <p className="eyebrow" data-testid="am4-module5-locked">Module 5 opens once your Plan Adoption Conclusion is saved and the plan is adopted and finalized.</p>
        )}
      </section>

      {showEdit && (
        <Modal onClose={() => setShowEdit(false)} testId="am4-edit-modal">
          <h2>Edit Facilitation Guide</h2>
          <textarea rows={22} style={{ width: "100%" }} value={editText} onChange={(e) => setEditText(e.target.value)} data-testid="am4-edit-text" />
          <button type="button" className="button" onClick={saveGuide} data-testid="am4-save-button">SAVE</button>
        </Modal>
      )}
    </div>
  );
}
