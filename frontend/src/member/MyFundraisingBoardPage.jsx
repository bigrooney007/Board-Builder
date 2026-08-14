import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Mail, X } from "lucide-react";
import { memberApi } from "./api";
import { MemberShell } from "./MemberShell";
import { myFundraisingBoardText } from "../content/appContent";

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

export default function MyFundraisingBoardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [viewDoc, setViewDoc] = useState(null);
  const [editFp, setEditFp] = useState(null);
  const [emailPrev, setEmailPrev] = useState(null);
  const [sending, setSending] = useState(false);
  const [polling, setPolling] = useState(false);

  const load = useCallback(() => {
    memberApi.get("/activation/my-board").then((res) => setData(res.data)).catch((err) => {
      setError(err.response?.status === 403 ? "Your account does not include access to this program." : "We could not load My Fundraising Board.");
    });
  }, []);
  useEffect(load, [load]);

  useEffect(() => {
    if (!data) return undefined;
    const generating = data.members.some((m) => m.fp_status === "Generating");
    if (!generating) { setPolling(false); return undefined; }
    setPolling(true);
    const timer = setTimeout(load, 3500);
    return () => clearTimeout(timer);
  }, [data, load]);

  const generate = async (member) => {
    try { await memberApi.post(`/activation/members/${member.participant_id}/portfolio/generate`); load(); } catch (err) {
      window.alert(err.response?.data?.detail || "Generation could not start.");
    }
  };
  const saveFp = async () => {
    try { await memberApi.put(`/activation/members/${editFp.participant_id}/portfolio`, { text: editFp.text }); setEditFp(null); load(); } catch { /* keep open */ }
  };
  const approveFp = async (member) => { try { await memberApi.post(`/activation/members/${member.participant_id}/portfolio/approve`); load(); } catch { /* ignore */ } };
  const prepareEmail = (member) => {
    memberApi.get(`/activation/members/${member.participant_id}/portfolio/email-preview`).then((res) => setEmailPrev({ ...res.data, member })).catch((err) => window.alert(err.response?.data?.detail || "Approve the portfolio first."));
  };
  const sendFp = async () => {
    setSending(true);
    try { await memberApi.post(`/activation/members/${emailPrev.member.participant_id}/portfolio/send`); setEmailPrev(null); load(); } catch (err) {
      window.alert(err.response?.data?.detail || "The email could not be sent.");
    }
    setSending(false);
  };

  if (error) return <MemberShell><main className="member-page"><p className="submit-error" data-testid="mfb-error">{error}</p></main></MemberShell>;
  if (!data) return <MemberShell><main className="member-page"><p className="sh-loading">Loading My Fundraising Board…</p></main></MemberShell>;

  return (
    <MemberShell>
      <main className="member-page" data-testid="my-fundraising-board">
        <header className="member-page-heading">
          <p className="eyebrow">Board Fundraising Activation</p>
          <h1>My Fundraising Board</h1>
          <p data-testid="mfb-supporting">Your Board helped build the fundraising plan, reviewed it, adopted the direction and agreed how members will help carry the work. This is where you can see what each Board Member owns, equip them with their individual Fundraising Portfolio and keep the Board connected to the fundraising strategy.</p>
        </header>

        <section className="member-card" data-testid="mfb-counts">
          <p style={{ margin: 0 }}>
            <strong>{data.counts.participating}</strong> Board Members Participating · <strong>{data.counts.responsibility_agreed}</strong> Responsibility Agreed · <strong>{data.counts.follow_up_needed}</strong> Follow-Up Needed · <strong>{data.counts.portfolios_approved}</strong> Portfolios Approved · <strong>{data.counts.portfolios_sent}</strong> Portfolios Sent
          </p>
        </section>

        <section className="member-card" data-testid="mfb-resources">
          <h2>{myFundraisingBoardText.h_yourFundraisingDirection}</h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" className="button" onClick={() => setViewDoc({ title: "Final Adopted Fundraising Strategy Plan", text: data.adopted_strategy })} disabled={!data.adopted_strategy} data-testid="mfb-view-strategy">FINAL ADOPTED FUNDRAISING STRATEGY PLAN</button>
            <button type="button" className="button button-outline" onClick={() => setViewDoc({ title: "Approved Board Fundraising Execution Toolkit", text: data.toolkit_text })} disabled={!data.toolkit_text} data-testid="mfb-view-toolkit">APPROVED BOARD FUNDRAISING EXECUTION TOOLKIT</button>
          </div>
          {!data.ready && <p className="eyebrow" style={{ marginTop: 10 }} data-testid="mfb-not-ready">Complete plan adoption (Module 4) and approve your Execution Toolkit (Module 5) to unlock your full Fundraising Board.</p>}
        </section>

        <section data-testid="mfb-members">
          {data.members.map((member) => {
            const canGenerate = member.responsibility_status === "Responsibility Agreed" && member.agreed_responsibility;
            return (
              <article className="member-card" key={member.participant_id} data-testid={`mfb-member-${member.participant_id}`}>
                <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                  <div>
                    <h2 style={{ margin: 0 }}>{member.name}</h2>
                    <p style={{ margin: "4px 0 0" }}>{member.role || "Board Member"} · {member.email}</p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999, display: "inline-block" }} data-testid={`mfb-resp-status-${member.participant_id}`}>{member.responsibility_status}</span>
                    <p className="eyebrow" style={{ marginTop: 6 }} data-testid={`mfb-fp-status-${member.participant_id}`}>Portfolio: {member.fp_status === "NONE" ? "NOT GENERATED" : member.fp_status.toUpperCase()}{member.fp_sent_at ? ` · sent ${new Date(member.fp_sent_at).toLocaleDateString()} (v${member.fp_sent_version})` : ""}</p>
                  </div>
                </div>
                {member.agreed_responsibility ? (
                  <p style={{ marginTop: 10 }} data-testid={`mfb-responsibility-${member.participant_id}`}><strong>Agreed Fundraising Responsibility:</strong> {member.agreed_responsibility}</p>
                ) : (
                  <p style={{ marginTop: 10 }} data-testid={`mfb-no-responsibility-${member.participant_id}`}>No fundraising responsibility has been recorded for this member yet.{member.responsibility_status === "Follow-Up Needed" && " Follow up and record what is agreed."} <Link to="/app/activation/self-guided/module/4">Go to Module 4 responsibilities</Link>.</p>
                )}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                  {member.fp_status === "Generating" ? (
                    <p data-testid={`mfb-generating-${member.participant_id}`}>Generating Fundraising Portfolio…{polling ? "" : ""}</p>
                  ) : (
                    <>
                      <button type="button" className="button" onClick={() => generate(member)} disabled={!canGenerate || !data.ready} title={canGenerate ? "" : "Record an agreed responsibility first"} data-testid={`mfb-generate-fp-${member.participant_id}`}>{member.fp_text ? "REGENERATE FUNDRAISING PORTFOLIO" : "GENERATE FUNDRAISING PORTFOLIO"}</button>
                      {member.fp_text && (
                        <>
                          <button type="button" className="button button-outline" onClick={() => setViewDoc({ title: `Fundraising Portfolio — ${member.name}`, text: member.fp_text })} data-testid={`mfb-view-fp-${member.participant_id}`}>VIEW ONLINE</button>
                          <button type="button" className="button button-outline" onClick={() => setEditFp({ participant_id: member.participant_id, text: member.fp_text })} data-testid={`mfb-edit-fp-${member.participant_id}`}>EDIT</button>
                          {member.fp_status === "Draft" && <button type="button" className="button" onClick={() => approveFp(member)} data-testid={`mfb-approve-fp-${member.participant_id}`}>APPROVE</button>}
                          <a className="button button-outline" href={`${API}/activation/members/${member.participant_id}/portfolio/pdf`} target="_blank" rel="noreferrer" data-testid={`mfb-pdf-fp-${member.participant_id}`}><Download size={15} /> PDF</a>
                          {(member.fp_status === "Approved" || member.fp_status === "SENT") && (
                            <button type="button" className="button" onClick={() => prepareEmail(member)} data-testid={`mfb-prepare-email-${member.participant_id}`}><Mail size={15} /> PREPARE PORTFOLIO EMAIL</button>
                          )}
                        </>
                      )}
                    </>
                  )}
                </div>
              </article>
            );
          })}
        </section>

        {data.ready && (
          <section className="member-card" style={{ textAlign: "center" }} data-testid="mfb-completion">
            <h2>{myFundraisingBoardText.h_yourFundraisingBoardIsReady}</h2>
            <p>Your Board has helped build the fundraising plan, reviewed and adopted the strategy, agreed how members will help carry the work, and now has the tools and individual direction needed to begin taking action.</p>
            <p>Your job now is to keep the plan moving, support Board Members in carrying their responsibilities and keep fundraising connected to the mission.</p>
          </section>
        )}

        <section className="member-card" data-testid="mfb-cross-sells">
          <h2>{myFundraisingBoardText.h_stillMissingTheRightPeople}</h2>
          <p>If the Board still has skill, experience, capacity or relationship gaps, recruit the right people to complete the Board.</p>
          <Link className="button" to="/recruit-your-board-yourself" data-testid="mfb-cross-recruit">RECRUIT NEW BOARD MEMBERS</Link>
          <h2 style={{ marginTop: 22 }}>Have Board Members Who Still Are Not Carrying Their Responsibility?</h2>
          <p>If some Board Members remain disengaged, reactivate them so those ready to serve can stand up and carry responsibility, while those no longer prepared to serve can be dealt with appropriately.</p>
          <Link className="button button-outline" to="/reactivate-your-board-yourself" data-testid="mfb-cross-reactivate">REACTIVATE MY BOARD</Link>
        </section>

        {viewDoc && (
          <Modal onClose={() => setViewDoc(null)} testId="mfb-view-modal">
            <h2>{viewDoc.title}</h2>
            <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 18, maxHeight: 480, overflowY: "auto" }} data-testid="mfb-view-text">{viewDoc.text}</div>
          </Modal>
        )}
        {editFp && (
          <Modal onClose={() => setEditFp(null)} testId="mfb-edit-modal">
            <h2>{myFundraisingBoardText.h_editFundraisingPortfolio}</h2>
            <textarea rows={20} style={{ width: "100%" }} value={editFp.text} onChange={(e) => setEditFp({ ...editFp, text: e.target.value })} data-testid="mfb-edit-text" />
            <button type="button" className="button" onClick={saveFp} data-testid="mfb-save-fp">SAVE</button>
          </Modal>
        )}
        {emailPrev && (
          <Modal onClose={() => setEmailPrev(null)} testId="mfb-email-modal">
            <h2>{myFundraisingBoardText.h_portfolioEmail}</h2>
            <p><strong>To:</strong> {emailPrev.to_name} &lt;{emailPrev.to_email}&gt;</p>
            <p><strong>Subject:</strong> <span data-testid="mfb-email-subject">{emailPrev.subject}</span></p>
            <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 14, borderRadius: 6, maxHeight: 300, overflowY: "auto" }} data-testid="mfb-email-body">{emailPrev.body}</div>
            <p style={{ marginTop: 10 }}><strong>Secure Portfolio Link:</strong> <span style={{ wordBreak: "break-all" }} data-testid="mfb-email-link">{emailPrev.form_link}</span></p>
            <button type="button" className="button" onClick={sendFp} disabled={sending} data-testid="mfb-send-confirm">{sending ? "Sending…" : "SEND"}</button>
          </Modal>
        )}
      </main>
    </MemberShell>
  );
}
