import { Fragment, useCallback, useEffect, useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

const GAME_VIDEO_KEYS = ["game_homepage", "game_welcome"];

const TextField = ({ label, value, onChange, testId, textarea, hint }) => (
  <label className="field" style={{ display: "block", marginTop: 14 }}>
    <span style={{ display: "block", fontWeight: 600, marginBottom: 6 }}>{label}</span>
    {textarea ? (
      <textarea rows={3} style={{ width: "100%" }} value={value} onChange={(event) => onChange(event.target.value)} data-testid={testId} />
    ) : (
      <input style={{ width: "100%" }} value={value} onChange={(event) => onChange(event.target.value)} data-testid={testId} />
    )}
    {hint && <small style={{ color: "#666" }}>{hint}</small>}
  </label>
);

const VideosManager = () => {
  const [videos, setVideos] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    const response = await client.get("/admin/flow-videos");
    const rows = (response.data.videos || []).filter((video) => GAME_VIDEO_KEYS.includes(video.key));
    setVideos(rows);
    setDrafts(Object.fromEntries(rows.map((video) => [video.key, video.url])));
  }, []);
  useEffect(() => { load().catch(() => {}); }, [load]);
  const save = async (key) => {
    setMessage("");
    try {
      await client.put(`/admin/flow-videos/${key}`, { url: drafts[key] || "" });
      setMessage("Video saved.");
      await load();
    } catch (err) {
      setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not save video.");
    }
  };
  return (
    <div className="admin-import-panel" style={{ marginTop: 20 }} data-testid="game-videos-panel">
      <h3>Game Videos</h3>
      <p style={{ color: "#555" }}>Paste a YouTube link (or 11-character video ID). Leave empty to show the "Video coming soon" placeholder.</p>
      {videos.map((video) => (
        <div key={video.key} style={{ marginTop: 12 }}>
          <strong>{video.name}</strong>
          <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
            <input style={{ flex: 1 }} value={drafts[video.key] ?? ""} onChange={(event) => setDrafts({ ...drafts, [video.key]: event.target.value })} data-testid={`game-video-input-${video.key}`} />
            <button className="button button-small" onClick={() => save(video.key)} data-testid={`game-video-save-${video.key}`}>Save</button>
          </div>
        </div>
      ))}
      {message && <p style={{ marginTop: 10 }} data-testid="game-videos-message">{message}</p>}
    </div>
  );
};

const modalOverlayStyle = { position: "fixed", inset: 0, background: "rgba(2, 6, 23, 0.6)", display: "grid", placeItems: "center", zIndex: 90, padding: 20 };
const modalStyle = { background: "#fff", borderRadius: 12, padding: 26, maxWidth: 480, width: "100%", boxShadow: "0 18px 50px rgba(0,0,0,0.25)" };

const fmtStamp = (raw) => {
  if (!raw) return "";
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleString("en-US", { year: "numeric", month: "long", day: "numeric", hour: "numeric", minute: "2-digit" });
};

const CustomersTable = () => {
  const [rows, setRows] = useState([]);
  const [expandedId, setExpandedId] = useState("");
  const [unlockTarget, setUnlockTarget] = useState(null);
  const [revokeTarget, setRevokeTarget] = useState(null);
  const [successInfo, setSuccessInfo] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    client.get("/admin/game/customers").then((r) => setRows(r.data.customers || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const unlock = async () => {
    setBusy(true); setMessage("");
    try {
      const response = await client.post(`/admin/game/customers/${unlockTarget.user_id}/unlock-testing`);
      setSuccessInfo({ user_id: unlockTarget.user_id, unlocked_at: response.data.unlocked_at });
      setUnlockTarget(null);
      load();
    } catch (err) {
      setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not unlock this account.");
      setUnlockTarget(null);
    }
    setBusy(false);
  };

  const revoke = async () => {
    setBusy(true); setMessage("");
    try {
      await client.post(`/admin/game/customers/${revokeTarget.user_id}/revoke-testing`);
      setMessage("Testing access revoked.");
      load();
    } catch (err) {
      setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not revoke testing access.");
    }
    setRevokeTarget(null);
    setBusy(false);
  };

  return (
    <div className="admin-import-panel" style={{ marginTop: 20 }} data-testid="game-customers-panel">
      <h3>Game Customers</h3>
      {message && <p style={{ marginTop: 8 }} data-testid="game-customers-message">{message}</p>}
      {rows.length === 0 ? <p style={{ color: "#555" }}>No Board Fundraising Game customers yet.</p> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr>{["Stage", "Name", "Email", "Organisation", "Goal", "Access", "Actions"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead>
            <tbody>
              {rows.map((row) => (
                <Fragment key={row.user_id}>
                  <tr data-testid={`game-customer-row-${row.user_id}`}>
                    <td>{row.stage}</td><td>{row.name}</td><td>{row.email}</td><td>{row.organization}</td>
                    <td>{row.goal_amount ? `$${Number(row.goal_amount).toLocaleString()}` : ""}</td>
                    <td data-testid={`game-customer-access-${row.user_id}`}>{row.access_state}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {row.access_state === "Not Unlocked" && (
                          <button className="button button-small" onClick={() => setUnlockTarget(row)} data-testid={`game-unlock-testing-${row.user_id}`}>
                            Unlock For Testing
                          </button>
                        )}
                        {row.access_state === "Unlocked For Testing" && (
                          <button className="button button-small" onClick={() => setRevokeTarget(row)} data-testid={`game-revoke-testing-${row.user_id}`}>
                            Revoke Testing Access
                          </button>
                        )}
                        <button className="button button-small" onClick={() => setExpandedId(expandedId === row.user_id ? "" : row.user_id)}
                          data-testid={`game-customer-details-${row.user_id}`}>
                          {expandedId === row.user_id ? "Hide" : "Details"}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedId === row.user_id && (
                    <tr>
                      <td colSpan={7} data-testid={`game-customer-record-${row.user_id}`}>
                        <strong>Board Fundraising Game Access</strong>
                        {row.purchase ? (
                          <p style={{ marginTop: 6 }}>
                            Access: Unlocked · Source: Stripe · {row.purchase.offer}{row.purchase.price_paid ? ` — $${Number(row.purchase.price_paid).toLocaleString()}` : ""}
                            {row.purchase.purchased_at && ` · Purchased: ${fmtStamp(row.purchase.purchased_at)}`}
                          </p>
                        ) : row.test_unlock?.active ? (
                          <p style={{ marginTop: 6 }}>
                            Access: Unlocked · Source: Admin Test
                            {row.test_unlock.unlocked_at && ` · Unlocked On: ${fmtStamp(row.test_unlock.unlocked_at)}`}
                            {row.test_unlock.unlocked_by && ` · Unlocked By: ${row.test_unlock.unlocked_by}`}
                          </p>
                        ) : (
                          <p style={{ marginTop: 6 }}>Access: {row.access_state}</p>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {unlockTarget && (
        <div style={modalOverlayStyle} data-testid="game-unlock-modal">
          <div style={modalStyle}>
            <h3>Unlock This Account For Testing?</h3>
            <p style={{ marginTop: 10, color: "#444" }}>
              This will give this account access to the post-payment Board Fundraising Game without creating a Stripe payment. Use this only for internal product testing.
            </p>
            <p style={{ marginTop: 12 }}><strong>Account:</strong> {unlockTarget.email}</p>
            {unlockTarget.organization && <p style={{ marginTop: 4 }}><strong>Organisation:</strong> {unlockTarget.organization}</p>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
              <button className="button button-small" onClick={() => setUnlockTarget(null)} data-testid="game-unlock-cancel">Cancel</button>
              <button className="button" onClick={unlock} disabled={busy} data-testid="game-unlock-confirm">
                {busy ? "Unlocking…" : "Unlock For Testing"}
              </button>
            </div>
          </div>
        </div>
      )}

      {revokeTarget && (
        <div style={modalOverlayStyle} data-testid="game-revoke-modal">
          <div style={modalStyle}>
            <h3>Revoke Testing Access?</h3>
            <p style={{ marginTop: 10, color: "#444" }}>
              This removes the admin testing payment bypass from this account. It does not delete the account or the Board Fundraising Game data already created.
            </p>
            <p style={{ marginTop: 12 }}><strong>Account:</strong> {revokeTarget.email}</p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
              <button className="button button-small" onClick={() => setRevokeTarget(null)} data-testid="game-revoke-cancel">Cancel</button>
              <button className="button" onClick={revoke} disabled={busy} data-testid="game-revoke-confirm">
                {busy ? "Revoking…" : "Revoke Testing Access"}
              </button>
            </div>
          </div>
        </div>
      )}

      {successInfo && (
        <div style={modalOverlayStyle} data-testid="game-unlock-success-modal">
          <div style={modalStyle}>
            <h3>Testing Access Enabled</h3>
            <p style={{ marginTop: 10, color: "#444" }}>This account now has access to the Board Fundraising Game without a Stripe payment.</p>
            <p style={{ marginTop: 12 }}><strong>Access Source:</strong> Admin Test</p>
            <p style={{ marginTop: 4 }}><strong>Unlocked:</strong> {fmtStamp(successInfo.unlocked_at)}</p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
              <button className="button" onClick={() => { setExpandedId(successInfo.user_id); setSuccessInfo(null); }} data-testid="game-unlock-open-record">
                Open Customer Record
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const IndividualGameContent = () => {
  const [sections, setSections] = useState([]);
  const [openId, setOpenId] = useState(0);
  const [drafts, setDrafts] = useState({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.get("/game/individual-content").then((r) => setSections(r.data.sections || [])).catch(() => {});
  }, []);

  const openSection = (section) => {
    if (openId === section.id) { setOpenId(0); return; }
    setDrafts({
      title: section.title, scenario: section.scenario,
      first_move_question: section.first_move_question, first_move_support: section.first_move_support || "",
      wisdom: section.wisdom || "", final_question: section.final_question || "",
      complete_label: section.complete_label,
      group_items: Object.fromEntries((section.groups || []).map((group) => [
        group.key, group.items.map((item) => item.hint ? `${item.text} | ${item.hint}` : item.text).join("\n"),
      ])),
    });
    setOpenId(section.id);
    setMessage("");
  };

  const save = async (section) => {
    setBusy(true); setMessage("");
    try {
      const payload = { ...drafts };
      payload.group_items = Object.fromEntries(Object.entries(drafts.group_items || {}).map(([key, lines]) => [
        key,
        String(lines).split("\n").filter((line) => line.trim()).map((line) => {
          const [text, ...rest] = line.split("|");
          return { text: text.trim(), hint: rest.join("|").trim() };
        }),
      ]));
      const response = await client.put(`/admin/game/individual-content/${section.id}`, payload);
      setSections(response.data.sections || []);
      setMessage(`Section ${section.id} saved.`);
    } catch (err) {
      setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not save this section.");
    }
    setBusy(false);
  };

  const setDraft = (key) => (value) => setDrafts((current) => ({ ...current, [key]: value }));
  const setGroupDraft = (key) => (value) => setDrafts((current) => ({ ...current, group_items: { ...current.group_items, [key]: value } }));

  return (
    <div className="admin-import-panel" style={{ marginTop: 20 }} data-testid="game-individual-content-panel">
      <h3>Individual Game Content</h3>
      <p style={{ color: "#555" }}>The 10 strategy sections board members play before Game Night. Defaults load automatically — edit only what you want to change.</p>
      {sections.map((section) => (
        <div key={section.id} style={{ marginTop: 10, border: "1px solid #ddd", borderRadius: 8, padding: "10px 14px" }}>
          <button className="button button-small" onClick={() => openSection(section)} data-testid={`game-ig-toggle-${section.id}`}>
            {openId === section.id ? "Close" : "Edit"} — Section {section.id}: {section.title}
          </button>
          {openId === section.id && (
            <div style={{ marginTop: 8 }}>
              <TextField label="Section title" value={drafts.title} onChange={setDraft("title")} testId={`game-ig-title-${section.id}`} />
              <TextField label="Scenario text" value={drafts.scenario} onChange={setDraft("scenario")} testId={`game-ig-scenario-${section.id}`} textarea
                hint="Placeholders available: {organisation}, {goal}, {deadline}" />
              <TextField label="First Move question" value={drafts.first_move_question} onChange={setDraft("first_move_question")} testId={`game-ig-firstmove-${section.id}`} textarea />
              <TextField label="First Move supporting text" value={drafts.first_move_support} onChange={setDraft("first_move_support")} testId={`game-ig-firstsupport-${section.id}`} textarea />
              <TextField label="Fundraising Wisdom text" value={drafts.wisdom} onChange={setDraft("wisdom")} testId={`game-ig-wisdom-${section.id}`} textarea />
              {(section.groups || []).map((group) => (
                <TextField key={group.key} label={`Guided prompts — ${group.heading} (one per line, format: Prompt | Optional hint)`}
                  value={drafts.group_items?.[group.key] || ""} onChange={setGroupDraft(group.key)} testId={`game-ig-group-${section.id}-${group.key}`} textarea />
              ))}
              {section.final_question !== undefined && section.type === "standard" && (
                <TextField label="Final question" value={drafts.final_question} onChange={setDraft("final_question")} testId={`game-ig-final-${section.id}`} textarea />
              )}
              <TextField label="Completion button wording" value={drafts.complete_label} onChange={setDraft("complete_label")} testId={`game-ig-complete-${section.id}`} />
              <div style={{ marginTop: 12 }}>
                <button className="button" onClick={() => save(section)} disabled={busy} data-testid={`game-ig-save-${section.id}`}>
                  {busy ? "Saving…" : `Save Section ${section.id}`}
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
      {message && <p style={{ marginTop: 10 }} data-testid="game-ig-message">{message}</p>}
    </div>
  );
};

const HostToolsContent = () => {
  const [content, setContent] = useState(null);
  const [openPanel, setOpenPanel] = useState("");
  const [openSection, setOpenSection] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.get("/admin/game/host-tools-content").then((r) => setContent(r.data.content)).catch(() => {});
  }, []);
  if (!content) return null;

  const togglePanel = (key) => { setOpenPanel(openPanel === key ? "" : key); setOpenSection(""); };
  const setCall = (patch) => setContent({ ...content, call_script: { ...content.call_script, ...patch } });
  const setCallSection = (index, field, value) => setCall({
    sections: content.call_script.sections.map((section, i) => i === index ? { ...section, [field]: value } : section),
  });
  const setGuide = (patch) => setContent({ ...content, facilitation: { ...content.facilitation, ...patch } });
  const setGuideSection = (index, patch) => setGuide({
    sections: content.facilitation.sections.map((section, i) => i === index ? { ...section, ...patch } : section),
  });
  const setBlock = (sectionIndex, blockIndex, patch) => setGuideSection(sectionIndex, {
    blocks: content.facilitation.sections[sectionIndex].blocks.map((block, i) => i === blockIndex ? { ...block, ...patch } : block),
  });
  const setChecklist = (patch) => setContent({ ...content, checklist: { ...content.checklist, ...patch } });
  const setGroup = (index, patch) => setChecklist({
    groups: content.checklist.groups.map((group, i) => i === index ? { ...group, ...patch } : group),
  });

  const save = async () => {
    setBusy(true); setMessage("");
    try {
      const response = await client.put("/admin/game/host-tools-content", content);
      setContent(response.data.content);
      setMessage("Host tools content saved.");
    } catch (err) {
      setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not save host tools content.");
    }
    setBusy(false);
  };

  return (
    <div className="admin-import-panel" style={{ marginTop: 20 }} data-testid="game-host-tools-panel">
      <h3>Host Tools Content</h3>
      <p style={{ color: "#555" }}>The Invitation Call Script, Facilitation Guide and Game Night Checklist shown to organisation users. Defaults load automatically — edit only what you want to change. Placeholders available: [Organisation Name], [Fundraising Goal], [Fundraising Deadline], [Board Member First Name].</p>

      <div style={{ marginTop: 12, border: "1px solid #ddd", borderRadius: 8, padding: "10px 14px" }}>
        <button className="button button-small" onClick={() => togglePanel("call")} data-testid="game-ht-toggle-call">
          {openPanel === "call" ? "Close" : "Edit"} — Invitation Call Script
        </button>
        {openPanel === "call" && (
          <div style={{ marginTop: 8 }}>
            <TextField label="Page title" value={content.call_script.page_title} onChange={(v) => setCall({ page_title: v })} testId="game-ht-call-title" />
            <TextField label="Intro text" value={content.call_script.intro} onChange={(v) => setCall({ intro: v })} testId="game-ht-call-intro" textarea />
            {content.call_script.sections.map((section, index) => (
              <div key={section.key} style={{ marginTop: 14, paddingLeft: 12, borderLeft: "3px solid #ddd" }}>
                <TextField label={`Section heading (${section.key})`} value={section.heading} onChange={(v) => setCallSection(index, "heading", v)} testId={`game-ht-call-heading-${section.key}`} />
                <TextField label="Section script" value={section.body} onChange={(v) => setCallSection(index, "body", v)} testId={`game-ht-call-body-${section.key}`} textarea />
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: 12, border: "1px solid #ddd", borderRadius: 8, padding: "10px 14px" }}>
        <button className="button button-small" onClick={() => togglePanel("guide")} data-testid="game-ht-toggle-guide">
          {openPanel === "guide" ? "Close" : "Edit"} — Facilitation Guide
        </button>
        {openPanel === "guide" && (
          <div style={{ marginTop: 8 }}>
            <TextField label="Page title" value={content.facilitation.page_title} onChange={(v) => setGuide({ page_title: v })} testId="game-ht-guide-title" />
            {content.facilitation.sections.map((section, sectionIndex) => (
              <div key={section.key} style={{ marginTop: 10, border: "1px solid #eee", borderRadius: 8, padding: "8px 12px" }}>
                <button className="button button-small" onClick={() => setOpenSection(openSection === section.key ? "" : section.key)} data-testid={`game-ht-guide-toggle-${section.key}`}>
                  {openSection === section.key ? "Close" : "Edit"} — {section.heading}
                </button>
                {openSection === section.key && (
                  <div style={{ marginTop: 8 }}>
                    <TextField label="Section heading" value={section.heading} onChange={(v) => setGuideSection(sectionIndex, { heading: v })} testId={`game-ht-guide-heading-${section.key}`} />
                    {section.blocks.map((block, blockIndex) => block.kind === "group_link" ? (
                      <p key={blockIndex} style={{ color: "#666", marginTop: 10 }}>Copy Group Game Link button (built-in, not editable).</p>
                    ) : (
                      <div key={blockIndex}>
                        {block.label !== undefined && (
                          <TextField label={`Block ${blockIndex + 1} label`} value={block.label} onChange={(v) => setBlock(sectionIndex, blockIndex, { label: v })} testId={`game-ht-guide-label-${section.key}-${blockIndex}`} />
                        )}
                        <TextField
                          label={`Block ${blockIndex + 1} — ${block.kind}${block.items ? " (one item per line)" : ""}`}
                          value={block.items ? block.items.join("\n") : block.text}
                          onChange={(v) => setBlock(sectionIndex, blockIndex, block.items ? { items: v.split("\n") } : { text: v })}
                          testId={`game-ht-guide-block-${section.key}-${blockIndex}`} textarea />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: 12, border: "1px solid #ddd", borderRadius: 8, padding: "10px 14px" }}>
        <button className="button button-small" onClick={() => togglePanel("checklist")} data-testid="game-ht-toggle-checklist">
          {openPanel === "checklist" ? "Close" : "Edit"} — Game Night Checklist
        </button>
        {openPanel === "checklist" && (
          <div style={{ marginTop: 8 }}>
            <TextField label="Page title" value={content.checklist.page_title} onChange={(v) => setChecklist({ page_title: v })} testId="game-ht-checklist-title" />
            <TextField label="Intro text" value={content.checklist.intro} onChange={(v) => setChecklist({ intro: v })} testId="game-ht-checklist-intro" textarea />
            {content.checklist.groups.map((group, index) => (
              <div key={group.key} style={{ marginTop: 14, paddingLeft: 12, borderLeft: "3px solid #ddd" }}>
                <TextField label={`Group heading (${group.key})`} value={group.heading} onChange={(v) => setGroup(index, { heading: v })} testId={`game-ht-checklist-heading-${group.key}`} />
                <TextField label="Checklist items (one per line)" value={group.items.join("\n")} onChange={(v) => setGroup(index, { items: v.split("\n") })} testId={`game-ht-checklist-items-${group.key}`} textarea />
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: 14 }}>
        <button className="button" onClick={save} disabled={busy} data-testid="game-ht-save">{busy ? "Saving…" : "Save Host Tools Content"}</button>
        {message && <span style={{ marginLeft: 12 }} data-testid="game-ht-message">{message}</span>}
      </div>
    </div>
  );
};

const PostGameCommunication = () => {
  const [content, setContent] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.get("/admin/game/postgame-email").then((r) => setContent(r.data.content)).catch(() => {});
  }, []);
  if (!content) return null;

  const set = (key) => (value) => setContent((current) => ({ ...current, [key]: value }));

  const save = async () => {
    setBusy(true); setMessage("");
    try {
      const response = await client.put("/admin/game/postgame-email", content);
      setContent(response.data.content);
      setMessage("Post-game email saved.");
    } catch (err) {
      setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not save the post-game email.");
    }
    setBusy(false);
  };

  return (
    <div className="admin-import-panel" style={{ marginTop: 20 }} data-testid="game-postgame-panel">
      <h3>Post-Game Communication</h3>
      <p style={{ color: "#555" }}>
        The Adopted Strategy delivery email sent to board members after Game Night. Placeholders available: [Board Member First Name], [Organisation Name], [Fundraising Goal], [Primary User Full Name], [Primary User Job Title], [Organisation Website].
      </p>
      <TextField label="Subject" value={content.subject} onChange={set("subject")} testId="game-pg-subject" />
      <TextField label="Opening" value={content.opening} onChange={set("opening")} testId="game-pg-opening" textarea />
      <TextField label="Strategy ready message (shown before the View Our Fundraising Strategy button)" value={content.strategy_ready} onChange={set("strategy_ready")} testId="game-pg-strategy-ready" textarea />
      <TextField label="Execution next-step message (shown after the button)" value={content.execution_next} onChange={set("execution_next")} testId="game-pg-execution-next" textarea />
      <div style={{ marginTop: 14 }}>
        <button className="button" onClick={save} disabled={busy} data-testid="game-pg-save">{busy ? "Saving…" : "Save Post-Game Email"}</button>
        {message && <span style={{ marginLeft: 12 }} data-testid="game-pg-message">{message}</span>}
      </div>
    </div>
  );
};

export const GameSection = () => {
  const [content, setContent] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { client.get("/game/content").then((r) => setContent(r.data.content)).catch(() => {}); }, []);
  if (!content) return <section><p>Loading…</p></section>;

  const set = (key) => (value) => setContent((current) => ({ ...current, [key]: value }));
  const setIntroParagraph = (index) => (value) => setContent((current) => {
    const intro_paragraphs = [...(current.intro_paragraphs || [])];
    intro_paragraphs[index] = value;
    return { ...current, intro_paragraphs };
  });
  const setStage = (index, field) => (value) => setContent((current) => {
    const stages = current.stages.map((stage, i) => i === index ? { ...stage, [field]: field === "items" ? value.split("\n").filter(Boolean) : value } : stage);
    return { ...current, stages };
  });
  const setOutcome = (index, field) => (value) => setContent((current) => {
    const outcomes = current.outcomes.map((outcome, i) => i === index ? { ...outcome, [field]: field === "paragraphs" ? value.split("\n").filter(Boolean) : value } : outcome);
    return { ...current, outcomes };
  });
  const setPf = (key) => (value) => setContent((current) => ({ ...current, profile_flow: { ...current.profile_flow, [key]: value } }));
  const setUp = (key) => (value) => setContent((current) => ({ ...current, upgrade_page: { ...current.upgrade_page, [key]: value } }));
  const setUpItem = (listKey, index, field, isList) => (value) => setContent((current) => ({
    ...current,
    upgrade_page: {
      ...current.upgrade_page,
      [listKey]: current.upgrade_page[listKey].map((item, i) => i === index ? { ...item, [field]: isList ? value.split("\n").filter(Boolean) : value } : item),
    },
  }));

  const save = async () => {
    setBusy(true); setMessage("");
    try {
      await client.put("/admin/game/content", content);
      setMessage("Homepage content saved. The homepage updates immediately.");
    } catch (err) {
      setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not save content.");
    }
    setBusy(false);
  };

  const groupStyle = { marginTop: 22, paddingTop: 14, borderTop: "2px solid #eee" };

  return (
    <section data-testid="admin-game-section">
      <div className="admin-import-panel" data-testid="game-content-panel">
        <h3>Board Fundraising Game — Homepage Content</h3>
        <p style={{ color: "#555" }}>Everything below controls the Board Fundraising Game homepage at the root of the website.</p>

        <div style={groupStyle}><h4>Hero (dark banner)</h4>
          <TextField label="Product label" value={content.hero_badge} onChange={set("hero_badge")} testId="game-content-hero-badge" />
          <TextField label="Main headline" value={content.headline} onChange={set("headline")} testId="game-content-headline" textarea />
          <TextField label="Subtitle" value={content.subheadline} onChange={set("subheadline")} testId="game-content-subheadline" textarea />
        </div>

        <div style={groupStyle}><h4>Intro Statement (white section)</h4>
          <TextField label="Section heading" value={content.intro_heading} onChange={set("intro_heading")} testId="game-content-intro-heading" />
          {[0, 1, 2].map((index) => (
            <TextField key={index} label={`Paragraph ${index + 1}`} value={(content.intro_paragraphs || [])[index] || ""}
              onChange={setIntroParagraph(index)} testId={`game-content-intro-paragraph-${index + 1}`} textarea />
          ))}
        </div>

        <div style={groupStyle}><h4>Fundraising Goal Section</h4>
          <TextField label="Question / headline" value={content.goal_label} onChange={set("goal_label")} testId="game-content-goal-label" />
          <TextField label="Goal input placeholder" value={content.goal_placeholder} onChange={set("goal_placeholder")} testId="game-content-goal-placeholder" />
          <TextField label="Primary CTA button text" value={content.cta_label} onChange={set("cta_label")} testId="game-content-cta-label" />
        </div>

        <div style={groupStyle}><h4>Video Section</h4>
          <label className="field" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 14 }}>
            <input type="checkbox" checked={!!content.video_enabled} onChange={(event) => set("video_enabled")(event.target.checked)} data-testid="game-content-video-enabled" />
            <span>Show the homepage video section</span>
          </label>
          <TextField label="Small label" value={content.video_label} onChange={set("video_label")} testId="game-content-video-label" />
          <TextField label="Heading" value={content.video_heading} onChange={set("video_heading")} testId="game-content-video-heading" />
          <TextField label="Supporting text" value={content.video_text} onChange={set("video_text")} testId="game-content-video-text" textarea
            hint="The video itself is managed in the Game Videos panel below (flow key game_homepage)." />
        </div>

        <div style={groupStyle}><h4>How It Works</h4>
          <TextField label="Small label" value={content.stages_label} onChange={set("stages_label")} testId="game-content-stages-label" />
          <TextField label="Main heading" value={content.stages_heading} onChange={set("stages_heading")} testId="game-content-stages-heading" />
          {content.stages.map((stage, index) => (
            <div key={stage.key} style={{ marginTop: 14, paddingLeft: 12, borderLeft: "3px solid #ddd" }}>
              <TextField label={`Stage ${index + 1} number`} value={stage.number || String(index + 1)} onChange={setStage(index, "number")} testId={`game-content-stage-${stage.key}-number`} />
              <TextField label={`Stage ${index + 1} heading`} value={stage.title} onChange={setStage(index, "title")} testId={`game-content-stage-${stage.key}-title`} />
              <TextField label={`Stage ${index + 1} paragraphs (one per line)`} value={stage.items.join("\n")} onChange={setStage(index, "items")} testId={`game-content-stage-${stage.key}-items`} textarea />
            </div>
          ))}
          <TextField label="CTA after How It Works" value={content.stages_cta_label} onChange={set("stages_cta_label")} testId="game-content-stages-cta" />
        </div>

        <div style={groupStyle}><h4>Outcomes</h4>
          <TextField label="Small label" value={content.outcomes_label} onChange={set("outcomes_label")} testId="game-content-outcomes-label" />
          <TextField label="Section heading" value={content.outcomes_heading} onChange={set("outcomes_heading")} testId="game-content-outcomes-heading" />
          {(content.outcomes || []).map((outcome, index) => (
            <div key={outcome.key} style={{ marginTop: 14, paddingLeft: 12, borderLeft: "3px solid #ddd" }}>
              <TextField label={`Outcome ${index + 1} heading`} value={outcome.heading} onChange={setOutcome(index, "heading")} testId={`game-content-outcome-${outcome.key}-heading`} />
              <TextField label={`Outcome ${index + 1} paragraphs (one per line)`} value={(outcome.paragraphs || []).join("\n")} onChange={setOutcome(index, "paragraphs")} testId={`game-content-outcome-${outcome.key}-paragraphs`} textarea />
            </div>
          ))}
        </div>

        <div style={groupStyle}><h4>Testimonials</h4>
          <TextField label="Testimonials section heading" value={content.testimonials_heading} onChange={set("testimonials_heading")} testId="game-content-testimonials-heading"
            hint="Testimonials themselves come from the existing site-wide testimonial system." />
        </div>

        <div style={groupStyle}><h4>FAQs</h4>
          <TextField label="FAQ section label" value={content.faqs_label} onChange={set("faqs_label")} testId="game-content-faqs-label" />
          <TextField label="FAQ heading" value={content.faqs_heading} onChange={set("faqs_heading")} testId="game-content-faqs-heading" />
          <TextField label="FAQs (one per line, format: Question | Answer)" textarea
            value={content.faqs.map((faq) => `${faq.q} | ${faq.a}`).join("\n")}
            onChange={(value) => set("faqs")(value.split("\n").filter(Boolean).map((line) => {
              const [q, ...rest] = line.split("|");
              return { q: (q || "").trim(), a: rest.join("|").trim() };
            }).filter((faq) => faq.q))}
            testId="game-content-faqs" />
        </div>

        <div style={groupStyle}><h4>Final CTA</h4>
          <TextField label="Heading" value={content.closing_heading} onChange={set("closing_heading")} testId="game-content-closing-heading" />
          <TextField label="Supporting text" value={content.closing_text} onChange={set("closing_text")} testId="game-content-closing-text" textarea />
          <TextField label="Button text" value={content.closing_cta_label} onChange={set("closing_cta_label")} testId="game-content-closing-cta" />
        </div>

        <div style={groupStyle}><h4>Pre-Payment Profile Content</h4>
          {[["heading", "Main profile heading"], ["supporting", "Main profile supporting text"], ["step1_heading", "Step 1 heading"],
            ["step2_heading", "Step 2 heading"], ["step3_heading", "Step 3 heading"], ["review_heading", "Review heading"],
            ["review_supporting", "Review supporting text"], ["save_button", "Save Profile button text"],
            ["saved_heading", "Profile Saved heading"], ["saved_supporting", "Profile Saved supporting text"],
            ["next_heading", "Next-step heading"], ["next_supporting", "Next-step supporting text"],
            ["invite_cta", "Invite board CTA text"]].map(([key, label]) => (
            <TextField key={key} label={label} value={(content.profile_flow || {})[key] || ""} onChange={setPf(key)}
              testId={`game-content-pf-${key}`} textarea={key.includes("supporting")} />
          ))}
        </div>

        <div style={groupStyle}><h4>Upgrade Page Content</h4>
          {[["label", "Small label"], ["heading", "Main heading"], ["supporting", "Supporting text"],
            ["intro_heading", "Intro heading"]].map(([key, label]) => (
            <TextField key={key} label={label} value={(content.upgrade_page || {})[key] || ""} onChange={setUp(key)}
              testId={`game-content-up-${key}`} textarea={key === "supporting"} />
          ))}
          <TextField label="Intro paragraphs (one per line)" value={((content.upgrade_page || {}).intro_paragraphs || []).join("\n")}
            onChange={(value) => setUp("intro_paragraphs")(value.split("\n").filter(Boolean))} testId="game-content-up-intro-paragraphs" textarea />
          <TextField label="Outcomes heading" value={(content.upgrade_page || {}).outcomes_heading || ""} onChange={setUp("outcomes_heading")} testId="game-content-up-outcomes-heading" />
          {((content.upgrade_page || {}).outcomes || []).map((outcome, index) => (
            <div key={index} style={{ marginTop: 12, paddingLeft: 12, borderLeft: "3px solid #ddd" }}>
              <TextField label={`Outcome ${index + 1} heading`} value={outcome.heading} onChange={setUpItem("outcomes", index, "heading")} testId={`game-content-up-outcome-${index + 1}-heading`} />
              <TextField label={`Outcome ${index + 1} body (one paragraph per line)`} value={(outcome.paragraphs || []).join("\n")} onChange={setUpItem("outcomes", index, "paragraphs", true)} testId={`game-content-up-outcome-${index + 1}-body`} textarea />
            </div>
          ))}
          <TextField label="Included features heading" value={(content.upgrade_page || {}).features_heading || ""} onChange={setUp("features_heading")} testId="game-content-up-features-heading" />
          {((content.upgrade_page || {}).features || []).map((feature, index) => (
            <div key={index} style={{ marginTop: 12, paddingLeft: 12, borderLeft: "3px solid #ddd" }}>
              <TextField label={`Feature ${index + 1} heading`} value={feature.heading} onChange={setUpItem("features", index, "heading")} testId={`game-content-up-feature-${index + 1}-heading`} />
              <TextField label={`Feature ${index + 1} description`} value={feature.description} onChange={setUpItem("features", index, "description")} testId={`game-content-up-feature-${index + 1}-description`} textarea />
            </div>
          ))}
          <TextField label="What Happens Next heading" value={(content.upgrade_page || {}).steps_heading || ""} onChange={setUp("steps_heading")} testId="game-content-up-steps-heading" />
          {((content.upgrade_page || {}).steps || []).map((step, index) => (
            <div key={index} style={{ marginTop: 12, paddingLeft: 12, borderLeft: "3px solid #ddd" }}>
              <TextField label={`Step ${index + 1} heading`} value={step.heading} onChange={setUpItem("steps", index, "heading")} testId={`game-content-up-step-${index + 1}-heading`} />
              <TextField label={`Step ${index + 1} description`} value={step.description} onChange={setUpItem("steps", index, "description")} testId={`game-content-up-step-${index + 1}-description`} textarea />
            </div>
          ))}
          {[["payment_heading", "Payment block heading"], ["payment_price", "Price display text"], ["payment_onetime", "One-time payment label"],
            ["payment_org_line", "Organisation/board line"], ["payment_subscription_line", "Subscription line"],
            ["payment_includes", "Included-summary text"], ["payment_cta", "Payment CTA text"]].map(([key, label]) => (
            <TextField key={key} label={label} value={(content.upgrade_page || {})[key] || ""} onChange={setUp(key)}
              testId={`game-content-up-${key}`} textarea={key === "payment_includes"}
              hint={key === "payment_price" ? "Display only. The actual Stripe charge remains the $497 Board Fundraising Game product." : undefined} />
          ))}
        </div>

        <div style={groupStyle}><h4>Pre-Payment Unlock Page (not shown on the homepage)</h4>
          <TextField label="Product benefits (one per line — shown before payment)" value={content.benefits.join("\n")} onChange={(value) => set("benefits")(value.split("\n").filter(Boolean))} testId="game-content-benefits" textarea />
          <TextField label="Pricing section heading" value={content.pricing_heading} onChange={set("pricing_heading")} testId="game-content-pricing-heading" />
          <TextField label="Price display" value={content.price_display} onChange={set("price_display")} testId="game-content-price-display" hint="Display only. The actual Stripe charge is the $497 Board Fundraising Game product." />
          <TextField label="Price note" value={content.price_note} onChange={set("price_note")} testId="game-content-price-note" />
        </div>

        <div style={{ marginTop: 18 }}>
          <button className="button" onClick={save} disabled={busy} data-testid="game-content-save">{busy ? "Saving…" : "Save Homepage Content"}</button>
          {message && <span style={{ marginLeft: 12 }} data-testid="game-content-message">{message}</span>}
        </div>
      </div>
      <VideosManager />
      <IndividualGameContent />
      <HostToolsContent />
      <PostGameCommunication />
      <CustomersTable />
    </section>
  );
};
