import { useEffect, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import { useMemberAuth } from "@/member/MemberAuthContext";
import "./game.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

let gameContentCache = null;
export const useGameContent = () => {
  const [content, setContent] = useState(gameContentCache);
  useEffect(() => {
    if (gameContentCache) return;
    axios.get(`${API}/game/content`).then((r) => { gameContentCache = r.data.content; setContent(gameContentCache); }).catch(() => {});
  }, []);
  return content;
};

export const money = (value) => {
  const num = Number(String(value ?? "").replace(/[^0-9.]/g, "")) || 0;
  return num ? `$${num.toLocaleString("en-US")}` : "";
};

export const formatDate = (value) => {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
};

export const GameVideo = ({ video, testId }) => (
  video?.youtube_id ? (
    <div className="bfg-video-frame" data-testid={testId}>
      <iframe
        src={`https://www.youtube.com/embed/${video.youtube_id}`}
        title="Board Fundraising Game video"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      />
    </div>
  ) : (
    <div className="bfg-video-frame bfg-video-placeholder" data-testid={testId}><p>Video coming soon</p></div>
  )
);

export const GameProgress = ({ steps, current }) => (
  <div className="bfg-progress" data-testid="bfg-progress">
    <p className="bfg-progress-label">Step {Math.min(current + 1, steps.length)} of {steps.length} — {steps[Math.min(current, steps.length - 1)]}</p>
    {steps.map((label, index) => (
      <span key={label} className={index < current ? "done" : index === current ? "current" : ""} />
    ))}
  </div>
);

export const BfgShell = ({ children, nav, shellClass = "" }) => {
  const navigate = useNavigate();
  const { member, loading, logout } = useMemberAuth();
  const defaultAuthNav = loading ? null : member ? (
    <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={async () => { await logout(); navigate("/login"); }} data-testid="bfg-default-logout-btn">Log Out</button>
  ) : (
    <Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/login" data-testid="bfg-default-login-btn">Log In</Link>
  );
  return (
    <div className={`bfg ${shellClass}`.trim()}>
      <header className="bfg-nav" style={{ justifyContent: "flex-end" }}>
        <div className="bfg-nav-actions">{nav ?? defaultAuthNav}</div>
      </header>
      {children}
      <footer className="bfg-footer">
        <p>© {new Date().getFullYear()} Nonprofit Board Builders, LLC. All rights reserved.</p>
        <Link to="/" data-testid="bfg-footer-home-link">Nonprofit Board Builder Home</Link>
      </footer>
    </div>
  );
};
