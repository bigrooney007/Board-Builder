import { Fragment, useCallback, useEffect, useState } from "react";
import axios from "axios";
import { VoiceGuidedAdmin } from "./VoiceGuidedAdmin";

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
            <thead><tr>{["Stage", "Name", "Email", "Organization", "Goal", "Access", "Actions"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead>
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
            {unlockTarget.organization && <p style={{ marginTop: 4 }}><strong>Organization:</strong> {unlockTarget.organization}</p>}
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
                hint="Placeholders available: {organization}, {goal}, {deadline}" />
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
      <p style={{ color: "#555" }}>The Invitation Call Script, Facilitation Guide and Game Night Checklist shown to organization users. Defaults load automatically — edit only what you want to change. Placeholders available: [Organization Name], [Fundraising Goal], [Fundraising Deadline], [Board Member First Name].</p>

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
        The Adopted Strategy delivery email sent to board members after Game Night. Placeholders available: [Board Member First Name], [Organization Name], [Fundraising Goal], [Primary User Full Name], [Primary User Job Title], [Organization Website].
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

const V3_KEYS = ["intro", "rounds", "guided", "strategy_ready", "current_reality", "participation", "board_completion", "fine_tuning", "mini_strategy", "primary_review", "group_complete"];

const V3GameContent = () => {
  const [open, setOpen] = useState(false);
  const [drafts, setDrafts] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    if (!open && !drafts) {
      try {
        const response = await client.get("/admin/game/v3-content");
        const content = response.data.content || {};
        setDrafts(Object.fromEntries(V3_KEYS.map((key) => [key, JSON.stringify(content[key] ?? {}, null, 2)])));
      } catch { setMessage("Could not load the game content."); }
    }
    setOpen((current) => !current);
  };

  const save = async () => {
    setBusy(true); setMessage("");
    try {
      const payload = {};
      for (const key of V3_KEYS) payload[key] = JSON.parse(drafts[key]);
      await client.put("/admin/game/v3-content", payload);
      setMessage("Game content saved. The game updates immediately.");
    } catch (err) {
      setMessage(err instanceof SyntaxError
        ? "One of the sections is not valid JSON. Fix the highlighted structure and try again."
        : (typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not save content."));
    }
    setBusy(false);
  };

  return (
    <div className="admin-import-panel" style={{ marginTop: 20 }} data-testid="game-v3-content-panel">
      <h3>Individual Game Content (V3 — 4 Rounds + AI Fine-Tuning)</h3>
      <p style={{ color: "#555" }}>All customer-facing copy for the simplified 4-round game, the fine-tuning review, the personal mini strategy, the post-payment strategy review and the Group Game completion screen. Edit carefully — the structure must stay valid JSON.</p>
      <button className="button button-small" onClick={toggle} data-testid="game-v3-toggle">{open ? "Hide Editor" : "Open Editor"}</button>
      {open && drafts && (
        <div style={{ marginTop: 12 }}>
          {V3_KEYS.map((key) => (
            <label key={key} style={{ display: "block", marginTop: 14 }}>
              <span style={{ display: "block", fontWeight: 600, marginBottom: 6 }}>{key.replace(/_/g, " ")}</span>
              <textarea rows={key === "rounds" ? 14 : 7} style={{ width: "100%", fontFamily: "monospace", fontSize: 12.5 }}
                value={drafts[key]} onChange={(event) => setDrafts({ ...drafts, [key]: event.target.value })}
                data-testid={`game-v3-field-${key}`} />
            </label>
          ))}
          <button className="button" style={{ marginTop: 12 }} onClick={save} disabled={busy} data-testid="game-v3-save">{busy ? "Saving…" : "Save Game Content"}</button>
        </div>
      )}
      {message && <p style={{ marginTop: 10 }} data-testid="game-v3-message">{message}</p>}
    </div>
  );
};

export const GameSection = () => {
  return (
    <section data-testid="admin-game-section">
      <div className="admin-import-panel" data-testid="game-content-panel">
        <h3>Board Fundraising Game — Public Page</h3>
        <p style={{ color: "#555" }}>
          The public Board Fundraising Game homepage is version-controlled as one page in the application source.
          This dashboard no longer stores a second database copy that can override a deployment.
        </p>
      </div>
      <VideosManager />
      <IndividualGameContent />
      <V3GameContent />
      <VoiceGuidedAdmin />
      <HostToolsContent />
      <PostGameCommunication />
      <CustomersTable />
    </section>
  );
};
