import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { NarrationControl, isNarrationMuted } from "./NarrationControl";
import { SpeakButton } from "./SpeakButton";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const GROUPS = [
  {
    key: "individuals", title: "Your Present Individual Donors", clip: "reality_donors",
    fields: [
      ["current_individual_donor_profile", "Who are your present individual donors? Describe the types or groups of people who currently give."],
      ["current_individual_donor_where", "Where do you presently find or meet these donors?"],
      ["current_individual_donor_attraction", "How do you presently attract them or get their attention?"],
      ["current_individual_donor_support", "What do they currently give to or help fund, and about how much do they give?"],
      ["current_individual_donor_process", "How do you presently move them from first contact to making a donation?"],
    ],
  },
  {
    key: "businesses", title: "Your Present Business Sponsors Or Partners", clip: "reality_businesses",
    fields: [
      ["current_business_profile", "Who are your present corporate sponsors or business partners? Describe the types of businesses that currently support you."],
      ["current_business_where", "Where did you find or first connect with these businesses?"],
      ["current_business_attraction", "How do you presently attract them or earn their interest?"],
      ["current_business_support", "What do they currently sponsor, fund or contribute, and about how much do they give?"],
      ["current_business_process", "What process do you presently use to secure and maintain their support?"],
    ],
  },
  {
    key: "grantors", title: "Your Present Grantors", clip: "reality_grantors",
    fields: [
      ["current_grantor_profile", "Who are your present grantors? Describe the types of foundations, agencies or other funders that currently fund you."],
      ["current_grantor_where", "Where do you presently find these grant opportunities?"],
      ["current_grantor_attraction", "How do you presently demonstrate credibility or build a relationship with them?"],
      ["current_grantor_support", "What do they currently fund, and about how much do they award?"],
      ["current_grantor_process", "What process do you presently follow before, during and after applying for their funding?"],
    ],
  },
];

export default function GameSituationPage() {
  const navigate = useNavigate();
  const reviewMode = new URLSearchParams(useLocation().search).get("review") === "1";
  const { member, loading } = useMemberAuth();
  const [phase, setPhase] = useState("loading");
  const [token, setToken] = useState("");
  const [index, setIndex] = useState(0);
  const [reality, setReality] = useState({});
  const [branding, setBranding] = useState({ logo_data: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);

  useEffect(() => { document.title = "Complete Your Fundraising Game | Board Fundraising Game"; }, []);
  useEffect(() => () => { if (audioRef.current) audioRef.current.pause(); }, []);
  useEffect(() => {
    if (!token) return;
    axios.get(`${API}/game/voice/manifest/${token}`).then((r) => setClips(r.data.clips || {})).catch(() => {});
  }, [token]);
  useEffect(() => {
    const clip = clips[GROUPS[index]?.clip];
    if (phase !== "reality" || !clip?.ready || isNarrationMuted()) return;
    if (audioRef.current) audioRef.current.pause();
    audioRef.current = new Audio(`${process.env.REACT_APP_BACKEND_URL}${clip.url}`);
    audioRef.current.play().catch(() => {});
  }, [phase, index, clips]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`, { replace: true }); return; }
    (async () => {
      try {
        const [situation, brand, self] = await Promise.all([
          memberApi.get("/game/situation"), memberApi.get("/game/branding"), memberApi.post("/game/self-play"),
        ]);
        setReality(situation.data.sections?.current_reality || {});
        setBranding(brand.data.branding || { logo_data: "" });
        setToken(self.data.token);
        const response = (await axios.get(`${API}/game/play/${self.data.token}/audience-response`)).data.response || {};
        if (!response.completed) { setPhase("play_first"); return; }
        if (situation.data.completed && !reviewMode) { navigate("/game/dashboard", { replace: true }); return; }
        setIndex(reviewMode ? 0 : Math.min(2, Math.max(0, Number(situation.data.current_step || 0))));
        setPhase("reality");
      } catch { setError("We could not load your game. Please refresh the page."); setPhase("error"); }
    })();
  }, [loading, member, navigate, reviewMode]);

  const play = (force = false) => {
    const clip = clips[GROUPS[index]?.clip];
    if (!clip?.ready || (isNarrationMuted() && !force)) return;
    if (audioRef.current) audioRef.current.pause();
    audioRef.current = new Audio(`${process.env.REACT_APP_BACKEND_URL}${clip.url}`);
    audioRef.current.play().catch(() => {});
  };

  const saveGroup = async () => {
    const group = GROUPS[index];
    const complete = group.fields.every(([key]) => String(reality[key] || "").trim());
    if (!complete) { setError("Answer each question, or use the button if you do not have this type of supporter yet."); return; }
    setBusy(true); setError("");
    try {
      const final = index === GROUPS.length - 1;
      const savedReality = final ? { ...reality, reviewed: "yes" } : reality;
      await memberApi.put("/game/situation", { sections: { current_reality: savedReality }, current_step: final ? 3 : index + 1 });
      if (final) {
        await memberApi.post("/game/situation/complete");
        navigate("/game/dashboard", { replace: true });
      } else { setIndex(index + 1); window.scrollTo({ top: 0 }); }
    } catch (err) { setError(err.response?.data?.detail || "We could not save your answers. Please try again."); }
    setBusy(false);
  };

  const noCurrent = () => {
    const group = GROUPS[index];
    const label = group.key === "individuals" ? "individual donors" : group.key === "businesses" ? "business sponsors or partners" : "grantors";
    const next = { ...reality };
    group.fields.forEach(([key]) => { next[key] = `We do not currently have ${label}.`; });
    setReality(next); setError("");
  };

  const shell = (children, testId) => <BfgShell><main className="bfg-flow" style={{ maxWidth: 760, margin: "0 auto", padding: "30px 20px 80px", textAlign: "center" }} data-testid={testId}>{children}{error && <p className="bfg-error">{error}</p>}</main></BfgShell>;
  if (loading || phase === "loading") return shell(<p style={{ marginTop: 40 }}>Loading your game…</p>, "bfg-situation-loading");
  if (phase === "error") return shell(null, "bfg-situation-error");

  if (phase === "play_first") {
    const chooseLogo = (event) => {
      const file = event.target.files?.[0]; setError("");
      if (!file) return;
      if (!file.type.startsWith("image/") || file.size > 500000) { setError("Choose an image file under 500KB."); return; }
      const reader = new FileReader(); reader.onload = () => setBranding({ logo_data: reader.result }); reader.readAsDataURL(file);
    };
    const begin = async () => {
      setBusy(true);
      try { if (branding.logo_data) await memberApi.put("/game/branding", branding); navigate(`/play/${token}`); }
      catch { setError("We could not save your logo."); setBusy(false); }
    };
    return shell(<>
      <p className="bfg-eyebrow">YOUR INDIVIDUAL BOARD FUNDRAISING GAME</p>
      <h1>Start With Your Ideas For Reaching The Fundraising Goal</h1>
      <p style={{ marginTop: 14, fontSize: 17 }}>You will identify the strongest individual, business and grantor audiences, then decide where to find them, how to attract them, what to ask them to fund, and the process that can turn a first contact into support.</p>
      <div className="bfg-card bfg-game-opening-card" style={{ marginTop: 22 }}>
        <h2>Add Your Organization Logo</h2>
        <div className="bfg-game-logo-control">
          {branding.logo_data ? <img src={branding.logo_data} alt="Organization logo" /> : <div className="bfg-game-logo-placeholder">Your logo will appear here</div>}
          <label className="bfg-btn bfg-btn-ghost bfg-btn-sm">CHOOSE LOGO<input type="file" accept="image/*" hidden onChange={chooseLogo} /></label>
        </div>
      </div>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy} onClick={begin}>{busy ? "SAVING…" : "START MY BOARD FUNDRAISING GAME"}</button>
    </>, "bfg-setup-play-first");
  }

  const group = GROUPS[index];
  return shell(<>
    <div style={{ position: "absolute", top: 14, right: 14 }}><NarrationControl audioRef={audioRef} onReplay={() => play(true)} /></div>
    <p className="bfg-eyebrow">YOUR PRESENT FUNDRAISING • {index + 1} OF 3</p>
    <h1>{group.title}</h1>
    <p style={{ marginTop: 12 }}>This information will appear beside the new ideas during the Group Game, so your Board can keep what already works and improve what needs to change.</p>
    {group.fields.map(([key, question]) => <div key={key} className="bfg-card" style={{ marginTop: 18, textAlign: "left", padding: 18 }}>
      <label className="bfg-field"><span style={{ fontSize: 16 }}>{question}</span>
        <textarea rows={4} value={reality[key] || ""} onChange={(event) => setReality((current) => ({ ...current, [key]: event.target.value }))} placeholder="Type your answer here..." />
      </label>
      <SpeakButton value={reality[key] || ""} onChange={(value) => setReality((current) => ({ ...current, [key]: value }))} testId={`bfg-reality-${key}-speak`} />
    </div>)}
    <button className="bfg-btn bfg-btn-ghost" style={{ marginTop: 18 }} onClick={noCurrent}>WE DO NOT HAVE THESE SUPPORTERS YET</button>
    <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 22 }}>
      {index > 0 && <button className="bfg-btn bfg-btn-ghost" onClick={() => setIndex(index - 1)}>Back</button>}
      <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={saveGroup}>{busy ? "SAVING…" : index === 2 ? "SAVE AND RETURN TO DASHBOARD" : "CONTINUE"}</button>
    </div>
  </>, "bfg-current-fundraising");
}
