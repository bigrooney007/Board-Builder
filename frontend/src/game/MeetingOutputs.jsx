import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, Mic, Pause, Play, Square } from "lucide-react";
import { memberApi } from "@/member/api";
import { useWakeLock } from "./useWakeLock";

const Recognition = typeof window !== "undefined" ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;

export const LiveMeetingRecorder = ({ onFinished = () => {}, title = "Record The Board Meeting", startLabel = "START MEETING TRANSCRIPTION", autoStart = false, controllerRef = null }) => {
  const [status, setStatus] = useState("idle"); // idle | recording | paused | finishing
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const recRef = useRef(null);
  const bufferRef = useRef("");
  const statusRef = useRef("idle");
  const tickRef = useRef(null);
  const flushRef = useRef(null);
  useWakeLock(status === "recording");

  const flush = async () => {
    const text = bufferRef.current.trim();
    if (!text) return;
    bufferRef.current = "";
    try { await memberApi.post("/game/meeting/recording/chunk", { text }); } catch { bufferRef.current = `${text} ${bufferRef.current}`.trim(); }
  };

  const startRecognition = () => {
    const rec = new Recognition();
    rec.continuous = true;
    rec.interimResults = false;
    rec.lang = "en-US";
    rec.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        if (event.results[i].isFinal) bufferRef.current = `${bufferRef.current} ${event.results[i][0].transcript}`.trim();
      }
      if (bufferRef.current.length > 900) flush();
    };
    rec.onend = () => { if (statusRef.current === "recording") { try { rec.start(); } catch { /* noop */ } } };
    rec.onerror = (event) => { if (event.error === "not-allowed") { setError("Microphone permission was denied. You can upload or paste a transcript instead."); stopAll("idle"); } };
    try { rec.start(); } catch { /* noop */ }
    recRef.current = rec;
  };

  const stopAll = (next) => {
    statusRef.current = next;
    setStatus(next);
    if (recRef.current) { try { recRef.current.stop(); } catch { /* noop */ } recRef.current = null; }
    clearInterval(tickRef.current);
    clearInterval(flushRef.current);
  };

  const start = () => {
    if (!Recognition) { setError("Live recording is not supported in this browser. Please upload or paste a transcript instead."); return; }
    setError("");
    statusRef.current = "recording";
    setStatus("recording");
    startRecognition();
    tickRef.current = setInterval(() => setElapsed((seconds) => seconds + 1), 1000);
    flushRef.current = setInterval(flush, 20000);
  };

  const pause = () => {
    statusRef.current = "paused";
    setStatus("paused");
    if (recRef.current) { try { recRef.current.stop(); } catch { /* noop */ } recRef.current = null; }
    clearInterval(tickRef.current);
    flush();
  };

  const resume = () => {
    statusRef.current = "recording";
    setStatus("recording");
    startRecognition();
    tickRef.current = setInterval(() => setElapsed((seconds) => seconds + 1), 1000);
  };

  const finish = async () => {
    stopAll("finishing");
    setError("");
    await flush();
    try {
      await memberApi.post("/game/meeting/recording/finish");
      await memberApi.post("/game/meeting/compile-final");
      setElapsed(0);
      statusRef.current = "idle";
      setStatus("idle");
      onFinished();
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not save your recording. You can paste or upload a transcript instead.");
      statusRef.current = "idle";
      setStatus("idle");
    }
  };

  useEffect(() => {
    if (!controllerRef) return undefined;
    controllerRef.current = {
      finish,
      isActive: () => ["recording", "paused"].includes(statusRef.current),
    };
    return () => { if (controllerRef.current?.finish === finish) controllerRef.current = null; };
  }, [controllerRef]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (autoStart) start(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => stopAll("idle"), []); // eslint-disable-line react-hooks/exhaustive-deps

  const clock = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;

  return (
    <div style={{ marginTop: 14, border: "1px solid #E5E7EB", borderRadius: 14, padding: 18 }} data-testid="bfg-live-recorder">
      <p style={{ fontWeight: 700, color: "#111827", margin: 0 }}>{title}</p>
      <p className="bfg-note" style={{ marginTop: 8 }}>
        Before recording, make sure everyone in the meeting knows the discussion is being recorded and transcribed for the purpose of completing your organization's fundraising strategy.
      </p>
      {status === "idle" && (
        <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 12 }} onClick={start} data-testid="bfg-record-meeting-btn">
          <Mic size={15} /> {startLabel}
        </button>
      )}
      {(status === "recording" || status === "paused") && (
        <div style={{ marginTop: 12 }}>
          <p style={{ fontWeight: 800, color: status === "recording" ? "#dc2626" : "#b45309", margin: 0 }} data-testid="bfg-recording-state">
            {status === "recording" ? "● RECORDING" : "❚❚ PAUSED"} — {clock}
          </p>
          <div style={{ display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap" }}>
            {status === "recording" ? (
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={pause} data-testid="bfg-recording-pause"><Pause size={13} /> PAUSE</button>
            ) : (
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={resume} data-testid="bfg-recording-resume"><Play size={13} /> RESUME</button>
            )}
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={finish} data-testid="bfg-recording-finish"><Square size={13} /> FINISH MEETING</button>
          </div>
        </div>
      )}
      {status === "finishing" && <p style={{ marginTop: 12, fontWeight: 700 }}>COMPILING YOUR FINAL FUNDRAISING STRATEGY…</p>}
      {error && <p className="bfg-error" style={{ marginTop: 10 }} data-testid="bfg-recording-error">{error}</p>}
    </div>
  );
};

export const CompleteBoardMeetingSection = ({ overview, onRefresh }) => {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reopen, setReopen] = useState(false);
  const fileInput = useRef(null);

  if (!overview?.group_completed) return null;
  const finalStatus = overview.final?.status || "none";

  const compile = async () => {
    setError("");
    if (!text.trim() && !file) { setError("Paste your transcript or upload a transcript file first."); return; }
    setBusy(true);
    try {
      if (file) {
        const form = new FormData();
        form.append("file", file);
        await memberApi.post("/game/meeting/transcript-upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      } else {
        await memberApi.post("/game/meeting/transcript", { text: text.trim() });
      }
      await memberApi.post("/game/meeting/compile-final");
      setReopen(false); setText(""); setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      onRefresh();
    } catch (err) {
      setError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "We could not start compiling your final strategy. Please try again.");
    }
    setBusy(false);
  };

  const showForm = reopen || (finalStatus !== "running" && finalStatus !== "done");

  return (
    <section className="bfg-panel" data-testid="bfg-complete-meeting-section">
      <div className="bfg-panel-head">
        <div>
          <h2>Complete Your Board Meeting</h2>
          <p className="bfg-panel-sub">
            Your Group Game captured the board's priorities. Now add the transcript from the rest of your meeting so we can capture the board's decisions, changes, responsibilities and additional ideas before creating the final fundraising strategy.
          </p>
        </div>
      </div>

      {finalStatus === "running" && (
        <div style={{ marginTop: 14 }} data-testid="bfg-final-compiling">
          <p style={{ fontWeight: 700, color: "#111827" }}>Compiling Your Final Fundraising Strategy</p>
          <p className="bfg-note">We are bringing together your organization's information, board ideas, Group Game priorities and meeting decisions.</p>
          <p className="bfg-note">This may take a few minutes. If it isn't ready immediately, check back in about 5 minutes. You can continue using your dashboard while we work.</p>
          <div className="bfg-doc-loading"><span /><span /><span /></div>
        </div>
      )}

      {finalStatus === "done" && !reopen && (
        <div style={{ marginTop: 14 }} data-testid="bfg-final-available">
          <p className="bfg-success" style={{ fontWeight: 700 }}>Final Strategy Available</p>
          <div className="bfg-bm-actions">
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm"
              onClick={() => navigate(`/game/strategy/view/${overview.final.strategy_id}`)} data-testid="bfg-view-final-strategy-btn">
              View Final Strategy
            </button>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => setReopen(true)} data-testid="bfg-new-transcript-btn">
              Submit A New Transcript
            </button>
          </div>
          <p className="bfg-note" style={{ marginTop: 8 }}>Submitting a new transcript creates an updated final strategy. Your previous strategy will remain saved.</p>
        </div>
      )}

      {finalStatus === "failed" && !reopen && !showForm && null}

      {(showForm || finalStatus === "failed") && finalStatus !== "running" && (
        <div style={{ marginTop: 14 }} data-testid="bfg-transcript-form">
          {finalStatus === "failed" && (
            <p className="bfg-error" data-testid="bfg-final-failed">We could not compile your final strategy. Your transcript is saved — please try again.</p>
          )}
          <LiveMeetingRecorder onFinished={onRefresh} />
          <p className="bfg-note" style={{ marginTop: 14 }}>Or use one of the alternatives below:</p>
          <label className="bfg-field">
            <span>Paste Transcript</span>
            <textarea rows={8} value={text} placeholder="Paste the transcript from the rest of your board meeting here."
              onChange={(event) => { setText(event.target.value); if (event.target.value.trim()) setFile(null); }}
              data-testid="bfg-transcript-textarea" />
          </label>
          <label className="bfg-field">
            <span>Or Upload Transcript (PDF, DOCX or TXT)</span>
            <input type="file" ref={fileInput} accept=".pdf,.docx,.txt"
              onChange={(event) => { setFile(event.target.files?.[0] || null); if (event.target.files?.[0]) setText(""); }}
              data-testid="bfg-transcript-file-input" />
          </label>
          {overview.transcript?.submitted && (
            <p className="bfg-note">A transcript was submitted {overview.transcript.filename ? `(${overview.transcript.filename})` : ""} — submitting again replaces it.</p>
          )}
          {error && <p className="bfg-error" data-testid="bfg-transcript-error">{error}</p>}
          <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 12 }} disabled={busy} onClick={compile} data-testid="bfg-compile-final-btn">
            {busy ? "Starting…" : "Compile Final Fundraising Strategy"}
          </button>
        </div>
      )}
    </section>
  );
};

const OUTPUT_CARDS = [
  { key: "final_strategy", tour: "final-strategy", title: "Final Fundraising Strategy",
    text: "Your organization's information, board ideas, priorities and meeting decisions in one fundraising strategy.", action: "View Final Strategy" },
  { key: "board_portfolios", tour: "board-portfolios", title: "Board Portfolios",
    text: "A personal portfolio for every board member showing exactly how they will participate.", action: "Open Board Portfolios" },
  { key: "relationship_mapping", tour: "relationship-mapping", title: "Relationship Mapping",
    text: "Board members identify people, businesses and grantors in their networks who match your funder profiles.", action: "Open Relationship Mapping" },
];

const STATUS_TEXT = {
  locked: "Locked — Complete Your Group Game First",
  meeting: "Complete Your Board Meeting To Unlock",
  generating: "Generating — check back in about 5 minutes",
  ready: "Ready",
};
const STATUS_COLOR = { locked: "#6B7280", meeting: "#b45309", generating: "#818cf8", ready: "#059669" };

export const FinalOutputsSection = ({ overview }) => {
  const navigate = useNavigate();
  const outputs = overview?.outputs || {};
  const finalId = overview?.final?.strategy_id || "";
  const destinations = {
    final_strategy: finalId ? `/game/strategy/view/${finalId}` : "",
    board_portfolios: "/game/portfolios",
    relationship_mapping: "/game/relationships",
  };
  return (
    <>
      <p className="bfg-eyebrow" style={{ marginTop: 30 }}>STEP 7 · AFTER THE GROUP GAME</p>
      <div className="bfg-output-grid" data-testid="bfg-final-outputs">
        {OUTPUT_CARDS.map((card) => {
          const state = outputs[card.key] || "locked";
          return (
            <section className={`bfg-panel bfg-output-card ${state!=="ready"?"is-locked":""}`} key={card.key} data-tour={card.tour} data-testid={`bfg-output-${card.key}`}>
              <span className="bfg-lock-badge" style={{ color: STATUS_COLOR[state] }} data-testid={`bfg-output-status-${card.key}`}>
                {STATUS_TEXT[state]}
              </span>
              <h4>{card.title}</h4>
              <p>{card.text}</p>
              <button className="bfg-btn bfg-btn-primary bfg-btn-sm" disabled={state!=="ready"||!destinations[card.key]} style={{ marginTop: 10 }}
                onClick={() => state==="ready"&&navigate(destinations[card.key])} data-testid={`bfg-output-open-${card.key}`}>
                {state!=="ready"&&<Lock size={14}/>} {card.action}
              </button>
            </section>
          );
        })}
      </div>
    </>
  );
};
