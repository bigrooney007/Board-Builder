import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE = process.env.REACT_APP_BACKEND_URL;

export const fetchVoiceManifest = async (token) => {
  try { return (await axios.get(`${API}/game/voice/manifest/${token}`)).data; } catch { return null; }
};

export const ModeSelect = ({ onVoice, onType, readTypeEnabled }) => (
  <div data-testid="bfg-voice-mode-select">
    <h1>How Would You Like To Play?</h1>
    <div className="bfg-card" style={{ marginTop: 20, padding: 22, border: "2px solid #4f46e5" }}>
      <h2 style={{ fontSize: 20 }}>Voice Guided</h2>
      <p style={{ marginTop: 8 }}>Listen to your fundraising guide and simply speak when it is your turn to answer.</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 14 }} onClick={onVoice} data-testid="bfg-play-with-voice-btn">Play With Voice</button>
    </div>
    {readTypeEnabled && (
      <div className="bfg-card" style={{ marginTop: 14, padding: 22 }}>
        <h2 style={{ fontSize: 20 }}>Read & Type</h2>
        <p style={{ marginTop: 8 }}>Read the game and type your answers.</p>
        <button className="bfg-btn bfg-btn-ghost" style={{ marginTop: 14 }} onClick={onType} data-testid="bfg-read-type-btn">Read & Type</button>
      </div>
    )}
  </div>
);

export const PermissionScreen = ({ onGranted, onType }) => {
  const [error, setError] = useState("");
  const grant = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      onGranted();
    } catch { setError("We could not access your microphone. You can continue by typing your answers."); }
  };
  return (
    <div data-testid="bfg-voice-permission">
      <h1>Play With Voice</h1>
      <p style={{ marginTop: 14 }}>Your fundraising guide will walk you through the game. When it is your turn, simply speak naturally and your answer will appear as text for you to review. Your voice recording is not saved.</p>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 20 }} onClick={grant} data-testid="bfg-continue-with-voice-btn">Continue With Voice</button>
      {error && (<><p className="bfg-error">{error}</p>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 10 }} onClick={onType} data-testid="bfg-permission-type-btn">Read & Type Instead</button></>)}
    </div>
  );
};

const srSupported = () => !!(window.SpeechRecognition || window.webkitSpeechRecognition);

export const VoicePanel = ({ token, manifest, steps, stepsKey, onCapture, onFinished, soundOn, setSoundOn }) => {
  const [idx, setIdx] = useState(0);
  const [mode, setMode] = useState("idle");
  const [transcript, setTranscript] = useState("");
  const [paused, setPaused] = useState(false);
  const audioRef = useRef(null);
  const recRef = useRef(null);
  const silenceRef = useRef(null);
  const finishedRef = useRef(false);
  const soundRef = useRef(soundOn);
  soundRef.current = soundOn;

  const step = steps[idx] || null;

  const stopAudio = () => { if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; } };
  const stopRec = () => {
    clearTimeout(silenceRef.current);
    if (recRef.current) { try { recRef.current.onend = null; recRef.current.stop(); } catch { /* noop */ } recRef.current = null; }
  };

  const advance = useCallback(() => setIdx((current) => current + 1), []);

  const playUrl = useCallback((url, onEnd) => {
    stopAudio();
    if (!soundRef.current || !url) { onEnd(); return; }
    const audio = new Audio(`${BASE}${url}`);
    audioRef.current = audio;
    audio.onended = onEnd;
    audio.onerror = onEnd;
    audio.play().catch(onEnd);
  }, []);

  const startListening = useCallback(() => {
    if (!srSupported() || !manifest?.browser_stt_on) { setTranscript(""); setMode("typing"); return; }
    setMode("listening"); setTranscript("");
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    rec.continuous = true; rec.interimResults = true; rec.lang = "en-US";
    let finalText = "";
    rec.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        if (event.results[i].isFinal) finalText += `${event.results[i][0].transcript} `;
        else interim += event.results[i][0].transcript;
      }
      setTranscript((finalText + interim).trim());
      clearTimeout(silenceRef.current);
      silenceRef.current = setTimeout(() => { try { rec.stop(); } catch { /* noop */ } }, 3000);
    };
    rec.onend = () => {
      clearTimeout(silenceRef.current);
      recRef.current = null;
      setMode("transcribing");
      setTimeout(() => setMode("review"), 350);
    };
    rec.onerror = () => {};
    recRef.current = rec;
    rec.start();
  }, [manifest]);

  useEffect(() => { setIdx(0); setMode("idle"); finishedRef.current = false; }, [stepsKey]);

  useEffect(() => {
    stopAudio(); stopRec(); setPaused(false);
    if (!step) {
      if (!finishedRef.current && steps.length) { finishedRef.current = true; onFinished?.(); }
      setMode("idle");
      return undefined;
    }
    if (step.clip) {
      setMode("speaking");
      const clip = manifest?.clips?.[step.clip];
      playUrl(clip?.ready ? clip.url : "", advance);
    } else if (step.personal) {
      setMode("speaking");
      axios.post(`${API}/game/voice/personal/${token}`, { point_id: step.personal })
        .then((response) => {
          const fallback = manifest?.clips?.[response.data.fallback_narration_id];
          playUrl(response.data.url || (fallback?.ready ? fallback.url : ""), advance);
        })
        .catch(advance);
    } else if (step.capture) {
      startListening();
    }
    return () => { stopAudio(); stopRec(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, stepsKey, steps.length]);

  if (!step) return null;
  const capture = step.capture;

  const accept = (again) => {
    const text = transcript.trim();
    if (text) onCapture(capture.target, text);
    if (again) startListening(); else advance();
  };

  return (
    <div className="bfg-card" style={{ marginTop: 18, padding: 20, textAlign: "center" }} data-testid="bfg-voice-panel">
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }} className="bfg-no-print">
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setSoundOn(!soundOn)} data-testid="bfg-sound-toggle">
          {soundOn ? "Sound Off" : "Turn Voice Back On"}
        </button>
        {mode === "speaking" && soundOn && (
          <>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" data-testid="bfg-narration-pause"
              onClick={() => { if (audioRef.current) { if (paused) audioRef.current.play(); else audioRef.current.pause(); setPaused(!paused); } }}>
              {paused ? "Resume" : "Pause"}
            </button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" data-testid="bfg-narration-replay"
              onClick={() => { if (audioRef.current) { audioRef.current.currentTime = 0; audioRef.current.play(); setPaused(false); } }}>
              Replay
            </button>
          </>
        )}
      </div>
      {mode === "speaking" && (
        <p style={{ marginTop: 10, fontWeight: 700 }} data-testid="bfg-guide-speaking">Your Fundraising Game Guide Is Speaking…</p>
      )}
      {capture && mode === "listening" && (
        <div data-testid="bfg-voice-listening">
          <p style={{ fontWeight: 800, fontSize: 22, marginTop: 8 }}>Your Turn</p>
          <p style={{ marginTop: 6, fontWeight: 700, color: "#4f46e5" }}>● Listening…</p>
          {capture.label && <p style={{ marginTop: 8, fontWeight: 600 }}>{capture.label}</p>}
          {transcript && <p style={{ marginTop: 10, fontSize: 14 }}>{transcript}</p>}
          <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 14, flexWrap: "wrap" }}>
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => stopRec() || setMode("review")} data-testid="bfg-im-done-btn">I'm Done</button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => { stopRec(); setMode("typing"); }} data-testid="bfg-type-instead-btn">Type Instead</button>
            {capture.skippable && <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => { stopRec(); advance(); }} data-testid="bfg-skip-btn">Skip</button>}
          </div>
        </div>
      )}
      {capture && mode === "transcribing" && <p style={{ marginTop: 12, fontWeight: 700 }} data-testid="bfg-transcribing">Turning Your Answer Into Text…</p>}
      {capture && (mode === "review" || mode === "typing") && (
        <div style={{ textAlign: "left", marginTop: 12 }} data-testid="bfg-voice-review">
          <h3 style={{ textAlign: "center" }}>{mode === "typing" ? (capture.label || "Type your answer") : "Here's What We Heard"}</h3>
          {mode === "typing" && !srSupported() && (
            <p style={{ fontSize: 13.5, marginTop: 6, textAlign: "center" }}>Voice answers aren't available on this device right now. You can continue by typing your answer.</p>
          )}
          {mode === "review" && <p style={{ fontSize: 13.5, marginTop: 6, textAlign: "center" }}>Review your answer. You can change anything before continuing.</p>}
          <textarea rows={4} style={{ width: "100%", marginTop: 10 }} value={transcript}
            onChange={(event) => setTranscript(event.target.value)} data-testid="bfg-voice-transcript" />
          <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 12, flexWrap: "wrap" }}>
            {capture.list && <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={!transcript.trim()} onClick={() => accept(true)} data-testid="bfg-add-another-btn">{capture.addLabel || "+ Add Another"}</button>}
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" disabled={!transcript.trim() && !capture.skippable} onClick={() => accept(false)} data-testid="bfg-voice-continue-btn">Continue</button>
            {srSupported() && <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={startListening} data-testid="bfg-say-again-btn">Say It Again</button>}
            {capture.skippable && <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={advance} data-testid="bfg-review-skip-btn">Skip</button>}
          </div>
        </div>
      )}
    </div>
  );
};
