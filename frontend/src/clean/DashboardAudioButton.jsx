import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Pause, Volume2 } from "lucide-react";
import "./dashboard-audio.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TUTORIAL_BY_PRODUCT = {
  recruitment: "dashboard-recruitment",
  "board-fundraising-game": "dashboard-fundraising-game",
  recommitment: "dashboard-recommitment",
  "strategic-planning": "dashboard-strategic-planning",
};

const manifestCache = new Map();
const manifestPromises = new Map();

const loadManifest = (product) => {
  if (manifestCache.has(product)) return Promise.resolve(manifestCache.get(product));
  if (!manifestPromises.has(product)) {
    const tutorial = TUTORIAL_BY_PRODUCT[product];
    manifestPromises.set(product,
      axios.get(`${API}/game/voice/tutorial/${tutorial}`)
        .then((response) => {
          const clips = response.data.clips || {};
          manifestCache.set(product, clips);
          return clips;
        })
        .catch(() => ({}))
    );
  }
  return manifestPromises.get(product);
};

export const refreshDashboardAudioManifest = (product) => {
  manifestCache.delete(product);
  manifestPromises.delete(product);
};

export default function DashboardAudioButton({ product, narrationId, className = "" }) {
  const [clip, setClip] = useState(null);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    let live = true;
    loadManifest(product).then((clips) => {
      if (live) setClip(clips[narrationId] || null);
    });
    return () => {
      live = false;
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, [product, narrationId]);

  const toggle = async () => {
    if (!clip?.ready || !clip?.url) return;
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      setPlaying(false);
      return;
    }
    if (!audioRef.current) {
      audioRef.current = new Audio(`${API.replace(/\/api$/, "")}${clip.url}`);
      audioRef.current.onended = () => setPlaying(false);
      audioRef.current.onerror = () => setPlaying(false);
    }
    try {
      await audioRef.current.play();
      setPlaying(true);
    } catch {
      setPlaying(false);
    }
  };

  return (
    <button type="button" className={`dashboard-audio-button ${playing ? "is-playing" : ""} ${className}`}
      onClick={toggle} title={playing ? "Pause section audio" : "Play section audio"}
      aria-label={playing ? "Pause section audio" : "Play section audio"}
      data-testid={`dashboard-audio-${narrationId}`}>
      {playing ? <Pause size={16}/> : <Volume2 size={16}/>}
    </button>
  );
}
