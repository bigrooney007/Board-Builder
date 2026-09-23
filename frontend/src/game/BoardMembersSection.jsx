import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { memberApi } from "@/member/api";

const statusClass = (status) => {
  if (status === "Game Completed") return "completed";
  if (status === "Game In Progress" || status === "Game Started") return "progress";
  if (status === "Invited") return "invited";
  return "";
};

const remainingText = (availableAt) => {
  if (!availableAt) return "";
  const diff = new Date(availableAt).getTime() - Date.now();
  if (diff <= 0) return "";
  const hours = Math.floor(diff / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  return `${hours}h ${minutes}m`;
};

const MemberForm = ({ initial, onSave, onCancel, busy, saveLabel }) => {
  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const submit = () => {
    if (!form.full_name.trim()) { setError("Full name is required."); return; }
    if (!form.email.trim()) { setError("Email address is required."); return; }
    setError("");
    onSave(form, setError);
  };
  return (
    <div style={{ marginTop: 10 }} data-testid="bfg-bm-form">
      <label className="bfg-field"><span>Full Name <b>*</b></span>
        <input value={form.full_name} onChange={set("full_name")} data-testid="bfg-bm-name" />
      </label>
      <label className="bfg-field"><span>Email Address <b>*</b></span>
        <input type="email" value={form.email} onChange={set("email")} data-testid="bfg-bm-email" />
      </label>
      <label className="bfg-field"><span>Board Title</span>
        <input value={form.board_title} placeholder="Board Chair, Treasurer, Secretary, Board Member" onChange={set("board_title")} data-testid="bfg-bm-title" />
      </label>
      <label className="bfg-field"><span>Participant Role <b>*</b></span>
        <select value={form.participant_role || "board_member"} onChange={set("participant_role")} data-testid="bfg-bm-role">
          <option value="board_member">Board Member</option>
          <option value="staff">Staff / Team Member</option>
          <option value="volunteer">Volunteer</option>
          <option value="other_leader">Other Organizational Leader</option>
        </select>
      </label>
      {error && <p className="bfg-error">{error}</p>}
      <div className="bfg-form-actions">
        <button className="bfg-btn bfg-btn-ghost" onClick={onCancel} data-testid="bfg-bm-cancel">Cancel</button>
        <button className="bfg-btn bfg-btn-primary" onClick={submit} disabled={busy} data-testid="bfg-bm-save">{busy ? "Saving…" : saveLabel}</button>
      </div>
    </div>
  );
};

const ResponsesView = ({ memberId }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    memberApi.get(`/game/board-members/${memberId}/responses`).then((r) => setData(r.data)).catch(() => setData({ responses: [] }));
  }, [memberId]);
  if (!data) return <p className="bfg-note">Loading responses…</p>;
  if (!data.responses.length) return <p className="bfg-note">No responses yet.</p>;
  return (
    <div className="bfg-responses-view" data-testid="bfg-responses-view">
      {data.responses.map((response) => (
        <div key={response.section_id} style={{ marginBottom: 14 }}>
          <h4>{response.section_id}. {response.section_title} {response.completed ? "— Completed" : "— In Progress"}</h4>
          {(response.first_response || []).length > 0 && (
            <><p className="bfg-note" style={{ marginTop: 6 }}>First move:</p>
            <ul>{response.first_response.map((idea, index) => <li key={index}>{idea}</li>)}</ul></>
          )}
          {Object.entries(response.guided_selections || {}).map(([group, items]) => items.length > 0 && (
            <div key={group}><p className="bfg-note" style={{ marginTop: 6 }}>Selected ({group.replace(/_/g, " ")}):</p>
              <ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></div>
          ))}
          {Object.entries(response.additional_ideas || {}).map(([group, items]) => items.length > 0 && (
            <div key={group}><p className="bfg-note" style={{ marginTop: 6 }}>Additional ideas ({group.replace(/_/g, " ")}):</p>
              <ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></div>
          ))}
          {Object.entries(response.stage_responses || {}).map(([stage, value]) => (Array.isArray(value) ? value.length > 0 : value) && (
            <div key={stage}><p className="bfg-note" style={{ marginTop: 6 }}>{stage.replace(/_/g, " ").toUpperCase()}:</p>
              <ul>{(Array.isArray(value) ? value : [value]).map((item, index) => <li key={index}>{item}</li>)}</ul></div>
          ))}
          {(response.final_response || []).length > 0 && (
            <><p className="bfg-note" style={{ marginTop: 6 }}>Final ideas:</p>
            <ul>{response.final_response.map((idea, index) => <li key={index}>{idea}</li>)}</ul></>
          )}
          {(response.preferences || []).length > 0 && (
            <><p className="bfg-note" style={{ marginTop: 6 }}>Selected ways to help:</p>
            <ul>{response.preferences.map((pref, index) => (
              <li key={index}>{pref.option}{pref.involvement ? ` — ${pref.involvement}` : ""}{pref.note ? ` (${pref.note})` : ""}</li>
            ))}</ul></>
          )}
          {(response.do_not_want || []).length > 0 && (
            <><p className="bfg-note" style={{ marginTop: 6 }}>Prefers NOT to:</p>
            <ul>{response.do_not_want.map((item, index) => <li key={index}>{item}</li>)}</ul></>
          )}
        </div>
      ))}
    </div>
  );
};

export const BoardMembersSection = ({ onChanged = () => {} }) => {
  const [members, setMembers] = useState([]);
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState("");
  const [viewingId, setViewingId] = useState("");
  const [confirmRemove, setConfirmRemove] = useState(null);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [copiedId, setCopiedId] = useState("");
  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("response") || "";
    if (requested) setViewingId(requested);
  }, []);

  const load = useCallback(async () => {
    try {
      const response = await memberApi.get("/game/board-members");
      setMembers(response.data.board_members || []);
      onChanged(response.data.board_members || []);
    } catch { /* ignore */ }
  }, [onChanged]);
  useEffect(() => { load(); }, [load]);

  const origin = { origin_url: window.location.origin };
  const run = async (key, fn, successMessage) => {
    setBusy(key); setNotice("");
    try { await fn(); if (successMessage) setNotice(successMessage); await load(); }
    catch (err) {
      const detail = err.response?.data?.detail;
      if (detail === "meeting_details_required") {
        setNotice("ADD YOUR BOARD MEETING AND FUNDING DEADLINE FIRST — Save the meeting date, time and the date the money is needed so the invitation carries the full context and the execution plan can be built to the deadline.");
        document.querySelector('[data-tour="prepare-meeting"]')?.scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        setNotice(typeof detail === "string" ? detail : "Something went wrong. Please try again.");
      }
    }
    setBusy("");
  };

  const addMember = (form, setError) => {
    setBusy("add");
    memberApi.post("/game/board-members", form)
      .then(() => { setAdding(false); load(); })
      .catch((err) => setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not add this board member."))
      .finally(() => setBusy(""));
  };

  const editMember = (memberId) => (form, setError) => {
    setBusy("edit");
    memberApi.put(`/game/board-members/${memberId}`, form)
      .then(() => { setEditingId(""); load(); })
      .catch((err) => setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not save changes."))
      .finally(() => setBusy(""));
  };

  const copyLink = async (member) => {
    const link = `${window.location.origin}/play/${member.token}`;
    try { await navigator.clipboard.writeText(link); } catch {
      window.prompt("Copy this game link:", link);
    }
    setCopiedId(member.member_id);
    setTimeout(() => setCopiedId(""), 2500);
  };

  const notInvited = members.filter((member) => member.invitation_status !== "invited").length;
  const eligibleReminders = members.filter((member) =>
    member.invitation_status === "invited" && member.sections_completed < member.total_sections && !remainingText(member.reminder_available_at)).length;

  return (
    <section id="bfg-board-members-section" className="bfg-panel" data-testid="bfg-board-members-section">
      <div className="bfg-panel-head">
        <div>
          <><p className="bfg-eyebrow">BOARD PARTICIPANTS</p><h2>Invite Board Members And Others In Your Organization</h2></>
          <p className="bfg-panel-sub">Add the people you want in the game, send or resend invitations, copy their game link, and use the person-specific call script when you need to follow up. Save your meeting details first so every invitation includes your Board Fundraising Day/Night.</p>
        </div>
        <div className="bfg-bm-actions" style={{ marginTop: 0 }}>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => { setAdding(!adding); setEditingId(""); }} data-testid="bfg-add-board-member-btn">Add Board Member</button>
          {notInvited > 0 && (
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={busy === "invite-all"}
              onClick={() => run("invite-all", () => memberApi.post("/game/board-members/invite-all", origin), "Invitations sent.")}
              data-testid="bfg-invite-all-btn">Send Invitations To All</button>
          )}
          {eligibleReminders > 0 && (
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={busy === "remind-all"}
              onClick={() => run("remind-all", () => memberApi.post("/game/board-members/remind-all", origin), "Reminders sent.")}
              data-testid="bfg-remind-all-btn">Remind Everyone Who Hasn't Finished</button>
          )}
        </div>
      </div>

      {adding && (
        <MemberForm initial={{ full_name: "", email: "", board_title: "" }} onSave={addMember}
          onCancel={() => setAdding(false)} busy={busy === "add"} saveLabel="Add Board Member" />
      )}
      {notice && <p className="bfg-note" data-testid="bfg-bm-notice">{notice}</p>}

      <div className="bfg-bm-table">
        {members.length === 0 && !adding && <p className="bfg-note">No board members added yet.</p>}
        {members.map((member) => {
          const remaining = remainingText(member.reminder_available_at);
          const completed = member.sections_completed >= member.total_sections;
          return (
            <div className="bfg-bm-row" key={member.member_id} data-testid={`bfg-bm-row-${member.member_id}`}>
              <div className="bfg-bm-top">
                <div>
                  <strong>{member.full_name}</strong>{member.board_title && <small> — {member.board_title}</small>}
                  <div><small>{member.email}</small></div>
                </div>
                <span className={`bfg-status-pill ${statusClass(member.status)}`} data-testid={`bfg-bm-status-${member.member_id}`}>{member.status}</span>
              </div>
              <p className="bfg-bm-progress">{member.sections_completed} of {member.total_sections} sections complete</p>
              {editingId === member.member_id ? (
                <MemberForm initial={{ full_name: member.full_name, email: member.email, board_title: member.board_title }}
                  onSave={editMember(member.member_id)} onCancel={() => setEditingId("")} busy={busy === "edit"} saveLabel="Save Changes" />
              ) : (
                <div className="bfg-bm-actions">
                  {member.invitation_status !== "invited" && (
                    <button className="bfg-btn bfg-btn-primary bfg-btn-sm" disabled={busy === `invite-${member.member_id}`}
                      onClick={() => run(`invite-${member.member_id}`, () => memberApi.post(`/game/board-members/${member.member_id}/invite`, origin), "Invitation sent.")}
                      data-testid={`bfg-invite-btn-${member.member_id}`}>Send Invitation</button>
                  )}
                  {member.invitation_status === "invited" && !completed && (
                    remaining ? (
                      <span className="bfg-note" data-testid={`bfg-reminder-wait-${member.member_id}`}>Reminder sent. Available again in {remaining}.</span>
                    ) : (
                      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={busy === `remind-${member.member_id}`}
                        onClick={() => run(`remind-${member.member_id}`, () => memberApi.post(`/game/board-members/${member.member_id}/remind`, origin), "Reminder sent.")}
                        data-testid={`bfg-remind-btn-${member.member_id}`}>Send Reminder</button>
                    )
                  )}
                  <Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to={`/game/host/call-script?member=${member.member_id}`}
                    data-testid={`bfg-call-script-${member.member_id}`}>Call Script</Link>
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => copyLink(member)} data-testid={`bfg-copy-link-${member.member_id}`}>
                    {copiedId === member.member_id ? "Link Copied" : "Copy Game Link"}
                  </button>
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setViewingId(viewingId === member.member_id ? "" : member.member_id)}
                    data-testid={`bfg-view-responses-${member.member_id}`}>
                    {viewingId === member.member_id ? "Hide Responses" : "View Responses"}
                  </button>
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => { setEditingId(member.member_id); setAdding(false); }}
                    data-testid={`bfg-edit-bm-${member.member_id}`}>Edit</button>
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setConfirmRemove(member)} data-testid={`bfg-remove-bm-${member.member_id}`}>Remove</button>
                </div>
              )}
              {viewingId === member.member_id && <ResponsesView memberId={member.member_id} />}
              {confirmRemove?.member_id === member.member_id && (
                <div className="bfg-error" style={{ marginTop: 12 }} data-testid="bfg-remove-confirm">
                  {member.game_started
                    ? "This board member has already started the game. Removing them will remove them from this Game Night but will preserve their existing responses. Continue?"
                    : `Remove ${member.full_name} from this Game Night?`}
                  <div className="bfg-bm-actions">
                    <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setConfirmRemove(null)} data-testid="bfg-remove-cancel">Cancel</button>
                    <button className="bfg-btn bfg-btn-primary bfg-btn-sm" disabled={busy === `remove-${member.member_id}`}
                      onClick={() => { setConfirmRemove(null); run(`remove-${member.member_id}`, () => memberApi.delete(`/game/board-members/${member.member_id}`)); }}
                      data-testid="bfg-remove-confirm-btn">Remove From Game Night</button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default BoardMembersSection;
