import { useEffect, useRef, useState } from "react";
import { Mic, Square } from "lucide-react";

const Recognition = typeof window !== "undefined" ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;

export const SpeakButton = ({ value, onChange, testId }) => {
  const [listening, setListening] = useState(false);
  const recRef = useRef(null);
  const baseRef = useRef("");
  const finalsRef = useRef("");
  const valueRef = useRef(value);
  valueRef.current = value;

  useEffect(() => () => { if (recRef.current) { try { recRef.current.stop(); } catch { /* noop */ } } }, []);
  if (!Recognition) return null;

  const emit = (interim) => {
    const spoken = `${finalsRef.current}${interim ? ` ${interim}` : ""}`.trim();
    const base = baseRef.current.trim();
    onChange(base ? `${base} ${spoken}`.trim() : spoken);
  };

  const stop = () => {
    setListening(false);
    if (recRef.current) { try { recRef.current.stop(); } catch { /* noop */ } recRef.current = null; }
  };

  const start = () => {
    try {
      const rec = new Recognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";
      baseRef.current = valueRef.current || "";
      finalsRef.current = "";
      rec.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalsRef.current = `${finalsRef.current} ${transcript}`.trim();
          else interim += transcript;
        }
        emit(interim);
      };
      rec.onerror = () => setListening(false);
      rec.onend = () => setListening(false);
      rec.start();
      recRef.current = rec;
      setListening(true);
    } catch { setListening(false); }
  };

  return (
    <button type="button" className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 10 }}
      onClick={listening ? stop : start} data-testid={testId || "bfg-speak-answer-btn"}>
      {listening ? <><Square size={13} /> LISTENING… (tap to stop)</> : <><Mic size={13} /> SPEAK MY ANSWER</>}
    </button>
  );
};

export default SpeakButton;
