import { useEffect, useState } from "react";
import axios from "axios";
import StrategicPlanningDashboard from "./StrategicPlanningDashboard";
import { BfgShell } from "@/game/gameShared";
import "./guided-products.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function FacilitatedPlanningComplete() {
  return <BfgShell><main className="guided-page"><section className="guided-section guided-confirm">
    <p className="bfg-eyebrow">STRATEGIC PLANNING</p>
    <h1>Your organization’s starting point is saved.</h1>
    <p>Rooney will use your answers to prepare the Board’s planning questions and meeting. You can return to your personal link to review what you shared.</p>
  </section></main></BfgShell>;
}

export function FacilitatedPlanningDashboard() {
  const sid = new URLSearchParams(window.location.search).get("session_id") || "";
  const [access, setAccess] = useState(null);
  useEffect(() => {
    if (!sid) { setAccess("Missing workspace link."); return; }
    axios.get(`${API}/guided/admin/strategic-planning/facilitated-access`,
      { params: { session_id: sid }, withCredentials: true })
      .then(() => setAccess(true))
      .catch(e => setAccess(e.response?.data?.detail || "Administrator login required."));
  }, [sid]);
  if (access !== true) return <BfgShell><main className="guided-page"><section className="guided-section">
    <h1>Facilitated Strategic Planning</h1><p>{access || "Opening workspace…"}</p>
  </section></main></BfgShell>;
  return <StrategicPlanningDashboard />;
}
