import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Headphones, Volume2, X } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE = process.env.REACT_APP_BACKEND_URL;

const ITEMS = [
  { clip: "rct_how_this_works", label: "HOW THIS WORKS", target: "fbb-recruitment-heading" },
  { clip: "rct_intake", label: "Fill The Intake Form", target: "br-section-intake" },
  { clip: "rct_identify", label: "Identify Board Members Needed", target: "br-section-identify" },
  { clip: "rct_strategy", label: "Generate Recruitment Materials", target: "br-section-materials" },
  { clip: "rct_launch", label: "Launch Recruitment Campaign", target: "br-section-campaign" },
  { clip: "rct_review", label: "View Applicants And Interviews", target: "br-section-applicants" },
  { clip: "rct_references", label: "Automated Reference Check", target: "br-section-references" },
  { clip: "rct_onboarding", label: "Onboarding And Conditional Appointment", target: "br-section-onboarding" },
  { clip: "rct_onboarding", label: "Final Appointment And Portfolio", target: "br-section-portfolio" },
  { clip: "rct_onboarding", label: "First Board Meeting", target: "br-section-first-meeting" },
];

export const RecruitmentTutorial = () => {
  const [open, setOpen] = useState(false);
  const [used, setUsed] = useState(() => localStorage.getItem("sgrTutorialUsed") === "1");
  const [clips, setClips] = useState({});
  const [playing, setPlaying] = useState("");
  const audioRef = useRef(null);
  const highlightRef = useRef(null);

  useEffect(() => {
    axios.get(`${API}/game/voice/tutorial/recruitment`).then((r) => setClips(r.data.clips || {})).catch(() => {});
    return () => { if (audioRef.current) audioRef.current.pause(); clearHighlight(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const clearHighlight = () => {
    if (highlightRef.current) { highlightRef.current.classList.remove("sgr-highlight"); highlightRef.current = null; }
  };

  const stop = () => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    setPlaying("");
    clearHighlight();
  };

  const select = (item) => {
    setOpen(false);
    setUsed(true);
    localStorage.setItem("sgrTutorialUsed", "1");
    stop();
    const element = document.querySelector(`[data-testid="${item.target}"]`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
      element.classList.add("sgr-highlight");
      highlightRef.current = element;
    }
    const clip = clips[item.clip];
    if (clip?.ready) {
      const audio = new Audio(`${BASE}${clip.url}`);
      audioRef.current = audio;
      audio.onended = () => { setPlaying(""); clearHighlight(); };
      audio.play().then(() => setPlaying(item.clip)).catch(() => {});
    }
  };

  return (
    <>
      <button className="sgr-btn sgr-btn-primary" onClick={() => setOpen(true)} data-testid="sgr-tutorial-open-btn">
        <Headphones size={15} /> {used ? "OPEN AUDIO TUTORIAL" : "START AUDIO TUTORIAL"}
      </button>
      {playing && (
        <button className="sgr-tutorial-stop" onClick={stop} data-testid="sgr-tutorial-stop-btn">
          <Volume2 size={14} /> Stop narration
        </button>
      )}
      {!open && (
        <button className="sgr-tutorial-fab" onClick={() => setOpen(true)} data-testid="sgr-tutorial-fab">
          <Headphones size={16} /> Tutorial
        </button>
      )}
      {open && (
        <div className="sgr-tutorial-overlay" data-testid="sgr-tutorial-selector">
          <div className="sgr-tutorial-modal">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ margin: 0 }}>WHAT DO YOU NEED HELP WITH?</h3>
              <button className="sgr-tutorial-close" onClick={() => setOpen(false)} data-testid="sgr-tutorial-close-btn"><X size={18} /></button>
            </div>
            <div style={{ marginTop: 14 }}>
              {ITEMS.map((item) => {
                return (
                  <button key={`${item.clip}-${item.target}`} className="sgr-tutorial-item" onClick={() => select(item)} data-testid={`sgr-tutorial-item-${item.target}`}>
                    <span>{item.label}</span>
                    <Volume2 size={16} aria-hidden="true" />
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default RecruitmentTutorial;
