import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import PublicStartLayout from "@/funnels/PublicStartLayout";
import { trackPlatformEvent } from "@/clean/platform";
import { usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RecruitFreePage() {
  usePageMeta("Start Your Board Recruitment | Nonprofit Board Builder", "Enter your details and answer the six recruitment questions.", true);
  const navigate = useNavigate();
  const [lead, setLead] = useState({ name: "", email: "", organization: "", count: "", notSure: false });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const savedToken = localStorage.getItem("recruitFreeToken");

  const start = async () => {
    if (!lead.name.trim() || !lead.email.trim() || !lead.organization.trim() || (!lead.count.trim() && !lead.notSure)) {
      setError("Add your name, email, organization and the number of board members you want, or choose I'm not sure yet.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(lead.email.trim()) || (!lead.notSure && Number(lead.count) < 1)) {
      setError("Enter a valid email and a board member number greater than zero.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await axios.post(`${API}/recruit/free/start`, {
        name: lead.name.trim(),
        email: lead.email.trim(),
        organization: lead.organization.trim(),
        desired_count: lead.notSure ? "not_sure" : lead.count.trim(),
      });
      if (response.data.existing) {
        setError(response.data.message || "Please check your email for your saved assessment link.");
        setBusy(false);
        return;
      }
      localStorage.setItem("recruitFreeToken", response.data.token);
      trackPlatformEvent("recruitment", "contact_entered");
      window.scrollTo({ top: 0 });
      navigate(`/recruit/questions?token=${encodeURIComponent(response.data.token)}`);
    } catch (err) {
      setError(err.response?.data?.detail || "We could not save your details. Please check them and try again.");
    }
    setBusy(false);
  };

  const field = {
    width: "100%",
    marginTop: 10,
    padding: 14,
    border: "1px solid #d1d5db",
    borderRadius: 12,
    fontSize: 16,
  };

  const leadForm = (
    <form className="public-start-card" data-testid="recruit-free-landing" style={{ textAlign: "center" }} onSubmit={(event) => { event.preventDefault(); start(); }}>
      <h1 data-testid="recruit-free-heading">
        Start With Your Six Recruitment Questions
      </h1>
      <p style={{ marginTop: 14 }}>
        Tell us about your organization. Your answers will be saved as you work through the questions.
      </p>
      <label className="sr-only" htmlFor="recruit-lead-name">Your name</label>
      <input id="recruit-lead-name" style={field} placeholder="Your name" autoComplete="name" required value={lead.name}
        onChange={(event) => setLead({ ...lead, name: event.target.value })} data-testid="recruit-free-name" />
      <label className="sr-only" htmlFor="recruit-lead-email">Email address</label>
      <input id="recruit-lead-email" style={field} placeholder="Email address" type="email" autoComplete="email" required value={lead.email}
        onChange={(event) => setLead({ ...lead, email: event.target.value })} data-testid="recruit-free-email" />
      <label className="sr-only" htmlFor="recruit-lead-org">Organization name</label>
      <input id="recruit-lead-org" style={field} placeholder="Organization name" autoComplete="organization" required value={lead.organization}
        onChange={(event) => setLead({ ...lead, organization: event.target.value })} data-testid="recruit-free-org" />

      <p style={{ marginTop: 16, fontWeight: 700, color: "#111827" }}>How many new Board Members do you want to recruit?</p>
      <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
        <input style={{ ...field, width: 140, marginTop: 8 }} inputMode="numeric" aria-label="Number of new board members" placeholder="Number"
          disabled={lead.notSure} value={lead.count}
          onChange={(event) => setLead({ ...lead, count: event.target.value.replace(/[^0-9]/g, "") })}
          data-testid="recruit-free-count" />
        <button type="button"
          className={`bfg-btn bfg-btn-sm ${lead.notSure ? "bfg-btn-primary" : "bfg-btn-ghost"}`}
          style={{ marginTop: 8 }}
          onClick={() => setLead({ ...lead, notSure: !lead.notSure, count: "" })}
          data-testid="recruit-free-not-sure">
          I'M NOT SURE YET
        </button>
      </div>

      <button type="submit" className="bfg-btn bfg-btn-primary" style={{ marginTop: 24 }} disabled={busy}
        data-testid="recruit-free-start-btn">
        {busy ? "Saving…" : "START MY SIX RECRUITMENT QUESTIONS"}
      </button>
      {savedToken && <p><button type="button" className="bfg-btn bfg-btn-ghost" onClick={() => navigate(`/recruit/questions?token=${encodeURIComponent(savedToken)}`)}>CONTINUE MY SAVED ASSESSMENT</button></p>}
      {error && <p className="bfg-error" data-testid="recruit-free-error">{error}</p>}
    </form>
  );

  return <PublicStartLayout backTo="/recruit" backLabel="Read about Board Recruitment" testId="recruit-start-page">{leadForm}</PublicStartLayout>;
}
