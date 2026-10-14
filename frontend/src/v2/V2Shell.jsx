import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { errorMessage, v2Api } from "./api";
import { CALENDLY_URL } from "./content";
import "./v2.css";

export function Loading({ children = "Opening your resources…" }) {
  return <p className="v2-loading" role="status">{children}</p>;
}
export function ErrorNotice({ error, children }) {
  return (error || children) ? <div className="v2-error" role="alert">{error || children}</div> : null;
}
export function AssistanceLink({ className = "v2-button v2-button-secondary", children = "Book a Call" }) {
  return <a className={className} href={CALENDLY_URL} target="_blank" rel="noopener noreferrer">{children}<ArrowRight size={17} aria-hidden="true" /></a>;
}
export function useV2Meta(title = "Nonprofit Board Builder preview") {
  const { pathname } = useLocation();
  useEffect(() => {
    const oldTitle = document.title;
    document.title = `${title} | Nonprofit Board Builder`;
    const old = document.querySelector('meta[name="robots"]');
    const oldContent = old?.getAttribute("content");
    const meta = old || document.createElement("meta");
    meta.name = "robots"; meta.content = "noindex, nofollow, noarchive";
    if (!old) document.head.appendChild(meta);
    return () => {
      document.title = oldTitle;
      if (old) meta.setAttribute("content", oldContent || ""); else meta.remove();
    };
  }, [title, pathname]);
}
export default function V2Shell({ children, title, narrow = false, participant = false }) {
  useV2Meta(title);
  return <div className="v2-app">
    <a className="v2-skip" href="#v2-main">Skip to content</a>
    <header className="v2-header">
      {participant
        ? <div className="v2-brand"><span className="v2-brand-mark" aria-hidden="true">BB</span><span>Nonprofit Board Builder<small>Practical tools for your board</small></span></div>
        : <Link className="v2-brand" to="/v2"><span className="v2-brand-mark" aria-hidden="true">BB</span><span>Nonprofit Board Builder<small>Practical tools for your board</small></span></Link>}
      {!participant && <Link className="v2-recovery-link" to="/v2/recover">Recover my resources</Link>}
    </header>
    <main id="v2-main" className={narrow ? "v2-main v2-main-narrow" : "v2-main"}>{children}</main>
    <footer className="v2-footer"><p>© {new Date().getFullYear()} Nonprofit Board Builder</p><span><ShieldCheck size={15} aria-hidden="true" /> Self-guided board resources</span></footer>
  </div>;
}

export function PreviewGate({ children }) {
  const [state, setState] = useState("loading");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const check = useCallback(async () => {
    try { const { data } = await v2Api.get("/access"); setState(data.allowed === true ? "allowed" : "locked"); }
    catch (err) { setState(err.response?.status === 404 ? "disabled" : err.response?.status === 403 || err.response?.status === 401 ? "locked" : "failed"); }
  }, []);
  useEffect(() => { check(); }, [check]);
  const unlock = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await v2Api.post("/preview-access", { key }); setKey(""); await check(); }
    catch (err) { setError(errorMessage(err, "We could not verify your preview access. Please check the key.")); }
    finally { setBusy(false); }
  };
  if (state === "allowed") return children;
  return <V2Shell title="Private preview" narrow>
    {state === "loading" ? <Loading>Checking your secure access…</Loading> : <section className="v2-card">
      <p className="v2-eyebrow">PRIVATE PREVIEW</p><h1>{state === "disabled" ? "This preview is not available." : "Open your Board Builder preview"}</h1>
      {state === "locked" && <><p>This version is available to invited testers and customers with a secure resource link. Enter your preview key to continue.</p><form onSubmit={unlock}><label>Preview key<input type="password" autoComplete="off" required value={key} onChange={(e) => setKey(e.target.value)} /></label><ErrorNotice error={error} /><button className="v2-button" disabled={busy}>{busy ? "Checking access…" : "Open preview"}</button></form></>}
      {state === "failed" && <><ErrorNotice>We could not check your access. Please try again.</ErrorNotice><button className="v2-button" onClick={() => { setState("loading"); check(); }}>Try again</button></>}
      <p><Link to="/v2/recover">Recover a purchased resource link</Link></p>
    </section>}
  </V2Shell>;
}
