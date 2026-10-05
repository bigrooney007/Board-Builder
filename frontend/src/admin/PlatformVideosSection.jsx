import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { RefreshCw, Save } from "lucide-react";
import { VIDEO_KEYS } from "@/clean/platform";
import DashboardSectionAudioAdmin from "@/admin/DashboardSectionAudioAdmin";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });
const PAYMENT_VIDEO_KEYS = ["recruitment_upgrade", "game_homepage", "strategic_planning_demonstration", "board_recommitment_demonstration"];

function AudioVoiceSelectionAdmin() {
  const [settings, setSettings] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    client.get("/admin/game/voice/settings").then(({data}) => setSettings(data.settings))
      .catch(() => setMessage("Could not load voice settings."));
  }, []);
  const save = async () => {
    setBusy(true); setMessage("");
    try {
      const response = await client.put("/admin/game/voice/settings", {settings: {
        test_voice_id: settings.test_voice_id || "", live_voice_id: settings.live_voice_id || "",
      }});
      setSettings(response.data.settings);
      setMessage("Voice selection saved. Regenerate the clips you want to use with the new voice.");
    } catch (error) { setMessage(error.response?.data?.detail || "Could not save voice selection."); }
    setBusy(false);
  };
  return <section className="admin-platform-subsection" data-testid="admin-audio-voice-selection">
    <h2>Choose The Voice For Your Audio</h2>
    <p>Paste an ElevenLabs Voice ID for Test and Live. Leave a field empty to use the existing server voice. Changing a voice does not replace a recording until you regenerate that clip below.</p>
    {settings && <div className="admin-filters">
      <label>Test voice ID<input value={settings.test_voice_id || ""} onChange={e=>setSettings({...settings,test_voice_id:e.target.value})} placeholder={`Current server voice ${settings.test_voice_ref || ""}`}/></label>
      <label>Live voice ID<input value={settings.live_voice_id || ""} onChange={e=>setSettings({...settings,live_voice_id:e.target.value})} placeholder={`Current server voice ${settings.live_voice_ref || ""}`}/></label>
      <button className="button button-small" onClick={save} disabled={busy}>{busy ? "SAVING…" : "SAVE VOICE SELECTION"}</button>
    </div>}
    {message && <p className="admin-message" role="status">{message}</p>}
  </section>;
}

function RecruitmentLaunchVideoAdmin() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    client.get("/admin/platform/recruitment-section-videos")
      .then(({ data }) => { setUrl(data.videos?.find((video) => video.key === "launch")?.url || ""); setLoaded(true); })
      .catch(() => setMessage("Could not load the recruitment launch video. Refresh to try again."));
  }, []);
  const save = async () => {
    setBusy(true); setMessage("");
    try {
      await client.put("/admin/platform/recruitment-section-videos/launch", { url });
      window.dispatchEvent(new Event("recruitment-videos-changed"));
      setMessage("Saved. The Launch Your Campaign section now uses this video.");
    } catch (error) { setMessage(error.response?.data?.detail || "Could not save the launch video."); }
    setBusy(false);
  };
  return <section className="member-card" data-testid="admin-recruitment-launch-video">
    <h2>Launch Your Recruitment Campaign In The Next 30 Minutes</h2>
    <p>This video appears in Launch Your Campaign on the client Recruitment dashboard. Replace the link here whenever you want to update it.</p>
    <label className="admin-notes">YouTube URL or Video ID
      <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://youtu.be/..." data-testid="recruitment-launch-video-url" />
    </label>
    <button className="button button-small" disabled={busy || !loaded} onClick={save} data-testid="save-recruitment-launch-video"><Save size={14} /> {busy ? "SAVING…" : "SAVE CAMPAIGN VIDEO"}</button>
    {message && <p className="admin-message" role="status">{message}</p>}
  </section>;
}

export function PlatformVideosSection() {
  const [videos, setVideos] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [saving, setSaving] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const response = await client.get("/admin/platform/videos");
      setVideos(response.data.videos || []);
      setDrafts(Object.fromEntries((response.data.videos || []).map((item) => [item.key, item.url || ""])));
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not load platform videos.");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (key) => {
    setSaving(key);
    setMessage("");
    try {
      await client.put(`/admin/platform/videos/${key}`, { url: drafts[key] || "" });
      window.dispatchEvent(new Event("platform-videos-changed"));
      setMessage("Video saved.");
      await load();
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not save video.");
    }
    setSaving("");
  };

  const ordered = VIDEO_KEYS.filter(([key])=>key!=="game_upgrade").map(([key, name, flow]) =>
    videos.find((row) => row.key === key) || { key, name, flow, url: "", youtube_id: "" }
  );
  const videoCard = (video) => <article className="member-card" key={video.key} data-testid={`admin-video-${video.key}`}>
    <h3>{video.name}</h3><p>{video.flow}</p>
    <label className="admin-notes">YouTube URL or Video ID
      <input value={drafts[video.key] ?? ""} onChange={(event) => setDrafts({ ...drafts, [video.key]: event.target.value })} placeholder="https://youtu.be/..." />
    </label>
    <button className="button button-small" disabled={saving === video.key} onClick={() => save(video.key)}>
      <Save size={14} /> {saving === video.key ? "SAVING…" : "SAVE VIDEO"}
    </button>
    {video.youtube_id && <a href={`https://www.youtube.com/watch?v=${video.youtube_id}`} target="_blank" rel="noreferrer">Watch saved video</a>}
  </article>;

  return (
    <section data-testid="clean-platform-videos">
      <div className="admin-funnel-numbers-head">
        <div>
          <h2>Videos For The Four Offers</h2>
          <p>Update the video each lead sees before choosing how to pay. The Board Fundraising Game payment page uses the same demonstration video saved here under Board Fundraising Game Demonstration.</p>
        </div>
        <button className="button button-back button-small" onClick={()=>{setMessage("");load()}}><RefreshCw size={15} /> Refresh</button>
      </div>
      {message && <p className="admin-message">{message}</p>}
      <div className="admin-preview-dashboard-grid">{ordered.filter(video=>PAYMENT_VIDEO_KEYS.includes(video.key)).map(videoCard)}</div>
      <details className="admin-import-panel" style={{marginTop:22}}><summary style={{cursor:"pointer",fontWeight:800}}>Onboarding And Other Videos</summary>
        <div className="admin-preview-dashboard-grid" style={{marginTop:16}}>{ordered.filter(video=>!PAYMENT_VIDEO_KEYS.includes(video.key)).map(videoCard)}</div>
      </details>
      <RecruitmentLaunchVideoAdmin />
      <AudioVoiceSelectionAdmin />
      <DashboardSectionAudioAdmin />
    </section>
  );
}
