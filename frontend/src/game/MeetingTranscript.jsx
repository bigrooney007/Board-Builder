import { useEffect, useRef, useState } from "react";
import { memberApi } from "@/member/api";

const SR = () => window.SpeechRecognition || window.webkitSpeechRecognition;

export const MeetingTranscript = ({ sectionKey, consented }) => {
  const supported = Boolean(SR());
  const [mode, setMode] = useState("idle");
  const [consentDone, setConsentDone] = useState(consented);
  const [showConsent, setShowConsent] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [notes, setNotes] = useState("");
  const [notesPasted, setNotesPasted] = useState(false);
  const [notesSaved, setNotesSaved] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [transcript, setTranscript] = useState(null);
  const [segmentEdits, setSegmentEdits] = useState({});
  const [savedSegment, setSavedSegment] = useState("");
  const recRef = useRef(null);
  const modeRef = useRef("idle");
  const sectionRef = useRef(sectionKey);

  useEffect(() => { sectionRef.current = sectionKey; }, [sectionKey]);
  useEffect(() => { setConsentDone((prev) => prev || consented); }, [consented]);
  useEffect(() => () => { modeRef.current = "stopped"; try { recRef.current?.stop(); } catch { /* ignore */ } }, []);

  const setModeBoth = (value) => { modeRef.current = value; setMode(value); };

  const startRecognition = () => {
    const Recognition = SR();
    const rec = new Recognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        if (event.results[i].isFinal) {
          const text = event.results[i][0].transcript.trim();
          if (text) {
            memberApi.post("/game/meeting-review/transcript", {
              section_key: sectionRef.current, text, source: "live_transcript" }).catch(() => {});
          }
        }
      }
    };
    rec.onend = () => {
      if (modeRef.current === "active") { try { rec.start(); } catch { /* ignore */ } }
    };
    recRef.current = rec;
    setModeBoth("active");
    try { rec.start(); } catch { /* ignore */ }
  };

  const requestStart = () => {
    if (!consentDone) { setShowConsent(true); return; }
    startRecognition();
  };

  const confirmConsent = async () => {
    try { await memberApi.post("/game/meeting-review/consent"); } catch { /* non-blocking */ }
    setConsentDone(true);
    setShowConsent(false);
    startRecognition();
  };

  const pause = () => { setModeBoth("paused"); try { recRef.current?.stop(); } catch { /* ignore */ } };
  const resume = () => { setModeBoth("active"); try { recRef.current?.start(); } catch { /* ignore */ } };
  const stop = () => { setModeBoth("stopped"); try { recRef.current?.stop(); } catch { /* ignore */ } };

  const saveNotes = async () => {
    if (!notes.trim()) return;
    try {
      await memberApi.post("/game/meeting-review/transcript", {
        section_key: sectionRef.current, text: notes.trim(),
        source: notesPasted ? "pasted_transcript" : "manual_notes" });
      setNotes(""); setNotesPasted(false); setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 2500);
    } catch { /* keep text */ }
  };

  const loadTranscript = async () => {
    try { setTranscript((await memberApi.get("/game/meeting-review/transcript")).data); } catch { /* ignore */ }
  };

  const toggleTranscript = () => {
    const next = !showTranscript;
    setShowTranscript(next);
    if (next) loadTranscript();
  };

  const saveSegment = async (segmentId) => {
    try {
      await memberApi.put(`/game/meeting-review/transcript/${segmentId}`, { text: segmentEdits[segmentId] ?? "" });
      setSavedSegment(segmentId);
      setTimeout(() => setSavedSegment(""), 2000);
    } catch { /* ignore */ }
  };

  return (
    <section className="bfg-panel" data-testid="bfg-mr-transcript-panel">
      <h2>Meeting Transcript</h2>
      <p className="bfg-panel-sub">Turn on live transcription to capture the discussion and decisions your board makes while reviewing the strategy.</p>

      {supported ? (
        <div style={{ marginTop: 14 }}>
          {mode === "idle" || mode === "stopped" ? (
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={requestStart} data-testid="bfg-start-transcript-btn">
              Start Live Transcript
            </button>
          ) : mode === "active" ? (
            <div>
              <p className="bfg-success" style={{ fontWeight: 700 }} data-testid="bfg-transcript-active">● Transcription Active</p>
              <div className="bfg-bm-actions">
                <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={pause} data-testid="bfg-pause-transcript-btn">Pause Transcript</button>
                <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={stop} data-testid="bfg-stop-transcript-btn">Stop Transcript</button>
              </div>
            </div>
          ) : (
            <div>
              <p className="bfg-note" style={{ fontWeight: 700 }} data-testid="bfg-transcript-paused">Transcript Paused</p>
              <div className="bfg-bm-actions">
                <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={resume} data-testid="bfg-resume-transcript-btn">Resume Transcript</button>
                <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={stop} data-testid="bfg-stop-transcript-btn-paused">Stop Transcript</button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ marginTop: 14 }} data-testid="bfg-transcript-unavailable">
          <p className="bfg-note" style={{ fontWeight: 700 }}>Live Transcription Isn't Available In This Browser</p>
          <p className="bfg-note">You can still capture the board's decisions by typing meeting notes below or pasting a transcript after the meeting.</p>
        </div>
      )}

      <label className="bfg-field">
        <span>Meeting Notes / Transcript</span>
        <textarea rows={5} value={notes}
          onChange={(event) => setNotes(event.target.value)}
          onPaste={() => setNotesPasted(true)}
          placeholder="Type meeting notes or paste a transcript for the section currently being reviewed…"
          data-testid="bfg-meeting-notes-input" />
      </label>
      {notesSaved && <p className="bfg-success" data-testid="bfg-notes-saved">Meeting notes saved</p>}
      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 10 }} disabled={!notes.trim()}
        onClick={saveNotes} data-testid="bfg-save-notes-btn">
        Save Meeting Notes
      </button>

      <div style={{ marginTop: 18 }}>
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={toggleTranscript} data-testid="bfg-view-transcript-btn">
          {showTranscript ? "Hide Meeting Transcript" : "View Meeting Transcript"}
        </button>
        {showTranscript && (
          <div style={{ marginTop: 12 }} data-testid="bfg-transcript-view">
            {!transcript || transcript.sections.length === 0 ? (
              <p className="bfg-note">No transcript captured yet.</p>
            ) : transcript.sections.map((section) => (
              <div key={section.section_key} style={{ marginTop: 14 }}>
                <p className="bfg-eyebrow" style={{ marginBottom: 8 }}>{section.title}</p>
                {section.segments.map((segment) => (
                  <div key={segment.segment_id} style={{ marginBottom: 10 }}>
                    <textarea className="bfg-mr-segment" rows={2}
                      value={segmentEdits[segment.segment_id] ?? segment.text}
                      onChange={(event) => setSegmentEdits((current) => ({ ...current, [segment.segment_id]: event.target.value }))}
                      data-testid={`bfg-transcript-segment-${segment.segment_id}`} />
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <small style={{ color: "#64748b" }}>{segment.source === "live_transcript" ? "Live transcript" : segment.source === "pasted_transcript" ? "Pasted transcript" : "Meeting notes"}</small>
                      {segmentEdits[segment.segment_id] !== undefined && segmentEdits[segment.segment_id] !== segment.text && (
                        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => saveSegment(segment.segment_id)}
                          data-testid={`bfg-save-segment-${segment.segment_id}`}>
                          Save Transcript Changes
                        </button>
                      )}
                      {savedSegment === segment.segment_id && <small className="bfg-success">Saved</small>}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {showConsent && (
        <div className="bfg-modal-overlay" data-testid="bfg-consent-modal">
          <div className="bfg-modal">
            <h2>Start Live Meeting Transcript?</h2>
            <p className="bfg-panel-sub" style={{ marginTop: 10 }}>
              Make sure everyone in the meeting knows that the discussion will be transcribed before you continue.
            </p>
            <label className={`bfg-check ${consentChecked ? "checked" : ""}`} style={{ marginTop: 16 }}>
              <input type="checkbox" checked={consentChecked} onChange={(event) => setConsentChecked(event.target.checked)}
                data-testid="bfg-consent-checkbox" />
              I confirm that participants have been informed that live transcription is being used.
            </label>
            <div className="bfg-form-actions">
              <button className="bfg-btn bfg-btn-ghost" onClick={() => setShowConsent(false)} data-testid="bfg-consent-cancel-btn">Cancel</button>
              <button className="bfg-btn bfg-btn-primary" disabled={!consentChecked} onClick={confirmConsent} data-testid="bfg-consent-start-btn">
                Start Transcription
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
