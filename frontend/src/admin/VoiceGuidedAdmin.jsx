import { useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

const STATUS_STYLE = {
  ready: { label: "READY", color: "#059669" },
  missing: { label: "MISSING", color: "#b91c1c" },
  needs_regeneration: { label: "NEEDS REGENERATION", color: "#92400e" },
};

const StatusBadge = ({ status }) => {
  const item = STATUS_STYLE[status] || STATUS_STYLE.missing;
  return <span style={{ fontSize: 11, fontWeight: 700, color: item.color }}>{item.label}</span>;
};

export const VoiceGuidedAdmin = () => {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState(null);
  const [assets, setAssets] = useState([]);
  const [missingLive, setMissingLive] = useState([]);
  const [bulk, setBulk] = useState(null);
  const [busyId, setBusyId] = useState("");
  const [confirmId, setConfirmId] = useState("");
  const [bulkConfirm, setBulkConfirm] = useState(false);
  const [message, setMessage] = useState("");
  const [personalClips, setPersonalClips] = useState([]);
  const [previewNames, setPreviewNames] = useState({});

  const load = async () => {
    const [settingsResponse, assetsResponse] = await Promise.all([
      client.get("/admin/game/voice/settings"), client.get("/admin/game/voice/assets")]);
    setSettings(settingsResponse.data.settings);
    setAssets(assetsResponse.data.assets);
    setMissingLive(assetsResponse.data.missing_live || []);
    setPersonalClips(assetsResponse.data.personal_clips || []);
    setBulk(assetsResponse.data.bulk || null);
    return assetsResponse.data.bulk;
  };

  const toggle = async () => {
    if (!open && !settings) await load().catch(() => setMessage("Could not load voice settings."));
    setOpen(!open);
  };

  const pollBulk = () => {
    const timer = setInterval(async () => {
      try { const status = await load(); if (!status?.running) clearInterval(timer); }
      catch { clearInterval(timer); }
    }, 4000);
  };

  const saveSettings = async () => {
    setMessage("");
    try {
      const response = await client.put("/admin/game/voice/settings", { settings });
      setSettings(response.data.settings);
      setMessage("Voice settings saved.");
    } catch { setMessage("Could not save settings."); }
  };

  const saveText = async (asset) => {
    setBusyId(asset.narration_id); setMessage("");
    try { await client.put(`/admin/game/voice/assets/${asset.narration_id}`, { text: asset.text }); setMessage("Script text saved."); await load(); }
    catch { setMessage("Could not save text."); }
    setBusyId("");
  };

  const generate = async (asset, environment, force) => {
    setBusyId(`${asset.narration_id}:${environment}`); setMessage(""); setConfirmId("");
    try {
      await client.post(`/admin/game/voice/assets/${asset.narration_id}/generate`, { environment, force: !!force });
      setMessage(`${environment === "live" ? "Live" : "Test"} audio generated: ${asset.narration_id}`);
      await load();
    } catch (err) { setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Generation failed."); }
    setBusyId("");
  };

  const generateAllMissing = async () => {
    setBulkConfirm(false); setMessage("");
    try {
      const response = await client.post("/admin/game/voice/generate-missing-live");
      if (response.data.started) { setMessage(`Generating ${response.data.total} missing production clips…`); pollBulk(); }
      else setMessage("No missing production clips to generate.");
    } catch (err) { setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Could not start generation."); }
  };

  const generatePreview = async (asset) => {
    const pointId = asset.narration_id.replace("template_", "");
    const firstName = (previewNames[pointId] || "").trim();
    if (!firstName) { setMessage("Enter a first name for the preview clip."); return; }
    setBusyId(`preview:${pointId}`); setMessage("");
    try {
      await client.post("/admin/game/voice/personal-preview", { point_id: pointId, first_name: firstName });
      setMessage(`Personalized ${settings.voice_environment} clip ready.`);
      await load();
    } catch (err) { setMessage(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Generation failed."); }
    setBusyId("");
  };

  const playWithClip01 = (clip) => {
    const personal = new Audio(`${API}${clip.url}`);
    personal.onended = () => { new Audio(`${API}/game/voice/audio/c01?v=x`).play().catch(() => {}); };
    personal.play().catch(() => {});
  };

  const check = (key, label) => (
    <label style={{ display: "inline-block", marginRight: 18, marginTop: 8 }}>
      <input type="checkbox" checked={!!settings[key]} onChange={(event) => setSettings({ ...settings, [key]: event.target.checked })} data-testid={`voice-setting-${key}`} /> {label}
    </label>
  );

  return (
    <div className="admin-import-panel" style={{ marginTop: 20 }} data-testid="voice-guided-panel">
      <h3>Voice Guided Game
        {settings?.voice_environment === "test" && open && (
          <span style={{ marginLeft: 10, fontSize: 12, fontWeight: 800, color: "#92400e", background: "#fef3c7", padding: "3px 8px", borderRadius: 6 }} data-testid="voice-test-badge">TEST VOICE</span>
        )}
      </h3>
      <p style={{ color: "#555" }}>Narrator script ships preloaded word-for-word. Generate Test clips to approve the voice, then generate Live clips for production. Audio is never generated automatically. The API key stays server-side.</p>
      <button className="button button-small" onClick={toggle} data-testid="voice-guided-toggle">{open ? "Hide" : "Open Voice Settings"}</button>

      {open && settings && (
        <div style={{ marginTop: 12 }}>
          <div style={{ padding: 10, background: "#f9fafb", borderRadius: 8 }}>
            <label style={{ fontWeight: 700 }}>Active Voice Environment{" "}
              <select value={settings.voice_environment} onChange={(event) => setSettings({ ...settings, voice_environment: event.target.value })} data-testid="voice-environment-select">
                <option value="test">Test Voice (preview/approval)</option>
                <option value="live">Live Voice (production customers)</option>
              </select>
            </label>
            <p style={{ fontSize: 12.5, color: "#555", marginTop: 6 }}>
              Test Voice: {settings.test_voice_ref} · Live Voice: {settings.live_voice_ref} · API key: {settings.provider_key_configured ? "configured (server-side)" : "NOT configured"}
            </p>
          </div>

          <div style={{ marginTop: 10 }}>
            {check("voice_enabled", "Voice Guided Mode")}
            {check("read_type_enabled", "Read & Type Mode")}
            {check("narration_on", "Narration")}
            {check("personalization_on", "Personalized Voice Moments")}
            {check("browser_stt_on", "Browser Speech Recognition")}
            {check("generic_fallback_on", "Generic Voice Fallback")}
          </div>
          <div style={{ marginTop: 8 }}>
            <label style={{ marginRight: 18 }}>
              <span style={{ fontWeight: 600 }}>Default Mode </span>
              <select value={settings.default_mode} onChange={(event) => setSettings({ ...settings, default_mode: event.target.value })} data-testid="voice-setting-default-mode">
                <option value="voice">Voice Guided</option><option value="type">Read & Type</option>
              </select>
            </label>
            <label>
              <span style={{ fontWeight: 600 }}>Max Personalized Clips Per Game </span>
              <input type="number" min="0" max="10" style={{ width: 60 }} value={settings.max_personal_clips}
                onChange={(event) => setSettings({ ...settings, max_personal_clips: Number(event.target.value) })} data-testid="voice-setting-max-clips" />
            </label>
          </div>
          <button className="button" style={{ marginTop: 10 }} onClick={saveSettings} data-testid="voice-settings-save">Save Voice Settings</button>

          <div style={{ marginTop: 22, padding: 12, background: "#eef2ff", borderRadius: 8 }}>
            <strong>Production Narration</strong>
            <p style={{ fontSize: 13, marginTop: 4 }}>{missingLive.length} missing production clip{missingLive.length === 1 ? "" : "s"}. Completed clips are never regenerated by this action.</p>
            {bulk?.running ? (
              <p style={{ fontWeight: 700, marginTop: 6 }} data-testid="voice-bulk-progress">Generating… {bulk.done} of {bulk.total} clips complete{bulk.failed?.length ? ` (${bulk.failed.length} failed)` : ""}</p>
            ) : bulkConfirm ? (
              <div style={{ marginTop: 8 }} data-testid="voice-bulk-confirm">
                <p style={{ fontWeight: 700 }}>Generate Live Narration?</p>
                <p style={{ fontSize: 13, marginTop: 4 }}>You are about to generate {missingLive.length} missing production narration clips using ElevenLabs.</p>
                <p style={{ fontSize: 13, marginTop: 4 }}>Existing completed narration will not be regenerated.</p>
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button className="button button-small" onClick={() => setBulkConfirm(false)} data-testid="voice-bulk-cancel">Cancel</button>
                  <button className="button button-small" onClick={generateAllMissing} data-testid="voice-bulk-generate">Generate {missingLive.length} Missing Clips</button>
                </div>
              </div>
            ) : (
              <button className="button button-small" style={{ marginTop: 6 }} disabled={!missingLive.length}
                onClick={() => setBulkConfirm(true)} data-testid="voice-bulk-open">Generate All Missing Live Narration</button>
            )}
          </div>

          <h4 style={{ marginTop: 22 }}>Narration Library</h4>
          {assets.map((asset, index) => (
            <div key={asset.narration_id} style={{ marginTop: 12, borderTop: "1px solid #eee", paddingTop: 10 }} data-testid={`voice-asset-${asset.narration_id}`}>
              <strong>{asset.narration_id}</strong> — {asset.label}
              <span style={{ marginLeft: 8, fontSize: 12, color: "#666" }}>script v{asset.script_version}</span>
              {asset.kind === "static" && (asset.test.status !== "missing" || asset.live.status !== "missing") && (
                <audio controls preload="none" style={{ display: "block", marginTop: 6, width: "100%", maxWidth: 420 }}
                  src={`${API}/game/voice/audio/${asset.narration_id}?v=${settings.voice_environment}${asset[settings.voice_environment]?.version || 0}`}
                  data-testid={`voice-asset-player-${asset.narration_id}`} />
              )}
              <textarea rows={3} style={{ width: "100%", marginTop: 6, fontSize: 12.5 }} value={asset.text}
                onChange={(event) => setAssets(assets.map((row, i) => i === index ? { ...row, text: event.target.value } : row))}
                data-testid={`voice-asset-text-${asset.narration_id}`} />
              <div style={{ display: "flex", gap: 14, marginTop: 6, flexWrap: "wrap", alignItems: "center" }}>
                <button className="button button-small" disabled={busyId === asset.narration_id} onClick={() => saveText(asset)} data-testid={`voice-asset-save-${asset.narration_id}`}>Save Text</button>
                {asset.kind === "template" && (
                  <span>
                    <input placeholder="First name" style={{ width: 110 }} value={previewNames[asset.narration_id.replace("template_", "")] || ""}
                      onChange={(event) => setPreviewNames({ ...previewNames, [asset.narration_id.replace("template_", "")]: event.target.value })}
                      data-testid={`voice-preview-name-${asset.narration_id}`} />{" "}
                    <button className="button button-small" disabled={busyId === `preview:${asset.narration_id.replace("template_", "")}`}
                      onClick={() => generatePreview(asset)} data-testid={`voice-preview-generate-${asset.narration_id}`}>
                      {busyId === `preview:${asset.narration_id.replace("template_", "")}` ? "Generating…" : `Generate ${settings.voice_environment === "live" ? "Live" : "Test"} Preview Clip`}
                    </button>
                  </span>
                )}
                {asset.kind === "static" && (
                  <>
                    <span>Test: <StatusBadge status={asset.test.status} />{" "}
                      <button className="button button-small" disabled={busyId === `${asset.narration_id}:test`}
                        onClick={() => generate(asset, "test", asset.test.status !== "missing")} data-testid={`voice-gen-test-${asset.narration_id}`}>
                        {busyId === `${asset.narration_id}:test` ? "Generating…" : asset.test.status === "missing" ? "Generate Test Clip" : "Regenerate Test Clip"}
                      </button>
                    </span>
                    <span>Live: <StatusBadge status={asset.live.status} />{" "}
                      {asset.live.status === "ready" ? (
                        confirmId === asset.narration_id ? (
                          <span data-testid={`voice-live-confirm-${asset.narration_id}`}>
                            <em style={{ fontSize: 12 }}>Regenerate This Narration Clip? This will replace the current production audio for this clip using the current Live Voice.</em>{" "}
                            <button className="button button-small" onClick={() => setConfirmId("")} data-testid={`voice-live-cancel-${asset.narration_id}`}>Cancel</button>{" "}
                            <button className="button button-small" onClick={() => generate(asset, "live", true)} data-testid={`voice-live-regen-${asset.narration_id}`}>Regenerate Clip</button>
                          </span>
                        ) : (
                          <button className="button button-small" onClick={() => setConfirmId(asset.narration_id)} data-testid={`voice-live-regen-open-${asset.narration_id}`}>Regenerate Clip</button>
                        )
                      ) : (
                        <button className="button button-small" disabled={busyId === `${asset.narration_id}:live`}
                          onClick={() => generate(asset, "live", asset.live.status === "needs_regeneration")} data-testid={`voice-gen-live-${asset.narration_id}`}>
                          {busyId === `${asset.narration_id}:live` ? "Generating…" : "Generate Live Clip"}
                        </button>
                      )}
                      {asset.live.generated_at && <span style={{ fontSize: 11, color: "#666", marginLeft: 6 }}>{asset.live.generated_at.slice(0, 10)} · voice {asset.live.voice_ref}</span>}
                    </span>
                  </>
                )}
              </div>
            </div>
          ))}

          {personalClips.length > 0 && (
            <div style={{ marginTop: 22 }} data-testid="voice-personal-clips">
              <h4>Personalized Clips (cached)</h4>
              {personalClips.map((clip) => (
                <div key={clip.cache_key} style={{ marginTop: 10, borderTop: "1px solid #eee", paddingTop: 8 }} data-testid={`voice-personal-${clip.cache_key.slice(0, 8)}`}>
                  <strong>{clip.text}</strong>
                  <span style={{ marginLeft: 8, fontSize: 12, color: clip.environment === "test" ? "#92400e" : "#059669", fontWeight: 700 }}>{(clip.environment || "").toUpperCase()}</span>
                  <span style={{ marginLeft: 8, fontSize: 11, color: "#666" }}>{(clip.created_at || "").slice(0, 10)}</span>
                  <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 4 }}>
                    <audio controls preload="none" style={{ maxWidth: 320 }} src={`${API}${clip.url}`} data-testid={`voice-personal-player-${clip.cache_key.slice(0, 8)}`} />
                    <button className="button button-small" onClick={() => playWithClip01(clip)} data-testid={`voice-personal-chain-${clip.cache_key.slice(0, 8)}`}>Play With Clip 01</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {message && <p style={{ marginTop: 10 }} data-testid="voice-guided-message">{message}</p>}
    </div>
  );
};
