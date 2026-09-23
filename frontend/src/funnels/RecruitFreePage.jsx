import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import RecruitmentHomePage from "@/funnels/RecruitmentHomePage";
import { trackPlatformEvent } from "@/clean/platform";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RecruitFreePage() {
  const navigate = useNavigate();
  const [lead, setLead] = useState({ name: "", email: "", organization: "", count: "", notSure: false });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    document.title = "Board Recruitment | Nonprofit Board Builder";
    localStorage.removeItem("recruitFreeToken");
  }, []);

  const start = async () => {
    if (!lead.name.trim() || !lead.email.trim() || !lead.organization.trim() || (!lead.count.trim() && !lead.notSure)) {
      setError("Please complete every field, or choose I'M NOT SURE YET.");
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
      localStorage.setItem("recruitFreeToken", response.data.token);
      trackPlatformEvent("recruitment", "contact_entered");
      navigate("/recruit/walkthrough");
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
    fontSize: 15,
  };

  const leadForm = (
    <div data-testid="recruit-free-landing" style={{ textAlign: "center" }}>
      <h3 style={{ marginTop: 0, fontSize: 22, lineHeight: 1.3 }} data-testid="recruit-free-heading">
        See The Exact Step-By-Step Process To Recruit The Board Members Your Organization Needs
      </h3>
      <p style={{ marginTop: 14 }}>
        Tell us who you are and how many new Board Members you want to recruit. The six strategic Recruitment Questions come after you join the platform.
      </p>
      <input style={field} placeholder="Your Name" value={lead.name}
        onChange={(event) => setLead({ ...lead, name: event.target.value })} data-testid="recruit-free-name" />
      <input style={field} placeholder="Email Address" type="email" value={lead.email}
        onChange={(event) => setLead({ ...lead, email: event.target.value })} data-testid="recruit-free-email" />
      <input style={field} placeholder="Organization Name" value={lead.organization}
        onChange={(event) => setLead({ ...lead, organization: event.target.value })} data-testid="recruit-free-org" />

      <p style={{ marginTop: 16, fontWeight: 700, color: "#111827" }}>How many new Board Members do you want to recruit?</p>
      <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
        <input style={{ ...field, width: 140, marginTop: 8 }} inputMode="numeric" placeholder="Number"
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

      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 24 }} disabled={busy}
        onClick={start} data-testid="recruit-free-start-btn">
        {busy ? "Opening…" : "SHOW ME THE STEP-BY-STEP PROCESS"}
      </button>
      {error && <p className="bfg-error" data-testid="recruit-free-error">{error}</p>}
    </div>
  );

  return <RecruitmentHomePage form={leadForm} />;
}
