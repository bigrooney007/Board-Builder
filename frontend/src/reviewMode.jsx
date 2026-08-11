import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
let cached = null;
let pending = null;

export const useReviewMode = () => {
  const [active, setActive] = useState(cached === true);
  useEffect(() => {
    if (cached !== null) { setActive(cached); return; }
    if (!pending) {
      pending = axios.get(`${API}/review-mode/status`, { withCredentials: true })
        .then((response) => { cached = !!response.data.active; return cached; })
        .catch(() => { cached = false; return false; });
    }
    pending.then((value) => setActive(value));
  }, []);
  return active;
};

export const ReviewModeBanner = () => {
  const active = useReviewMode();
  if (!active) return null;
  return (
    <div className="review-mode-banner" data-testid="owner-review-banner">
      OWNER REVIEW MODE — Customer validation, payment and execution requirements are temporarily bypassed for this admin account only.
    </div>
  );
};

const MODULE_TITLES = {
  1: "Identify the Board Members Your Organization Needs",
  2: "Build Your Recruitment Strategy",
  3: "Launch Your Recruitment Campaign",
  4: "Interview Your Applicants",
  5: "Complete References and Background Checks",
  6: "Onboard Your New Board Members",
};

const reviewLabelFor = (path) => {
  if (path === "/recruit") return "Recruitment Form";
  if (path === "/recruit/process") return "Recruitment Process Page";
  if (path === "/recruit/checkout") return "Checkout Page";
  const match = path.match(/^\/app\/recruitment\/[^/]+\/module\/(\d)/);
  if (match) return `Module ${match[1]} — ${MODULE_TITLES[match[1]] || ""}`.trim();
  if (path.startsWith("/app/recruitment")) return "Program Overview";
  if (path.startsWith("/app/materials")) return "Materials Library";
  return "";
};

export const ReviewProgressTracker = () => {
  const active = useReviewMode();
  const { pathname } = useLocation();
  useEffect(() => {
    if (!active) return;
    const label = reviewLabelFor(pathname);
    if (!label) return;
    axios.post(`${API}/review-mode/progress`, { route: pathname, label }, { withCredentials: true }).catch(() => {});
  }, [active, pathname]);
  return null;
};
