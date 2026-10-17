import { useCallback, useState } from "react";
import { memberApi } from "@/member/api";
import { LiveMeetingRecorder } from "./MeetingOutputs";

export default function MeetingMicrophonePrompt({ session, controllerRef, reload }) {
  const [asking, setAsking] = useState(session.status !== "completed");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const confirmNotice = useCallback(async () => {
    await memberApi.post("/game/group/audience/recording-consent", { confirmed: true });
    await reload();
  }, [reload]);
  const enable = async () => {
    setBusy(true); setError("");
    try {
      const started = await controllerRef.current?.start();
      if (started) setAsking(false);
      else setError("Microphone access was not enabled. You can try again or continue without transcription.");
    } finally { setBusy(false); }
  };
  if (session.status === "completed") return null;
  return <section className="bfg-panel">
    <h2>Meeting Microphone and Transcript</h2>
    <LiveMeetingRecorder requestMicrophone beforeStart={confirmNotice} compileOnFinish={false} controllerRef={controllerRef} onFinished={reload} startLabel="ENABLE MEETING MICROPHONE"/>
    {asking && <div role="dialog" aria-modal="true" aria-labelledby="meeting-microphone-title" style={{position:"fixed",inset:0,zIndex:1000,background:"#0009",display:"grid",placeItems:"center",padding:20}}>
      <div className="bfg-panel" style={{width:"100%",maxWidth:560,maxHeight:"90vh",overflowY:"auto"}}>
        <h2 id="meeting-microphone-title">Enable your meeting microphone</h2>
        <p>Allow the app to listen to your discussion and save a transcript that helps you preserve the fundraising strategy your board agrees on. Choose a microphone that can hear your meeting.</p>
        <p>Tell everyone that the discussion will be transcribed before enabling the microphone. By selecting Enable Meeting Microphone, you confirm that everyone has been informed and agrees to transcription.</p>
        <p>Your board's approved decisions remain the source of the final strategy.</p>
        {error && <p className="bfg-error" role="alert">{error}</p>}
        <div className="guided-actions">
          <button autoFocus className="bfg-btn bfg-btn-primary" disabled={busy} onClick={enable}>{busy?"Requesting Microphone Access…":"Enable Meeting Microphone"}</button>
          <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={()=>setAsking(false)}>Continue Without Microphone</button>
        </div>
      </div>
    </div>}
  </section>;
}
