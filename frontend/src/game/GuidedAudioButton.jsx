import { Volume2, VolumeX } from "lucide-react";

export default function GuidedAudioButton({ narration }) {
  return <button type="button" className="guided-audio-button" onClick={narration.toggle}
    aria-label={narration.muted ? "Turn audio on" : "Turn audio off"}
    aria-pressed={!narration.muted} title={narration.muted ? "Turn audio on" : "Turn audio off"}
    data-testid="guided-audio-toggle">
    {narration.muted ? <VolumeX size={20} /> : <Volume2 size={20} />}
  </button>;
}
