import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { Volume2, VolumeX } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE = process.env.REACT_APP_BACKEND_URL;

const STEPS = [
  { key: "play-individual-game", target: "play-individual-game", clip: "lead_opening", title: "Step 1 — Play My Board Fundraising Game",
    text: "Start with your own game. For each strategic area, answer one question, review the sharper actionable version of your idea and approve the version that best reflects what you mean." },
  { key: "working-strategy", target: "working-strategy", clip: "bgt_working_strategy", title: "Step 2 — Working Fundraising Strategy",
    text: "As soon as your individual game and current fundraising reality are complete, your first working strategy begins generating in the background. Return here to open it or create an updated version later." },
  { key: "prepare-meeting", target: "prepare-meeting", clip: "bgt_prepare_meeting", title: "Step 3 — Set Board Fundraising Day/Night",
    text: "Add the date, time and format for the Board meeting where everyone will bring their ideas together." },
  { key: "board-participation", target: "board-participation", clip: "bgt_invite_board", title: "Step 4 — Invite The Board",
    text: "Add participants, send or resend their invitation, copy their individual game link and use the person-specific call script when you need to follow up." },
  { key: "meeting-resources", target: "meeting-resources", clip: "bgt_meeting_resources", title: "Step 5 — Fundraising Game Guide",
    text: "Open the facilitation guide when you want the step-by-step reference for running the Group Game with your Board." },
  { key: "group-game", target: "group-game", clip: "bgt_group_game", title: "Step 6 — Group Game",
    text: "Bring everyone's ideas onto one shared review screen. Discuss them, select every idea the Board agrees should move forward and add any new wording the Board agrees during the conversation." },
  { key: "final-strategy", target: "final-strategy", clip: "bgt_final_strategy", title: "Step 7 — Final Fundraising Strategy",
    text: "When the Group Game ends, the final organizational fundraising strategy begins generating automatically from the Board's agreed decisions. The meeting transcript adds context when available but does not block generation." },
  { key: "board-portfolios", target: "board-portfolios", clip: "bgt_board_portfolios", title: "Board Portfolios",
    text: "Once the final strategy is ready, create a personal fundraising portfolio for each Board Member from the role and participation information they actually provided." },
  { key: "relationship-mapping", target: "relationship-mapping", clip: "bgt_relationship_mapping", title: "Relationship Mapping",
    text: "Relationship Mapping helps Board Members identify people, businesses and grantors in their own networks who match the funding audiences in the final strategy." },
];

export const DashboardTour = ({ onClose }) => {
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState(null);
  const [muted, setMuted] = useState(false);
  const [clips, setClips] = useState({});
  const timer = useRef(null);
  const audioRef = useRef(null);
  const played = useRef(new Set());
  const mutedRef = useRef(false);
  const step = STEPS[index];

  useEffect(() => {
    axios.get(`${API}/game/voice/tutorial/board-game`).then((r) => setClips(r.data.clips || {})).catch(() => {});
    return () => { if (audioRef.current) audioRef.current.pause(); };
  }, []);

  const stopAudio = () => { if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; } };

  useEffect(() => {
    stopAudio();
    const clip = clips[STEPS[index].clip];
    const key = STEPS[index].clip;
    if (!mutedRef.current && clip?.ready && !played.current.has(key)) {
      played.current.add(key);
      const audio = new Audio(`${BASE}${clip.url}`);
      audioRef.current = audio;
      audio.play().catch(() => {});
    }
  }, [index, clips]);

  const toggleMute = () => {
    if (!muted) { stopAudio(); mutedRef.current = true; setMuted(true); }
    else { mutedRef.current = false; setMuted(false); }
  };

  const close = () => { stopAudio(); onClose(); };

  const measure = useCallback(() => {
    const element = document.querySelector(`[data-tour="${STEPS[index].target}"]`);
    if (!element) { setRect(null); return; }
    const box = element.getBoundingClientRect();
    setRect({ top: box.top, left: box.left, width: box.width, height: box.height });
  }, [index]);

  useEffect(() => {
    const element = document.querySelector(`[data-tour="${step.target}"]`);
    if (element) element.scrollIntoView({ behavior: "smooth", block: "center" });
    setRect(null);
    clearTimeout(timer.current);
    timer.current = setTimeout(measure, 420);
    const onMove = () => measure();
    window.addEventListener("resize", onMove);
    window.addEventListener("scroll", onMove, true);
    return () => {
      clearTimeout(timer.current);
      window.removeEventListener("resize", onMove);
      window.removeEventListener("scroll", onMove, true);
    };
  }, [index, measure, step.target]);

  const last = index === STEPS.length - 1;
  const panelTop = rect
    ? (rect.top + rect.height + 240 < window.innerHeight ? rect.top + rect.height + 16 : Math.max(16, rect.top - 236))
    : window.innerHeight / 2 - 130;
  const panelLeft = rect ? Math.min(Math.max(16, rect.left), window.innerWidth - 396) : window.innerWidth / 2 - 190;

  return (
    <div data-testid="bfg-dashboard-tour" style={{ position: "fixed", inset: 0, zIndex: 4000 }}>
      {rect ? (
        <div style={{
          position: "fixed", top: rect.top - 8, left: rect.left - 8,
          width: rect.width + 16, height: rect.height + 16, borderRadius: 14,
          boxShadow: "0 0 0 9999px rgba(15, 23, 42, 0.62)", border: "2px solid #ffffff",
          pointerEvents: "none", transition: "all 260ms ease",
        }} />
      ) : (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15, 23, 42, 0.62)" }} />
      )}
      <div style={{
        position: "fixed", top: panelTop, left: panelLeft, width: 380, maxWidth: "calc(100vw - 32px)",
        background: "#ffffff", borderRadius: 14, padding: "20px 22px",
        boxShadow: "0 18px 50px rgba(0,0,0,0.35)", transition: "all 260ms ease",
      }} data-testid={`bfg-tour-step-${step.key}`}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: "#6B7280", textTransform: "uppercase", margin: 0 }}>
            Step {index + 1} of {STEPS.length}
          </p>
          <button onClick={toggleMute} title={muted ? "Turn narration on" : "Turn narration off"}
            style={{ background: "none", border: "none", cursor: "pointer", color: muted ? "#9CA3AF" : "#4f46e5", padding: 4 }}
            data-testid="bfg-tour-speaker-btn">
            {muted ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
        </div>
        <h3 style={{ margin: "8px 0 0", fontSize: 18, color: "#111827" }}>{step.title}</h3>
        <p style={{ marginTop: 10, fontSize: 14, lineHeight: 1.6, color: "#374151" }}>{step.text}</p>
        <div style={{ display: "flex", gap: 8, marginTop: 18, alignItems: "center" }}>
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={close} data-testid="bfg-tour-exit-btn">Exit Tutorial</button>
          <span style={{ flex: 1 }} />
          <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={index === 0}
            onClick={() => setIndex(index - 1)} data-testid="bfg-tour-back-btn">Back</button>
          <button className="bfg-btn bfg-btn-primary bfg-btn-sm"
            onClick={() => (last ? close() : setIndex(index + 1))} data-testid="bfg-tour-next-btn">
            {last ? "Finish Tutorial" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardTour;
