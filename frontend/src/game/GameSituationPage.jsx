import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { NarrationControl, isNarrationMuted } from "./NarrationControl";
import { SpeakButton } from "./SpeakButton";
import { GameNightSection } from "./GameNightSection";

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
      ["current_individual_donor_seeking", "What are you hoping to raise from individual donors now, and what would their support make possible?"],
      ["current_individual_donor_motivation", "Why do you think these donors choose to give to your organization?"],
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
      ["current_business_seeking", "What are you hoping to raise from businesses now, and how would you like them to help?"],
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
      ["current_grantor_seeking", "What are you hoping to raise from grantmakers now, and what would that fund?"],
    ],
  },
];

export default function GameSituationPage() {
  const navigate = useNavigate();
  const reviewMode = new URLSearchParams(useLocation().search).get("review") === "1";
  const { member, loading } = useMemberAuth();
  const [phase, setPhase] = useState("loading");
  const [fiveIdeasSaved, setFiveIdeasSaved] = useState(false);
  const [token, setToken] = useState("");
  const [index, setIndex] = useState(0);
  const [reality, setReality] = useState({});
  const [capacity, setCapacity] = useState({ team: {}, technology: {}, materials: {} });
  const [meetingReady, setMeetingReady] = useState(false);
  const [setupStep, setSetupStep] = useState(0);
  const [situationComplete, setSituationComplete] = useState(false);
  const [leadParticipationComplete, setLeadParticipationComplete] = useState(false);
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
        const [situation, brand, self, meeting] = await Promise.all([
          memberApi.get("/game/situation"), memberApi.get("/game/branding"), memberApi.post("/game/self-play"), memberApi.get("/game/night"),
        ]);
        setReality(situation.data.sections?.current_reality || {});
        setCapacity({
          team: situation.data.sections?.team || {}, technology: situation.data.sections?.technology || {},
          materials: situation.data.sections?.materials || {},
        });
        setBranding(brand.data.branding || { logo_data: "" });
        setToken(self.data.token);
        const response = (await axios.get(`${API}/game/play/${self.data.token}/audience-response`)).data.response || {};
        setFiveIdeasSaved(response.game_version === 5 && ["1", "2", "3", "4", "5"].every((key) => (response.original_answers?.[key] || "").trim()));
        setSituationComplete(Boolean(situation.data.completed));
        setLeadParticipationComplete(Boolean(response.completed));
        const ready = Boolean(meeting.data.night?.meeting_date && meeting.data.night?.start_time && meeting.data.night?.funding_deadline);
        setMeetingReady(ready);
        if (situation.data.completed && response.completed && ready && !reviewMode) { navigate("/game/dashboard#bfg-board-members-section", { replace: true }); return; }
        setSetupStep(Number(situation.data.current_step || 0));
        setIndex(reviewMode ? 0 : Math.min(2, Math.max(0, Number(situation.data.current_step || 0))));
        if (reviewMode) setPhase("reality");
        else if (Number(situation.data.current_step || 0) >= 4 || situation.data.completed) {
          if (!response.completed) setPhase("play_first");
          else if (!ready) setPhase("meeting");
          else {
            if (!situation.data.completed) await memberApi.post("/game/situation/complete");
            navigate("/game/dashboard#bfg-board-members-section", { replace: true });
          }
        } else if (Number(situation.data.current_step || 0) >= 3) setPhase("capacity");
        else setPhase("reality");
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

  const saveGroup = async (answers = reality) => {
    const group = GROUPS[index];
    const complete = answers[`${group.key}_status`] === "none" || group.fields.every(([key]) => String(answers[key] || "").trim());
    if (!complete) { setError("Answer each question, or use the button if you do not have this type of supporter yet."); return; }
    setBusy(true); setError("");
    try {
      const final = index === GROUPS.length - 1;
      const savedReality = { ...answers, [`${group.key}_status`]: answers[`${group.key}_status`] === "none" ? "none" : "current",
        ...(reviewMode && situationComplete && !reality.setup_version ? {} : { setup_version: "post_payment_v2" }) };
      await memberApi.put("/game/situation", { sections: { current_reality: savedReality },
        current_step: reviewMode && situationComplete ? Math.max(4, setupStep) : index + 1 });
      setReality(savedReality);
      if (final) {
        setPhase("capacity"); window.scrollTo({ top: 0 });
      } else { setIndex(index + 1); window.scrollTo({ top: 0 }); }
    } catch (err) { setError(err.response?.data?.detail || "We could not save your answers. Please try again."); }
    setBusy(false);
  };

  const noCurrent = () => {
    const group = GROUPS[index];
    const next = { ...reality, [`${group.key}_status`]: "none" };
    group.fields.forEach(([key]) => { next[key] = ""; });
    saveGroup(next);
  };

  const saveCapacity = async () => {
    const needed = [["team", "who_handles"], ["team", "board_involvement"], ["technology", "tools"],
      ["technology", "tech_working"], ["materials", "materials"]];
    if (needed.some(([section, key]) => !String(capacity[section]?.[key] || "").trim())) {
      setError("Please describe each part of your current capacity. If you don't have something yet, you can say so."); return;
    }
    setBusy(true); setError("");
    try {
      await memberApi.put("/game/situation", { sections: { ...capacity, current_reality: { ...reality, reviewed: "yes", setup_version: "post_payment_v2" } }, current_step: 4 });
      setPhase("play_first"); window.scrollTo({ top: 0 });
    } catch (err) { setError(err.response?.data?.detail || "We could not save your current resources. Please try again."); }
    finally { setBusy(false); }
  };

  const shell = (children, testId) => <BfgShell><main className="bfg-flow bfg-setup-flow" data-testid={testId}>{children}{error && <p className="bfg-error" role="alert">{error}</p>}</main></BfgShell>;
  const finishMeetingSetup = async () => {
    if (setupStep >= 4 && leadParticipationComplete) {
      try { await memberApi.post("/game/situation/complete"); navigate("/game/dashboard#bfg-board-members-section"); }
      catch (err) { setError(err.response?.data?.detail || "We could not finish the setup. Please try again."); }
    } else { setPhase(reviewMode ? "reality" : setupStep >= 3 ? "capacity" : "reality"); window.scrollTo({ top: 0 }); }
  };
  if (loading || phase === "loading") return shell(<p style={{ marginTop: 40 }}>Loading your game…</p>, "bfg-situation-loading");
  if (phase === "error") return shell(null, "bfg-situation-error");

  if (phase === "meeting") return shell(<>
    <p className="bfg-eyebrow">BOARD FUNDRAISING GAME SETUP • FINAL STEP</p>
    <h1>When Is Your Next Board Meeting?</h1>
    <p style={{ margin: "14px auto 22px" }}>Your board members will play individually before this meeting. Tell us when the board meets and when you need to raise your fundraising goal, so your final strategy works toward a real deadline.</p>
    <div className="bfg-setup-fields"><GameNightSection autoOpen onSaved={() => setMeetingReady(true)} /></div>
    {meetingReady && <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} onClick={finishMeetingSetup}>{setupStep >= 4 && leadParticipationComplete ? "INVITE MY BOARD MEMBERS" : "CONTINUE SETUP"}</button>}
  </>, "bfg-setup-meeting");

  if (phase === "capacity") {
    const fields = [
      ["team", "who_handles", "Who currently handles fundraising and donor relationships for your organization?"],
      ["team", "board_involvement", "How is your board involved in fundraising today?"],
      ["technology", "tools", "What tools or systems do you already use to track funders and fundraising?"],
      ["technology", "tech_working", "What works well with those tools, and where do you need more support?"],
      ["materials", "materials", "What fundraising materials, stories, evidence or campaign resources do you already have?"],
    ];
    return shell(<>
      <p className="bfg-eyebrow">YOUR PRESENT FUNDRAISING • TEAM & RESOURCES</p>
      <h1>What Can You Already Build On?</h1>
      <p style={{ marginTop: 12 }}>Tell us what exists today. If you don't have a team, tool or material yet, say so. Your board can then make a practical plan with the resources you actually have.</p>
      <div className="bfg-setup-fields">{fields.map(([section, key, question], fieldIndex) => <div key={`${section}-${key}`} className="bfg-card bfg-setup-field">
        <span className="bfg-setup-field-number">{String(fieldIndex + 1).padStart(2, "0")}</span>
        <label className="bfg-field"><span>{question}</span>
          <textarea rows={4} value={capacity[section]?.[key] || ""} onChange={(event) => setCapacity((current) => ({ ...current, [section]: { ...current[section], [key]: event.target.value } }))} placeholder="Describe what exists today, or say none yet…" />
        </label>
        <SpeakButton value={capacity[section]?.[key] || ""} onChange={(value) => setCapacity((current) => ({ ...current, [section]: { ...current[section], [key]: value } }))} />
      </div>)}</div>
      <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 22 }}>
        <button className="bfg-btn bfg-btn-ghost" onClick={() => { setIndex(2); setPhase("reality"); }}>BACK</button>
        <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={saveCapacity}>{busy ? "SAVING…" : "CONTINUE TO MY PARTICIPATION"}</button>
      </div>
    </>, "bfg-current-capacity");
  }

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
      <h1>{fiveIdeasSaved ? "How Will You Personally Participate?" : "Start With Your Ideas For Reaching The Fundraising Goal"}</h1>
      <p style={{ marginTop: 14, fontSize: 17 }}>{fiveIdeasSaved ? "Your five ideas and present fundraising reality are saved. Now tell us which part of the process you can personally take responsibility for. Then you can invite your board." : "Answer five questions about one funding audience, where to find them, how to attract them, what to ask and how to build a relationship toward giving."}</p>
      <div className="bfg-card bfg-game-opening-card" style={{ marginTop: 22 }}>
        <h2>Add Your Organization Logo</h2>
        <div className="bfg-game-logo-control">
          {branding.logo_data ? <img src={branding.logo_data} alt="Organization logo" /> : <div className="bfg-game-logo-placeholder">Your logo will appear here</div>}
          <label className="bfg-btn bfg-btn-ghost bfg-btn-sm">CHOOSE LOGO<input type="file" accept="image/*" hidden onChange={chooseLogo} /></label>
        </div>
      </div>
      <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 22 }} disabled={busy} onClick={begin}>{busy ? "SAVING…" : fiveIdeasSaved ? "CONTINUE TO MY PARTICIPATION" : "START MY BOARD FUNDRAISING GAME"}</button>
    </>, "bfg-setup-play-first");
  }

  const group = GROUPS[index];
  const groupStatus = reality[`${group.key}_status`] || (group.fields.some(([key]) => String(reality[key] || "").trim()) ? "current" : "");
  return shell(<>
    <div className="bfg-setup-header"><p className="bfg-eyebrow">YOUR PRESENT FUNDRAISING • {index + 1} OF 3</p><NarrationControl audioRef={audioRef} onReplay={() => play(true)} /></div>
    <h1>{group.title}</h1>
    <p style={{ marginTop: 12 }}>Do you currently receive support from this group? If you do, tell us about those relationships so your Board can build on what exists. If you do not, you can move straight to the next section.</p>
    <div className="bfg-setup-choices">
      <button className={`bfg-btn bfg-btn-ghost ${groupStatus === "current" ? "is-selected" : ""}`} aria-pressed={groupStatus === "current"} onClick={() => setReality((current) => ({ ...current, [`${group.key}_status`]: "current" }))}>YES, WE HAVE THESE SUPPORTERS</button>
      <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={noCurrent}>WE DO NOT HAVE THESE SUPPORTERS YET</button>
    </div>
    {groupStatus === "current" && <div className="bfg-setup-fields">{group.fields.map(([key, question], fieldIndex) => <div key={key} className="bfg-card bfg-setup-field">
      <span className="bfg-setup-field-number">{String(fieldIndex + 1).padStart(2, "0")}</span>
      <label className="bfg-field"><span>{question}</span>
        <textarea rows={4} value={reality[key] || ""} onChange={(event) => setReality((current) => ({ ...current, [key]: event.target.value, [`${group.key}_status`]: "current" }))} placeholder="Type your answer here..." />
      </label>
      <SpeakButton value={reality[key] || ""} onChange={(value) => setReality((current) => ({ ...current, [key]: value, [`${group.key}_status`]: "current" }))} testId={`bfg-reality-${key}-speak`} />
    </div>)}</div>}
    <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 22 }}>
      {index > 0 && <button className="bfg-btn bfg-btn-ghost" onClick={() => setIndex(index - 1)}>Back</button>}
      {groupStatus === "current" && <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={() => saveGroup()}>{busy ? "SAVING…" : index === 2 ? "CONTINUE TO TEAM & RESOURCES" : "CONTINUE"}</button>}
    </div>
  </>, "bfg-current-fundraising");
}
