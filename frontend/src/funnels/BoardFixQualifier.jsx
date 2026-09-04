import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIMELINES = ["As soon as possible", "Within 30 days", "Within 60 days", "Within 90 days", "I am not sure yet"];

const BRANCHES = {
  recruitment: {
    optionLabel: "I need to recruit the right Board Members",
    countLabel: "How many Board Members do you need to recruit?",
    timelineLabel: "How soon do you need to have them recruited?",
  },
  fundraising_activation: {
    optionLabel: "I need to activate my Board to start raising money and build our fundraising system",
    countLabel: "How many Board Members do you currently have?",
    timelineLabel: "How soon do you need your Board actively helping you raise money and build your organization's fundraising system?",
  },
};

const cardStyle = { border: "1px solid #d8ded9", borderRadius: 10, padding: "22px 24px", background: "#fff" };

export const BoardFixQualifier = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [priority, setPriority] = useState("");
  const [count, setCount] = useState("");
  const [timeline, setTimeline] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = new URLSearchParams(location.search).get("t") || "";
    if (token) {
      try { sessionStorage.setItem("funnelLeadContext", JSON.stringify({ result_token: token })); } catch { /* best effort */ }
    }
  }, [location.search]);

  const storedToken = () => {
    try { return JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}").result_token || ""; } catch { return ""; }
  };

  const branch = priority ? BRANCHES[priority] : null;

  const submit = async () => {
    setError("");
    if (!count.trim()) { setError("Enter a number so I can point you to the right process."); return; }
    if (!timeline) { setError("Choose the timeline that best fits your situation."); return; }
    setBusy(true);
    try {
      const response = await axios.post(`${API}/funnel-leads/qualify`, {
        token: storedToken(), priority, board_count: count.trim(), timeline,
      });
      navigate(response.data.route);
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your answers. Please try again.");
      setBusy(false);
    }
  };

  return (
    <section className="board-fix-qualifier" data-testid="board-fix-qualifier" style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 26 }}>
      <div style={cardStyle} data-testid="qualifier-priority-card">
        <h2 style={{ textAlign: "center", fontWeight: 800, fontSize: "1.7rem", marginTop: 0 }} data-testid="qualifier-heading">What Does Your Board Need Most Right Now?</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 14 }}>
          {Object.entries(BRANCHES).map(([key, meta]) => (
            <button key={key} type="button"
              className={priority === key ? "button" : "button button-outline"}
              onClick={() => { setPriority(key); setCount(""); setTimeline(""); setError(""); }}
              data-testid={`qualifier-priority-${key}`}
              style={{ textAlign: "center", whiteSpace: "normal", lineHeight: 1.35 }}>
              {meta.optionLabel}
            </button>
          ))}
        </div>
      </div>
      {branch && (
        <div style={cardStyle} data-testid={`qualifier-branch-${priority}`}>
          <label className="field" style={{ display: "block" }}>
            <span style={{ fontWeight: 700 }}>{branch.countLabel}</span>
            <input type="number" min="0" max="99" value={count} onChange={(e) => setCount(e.target.value)}
              data-testid="qualifier-count-input" style={{ display: "block", marginTop: 8, padding: "10px 12px", borderRadius: 6, border: "1px solid #cfd6d2", width: 140 }} />
          </label>
          <p style={{ fontWeight: 700, marginBottom: 8, marginTop: 18 }}>{branch.timelineLabel}</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {TIMELINES.map((option) => (
              <button key={option} type="button" className={timeline === option ? "button button-small" : "button button-small button-outline"}
                onClick={() => setTimeline(option)} data-testid={`qualifier-timeline-${option.replace(/\s+/g, "-").toLowerCase()}`}>
                {option}
              </button>
            ))}
          </div>
          <div style={{ marginTop: 20 }}>
            <button type="button" className="button" onClick={submit} disabled={busy} data-testid="qualifier-submit-button">
              {busy ? "One moment…" : "SHOW ME WHAT TO DO"}
            </button>
          </div>
          {error && <p className="submit-error" data-testid="qualifier-error" style={{ marginTop: 10 }}>{error}</p>}
        </div>
      )}
    </section>
  );
};
