import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL || "";
const MUTE_KEY = "bfg_narration_muted";

// Prefer the owner's generated recording. Until a new script has been recorded,
// read the same words using the browser's voice where it is available.
export function useGuidedNarration(tutorial, narrationId, words) {
  const [clips, setClips] = useState(null);
  const [muted, setMuted] = useState(() => sessionStorage.getItem(MUTE_KEY) === "1");
  const mutedRef = useRef(muted);
  const audioRef = useRef(null);

  const stop = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    if (typeof window.speechSynthesis !== "undefined") window.speechSynthesis.cancel();
  }, []);

  useEffect(() => {
    let active = true;
    axios.get(`${BASE}/api/game/voice/tutorial/${tutorial}`)
      .then(({ data }) => { if (active) setClips(data.clips || {}); })
      .catch(() => { if (active) setClips({}); });
    return () => { active = false; stop(); };
  }, [tutorial, stop]);

  const play = useCallback(() => {
    stop();
    if (mutedRef.current || !narrationId) return;
    const clip = clips?.[narrationId];
    const speak = () => {
      if (!words || typeof window.speechSynthesis === "undefined" || typeof window.SpeechSynthesisUtterance === "undefined") return;
      const utterance = new window.SpeechSynthesisUtterance(words);
      utterance.lang = "en-US";
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    };
    if (!clip?.ready) { speak(); return; }
    const audio = new Audio(`${BASE}${clip.url}`);
    audioRef.current = audio;
    audio.play().catch(speak);
  }, [clips, narrationId, words, stop]);

  useEffect(() => {
    if (!clips) return undefined;
    play();
    return stop;
  }, [clips, play, stop]);

  const toggle = () => {
    const next = !mutedRef.current;
    mutedRef.current = next;
    sessionStorage.setItem(MUTE_KEY, next ? "1" : "0");
    if (next) stop();
    else play();
    setMuted(next);
  };

  return { muted, toggle, play, stop };
}
