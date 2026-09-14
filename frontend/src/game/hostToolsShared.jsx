import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import "./game.css";

export const useHostTools = (memberId) => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  useEffect(() => {
    memberApi.get("/game/host-tools/content", { params: memberId ? { member_id: memberId } : {} })
      .then((response) => setData(response.data))
      .catch((err) => {
        if (err.response?.status === 401) navigate("/game/signup?mode=login", { replace: true });
        else navigate("/game/dashboard", { replace: true });
      });
  }, [memberId, navigate]);
  return data;
};

export const copyText = async (text) => {
  try { await navigator.clipboard.writeText(text); } catch { window.prompt("Copy this text:", text); }
};

export const HostDocShell = ({ children, actions, testId }) => (
  <div className="bfg bfg-pf-page bfg-ht-page" data-testid={testId}>
    <div className="bfg-ht-top bfg-no-print">
      <Link to="/game/dashboard" className="bfg-ht-back" data-testid="bfg-ht-back-link">← Back To Dashboard</Link>
      <div className="bfg-ht-actions">{actions}</div>
    </div>
    <div className="bfg-pf-doc">{children}</div>
  </div>
);

export const HostContextHeader = ({ title, rows }) => (
  <header className="bfg-pf-header">
    <p className="bfg-pf-eyebrow">Board Fundraising Game — Host Tools</p>
    <h1>{title}</h1>
    <div className="bfg-ht-meta">
      {rows.filter(([, value]) => value !== "" && value !== null && value !== undefined).map(([label, value]) => (
        <p key={label}><span>{label}:</span> <strong>{value}</strong></p>
      ))}
    </div>
  </header>
);

export const Paragraphs = ({ text }) => (
  <>{String(text || "").split("\n").filter((line) => line.trim()).map((line, index) => <p key={index}>{line}</p>)}</>
);
