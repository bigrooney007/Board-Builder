import { useEffect, useState } from "react";
import { memberApi } from "@/member/api";

const TIMEZONES = ["Eastern Time (ET)", "Central Time (CT)", "Mountain Time (MT)", "Pacific Time (PT)", "Alaska Time (AKT)", "Hawaii Time (HT)", "UTC"];
const FORMATS = [{ value: "in_person", label: "In Person" }, { value: "online", label: "Virtual" }, { value: "hybrid", label: "Hybrid" }];

const fmtDate = (raw) => {
  if (!raw) return "";
  const date = new Date(`${raw}T00:00:00`);
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
};
const fmtTime = (raw) => {
  if (!raw) return "";
  const [hours, minutes] = raw.split(":").map(Number);
  const date = new Date(); date.setHours(hours, minutes || 0);
  return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
};

export const GameNightSection = () => {
  const [night, setNight] = useState(null);
  const [defaultName, setDefaultName] = useState("");
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    memberApi.get("/game/night").then((response) => {
      setNight(response.data.night || {});
      setDefaultName(response.data.default_name || "");
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  const startEdit = () => {
    setForm({
      name: night?.name || defaultName || "Board Fundraising Day/Night",
      meeting_date: night?.meeting_date || "",
      funding_deadline: night?.funding_deadline || "",
      start_time: night?.start_time || "",
      timezone_name: night?.timezone || "Eastern Time (ET)",
      meeting_format: night?.meeting_format || "in_person",
      meeting_link: night?.meeting_link || "",
      meeting_location: night?.meeting_location || "",
      note: night?.note || "",
    });
    setEditing(true);
  };

  const save = async () => {
    setError("");
    if (!form.meeting_date) { setError("Meeting date is required."); return; }
    if (!form.funding_deadline) { setError("Funding deadline is required."); return; }
    if (new Date(form.funding_deadline + "T00:00:00") < new Date(form.meeting_date + "T00:00:00")) {
      setError("The funding deadline cannot be before the Board meeting date."); return;
    }
    if (!form.start_time) { setError("Start time is required."); return; }
    if (!form.timezone_name) { setError("Time zone is required."); return; }
    setBusy(true);
    try {
      const response = await memberApi.put("/game/night", form);
      setNight(response.data.night);
      setEditing(false);
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your meeting details. Please try again.");
    }
    setBusy(false);
  };

  if (!loaded) return null;
  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const saved = night?.meeting_date;
  const formatLabel = (FORMATS.find((item) => item.value === night?.meeting_format) || {}).label || night?.meeting_format;

  return (
    <section className="bfg-panel" data-testid="bfg-game-night-section">
      <div className="bfg-panel-head">
        <div>
          <><p className="bfg-eyebrow">BOARD MEETING</p><h2>Set Your Board Fundraising Day/Night</h2></>
          <p className="bfg-panel-sub">Set the next Board meeting and tell us when the money is needed. The funding deadline becomes the anchor for the execution timeline in your final fundraising strategy.</p>
        </div>
        {saved && !editing && (
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={startEdit} data-testid="bfg-edit-game-night-btn">Edit Meeting Details</button>
        )}
      </div>

      {!saved && !editing && (
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16 }} onClick={startEdit} data-testid="bfg-setup-game-night-btn">Add Meeting Details</button>
      )}

      {saved && !editing && (
        <div className="bfg-night-summary" data-testid="bfg-game-night-summary">
          <p className="bfg-eyebrow" style={{ margin: "8px 0 4px" }}>Your Next Board Fundraising Day/Night</p>
          <div className="bfg-summary-row"><span>Board Meeting Date</span><strong>{fmtDate(night.meeting_date)}</strong></div>
          <div className="bfg-summary-row"><span>Funding Deadline</span><strong>{fmtDate(night.funding_deadline)}</strong></div>
          <div className="bfg-summary-row"><span>Time</span><strong>{fmtTime(night.start_time)} {night.timezone}</strong></div>
          <div className="bfg-summary-row"><span>Format</span><strong>{formatLabel}</strong></div>
          {["online", "hybrid"].includes(night.meeting_format) && night.meeting_link && (
            <div className="bfg-summary-row"><span>Meeting Link</span><strong>{night.meeting_link}</strong></div>
          )}
          {["in_person", "hybrid"].includes(night.meeting_format) && night.meeting_location && (
            <div className="bfg-summary-row"><span>Location</span><strong>{night.meeting_location}</strong></div>
          )}
          {night.note && <div className="bfg-summary-row"><span>Meeting Notes</span><strong>{night.note}</strong></div>}
        </div>
      )}

      {editing && (
        <div style={{ marginTop: 8 }} data-testid="bfg-game-night-form">
          <div className="bfg-two-col">
            <label className="bfg-field"><span>Meeting Date <b>*</b></span>
              <input type="date" value={form.meeting_date} onChange={set("meeting_date")} data-testid="bfg-night-date" />
            </label>
            <label className="bfg-field"><span>When Do You Need The Money? <b>*</b></span>
              <input type="date" min={form.meeting_date || undefined} value={form.funding_deadline} onChange={set("funding_deadline")} data-testid="bfg-funding-deadline" />
              <small>This deadline determines whether your execution plan should be 30, 60, 90, 120 days or another realistic period.</small>
            </label>
          </div>
          <div className="bfg-two-col">
            <label className="bfg-field"><span>Start Time <b>*</b></span>
              <input type="time" value={form.start_time} onChange={set("start_time")} data-testid="bfg-night-time" />
            </label>
          </div>
          <div className="bfg-two-col">
            <label className="bfg-field"><span>Time Zone <b>*</b></span>
              <select value={form.timezone_name} onChange={set("timezone_name")} data-testid="bfg-night-timezone">
                {TIMEZONES.map((zone) => <option key={zone} value={zone}>{zone}</option>)}
              </select>
            </label>
            <label className="bfg-field"><span>Meeting Format <b>*</b></span>
              <select value={form.meeting_format} onChange={set("meeting_format")} data-testid="bfg-night-format">
                {FORMATS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
          </div>
          {["online", "hybrid"].includes(form.meeting_format) && (
            <label className="bfg-field"><span>Meeting Link</span>
              <input value={form.meeting_link} onChange={set("meeting_link")} data-testid="bfg-night-link" />
            </label>
          )}
          {["in_person", "hybrid"].includes(form.meeting_format) && (
            <label className="bfg-field"><span>Meeting Location</span>
              <input value={form.meeting_location} onChange={set("meeting_location")} data-testid="bfg-night-location" />
            </label>
          )}
          <label className="bfg-field"><span>Optional Meeting Notes</span>
            <textarea rows={3} value={form.note} placeholder="Add anything you want your board members to know before the meeting."
              onChange={set("note")} data-testid="bfg-night-note" />
          </label>
          {error && <p className="bfg-error" data-testid="bfg-night-error">{error}</p>}
          <div className="bfg-form-actions">
            {saved ? <button className="bfg-btn bfg-btn-ghost" onClick={() => setEditing(false)} data-testid="bfg-night-cancel">Cancel</button> : <span />}
            <button className="bfg-btn bfg-btn-primary" onClick={save} disabled={busy} data-testid="bfg-night-save">
              {busy ? "Saving…" : "Save Meeting Details"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
};

export default GameNightSection;
