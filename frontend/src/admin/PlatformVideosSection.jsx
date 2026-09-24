import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { RefreshCw, Save } from "lucide-react";
import { VIDEO_KEYS } from "@/clean/platform";
import DashboardSectionAudioAdmin from "@/admin/DashboardSectionAudioAdmin";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

function RecruitmentQuestionAudioAdmin() {
  const IDS = ["rct_question_1", "rct_question_2", "rct_question_3", "rct_question_4", "rct_question_5", "rct_question_6"];
  const [assets, setAssets] = useState([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setMessage("");
    try {
      const response = await client.get("/admin/game/voice/assets");
      setAssets((response.data.assets || []).filter((asset) => IDS.includes(asset.narration_id)));
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not load Recruitment Question audio.");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const updateText = (id, text) => setAssets((current) =>
    current.map((asset) => asset.narration_id === id ? { ...asset, text } : asset)
  );

  const save = async (asset) => {
    setBusy("save:" + asset.narration_id);
    setMessage("");
    try {
      await client.put("/admin/game/voice/assets/" + asset.narration_id, { text: asset.text });
      setMessage("Question script saved.");
      await load();
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not save this question script.");
    }
    setBusy("");
  };

  const generate = async (asset, environment) => {
    setBusy(environment + ":" + asset.narration_id);
    setMessage("");
    try {
      await client.post("/admin/game/voice/assets/" + asset.narration_id + "/generate", {
        environment,
        force: environment === "live" && asset.live?.status === "ready",
      });
      setMessage((environment === "live" ? "Live" : "Test") + " audio generated.");
      await load();
    } catch (error) {
      setMessage(error.response?.data?.detail || "Audio generation failed.");
    }
    setBusy("");
  };

  return (
    <div className="admin-platform-subsection" data-testid="admin-recruitment-question-audio">
      <div className="admin-funnel-numbers-head" style={{ marginTop: 36 }}>
        <div>
          <h2>Recruitment Question Audio</h2>
          <p>Edit the teaching script for each of the six Recruitment Questions, then generate or regenerate its ElevenLabs audio. If no live audio exists, the customer simply sees the question without audio.</p>
        </div>
        <button className="button button-back button-small" onClick={load}><RefreshCw size={15} /> Refresh</button>
      </div>
      {message && <p className="admin-message">{message}</p>}
      <div className="admin-preview-dashboard-grid">
        {assets.map((asset, index) => (
          <article className="member-card" key={asset.narration_id}>
            <p className="eyebrow">QUESTION {index + 1} AUDIO</p>
            <h3>{asset.label}</h3>
            <p className="material-meta">Test: {asset.test?.status || "missing"} · Live: {asset.live?.status || "missing"} · Script v{asset.script_version || 1}</p>
            <label className="admin-notes">
              Teaching Script
              <textarea rows={7} value={asset.text || ""} onChange={(event) => updateText(asset.narration_id, event.target.value)} />
            </label>
            <div className="material-actions">
              <button className="button button-small" disabled={!!busy} onClick={() => save(asset)}>
                <Save size={14} /> {busy === "save:" + asset.narration_id ? "SAVING…" : "SAVE SCRIPT"}
              </button>
              <button className="button button-back button-small" disabled={!!busy} onClick={() => generate(asset, "test")}>
                {busy === "test:" + asset.narration_id ? "GENERATING…" : "GENERATE TEST AUDIO"}
              </button>
              <button className="button button-small" disabled={!!busy} onClick={() => generate(asset, "live")}>
                {busy === "live:" + asset.narration_id ? "GENERATING…" : asset.live?.status === "ready" ? "REGENERATE LIVE AUDIO" : "GENERATE LIVE AUDIO"}
              </button>
              {asset.live?.status === "ready" && (
                <audio controls preload="none" style={{ width: "100%", marginTop: 8 }}
                  src={`${API}/game/voice/audio/${asset.narration_id}?v=live${asset.live?.version || 0}`} />
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export function PlatformVideosSection() {
  const [videos, setVideos] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [saving, setSaving] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setMessage("");
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
      setMessage("Video saved.");
      await load();
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not save video.");
    }
    setSaving("");
  };

  const ordered = VIDEO_KEYS.map(([key, name, flow]) =>
    videos.find((row) => row.key === key) || { key, name, flow, url: "", youtube_id: "" }
  );

  return (
    <section data-testid="clean-platform-videos">
      <div className="admin-funnel-numbers-head">
        <div>
          <h2>The 8 Core Videos Within The Platform</h2>
          <p>Keep only the four public demonstration videos and four post-purchase onboarding videos here. Dashboard teaching is now handled by contextual audio below.</p>
        </div>
        <button className="button button-back button-small" onClick={load}><RefreshCw size={15} /> Refresh</button>
      </div>
      {message && <p className="admin-message">{message}</p>}
      <div className="admin-preview-dashboard-grid">
        {ordered.map((video, index) => (
          <article className="member-card" key={video.key}>
            <p className="eyebrow">VIDEO {index + 1}</p>
            <h3>{video.name}</h3>
            <p>{video.flow}</p>
            <label className="admin-notes">
              YouTube URL or Video ID
              <input value={drafts[video.key] ?? ""} onChange={(event) => setDrafts({ ...drafts, [video.key]: event.target.value })} placeholder="https://youtu.be/..." />
            </label>
            <button className="button button-small" disabled={saving === video.key} onClick={() => save(video.key)}>
              <Save size={14} /> {saving === video.key ? "SAVING…" : "SAVE VIDEO"}
            </button>
          </article>
        ))}
      </div>
      <DashboardSectionAudioAdmin />
      <RecruitmentQuestionAudioAdmin />
    </section>
  );
}
