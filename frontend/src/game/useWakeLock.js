import { useEffect, useRef } from "react";

export const useWakeLock = (active) => {
  const lockRef = useRef(null);

  useEffect(() => {
    if (!active || !navigator.wakeLock) return undefined;
    let cancelled = false;
    const acquire = async () => {
      try {
        lockRef.current = await navigator.wakeLock.request("screen");
      } catch { /* unsupported or denied — never blocks the game */ }
    };
    const onVisible = () => { if (!cancelled && document.visibilityState === "visible") acquire(); };
    acquire();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisible);
      if (lockRef.current) { lockRef.current.release().catch(() => {}); lockRef.current = null; }
    };
  }, [active]);
};

export default useWakeLock;
