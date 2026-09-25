import { Volume2 } from "lucide-react";

const MUTE_KEY = "bfg_narration_muted";
const PLAYED_KEY = "bfg_played_clips";

export const isNarrationMuted = () => sessionStorage.getItem(MUTE_KEY) === "1";
export const wasClipPlayed = (key) => (sessionStorage.getItem(PLAYED_KEY) || "").split(",").includes(key);
export const markClipPlayed = (key) => {
  const played = (sessionStorage.getItem(PLAYED_KEY) || "").split(",").filter(Boolean);
  if (!played.includes(key)) sessionStorage.setItem(PLAYED_KEY, [...played, key].join(","));
};

export const NarrationControl = ({ onReplay }) => {
  const replay = () => {
    sessionStorage.setItem(MUTE_KEY, "0");
    window.dispatchEvent(new Event("bfg-mute-changed"));
    onReplay?.();
  };
  return (
    <span style={{ display: "inline-flex", alignItems: "center" }}>
      <button onClick={replay} aria-label="Play audio instructions" title="Play audio instructions"
        data-testid="bfg-narration-toggle"
        style={{ background: "transparent", border: "none", cursor: "pointer", color: "#6B7280", padding: 6 }}>
        <Volume2 size={18} />
      </button>
    </span>
  );
};
