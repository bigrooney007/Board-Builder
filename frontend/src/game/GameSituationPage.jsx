import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { NarrationControl, isNarrationMuted } from "./NarrationControl";
import { SpeakButton } from "./SpeakButton";
import { GameNightSection } from "./GameNightSection";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

export const PRESENT_FUNDER_GROUPS = [
  {
    key: "individuals", title: "Your Present Individual Donors", clip: "reality_donors", prefix: "individual_donor",
    fields: [
      ["current_individual_donor_profile", "Who are your present individual donors, and why do you think they give?"],
      ["current_individual_donor_where", "Where do you find or meet these donors?"],
      ["current_individual_donor_process", "How do you raise money from them, from first contact through receiving their support?"],
      ["current_individual_donor_support", "What do you ask these donors to fund, and how much do you ask them to give?"],
    ],
  },
  {
    key: "businesses", title: "Your Present Business Sponsors Or Partners", clip: "reality_businesses", prefix: "business",
    fields: [
      ["current_business_profile", "What types of businesses presently support you, and why do you think they give?"],
      ["current_business_where", "Where do you find or connect with these businesses?"],
      ["current_business_process", "How do you raise money from these businesses, from first contact through receiving their support?"],
      ["current_business_support", "What do you ask these businesses to sponsor or fund, and how much do you ask them to give?"],
    ],
  },
  {
    key: "grantors", title: "Your Present Grantors", clip: "reality_grantors", prefix: "grantor",
    fields: [
      ["current_grantor_profile", "What types of grantors presently fund you, and why do they fund your work?"],
      ["current_grantor_where", "Where do you find these grantors or their funding opportunities?"],
      ["current_grantor_process", "What process do you use to raise money from these grantors?"],
      ["current_grantor_support", "What do you ask these grantors to fund, and how much do you request?"],
    ],
  },
];

const groupStatus = (reality, group) => reality[group.key + "_status"]
  || (group.fields.some(([key]) => String(reality[key] || "").trim()) ? "current" : "");
const groupComplete = (reality, group) => groupStatus(reality, group) === "none"
  || (groupStatus(reality, group) === "current" && group.fields.every(([key]) => String(reality[key] || "").trim()));

function savedRealityForForm(saved) {
  const reality = { ...saved };
  // Keep separately saved motivations visible when resuming the older, longer form.
  if (reality.setup_version !== "present_funders_v3") {
    PRESENT_FUNDER_GROUPS.forEach((group) => {
      const key = "current_" + group.prefix + "_profile";
      const motivation = String(reality["current_" + group.prefix + "_motivation"] || "").trim();
      if (motivation && !String(reality[key] || "").includes(motivation)) {
        reality[key] = [reality[key], "Why they give: " + motivation].filter(Boolean).join("\n\n");
      }
    });
  }
  return reality;
}

export default function GameSituationPage() {
  const navigate = useNavigate();
  const reviewMode = new URLSearchParams(useLocation().search).get("review") === "1";
  const { member, loading } = useMemberAuth();
  const [phase, setPhase] = useState("loading");
  const [index, setIndex] = useState(0);
  const [reality, setReality] = useState({});
  const [meetingReady, setMeetingReady] = useState(false);
  const [leadParticipationComplete, setLeadParticipationComplete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clips, setClips] = useState({});
  const audioRef = useRef(null);

  useEffect(() => { document.title = "Your Present Fundraising | Board Fundraising Game"; }, []);
  useEffect(() => () => { if (audioRef.current) audioRef.current.pause(); }, []);
  useEffect(() => {
    if (loading) return undefined;
    if (!member) {
      navigate("/login?next=" + encodeURIComponent(window.location.pathname + window.location.search), { replace: true });
      return undefined;
    }
    let active = true;
    (async () => {
      try {
        const [situation, self, meeting] = await Promise.all([
          memberApi.get("/game/situation"), memberApi.post("/game/self-play"), memberApi.get("/game/night"),
        ]);
        const saved = savedRealityForForm(situation.data.sections?.current_reality || {});
        const response = (await axios.get(API + "/game/play/" + self.data.token + "/audience-response")).data.response || {};
        if (!active) return;
        setReality(saved);
        const participated = Boolean(response.completed);
        const ready = Boolean(meeting.data.night?.meeting_date && meeting.data.night?.start_time && meeting.data.night?.funding_deadline);
        setLeadParticipationComplete(participated);
        setMeetingReady(ready);
        axios.get(API + "/game/voice/manifest/" + self.data.token).then((r) => {
          if (active) setClips(r.data.clips || {});
        }).catch(() => {});
        const realityReady = PRESENT_FUNDER_GROUPS.every((group) => groupComplete(saved, group));
        if (reviewMode) { setIndex(0); setPhase("reality"); return; }
        // Resume customers who reached the old resources page using their saved funder answers.
        if (realityReady && Number(situation.data.current_step || 0) >= 3) {
          if (saved.setup_version !== "present_funders_v3" || !saved.reviewed) {
            const migrated = { ...saved, reviewed: "yes", setup_version: "present_funders_v3" };
            await memberApi.put("/game/situation", { sections: { current_reality: migrated }, current_step: 3 });
            if (!active) return;
            setReality(migrated);
          }
          if (!participated) { navigate("/play/" + self.data.token, { replace: true }); return; }
          if (!ready) { setPhase("meeting"); return; }
          if (!situation.data.completed) await memberApi.post("/game/situation/complete");
          if (active) navigate("/game/dashboard#bfg-board-members-section", { replace: true });
          return;
        }
        const pending = PRESENT_FUNDER_GROUPS.findIndex((group) => !groupComplete(saved, group));
        setIndex(Math.max(0, pending));
        setPhase("reality");
      } catch (err) {
        if (active) {
          setError(err.response?.data?.detail || "We could not load your saved answers. Please refresh the page.");
          setPhase("error");
        }
      }
    })();
    return () => { active = false; };
  }, [loading, member, navigate, reviewMode]);

  useEffect(() => {
    const clip = clips[PRESENT_FUNDER_GROUPS[index]?.clip];
    if (phase !== "reality" || !clip?.ready || isNarrationMuted()) return;
    if (audioRef.current) audioRef.current.pause();
    audioRef.current = new Audio(process.env.REACT_APP_BACKEND_URL + clip.url);
    audioRef.current.play().catch(() => {});
  }, [phase, index, clips]);

  const play = () => {
    const clip = clips[PRESENT_FUNDER_GROUPS[index]?.clip];
    if (!clip?.ready) return;
    if (audioRef.current) audioRef.current.pause();
    audioRef.current = new Audio(process.env.REACT_APP_BACKEND_URL + clip.url);
    audioRef.current.play().catch(() => {});
  };

  const saveGroup = async (answers = reality) => {
    const group = PRESENT_FUNDER_GROUPS[index];
    if (!groupComplete(answers, group)) {
      setError("Answer the four questions, or choose the option if you do not have these supporters yet."); return;
    }
    setBusy(true); setError("");
    try {
      const final = index === PRESENT_FUNDER_GROUPS.length - 1;
      const saved = { ...answers, [group.key + "_status"]: groupStatus(answers, group), setup_version: "present_funders_v3",
        ...(final ? { reviewed: "yes" } : {}) };
      await memberApi.put("/game/situation", { sections: { current_reality: saved }, current_step: final || reviewMode ? 3 : index + 1 });
      setReality(saved);
      if (!final) { setIndex(index + 1); window.scrollTo({ top: 0 }); }
      else if (leadParticipationComplete) {
        if (meetingReady) {
          await memberApi.post("/game/situation/complete");
          navigate("/game/dashboard#bfg-board-members-section");
        }
        else setPhase("meeting");
      } else {
        const self = await memberApi.post("/game/self-play");
        navigate("/play/" + self.data.token);
      }
    } catch (err) { setError(err.response?.data?.detail || "We could not save your answers. Please try again."); }
    finally { setBusy(false); }
  };
  const noCurrent = () => {
    const group = PRESENT_FUNDER_GROUPS[index];
    saveGroup({ ...reality, [group.key + "_status"]: "none" });
  };
  const finishMeetingSetup = async () => {
    setBusy(true); setError("");
    try {
      await memberApi.post("/game/situation/complete");
      navigate("/game/dashboard#bfg-board-members-section");
    } catch (err) { setError(err.response?.data?.detail || "We could not finish your meeting setup. Please try again."); }
    finally { setBusy(false); }
  };
  const shell = (children, testId) => <BfgShell><main className="bfg-flow bfg-setup-flow" data-testid={testId}>
    {children}{error && <p className="bfg-error" role="alert">{error}</p>}
  </main></BfgShell>;
  if (loading || phase === "loading") return shell(<p style={{ marginTop: 40 }}>Opening your saved fundraising answers…</p>, "bfg-situation-loading");
  if (phase === "error") return shell(<button className="bfg-btn bfg-btn-primary" onClick={() => window.location.reload()}>TRY AGAIN</button>, "bfg-situation-error");
  if (phase === "meeting") return shell(<>
    <p className="bfg-eyebrow">BOARD FUNDRAISING GAME SETUP • FINAL STEP</p>
    <h1>When Is Your Next Board Meeting?</h1>
    <p style={{ margin: "14px auto 22px" }}>Your participation answer is saved. Set your meeting date and time and the deadline for your fundraising goal, then invite your board.</p>
    <div className="bfg-setup-fields"><GameNightSection autoOpen onSaved={() => setMeetingReady(true)} /></div>
    {meetingReady && <button className="bfg-btn bfg-btn-primary" disabled={busy} style={{ marginTop: 22 }} onClick={finishMeetingSetup}>
      {busy ? "SAVING…" : "INVITE MY BOARD MEMBERS"}
    </button>}
  </>, "bfg-setup-meeting");

  const group = PRESENT_FUNDER_GROUPS[index];
  const status = groupStatus(reality, group);
  return shell(<>
    <div className="bfg-setup-header"><p className="bfg-eyebrow">YOUR PRESENT FUNDRAISING • {index + 1} OF 3</p><NarrationControl audioRef={audioRef} onReplay={play} /></div>
    <h1>{group.title}</h1>
    <p style={{ marginTop: 12 }}>Tell us about the support you already receive in four short answers. If you have no supporters in this group, continue to the next section.</p>
    <div className="bfg-setup-choices">
      <button className={"bfg-btn bfg-btn-ghost " + (status === "current" ? "is-selected" : "")} aria-pressed={status === "current"}
        onClick={() => setReality((current) => ({ ...current, [group.key + "_status"]: "current" }))}>YES, WE HAVE THESE SUPPORTERS</button>
      <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={noCurrent}>WE DO NOT HAVE THESE SUPPORTERS YET</button>
    </div>
    {status === "current" && <div className="bfg-setup-fields">{group.fields.map(([key, question], fieldIndex) => <div key={key} className="bfg-card bfg-setup-field">
      <span className="bfg-setup-field-number">{String(fieldIndex + 1).padStart(2, "0")}</span>
      <label className="bfg-field"><span>{question}</span>
        <textarea rows={3} value={reality[key] || ""} onChange={(event) => setReality((current) => ({ ...current, [key]: event.target.value }))}
          placeholder="Type your answer here..." />
      </label>
      <SpeakButton value={reality[key] || ""} onChange={(value) => setReality((current) => ({ ...current, [key]: value }))} testId={"bfg-reality-" + key + "-speak"} />
    </div>)}</div>}
    <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 22 }}>
      {index > 0 && <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => setIndex(index - 1)}>BACK</button>}
      {status === "current" && <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={() => saveGroup()}>
        {busy ? "SAVING…" : index === 2 ? "CONTINUE TO MY PARTICIPATION" : "CONTINUE"}
      </button>}
    </div>
  </>, "bfg-current-fundraising");
}
