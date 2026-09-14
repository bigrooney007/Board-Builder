import { useCallback, useEffect, useState } from "react";
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

const CustomersTable = () => {
  const [rows, setRows] = useState([]);
  useEffect(() => { client.get("/admin/game/customers").then((r) => setRows(r.data.customers || [])).catch(() => {}); }, []);
  return (
    <div className="admin-import-panel" style={{ marginTop: 20 }} data-testid="game-customers-panel">
      <h3>Game Customers</h3>
      {rows.length === 0 ? <p style={{ color: "#555" }}>No Board Fundraising Game customers yet.</p> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr>{["Stage", "Name", "Email", "Organisation", "Goal", "Deadline", "Updated"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.user_id} data-testid={`game-customer-row-${row.user_id}`}>
                  <td>{row.stage}</td><td>{row.name}</td><td>{row.email}</td><td>{row.organization}</td>
                  <td>{row.goal_amount ? `$${Number(row.goal_amount).toLocaleString()}` : ""}</td>
                  <td>{row.goal_deadline}</td><td>{row.updated_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
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

export const GameSection = () => {
  const [content, setContent] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { client.get("/game/content").then((r) => setContent(r.data.content)).catch(() => {}); }, []);
  if (!content) return <section><p>Loading…</p></section>;

  const set = (key) => (value) => setContent((current) => ({ ...current, [key]: value }));
  const setStage = (index, field) => (value) => setContent((current) => {
    const stages = current.stages.map((stage, i) => i === index ? { ...stage, [field]: field === "items" ? value.split("\n").filter(Boolean) : value } : stage);
    return { ...current, stages };
  });

  const save = async () => {
    setBusy(true); setMessage("");
    try {
      await client.put("/admin/game/content", content);
      setMessage("Website content saved. The homepage updates immediately.");
    } catch (err) {
      setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not save content.");
    }
    setBusy(false);
  };

  return (
    <section data-testid="admin-game-section">
      <div className="admin-import-panel" data-testid="game-content-panel">
        <h3>Board Fundraising Game — Website Content</h3>
        <p style={{ color: "#555" }}>Everything below controls the new homepage at the root of the website. The old homepage now lives at /fundraising-system.</p>
        <TextField label="Hero badge" value={content.hero_badge} onChange={set("hero_badge")} testId="game-content-hero-badge" />
        <TextField label="Homepage headline" value={content.headline} onChange={set("headline")} testId="game-content-headline" textarea />
        <TextField label="Homepage subheadline" value={content.subheadline} onChange={set("subheadline")} testId="game-content-subheadline" textarea />
        <TextField label="Fundraising goal input label" value={content.goal_label} onChange={set("goal_label")} testId="game-content-goal-label" />
        <TextField label="Primary CTA wording" value={content.cta_label} onChange={set("cta_label")} testId="game-content-cta-label" />
        <label className="field" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 14 }}>
          <input type="checkbox" checked={!!content.video_enabled} onChange={(event) => set("video_enabled")(event.target.checked)} data-testid="game-content-video-enabled" />
          <span>Show the homepage video section</span>
        </label>
        <TextField label="Video section heading" value={content.video_heading} onChange={set("video_heading")} testId="game-content-video-heading" />
        <TextField label="Video supporting text" value={content.video_text} onChange={set("video_text")} testId="game-content-video-text" textarea />
        <TextField label="Stages section heading" value={content.stages_heading} onChange={set("stages_heading")} testId="game-content-stages-heading" />
        {content.stages.map((stage, index) => (
          <div key={stage.key} style={{ marginTop: 14, paddingLeft: 12, borderLeft: "3px solid #ddd" }}>
            <TextField label={`Stage ${index + 1} title`} value={stage.title} onChange={setStage(index, "title")} testId={`game-content-stage-${stage.key}-title`} />
            <TextField label={`Stage ${index + 1} points (one per line)`} value={stage.items.join("\n")} onChange={setStage(index, "items")} testId={`game-content-stage-${stage.key}-items`} textarea />
          </div>
        ))}
        <TextField label="Benefits section heading" value={content.benefits_heading} onChange={set("benefits_heading")} testId="game-content-benefits-heading" />
        <TextField label="Product benefits (one per line — also shown before payment)" value={content.benefits.join("\n")} onChange={(value) => set("benefits")(value.split("\n").filter(Boolean))} testId="game-content-benefits" textarea />
        <TextField label="Pricing section heading" value={content.pricing_heading} onChange={set("pricing_heading")} testId="game-content-pricing-heading" />
        <TextField label="Price display" value={content.price_display} onChange={set("price_display")} testId="game-content-price-display" hint="Display only. The actual Stripe charge is the $497 Board Fundraising Game product." />
        <TextField label="Price note" value={content.price_note} onChange={set("price_note")} testId="game-content-price-note" />
        <TextField label="FAQ section heading" value={content.faqs_heading} onChange={set("faqs_heading")} testId="game-content-faqs-heading" />
        <TextField label="FAQs (one per line, format: Question | Answer)" textarea
          value={content.faqs.map((faq) => `${faq.q} | ${faq.a}`).join("\n")}
          onChange={(value) => set("faqs")(value.split("\n").filter(Boolean).map((line) => {
            const [q, ...rest] = line.split("|");
            return { q: (q || "").trim(), a: rest.join("|").trim() };
          }).filter((faq) => faq.q))}
          testId="game-content-faqs" />
        <TextField label="Testimonials section heading" value={content.testimonials_heading} onChange={set("testimonials_heading")} testId="game-content-testimonials-heading" hint="Testimonials themselves come from the existing site-wide testimonial system." />
        <div style={{ marginTop: 18 }}>
          <button className="button" onClick={save} disabled={busy} data-testid="game-content-save">{busy ? "Saving…" : "Save Website Content"}</button>
          {message && <span style={{ marginLeft: 12 }} data-testid="game-content-message">{message}</span>}
        </div>
      </div>
      <VideosManager />
      <IndividualGameContent />
      <CustomersTable />
    </section>
  );
};
