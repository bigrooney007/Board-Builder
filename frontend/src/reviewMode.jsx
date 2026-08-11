import { useEffect, useState } from "react";
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
