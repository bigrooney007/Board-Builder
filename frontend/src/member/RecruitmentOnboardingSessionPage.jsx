import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Copy } from "lucide-react";
import { MemberShell } from "./MemberShell";
import { memberApi } from "./api";
import "./sgr.css";
import "../funnels/strategic-planning-dashboard.css";

export default function RecruitmentOnboardingSessionPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    try {
      const response = await memberApi.get("/workspace/onboarding-live");
      setData(response.data);
      setMessage("");
    } catch (error) {
      setMessage(error.response?.data?.detail || "The live onboarding session could not be opened.");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const session = data?.session || {};
  const sections = data?.sections || [];
  const index = Math.min(Number(session.current_section_index || 0), Math.max(0, sections.length - 1));
  const section = sections[index];
  const shareUrl = session.share_token ? `${window.location.origin}/onboarding-session/${session.share_token}` : "";

  const createShare = async () => {
    setBusy("share");
    try { await memberApi.post("/workspace/onboarding-live/share"); await load(); }
    catch (error) { setMessage(error.response?.data?.detail || "The shared onboarding link could not be created."); }
    setBusy("");
  };

  const start = async (restart = false) => {
    setBusy("start");
    try {
      if (restart) await memberApi.post("/workspace/onboarding-live/progress", { current_section_index: 0 });
      await memberApi.post("/workspace/onboarding-live/start");
      await load();
    } catch (error) { setMessage(error.response?.data?.detail || "The onboarding session could not be started."); }
    setBusy("");
  };

  const move = async (nextIndex) => {
    setBusy("move");
    try {
      await memberApi.post("/workspace/onboarding-live/progress", { current_section_index: nextIndex });
      await load();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) { setMessage(error.response?.data?.detail || "The onboarding screen could not be changed."); }
    setBusy("");
  };

  const complete = async () => {
    setBusy("complete");
    try {
      await memberApi.post("/workspace/onboarding-live/complete");
      await load();
    } catch (error) { setMessage(error.response?.data?.detail || "The onboarding session could not be completed."); }
    setBusy("");
  };

  return (
    <MemberShell>
      <main className="member-page" data-testid="recruitment-live-onboarding-page">
        <header className="member-page-heading">
          <p className="eyebrow">BOARD MEMBER ONBOARDING</p>
          <h1>Live Onboarding Session</h1>
          <p>Use your approved Board Member Manual as the shared onboarding experience. You control the screen. Board Members open one no-login link and follow the section you are presenting.</p>
        </header>

        {message && !data && <section className="member-card"><p className="submit-error">{message}</p><button className="button button-back" onClick={()=>navigate("/app/board-recruitment#br-section-onboarding")}>RETURN TO ONBOARDING</button></section>}

        {data && session.status !== "IN PROGRESS" && (
          <section className="member-card" data-testid="onboarding-live-prep">
            <h2>{session.status === "COMPLETED" ? "Onboarding Session Complete" : "Prepare The Onboarding Session"}</h2>
            <p>This live session is a facilitation tool only. Completing or skipping it does not control conditional, unconditional or final appointment decisions.</p>

            <div className="detail-section">
              <h3>1. Share The Board Screen</h3>
              <p>Create one link and paste it into your Zoom, Teams or meeting chat. Anyone with the link can follow the onboarding presentation without logging in.</p>
              {!shareUrl ? (
                <button className="button" disabled={busy==="share"} onClick={createShare}>{busy==="share" ? "CREATING…" : "CREATE SHARED ONBOARDING SCREEN"}</button>
              ) : (
                <div className="sp-linkbox">
                  <span>{shareUrl}</span>
                  <button onClick={()=>navigator.clipboard?.writeText(shareUrl)}><Copy size={14}/> COPY LINK</button>
                </div>
              )}
            </div>

            <div className="detail-section">
              <h3>2. Facilitate From The Board Manual</h3>
              <p>Use the Onboarding Facilitation Guide from your Recruitment dashboard as your speaking guide. This screen supplies the Board Manual section everyone should be looking at while you explain and discuss it.</p>
              <p><strong>{sections.length}</strong> Board Manual section{sections.length===1?"":"s"} will be presented.</p>
            </div>

            <div className="detail-section">
              <h3>3. Start The Session</h3>
              <p>When everyone has the shared link open, start. You will move through one Board Manual section at a time.</p>
              <button className="button" disabled={!shareUrl||busy==="start"} onClick={()=>start(session.status==="COMPLETED")}>
                {busy==="start" ? "STARTING…" : session.status==="COMPLETED" ? "START A NEW ONBOARDING SESSION" : "START ONBOARDING SESSION"}
              </button>
            </div>

            <button className="button button-back" onClick={()=>navigate("/app/board-recruitment#br-section-onboarding")}>RETURN TO RECRUITMENT DASHBOARD</button>
            {message && <p className="submit-error">{message}</p>}
          </section>
        )}

        {data && session.status === "IN PROGRESS" && section && (
          <section className="member-card" data-testid="onboarding-live-section">
            <div className="sp-session-topline"><span>Section {index+1} of {sections.length}</span><span>SHARED SCREEN LIVE</span></div>
            <p className="eyebrow">{data.organization_name || "Board Member Onboarding"}</p>
            <h1>{section.title}</h1>
            <div className="detail-section" style={{ whiteSpace: "pre-wrap", textAlign: "left" }}>{section.content}</div>

            <div className="detail-section">
              <h3>Facilitator Prompt</h3>
              <p>Explain this section in your own words, connect it to how your Board actually works, invite questions, and make sure people understand the expectation before moving forward.</p>
            </div>

            <div className="material-actions">
              {index>0 && <button className="button button-back" disabled={busy==="move"} onClick={()=>move(index-1)}>BACK</button>}
              {index<sections.length-1 && <button className="button" disabled={busy==="move"} onClick={()=>move(index+1)}>NEXT SECTION</button>}
              {index===sections.length-1 && <button className="button" disabled={busy==="complete"} onClick={complete}>{busy==="complete" ? "COMPLETING…" : "COMPLETE ONBOARDING SESSION"}</button>}
            </div>
            {message && <p className="submit-error">{message}</p>}
          </section>
        )}
      </main>
    </MemberShell>
  );
}
