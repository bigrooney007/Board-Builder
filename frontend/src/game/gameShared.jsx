import { useEffect, useState } from "react";
import axios from "axios";
import { Link, useLocation } from "react-router-dom";
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
  const content = useGameContent();
  const { pathname } = useLocation();
  const isRecruitment = pathname === "/recruit" || pathname.startsWith("/recruit/");
  return (
    <div className={`bfg ${shellClass}`.trim()}>
      <header className="bfg-nav">
        <Link to={isRecruitment ? "/recruit" : "/"} className="bfg-logo" data-testid="bfg-logo-link">
          <span className="bfg-logo-mark">{isRecruitment ? "NB" : "BG"}</span>
          <span><strong>Nonprofit Board Builder</strong><em>{isRecruitment ? "Board Recruitment" : "The Board Fundraising Game"}</em></span>
        </Link>
        <div className="bfg-nav-actions">{nav}</div>
      </header>
      {children}
      <footer className="bfg-footer">
        <p>© {new Date().getFullYear()} Nonprofit Board Builders, LLC. All rights reserved.</p>
        {!isRecruitment && <a href="/fundraising-system" data-testid="bfg-footer-system-link">Looking for the Fundraising Board Builder? Visit the fundraising system</a>}
        <a href={content?.footer_recruit_url || "/recruit"} data-testid="bfg-footer-recruit-link">
          {content?.footer_recruit_label || "Recruit Board Members With Fundraising Experience"}
        </a>
      </footer>
    </div>
  );
};
