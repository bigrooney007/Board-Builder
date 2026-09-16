import { useEffect, useState } from "react";
import { Volume2, VolumeX } from "lucide-react";

const MUTE_KEY = "bfg_narration_muted";
const PLAYED_KEY = "bfg_played_clips";

export const isNarrationMuted = () => sessionStorage.getItem(MUTE_KEY) === "1";
export const wasClipPlayed = (key) => (sessionStorage.getItem(PLAYED_KEY) || "").split(",").includes(key);
export const markClipPlayed = (key) => {
  const played = (sessionStorage.getItem(PLAYED_KEY) || "").split(",").filter(Boolean);
  if (!played.includes(key)) sessionStorage.setItem(PLAYED_KEY, [...played, key].join(","));
};

export const NarrationControl = ({ audioRef }) => {
  const [muted, setMuted] = useState(isNarrationMuted());
  useEffect(() => {
    const sync = () => setMuted(isNarrationMuted());
    window.addEventListener("bfg-mute-changed", sync);
    return () => window.removeEventListener("bfg-mute-changed", sync);
  }, []);
  const toggle = () => {
    const next = !isNarrationMuted();
    sessionStorage.setItem(MUTE_KEY, next ? "1" : "0");
    if (next && audioRef?.current) audioRef.current.pause();
    window.dispatchEvent(new Event("bfg-mute-changed"));
    setMuted(next);
  };
  return (
    <button onClick={toggle} aria-label={muted ? "Turn narration on" : "Turn narration off"}
      data-testid="bfg-narration-toggle"
      style={{ background: "transparent", border: "none", cursor: "pointer", color: "#6B7280", padding: 6 }}>
      {muted ? <VolumeX size={18} /> : <Volume2 size={18} />}
    </button>
  );
};
