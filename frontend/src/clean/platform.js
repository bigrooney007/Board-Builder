import { useEffect, useMemo, useState } from "react";
import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const FLOW_ROUTES = {
  main: { home: "/", dashboard: "" },
  recruitment: { home: "/recruit", demonstration: "/recruit/walkthrough", onboarding: "/recruit/welcome", dashboard: "/app/board-recruitment" },
  "board-fundraising-game": { home: "/board-fundraising-game", demonstration: "/game/demonstration", onboarding: "/game/welcome", dashboard: "/game/dashboard" },
  "strategic-planning": { home: "/strategic-planning", demonstration: "/strategic-planning/video", onboarding: "/strategic-planning/welcome", dashboard: "/strategic-planning/dashboard" },
  "board-recommitment": { home: "/board-recommitment", demonstration: "/board-recommitment/video", onboarding: "/board-recommitment/welcome", dashboard: "/board-recommitment/dashboard" },
  "facilitated-game": { home: "/organize-board-fundraising-game", dashboard: "" },
  "board-applicant-network": { home: "/join-a-board", dashboard: "" },
};

export const VIDEO_KEYS = [
  ["recruitment_demonstration", "Board Recruitment Demonstration", "recruitment"],
  ["recruitment_welcome", "Board Recruitment Onboarding", "recruitment"],
  ["game_homepage", "Board Fundraising Game Demonstration", "board-fundraising-game"],
  ["game_welcome", "Board Fundraising Game Onboarding", "board-fundraising-game"],
  ["strategic_planning_demonstration", "Strategic Planning Demonstration", "strategic-planning"],
  ["strategic_planning_welcome", "Strategic Planning Onboarding", "strategic-planning"],
  ["board_recommitment_demonstration", "Board Recommitment Demonstration", "board-recommitment"],
  ["board_recommitment_welcome", "Board Recommitment Onboarding", "board-recommitment"],
];

export const HOMEPAGE_KEYS = [
  ["main", "Main Home Page"],
  ["recruitment", "Board Recruitment"],
  ["board-fundraising-game", "Board Fundraising Game"],
  ["strategic-planning", "Strategic Planning"],
  ["board-recommitment", "Board Recommitment"],
  ["facilitated-game", "Let's Organize Your Board Fundraising Game"],
];

export const RECRUITMENT_SECTION_VIDEO_KEYS = [
  ["questions", "Answer The Six Recruitment Questions"],
  ["identify", "Identify The Board Members You Need"],
  ["materials", "Build The Application And Campaign Materials"],
  ["launch", "Launch Your Recruitment Campaign"],
  ["applicants", "Review Applicants"],
  ["interviews", "Run Board Candidate Interviews"],
  ["references", "Complete Reference Checks"],
  ["background", "Complete Background Checks"],
  ["onboarding-prep", "Prepare Onboarding And Appointment Emails"],
  ["onboarding-session", "Facilitate The Onboarding Session"],
  ["portfolios", "Create Board Member Portfolios"],
];

const VISITOR_KEY = "nbb_clean_visitor_id";

export const visitorId = () => {
  let value = localStorage.getItem(VISITOR_KEY);
  if (!value) {
    value = (window.crypto?.randomUUID?.() || `v_${Date.now()}_${Math.random().toString(36).slice(2)}`);
    localStorage.setItem(VISITOR_KEY, value);
  }
  return value;
};

export const trackPlatformEvent = (flow, event, extra = {}) => {
  if (!flow || !event) return Promise.resolve();
  return axios.post(`${API}/platform-analytics/event`, {
    flow,
    event,
    page: window.location.pathname,
    video_key: extra.video_key || "",
    visitor_id: visitorId(),
    progress: Number(extra.progress || 0),
    active_seconds: Number(extra.active_seconds || 0),
    metadata: extra.metadata || {},
  }).catch(() => {});
};

export const flowForPath = (pathname) => {
  if (pathname === "/") return "main";
  if (pathname === "/join-a-board") return "board-applicant-network";
  if (pathname.startsWith("/organize-board-fundraising-game")) return "facilitated-game";
  if (pathname.startsWith("/recruit") || pathname.startsWith("/app/board-recruitment") || pathname.startsWith("/onboarding-session")) return "recruitment";
  if (pathname.startsWith("/board-fundraising-game") || pathname.startsWith("/game") || pathname.startsWith("/play/") || pathname.startsWith("/group-game/") || pathname.startsWith("/board-portfolio/") || pathname.startsWith("/board-assistant/") || pathname.startsWith("/relationship-mapping/") || pathname.startsWith("/strategy/")) return "board-fundraising-game";
  if (pathname.startsWith("/strategic-") || pathname.startsWith("/community-need-research") || pathname.startsWith("/area-pack")) return "strategic-planning";
  if (pathname.startsWith("/board-recommitment") || pathname.startsWith("/portfolio/")) return "board-recommitment";
  return "";
};

export const dashboardForPath = (pathname) => Object.entries(FLOW_ROUTES).find(([, value]) => value.dashboard && value.dashboard === pathname)?.[0] || "";

export const platformUseFlowForPath = (pathname) => {
  if (pathname.startsWith("/app/board-recruitment") || pathname.startsWith("/app/recruitment/")) return "recruitment";
  if (
    pathname === "/game/dashboard" || pathname === "/game/setup" || pathname === "/game/group" ||
    pathname.startsWith("/play/") || pathname.startsWith("/group-game/") ||
    pathname.startsWith("/game/strategy/") || pathname.startsWith("/game/portfolios") ||
    pathname.startsWith("/board-portfolio/") || pathname.startsWith("/board-assistant/") ||
    pathname.startsWith("/game/host/") || pathname.startsWith("/game/relationships") ||
    pathname.startsWith("/relationship-mapping/") || pathname.startsWith("/game/final/") ||
    pathname === "/game/complete"
  ) return "board-fundraising-game";
  if (pathname === "/strategic-planning/dashboard" || pathname === "/strategic-planning/session") return "strategic-planning";
  if (pathname === "/board-recommitment/dashboard") return "board-recommitment";
  return "";
};

export const useHomepageContent = (pageKey, defaults = {}) => {
  const [remote, setRemote] = useState({});
  useEffect(() => {
    let live = true;
    axios.get(`${API}/platform/homepages/${pageKey}`)
      .then((response) => { if (live) setRemote(response.data.content || {}); })
      .catch(() => {});
    return () => { live = false; };
  }, [pageKey]);
  return useMemo(() => ({ ...defaults, ...remote }), [defaults, remote]);
};

let videosCache = null;
let videosPromise = null;

const loadVideos = () => {
  if (videosCache) return Promise.resolve(videosCache);
  if (!videosPromise) {
    videosPromise = axios.get(`${API}/platform/videos`).then((response) => {
      videosCache = response.data.videos || [];
      return videosCache;
    }).catch(() => []);
  }
  return videosPromise;
};

export const usePlatformVideo = (key) => {
  const [video, setVideo] = useState(() => videosCache?.find((item) => item.key === key) || null);
  useEffect(() => {
    let live = true;
    loadVideos().then((rows) => { if (live) setVideo(rows.find((item) => item.key === key) || null); });
    return () => { live = false; };
  }, [key]);
  return video;
};


let recruitmentSectionVideosCache = null;
let recruitmentSectionVideosPromise = null;

const loadRecruitmentSectionVideos = () => {
  if (recruitmentSectionVideosCache) return Promise.resolve(recruitmentSectionVideosCache);
  if (!recruitmentSectionVideosPromise) {
    recruitmentSectionVideosPromise = axios.get(`${API}/platform/recruitment-section-videos`).then((response) => {
      recruitmentSectionVideosCache = response.data.videos || [];
      return recruitmentSectionVideosCache;
    }).catch(() => []);
  }
  return recruitmentSectionVideosPromise;
};

export const useRecruitmentSectionVideo = (key) => {
  const [video, setVideo] = useState(() => recruitmentSectionVideosCache?.find((item) => item.key === key) || null);
  useEffect(() => {
    let live = true;
    loadRecruitmentSectionVideos().then((rows) => {
      if (live) setVideo(rows.find((item) => item.key === key) || null);
    });
    return () => { live = false; };
  }, [key]);
  return video;
};
