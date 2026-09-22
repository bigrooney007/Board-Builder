import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { dashboardForPath, flowForPath, trackPlatformEvent } from "./platform";

export default function PlatformAnalytics() {
  const location = useLocation();
  const activeRef = useRef({ flow: "", started: Date.now(), sent: 0 });

  useEffect(() => {
    const flow = flowForPath(location.pathname);
    if (!flow) return undefined;
    trackPlatformEvent(flow, "page_view");
    const dashboardFlow = dashboardForPath(location.pathname);
    if (dashboardFlow) trackPlatformEvent(dashboardFlow, "dashboard_entered");
    activeRef.current = { flow: dashboardFlow, started: Date.now(), sent: 0 };

    const flush = () => {
      const state = activeRef.current;
      if (!state.flow) return;
      const total = Math.floor((Date.now() - state.started) / 1000);
      const delta = total - state.sent;
      if (delta < 10) return;
      state.sent = total;
      trackPlatformEvent(state.flow, "platform_active", { active_seconds: Math.min(delta, 3600) });
    };
    const timer = dashboardFlow ? window.setInterval(flush, 30000) : null;
    window.addEventListener("pagehide", flush);
    return () => {
      if (timer) window.clearInterval(timer);
      flush();
      window.removeEventListener("pagehide", flush);
    };
  }, [location.pathname]);

  return null;
}
