import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Download, X } from "lucide-react";
import { memberApi } from "./api";
import { activationM5Text } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const dialogStyle = { background: "#fff", maxWidth: 780, width: "100%", padding: "28px", borderRadius: 8, position: "relative" };

export default function ActivationModule5() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState("");
  const pollRef = useRef(null);

  const load = useCallback(() => {
    memberApi.get("/activation/toolkit").then((res) => setData(res.data)).catch(() => setError("We could not load your execution toolkit workspace."));
  }, []);
  useEffect(load, [load]);

  useEffect(() => {
    if (data?.toolkit?.status === "Generating" && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await memberApi.get("/activation/toolkit");
          if (res.data.toolkit.status !== "Generating") {
            clearInterval(pollRef.current); pollRef.current = null;
            setGenerating(false); setData(res.data);
          }
        } catch { /* keep polling */ }
      }, 3000);
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [data?.toolkit?.status]);

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

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">Loading your execution toolkit workspace…</p>;

  const toolkit = data.toolkit;

  return (
    <div data-testid="activation-module5">
      <section className="member-card" data-testid="am5-intro">
        <h2>{activationM5Text.h_giveYourBoardTheTools}</h2>
        <p>The Board has helped build the fundraising plan, reviewed the strategy and agreed on the direction.</p>
        <p>Now give Board Members practical tools they can use to begin carrying their part of the fundraising work.</p>
      </section>

      {!data.gate_open ? (
        <section className="member-card" data-testid="am5-locked">
          <h2>{activationM5Text.h_thePlanMustBeAdopted}</h2>
          <p>The Fundraising Strategy Plan must be resolved and adopted — with your Plan Adoption Conclusion recorded — before execution tools are generated.</p>
          {data.plan_status === "Further Review Needed" && <p data-testid="am5-further-review-note">Your recorded plan status is <strong>Further Review Needed</strong>. Return to Module 4 to work through the outstanding items and record adoption.</p>}
          <Link className="button" to="/app/activation/self-guided/module/4" data-testid="am5-back-to-module4">GO TO MODULE 4 — FACILITATE PLAN ADOPTION</Link>
        </section>
      ) : (
        <>
          <section className="member-card" data-testid="am5-toolkit-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
              <h2 style={{ margin: 0 }}>Board Fundraising Execution Toolkit</h2>
              <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid="am5-toolkit-status">{toolkit.status === "NONE" ? "NOT GENERATED" : toolkit.status.toUpperCase()}</span>
            </div>
            <p style={{ marginTop: 10 }}>One organization-level set of practical emails, text messages, call scripts and stewardship tools built from your adopted strategy and the responsibilities your Board actually agreed to carry.</p>
            {toolkit.status === "Failed" && <p className="submit-error">Generation failed. Please try again.</p>}
            {toolkit.status === "Generating" || generating ? (
              <p data-testid="am5-generating">Generating your Board Fundraising Execution Toolkit… It will appear here automatically.</p>
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
              <p>Your Board helped build the fundraising plan, reviewed it, adopted the direction and now has practical tools to begin taking action.</p>
              <p>The next step is to go to your Fundraising Board Dashboard, where you can see each Board Member's responsibility and create their individual Fundraising Portfolio.</p>
              <Link className="button rwr-cta-button" to="/app/activation/self-guided/my-fundraising-board" data-testid="am5-go-to-board">GO TO MY FUNDRAISING BOARD</Link>
            </section>
          )}
        </>
      )}

      {showEdit && (
        <div style={overlayStyle} data-testid="am5-edit-modal">
          <div style={dialogStyle}>
            <button type="button" onClick={() => setShowEdit(false)} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid="am5-edit-modal-close"><X size={20} /></button>
            <h2>{activationM5Text.h_editExecutionToolkit}</h2>
            <textarea rows={22} style={{ width: "100%" }} value={editText} onChange={(e) => setEditText(e.target.value)} data-testid="am5-edit-text" />
            <button type="button" className="button" onClick={saveEdit} data-testid="am5-save-button">SAVE</button>
          </div>
        </div>
      )}
    </div>
  );
}
