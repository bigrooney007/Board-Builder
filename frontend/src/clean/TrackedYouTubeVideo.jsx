import { useEffect, useRef, useState } from "react";
import { trackPlatformEvent } from "./platform";

let apiPromise;
const youtubeApi = () => {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (apiPromise) return apiPromise;
  apiPromise = new Promise((resolve) => {
    const prior = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      if (typeof prior === "function") prior();
      resolve(window.YT);
    };
    if (!document.querySelector('script[src="https://www.youtube.com/iframe_api"]')) {
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(script);
    }
  });
  return apiPromise;
};

export default function TrackedYouTubeVideo({ video, flow, testId, title = "Product video", placeholder = "Video coming soon" }) {
  const mountRef = useRef(null);
  const playerRef = useRef(null);
  const startedRef = useRef(false);
  const sentProgressRef = useRef(0);
  const timerRef = useRef(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!video?.youtube_id || !mountRef.current) return undefined;
    let live = true;
    youtubeApi().then((YT) => {
      if (!live || !mountRef.current) return;
      playerRef.current = new YT.Player(mountRef.current, {
        videoId: video.youtube_id,
        playerVars: { rel: 0 },
        events: {
          onReady: () => setReady(true),
          onStateChange: (event) => {
            if (event.data === YT.PlayerState.PLAYING) {
              if (!startedRef.current) {
                startedRef.current = true;
                trackPlatformEvent(flow, "video_started", { video_key: video.key, progress: 0 });
              }
              if (!timerRef.current) {
                timerRef.current = window.setInterval(() => {
                  const player = playerRef.current;
                  const duration = Number(player?.getDuration?.() || 0);
                  const current = Number(player?.getCurrentTime?.() || 0);
                  if (!duration) return;
                  const progress = Math.min(99, Math.round((current / duration) * 100));
                  const checkpoint = Math.floor(progress / 10) * 10;
                  if (checkpoint >= 10 && checkpoint > sentProgressRef.current) {
                    sentProgressRef.current = checkpoint;
                    trackPlatformEvent(flow, "video_progress", { video_key: video.key, progress: checkpoint });
                  }
                }, 5000);
              }
            }
            if (event.data === YT.PlayerState.ENDED) {
              if (timerRef.current) window.clearInterval(timerRef.current);
              timerRef.current = null;
              sentProgressRef.current = 100;
              trackPlatformEvent(flow, "video_completed", { video_key: video.key, progress: 100 });
            }
          },
        },
      });
    });
    return () => {
      live = false;
      if (timerRef.current) window.clearInterval(timerRef.current);
      timerRef.current = null;
      try { playerRef.current?.destroy?.(); } catch {}
      playerRef.current = null;
    };
  }, [video?.youtube_id, video?.key, flow]);

  if (!video?.youtube_id) {
    return <div className="bfg-video-frame bfg-video-placeholder" data-testid={testId}><p>{placeholder}</p></div>;
  }

  return (
    <div className="bfg-video-frame" data-testid={testId} aria-label={title}>
      <div ref={mountRef} style={{ width: "100%", height: "100%" }} />
      {!ready && <span className="sr-only">Loading video</span>}
    </div>
  );
}
