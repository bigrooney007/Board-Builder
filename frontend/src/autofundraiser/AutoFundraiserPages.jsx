import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import "./autofundraiser.css";
import { AUTO_FUNDRAISER_LOGO } from "./logoData";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/autofundraiser`;

export const STRATEGY_QUESTIONS = [
  {
    key: "1",
    title: "From your point of view, if there is one audience you believe can really help your organization reach its fundraising goal, who are they?",
    hint: "Think about one particular type of person, business, company, foundation, grantmaker or other funding audience you believe has a strong reason to support what your organization does.",
  },
  {
    key: "2",
    title: "Where do you think you can actually find the kind of people or organizations you just identified?",
    hint: "Think about where they work, gather, network, belong, search for opportunities or pay attention.",
  },
  {
    key: "3",
    title: "How do you think your organization can get their attention and make them interested in your mission and what you do?",
    hint: "Focus on what can happen consistently before you ask them for money.",
  },
  {
    key: "4",
    title: "If you eventually get in front of these funders, what should you actually ask them to fund? And how much should you ask for?",
    hint: "Describe the thing you would ask them to support and the amount or range you believe makes sense.",
  },
  {
    key: "5",
    title: "From the first time they hear about your organization, what should the step-by-step process be for building the relationship and eventually getting them to give?",
    hint: "Think through the journey from first awareness to relationship, ask, follow-up and giving.",
  },
];

export const REALITY_GROUPS = [
  {
    key: "individuals",
    title: "Your Present Individual Donors",
    fields: [
      ["current_individual_donor_profile", "Who are your present individual donors? Describe the types or groups of people who currently give."],
      ["current_individual_donor_where", "Where do you presently find or meet these donors?"],
      ["current_individual_donor_attraction", "How do you presently attract them or get their attention?"],
      ["current_individual_donor_support", "What do they currently give to or help fund, and about how much do they give?"],
      ["current_individual_donor_process", "How do you presently move them from first contact to making a donation?"],
    ],
  },
  {
    key: "businesses",
    title: "Your Present Business Sponsors Or Partners",
    fields: [
      ["current_business_profile", "Who are your present corporate sponsors or business partners? Describe the types of businesses that currently support you."],
      ["current_business_where", "Where did you find or first connect with these businesses?"],
      ["current_business_attraction", "How do you presently attract them or earn their interest?"],
      ["current_business_support", "What do they currently sponsor, fund or contribute, and about how much do they give?"],
      ["current_business_process", "What process do you presently use to secure and maintain their support?"],
    ],
  },
  {
    key: "grantors",
    title: "Your Present Grantors",
    fields: [
      ["current_grantor_profile", "Who are your present grantors? Describe the types of foundations, agencies or other funders that currently fund you."],
      ["current_grantor_where", "Where do you presently find these grant opportunities?"],
      ["current_grantor_attraction", "How do you presently demonstrate credibility or build a relationship with them?"],
      ["current_grantor_support", "What do they currently fund, and about how much do they award?"],
      ["current_grantor_process", "What process do you presently follow before, during and after applying for their funding?"],
    ],
  },
];

function Logo({ compact = false }) {
  return <a href="/auto-fundraiser" className={compact ? "af-logo af-logo-compact" : "af-logo"} aria-label="Auto Fundraiser home">
    <img src={AUTO_FUNDRAISER_LOGO} alt="Auto Fundraiser" />
  </a>;
}

function Shell({ children, narrow = false }) {
  return <div className="af-app">
    <header className="af-header"><Logo compact /></header>
    <main className={narrow ? "af-shell af-shell-narrow" : "af-shell"}>{children}</main>
    <footer className="af-footer">© 2026 Auto Fundraiser</footer>
  </div>;
}

function Spinner({ label = "Auto Fundraiser is reviewing your fundraising approach…" }) {
  return <div className="af-thinking">
    <div className="af-orbit"><span /><span /><span /></div>
    <h2>{label}</h2>
    <p>We are looking for the strategy underneath the fundraising activities.</p>
  </div>;
}

export function AutoFundraiserHomePage() {
  const navigate = useNavigate();
  const [content, setContent] = useState(null);
  const [approach, setApproach] = useState("");
  const [file, setFile] = useState(null);
  const [noStrategy, setNoStrategy] = useState(false);
  const [capture, setCapture] = useState(false);
  const [identity, setIdentity] = useState({ name: "", email: "", organization_name: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    document.title = "Auto Fundraiser | Review Your Fundraising Strategy";
    axios.get(`${API}/homepage`).then(({ data }) => setContent(data)).catch(() => setContent({}));
  }, []);

  const canContinue = noStrategy || approach.trim() || file;

  const openCapture = () => {
    if (!canContinue) return;
    setCapture(true);
    setTimeout(() => document.getElementById("af-name")?.focus(), 60);
  };

  const submit = async () => {
    if (!identity.name.trim() || !identity.email.trim() || !identity.organization_name.trim()) return;
    setBusy(true); setError("");
    const form = new FormData();
    form.append("name", identity.name.trim());
    form.append("email", identity.email.trim());
    form.append("organization_name", identity.organization_name.trim());
    form.append("approach", approach.trim());
    form.append("no_strategy", noStrategy ? "true" : "false");
    if (file) form.append("file", file);
    try {
      const { data } = await axios.post(`${API}/leads`, form);
      navigate(data.diagnosis ? `/auto-fundraiser/result/${data.resume_token}` : `/auto-fundraiser/review/${data.resume_token}`);
    } catch (err) {
      setError(err.response?.data?.detail || "We could not start your review. Please try again.");
      setBusy(false);
    }
  };

  if (!content) return <Shell><Spinner label="Opening Auto Fundraiser…" /></Shell>;

  return <div className="af-home">
    <div className="af-home-top"><Logo /></div>
    <main className="af-hero">
      <div className="af-kicker">FUNDRAISING STRATEGY DIAGNOSTIC</div>
      <h1>{content.headline || "How Does Your Organization Currently Raise Money?"}</h1>
      <p className="af-problem">{content.problem_statement || "The number one reason nonprofits struggle to raise money is because of their fundraising strategy and approach."}</p>
      <p className="af-support">{content.supporting_text}</p>

      <div className={`af-composer ${noStrategy ? "af-composer-disabled" : ""}`}>
        <textarea
          rows={5}
          value={approach}
          disabled={noStrategy}
          onChange={(event) => setApproach(event.target.value)}
          placeholder={content.composer_placeholder || "Describe your current fundraising strategy or approach…"}
          aria-label="Describe your fundraising strategy or approach"
        />
        <div className="af-composer-tools">
          <label className="af-upload">
            <input type="file" accept=".pdf,.docx,.txt,.md,.csv" hidden disabled={noStrategy}
              onChange={(event) => setFile(event.target.files?.[0] || null)} />
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 17V5m0 0L7 10m5-5 5 5M5 19h14" /></svg>
            {file ? file.name : "Attach fundraising plan"}
          </label>
          {file && !noStrategy && <button className="af-file-clear" onClick={() => setFile(null)}>Remove</button>}
        </div>
      </div>

      <button className={`af-none ${noStrategy ? "active" : ""}`} onClick={() => { setNoStrategy(!noStrategy); if (!noStrategy) { setApproach(""); setFile(null); } }}>
        <span className="af-check">{noStrategy ? "✓" : ""}</span>
        {content.no_strategy_label || "I don't have a fundraising strategy"}
      </button>

      {!capture ? <button className="af-primary af-primary-wide" disabled={!canContinue} onClick={openCapture}>
        {content.cta || "REVIEW MY FUNDRAISING APPROACH"}
        <span>→</span>
      </button> : <section className="af-identity-card">
        <div>
          <span className="af-step-chip">LAST THING</span>
          <h2>Where should we save your review?</h2>
          <p>Your email also gives you a way back if you leave before finishing.</p>
        </div>
        <div className="af-fields-three">
          <label>Your name<input id="af-name" value={identity.name} onChange={(e) => setIdentity({ ...identity, name: e.target.value })} /></label>
          <label>Work email<input type="email" value={identity.email} onChange={(e) => setIdentity({ ...identity, email: e.target.value })} /></label>
          <label>Organization<input value={identity.organization_name} onChange={(e) => setIdentity({ ...identity, organization_name: e.target.value })} /></label>
        </div>
        {error && <p className="af-error">{error}</p>}
        <button className="af-primary af-primary-wide" disabled={busy || !identity.name.trim() || !identity.email.trim() || !identity.organization_name.trim()} onClick={submit}>
          {busy ? "REVIEWING…" : "START MY REVIEW"} <span>→</span>
        </button>
      </section>}
      {error && !capture && <p className="af-error">{error}</p>}
      <p className="af-privacy">Your fundraising material is used to assess your strategy and build your Auto Fundraiser record.</p>
    </main>
  </div>;
}

export function AutoFundraiserReviewPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [lead, setLead] = useState(null);
  const [note, setNote] = useState("");
  const [showNote, setShowNote] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const { data } = await axios.get(`${API}/leads/${token}`);
      if (data.diagnosis) { navigate(`/auto-fundraiser/result/${token}`, { replace: true }); return; }
      setLead(data);
    } catch (err) { setError(err.response?.data?.detail || "We could not open this fundraising review."); }
  };

  useEffect(() => { document.title = "Your Fundraising Review | Auto Fundraiser"; load(); }, [token]);

  const answer = async (knows) => {
    if (!lead?.next_clarification) return;
    setBusy(true); setError("");
    try {
      const { data } = await axios.post(`${API}/leads/${token}/clarify`, {
        criterion: lead.next_clarification.criterion,
        knows,
        note: note.trim(),
      });
      setNote(""); setShowNote(false);
      if (data.diagnosis) navigate(`/auto-fundraiser/result/${token}`);
      else setLead(data);
    } catch (err) {
      setError(err.response?.data?.detail || "We could not save that answer.");
      setBusy(false);
    }
  };

  if (!lead && !error) return <Shell narrow><Spinner /></Shell>;

  return <Shell narrow>
    {error && !lead ? <div className="af-message-card"><h1>We couldn't open this review.</h1><p>{error}</p></div> : <>
      <div className="af-progress-line"><span /><span /><span /></div>
      <div className="af-kicker">YOUR FUNDRAISING REVIEW</div>
      <h1 className="af-review-title">I've reviewed what you shared.</h1>
      <div className="af-readback">
        <span>WHAT I UNDERSTOOD</span>
        <p>{lead?.analysis?.summary}</p>
      </div>
      {lead?.next_clarification && <section className="af-question-card">
        <div className="af-question-number">{lead.next_clarification.criterion}</div>
        <h2>{lead.next_clarification.question}</h2>
        {lead.next_clarification.evidence && <p className="af-evidence">{lead.next_clarification.evidence}</p>}
        <div className="af-binary">
          <button disabled={busy} onClick={() => answer(true)}>YES, WE DO</button>
          <button disabled={busy} onClick={() => answer(false)}>NO, WE DON'T</button>
        </div>
        <button className="af-text-button" onClick={() => setShowNote(!showNote)}>{showNote ? "Hide note" : "I want to add a little context"}</button>
        {showNote && <textarea className="af-note" rows={4} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional. Add context without trying to build the strategy yet." />}
      </section>}
      {error && <p className="af-error">{error}</p>}
      <p className="af-micro">We are checking whether the strategic pieces exist. We are not asking you to build the strategy during this review.</p>
    </>}
  </Shell>;
}

export function AutoFundraiserResultPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [lead, setLead] = useState(null);
  const [content, setContent] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    document.title = "Your Fundraising Diagnosis | Auto Fundraiser";
    Promise.all([axios.get(`${API}/leads/${token}`), axios.get(`${API}/homepage`)])
      .then(([leadResponse, homeResponse]) => {
        if (!leadResponse.data.diagnosis) { navigate(`/auto-fundraiser/review/${token}`, { replace: true }); return; }
        setLead(leadResponse.data); setContent(homeResponse.data);
        axios.post(`${API}/leads/${token}/result-viewed`).catch(() => {});
      }).catch((err) => setError(err.response?.data?.detail || "We could not open your result."));
  }, [token]);

  const checkout = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await axios.post(`${API}/leads/${token}/checkout`);
      window.location.href = data.checkout_url;
    } catch (err) {
      setError(err.response?.data?.detail || "We could not start checkout.");
      setBusy(false);
    }
  };

  if (!lead || !content) return <Shell narrow>{error ? <p className="af-error">{error}</p> : <Spinner label="Preparing your fundraising diagnosis…" />}</Shell>;
  const d = lead.diagnosis;

  return <Shell>
    <section className="af-result-hero">
      <div className="af-kicker">YOUR FUNDRAISING DIAGNOSIS</div>
      <h1>{d.headline}</h1>
      <p>Based on the fundraising strategy or approach you shared with Auto Fundraiser.</p>
    </section>
    <div className="af-diagnosis-grid">
      <article className="af-diagnosis-card"><span>WHAT YOU TOLD US</span><p>{d.what_you_told_us}</p></article>
      <article className="af-diagnosis-card af-diagnosis-accent"><span>WHAT WE FOUND</span><p>{d.what_we_found}</p></article>
      <article className="af-diagnosis-card"><span>WHY THIS MATTERS</span><p>{d.why_it_matters}</p></article>
      <article className="af-diagnosis-card"><span>YOUR NEXT STEP</span><p>{d.next_step}</p></article>
    </div>
    <section className="af-offer">
      <div className="af-offer-copy">
        <span className="af-step-chip">NEXT</span>
        <h2>{content.result_offer_heading}</h2>
        <p>{content.result_offer_text}</p>
        <p className="af-offer-note">Your diagnosis becomes the starting context. After payment, we begin the actual strategy-building questions.</p>
      </div>
      <div className="af-price-card">
        <div className="af-price">{content.price || "$497"}</div>
        <div className="af-price-caption">ONE TIME</div>
        <button className="af-primary af-primary-wide" onClick={checkout} disabled={busy}>{busy ? "OPENING CHECKOUT…" : "BUILD MY FUNDRAISING STRATEGY"} <span>→</span></button>
        <p>Build the strategy. Invite others to contribute. Use your planning meeting to adopt the best ideas.</p>
      </div>
    </section>
    {error && <p className="af-error">{error}</p>}
  </Shell>;
}

export function AutoFundraiserPaymentSuccessPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState("");
  useEffect(() => {
    document.title = "Payment Confirmed | Auto Fundraiser";
    const sessionId = new URLSearchParams(location.search).get("session_id");
    if (!sessionId) { setError("Payment session is missing."); return; }
    axios.get(`${API}/checkout-status?session_id=${encodeURIComponent(sessionId)}`)
      .then(({ data }) => {
        if (!data.paid) { setError("Payment has not been confirmed yet."); return; }
        navigate(`/auto-fundraiser/strategy/${data.resume_token}`, { replace: true });
      }).catch((err) => setError(err.response?.data?.detail || "We could not verify your payment."));
  }, [location.search]);
  return <Shell narrow>{error ? <div className="af-message-card"><h1>We couldn't confirm the payment.</h1><p>{error}</p></div> : <Spinner label="Payment confirmed. Opening your strategy builder…" />}</Shell>;
}

function RealityForm({ value, onChange, onSave, busy }) {
  const [groupIndex, setGroupIndex] = useState(0);
  const group = REALITY_GROUPS[groupIndex];
  const noCurrent = () => {
    const label = group.key === "individuals" ? "individual donors" : group.key === "businesses" ? "business sponsors or partners" : "grantors";
    const next = { ...value };
    group.fields.forEach(([key]) => { next[key] = `We do not currently have ${label}.`; });
    onChange(next);
  };
  const complete = group.fields.every(([key]) => String(value[key] || "").trim());
  return <section className="af-work-card">
    <div className="af-kicker">YOUR PRESENT FUNDRAISING • {groupIndex + 1} OF 3</div>
    <h2>{group.title}</h2>
    <p>Tell Auto Fundraiser what is already happening today. The final strategy should build from reality, not pretend you are starting from zero.</p>
    <div className="af-form-stack">
      {group.fields.map(([key, question]) => <label key={key}>{question}
        <textarea rows={3} value={value[key] || ""} onChange={(e) => onChange({ ...value, [key]: e.target.value })} />
      </label>)}
    </div>
    <button className="af-secondary" onClick={noCurrent}>WE DO NOT HAVE THESE SUPPORTERS YET</button>
    <div className="af-row">
      {groupIndex > 0 && <button className="af-secondary" onClick={() => setGroupIndex(groupIndex - 1)}>BACK</button>}
      <button className="af-primary" disabled={!complete || busy} onClick={() => groupIndex < 2 ? setGroupIndex(groupIndex + 1) : onSave()}>
        {groupIndex < 2 ? "CONTINUE" : busy ? "SAVING…" : "SAVE PRESENT REALITY"}
      </button>
    </div>
  </section>;
}

export function AutoFundraiserStrategyPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [lead, setLead] = useState(null);
  const [phase, setPhase] = useState("loading");
  const [question, setQuestion] = useState(1);
  const [answer, setAnswer] = useState("");
  const [reality, setReality] = useState({});
  const [participation, setParticipation] = useState("");
  const [meeting, setMeeting] = useState({ date: "", time: "", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "", notes: "" });
  const [invite, setInvite] = useState({ name: "", email: "", role: "" });
  const [contributors, setContributors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const { data } = await axios.get(`${API}/strategy/${token}`);
      setLead(data);
      setReality(data.present_reality || {});
      setParticipation(data.participation || "");
      setMeeting({ date: "", time: "", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "", notes: "", ...(data.meeting || {}) });
      setContributors(data.contributors || []);
      const answers = data.strategy_answers || {};
      const missing = STRATEGY_QUESTIONS.find((q) => !String(answers[q.key] || "").trim());
      if (missing) { setQuestion(Number(missing.key)); setAnswer(""); setPhase("questions"); }
      else if (!data.present_reality || Object.keys(data.present_reality).length < 5) setPhase("reality");
      else if (!data.participation) setPhase("participation");
      else setPhase("planning");
    } catch (err) { setError(err.response?.data?.detail || "We could not open your strategy builder."); setPhase("error"); }
  };

  useEffect(() => { document.title = "Build Your Fundraising Strategy | Auto Fundraiser"; load(); }, [token]);

  const saveAnswer = async () => {
    if (!answer.trim()) return;
    setBusy(true); setError("");
    try {
      await axios.put(`${API}/strategy/${token}/answer`, { question, answer });
      const next = question + 1;
      if (next <= 5) { setQuestion(next); setAnswer(""); }
      else { setLead({ ...lead, strategy_answers: { ...(lead.strategy_answers || {}), [question]: answer } }); setPhase("reality"); }
      window.scrollTo({ top: 0 });
    } catch (err) { setError(err.response?.data?.detail || "We could not save your answer."); }
    finally { setBusy(false); }
  };

  const saveReality = async () => {
    setBusy(true); setError("");
    try { await axios.put(`${API}/strategy/${token}/reality`, { answers: reality }); setPhase("participation"); window.scrollTo({ top: 0 }); }
    catch (err) { setError(err.response?.data?.detail || "We could not save your present fundraising."); }
    finally { setBusy(false); }
  };

  const saveParticipation = async () => {
    if (!participation.trim()) return;
    setBusy(true); setError("");
    try { await axios.put(`${API}/strategy/${token}/participation`, { answer: participation }); setPhase("planning"); window.scrollTo({ top: 0 }); }
    catch (err) { setError(err.response?.data?.detail || "We could not save your participation answer."); }
    finally { setBusy(false); }
  };

  const saveMeeting = async () => {
    setBusy(true); setError("");
    try { await axios.put(`${API}/strategy/${token}/meeting`, meeting); }
    catch (err) { setError(err.response?.data?.detail || "We could not save the meeting details."); }
    finally { setBusy(false); }
  };

  const inviteContributor = async () => {
    if (!invite.name.trim() || !invite.email.trim()) return;
    setBusy(true); setError("");
    try {
      const { data } = await axios.post(`${API}/strategy/${token}/contributors`, invite);
      setContributors((current) => current.some((c) => c.token === data.token) ? current : [...current, data]);
      setInvite({ name: "", email: "", role: "" });
    } catch (err) { setError(err.response?.data?.detail || "We could not send that invitation."); }
    finally { setBusy(false); }
  };

  if (phase === "loading") return <Shell narrow><Spinner label="Opening your strategy builder…" /></Shell>;
  if (phase === "error") return <Shell narrow><div className="af-message-card"><h1>We couldn't open your strategy builder.</h1><p>{error}</p></div></Shell>;

  if (phase === "questions") {
    const q = STRATEGY_QUESTIONS[question - 1];
    return <Shell narrow>
      <div className="af-progress-line"><span className="active" /><span /><span /></div>
      <div className="af-kicker">BUILD YOUR STRATEGY • QUESTION {question} OF 5</div>
      <section className="af-work-card af-question-work">
        <h1>{q.title}</h1>
        <p>{q.hint}</p>
        <textarea rows={7} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Tell Auto Fundraiser what you think, in your own words…" />
        {error && <p className="af-error">{error}</p>}
        <button className="af-primary af-primary-wide" disabled={busy || !answer.trim()} onClick={saveAnswer}>{busy ? "SAVING…" : question === 5 ? "CONTINUE" : "NEXT QUESTION"} <span>→</span></button>
      </section>
    </Shell>;
  }

  if (phase === "reality") return <Shell><RealityForm value={reality} onChange={setReality} onSave={saveReality} busy={busy} />{error && <p className="af-error">{error}</p>}</Shell>;

  if (phase === "participation") return <Shell narrow>
    <div className="af-kicker">YOUR PARTICIPATION</div>
    <section className="af-work-card af-question-work">
      <h1>How Would You Be Comfortable Supporting Fundraising?</h1>
      <p>Tell us how you would personally like to participate, including relationships, introductions, leadership, outreach or other actions you are comfortable taking.</p>
      <textarea rows={7} value={participation} onChange={(e) => setParticipation(e.target.value)} placeholder="I would be comfortable helping by…" />
      {error && <p className="af-error">{error}</p>}
      <button className="af-primary af-primary-wide" disabled={busy || !participation.trim()} onClick={saveParticipation}>{busy ? "SAVING…" : "CONTINUE TO COLLABORATIVE PLANNING"} <span>→</span></button>
    </section>
  </Shell>;

  return <Shell>
    <section className="af-planning-hero">
      <div><div className="af-kicker">YOUR FUNDRAISING STRATEGY WORKSPACE</div><h1>Bring the people who will help execute the strategy into building it.</h1><p>Your own answers and present fundraising reality are saved. Now set the planning meeting and invite the people whose ideas should be in the room.</p></div>
      <div className="af-status-pill">PAID STRATEGY BUILDER</div>
    </section>

    <div className="af-planning-grid">
      <section className="af-work-card">
        <span className="af-card-label">1 • PLANNING MEETING</span>
        <h2>When will you review the ideas together?</h2>
        <div className="af-fields-three">
          <label>Date<input type="date" value={meeting.date || ""} onChange={(e) => setMeeting({ ...meeting, date: e.target.value })} /></label>
          <label>Time<input type="time" value={meeting.time || ""} onChange={(e) => setMeeting({ ...meeting, time: e.target.value })} /></label>
          <label>Timezone<input value={meeting.timezone || ""} onChange={(e) => setMeeting({ ...meeting, timezone: e.target.value })} /></label>
        </div>
        <label className="af-full-label">Anything people should know about the meeting<textarea rows={3} value={meeting.notes || ""} onChange={(e) => setMeeting({ ...meeting, notes: e.target.value })} /></label>
        <button className="af-secondary" disabled={busy} onClick={saveMeeting}>{busy ? "SAVING…" : "SAVE MEETING"}</button>
      </section>

      <section className="af-work-card">
        <span className="af-card-label">2 • INVITE CONTRIBUTORS</span>
        <h2>Who else should help shape the strategy?</h2>
        <p>Invite board members, staff, volunteers or other people across the organization. Each person answers the same five questions and says how they would support fundraising.</p>
        <div className="af-fields-three">
          <label>Name<input value={invite.name} onChange={(e) => setInvite({ ...invite, name: e.target.value })} /></label>
          <label>Email<input type="email" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} /></label>
          <label>Role<input value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })} placeholder="Board member, staff…" /></label>
        </div>
        <button className="af-primary" disabled={busy || !invite.name.trim() || !invite.email.trim()} onClick={inviteContributor}>SEND INVITATION</button>
        <div className="af-contributor-list">
          {contributors.length === 0 ? <p className="af-muted">No contributors invited yet.</p> : contributors.map((person) => <div key={person.token} className="af-contributor-row"><div><strong>{person.name}</strong><span>{person.role || person.email}</span></div><span className={person.completed ? "af-complete" : "af-waiting"}>{person.completed ? "COMPLETED" : "INVITED"}</span></div>)}
        </div>
      </section>
    </div>

    <section className="af-next-action">
      <div><span className="af-card-label">3 • NEXT BOARD OR TEAM MEETING</span><h2>Review everyone's ideas and adopt the strategy together.</h2><p>The meeting view places the answers side by side so you can select the ideas your organization wants in the final fundraising strategy.</p></div>
      <button className="af-primary" onClick={() => navigate(`/auto-fundraiser/meeting/${token}`)}>OPEN GROUP FUNDRAISING MEETING <span>→</span></button>
    </section>
    {error && <p className="af-error">{error}</p>}
  </Shell>;
}

export function AutoFundraiserContributorPage() {
  const { token } = useParams();
  const [state, setState] = useState(null);
  const [question, setQuestion] = useState(1);
  const [answers, setAnswers] = useState({});
  const [participation, setParticipation] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    document.title = "Contribute To The Fundraising Strategy | Auto Fundraiser";
    axios.get(`${API}/contribute/${token}`).then(({ data }) => {
      setState(data); setAnswers(data.contributor.answers || {}); setParticipation(data.contributor.participation || "");
      if (data.contributor.completed) setDone(true);
    }).catch((err) => setError(err.response?.data?.detail || "This contribution link is not available."));
  }, [token]);

  const submit = async () => {
    setBusy(true); setError("");
    try { await axios.post(`${API}/contribute/${token}`, { answers, participation }); setDone(true); }
    catch (err) { setError(err.response?.data?.detail || "We could not save your contribution."); }
    finally { setBusy(false); }
  };

  if (!state && !error) return <Shell narrow><Spinner label="Opening your fundraising planning form…" /></Shell>;
  if (error && !state) return <Shell narrow><div className="af-message-card"><h1>We couldn't open this invitation.</h1><p>{error}</p></div></Shell>;
  if (done) return <Shell narrow><div className="af-message-card af-success"><span>✓</span><h1>Your ideas are in.</h1><p>Thank you. {state.organization_name} will be able to review your responses during the group fundraising planning meeting.</p></div></Shell>;

  const person = state.contributor;
  if (question <= 5) {
    const q = STRATEGY_QUESTIONS[question - 1];
    return <Shell narrow>
      <div className="af-kicker">{state.organization_name} • QUESTION {question} OF 5</div>
      <section className="af-work-card af-question-work">
        <h1>{q.title}</h1><p>{q.hint}</p>
        <textarea rows={7} value={answers[String(question)] || ""} onChange={(e) => setAnswers({ ...answers, [String(question)]: e.target.value })} placeholder="Share your idea in your own words…" />
        <div className="af-row">{question > 1 && <button className="af-secondary" onClick={() => setQuestion(question - 1)}>BACK</button>}<button className="af-primary" disabled={!String(answers[String(question)] || "").trim()} onClick={() => setQuestion(question + 1)}>NEXT <span>→</span></button></div>
      </section>
    </Shell>;
  }

  return <Shell narrow>
    <div className="af-kicker">{state.organization_name} • YOUR PARTICIPATION</div>
    <section className="af-work-card af-question-work">
      <h1>How Would You Be Comfortable Supporting Fundraising?</h1>
      <p>Tell {state.organization_name} how you would personally like to participate, including any relationships, introductions or actions you are comfortable taking.</p>
      <textarea rows={7} value={participation} onChange={(e) => setParticipation(e.target.value)} placeholder="I would be comfortable helping by…" />
      {error && <p className="af-error">{error}</p>}
      <button className="af-primary af-primary-wide" disabled={busy || !participation.trim()} onClick={submit}>{busy ? "SAVING…" : "SUBMIT MY CONTRIBUTION"}</button>
    </section>
  </Shell>;
}

function StrategyView({ strategy }) {
  if (!strategy) return null;
  const sections = [
    ["Funding Audiences", strategy.funding_audiences],
    ["Where To Find Them", strategy.where_to_find],
    ["How To Attract Them", strategy.attraction],
    ["What To Ask", strategy.ask],
    ["Fundraising Process", strategy.fundraising_process],
    ["The System That Drives The Strategy", strategy.operating_system],
    ["How People Will Participate", strategy.participation],
    ["First 30 Days", strategy.first_30_days],
  ];
  return <section className="af-final-strategy">
    <div className="af-kicker">YOUR FINAL FUNDRAISING STRATEGY</div>
    <h1>{strategy.title}</h1>
    <p className="af-final-summary">{strategy.executive_summary}</p>
    {sections.map(([title, items]) => Array.isArray(items) && items.length > 0 ? <article key={title}><h2>{title}</h2><ul>{items.map((item, i) => <li key={i}>{typeof item === "string" ? item : JSON.stringify(item)}</li>)}</ul></article> : null)}
  </section>;
}

export function AutoFundraiserMeetingPage() {
  const { token } = useParams();
  const [state, setState] = useState(null);
  const [adopted, setAdopted] = useState({});
  const [notes, setNotes] = useState("");
  const [finalStrategy, setFinalStrategy] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    document.title = "Group Fundraising Planning | Auto Fundraiser";
    axios.get(`${API}/meeting/${token}`).then(({ data }) => {
      setState(data); setAdopted(data.adopted || {}); setFinalStrategy(data.final_strategy || null);
    }).catch((err) => setError(err.response?.data?.detail || "We could not open the group planning meeting."));
  }, [token]);

  const ideasFor = (key) => {
    const ideas = [];
    const organizer = state?.strategy_answers?.[key];
    if (organizer) ideas.push({ source: "Organizer", text: organizer });
    (state?.contributors || []).forEach((person) => {
      const text = person.answers?.[key];
      if (text) ideas.push({ source: person.name, text });
    });
    return ideas;
  };

  const toggle = (key, text) => {
    const current = adopted[key] || [];
    setAdopted({ ...adopted, [key]: current.includes(text) ? current.filter((x) => x !== text) : [...current, text] });
  };

  const canBuild = STRATEGY_QUESTIONS.every((q) => (adopted[q.key] || []).length > 0);

  const build = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await axios.post(`${API}/meeting/${token}/adopt`, { adopted, meeting_notes: notes });
      setFinalStrategy(data.final_strategy); window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) { setError(err.response?.data?.detail || "We could not build the final strategy."); }
    finally { setBusy(false); }
  };

  if (!state && !error) return <Shell><Spinner label="Preparing your group fundraising meeting…" /></Shell>;
  if (error && !state) return <Shell narrow><div className="af-message-card"><h1>We couldn't open this planning meeting.</h1><p>{error}</p></div></Shell>;
  if (finalStrategy) return <Shell><StrategyView strategy={finalStrategy} /></Shell>;

  return <Shell>
    <section className="af-meeting-hero"><div className="af-kicker">GROUP FUNDRAISING PLANNING</div><h1>Review the ideas. Choose what belongs in {state.organization_name}'s strategy.</h1><p>Everyone thought independently first. Now use the meeting to decide what the organization will actually adopt.</p></section>
    <div className="af-reality-summary">
      <span>YOUR PRESENT FUNDRAISING REALITY</span>
      <p>Keep what already works in mind as you make decisions. The final strategy will also use the present reality you documented before inviting contributors.</p>
    </div>
    {STRATEGY_QUESTIONS.map((q, index) => <section key={q.key} className="af-review-section">
      <div className="af-review-heading"><span>{String(index + 1).padStart(2, "0")}</span><div><h2>{q.title}</h2><p>Select one or more ideas the group agrees should become part of the strategy.</p></div></div>
      <div className="af-idea-grid">
        {ideasFor(q.key).map((idea, i) => {
          const selected = (adopted[q.key] || []).includes(idea.text);
          return <button key={i} className={`af-idea-card ${selected ? "selected" : ""}`} onClick={() => toggle(q.key, idea.text)}>
            <div className="af-idea-source">{idea.source}</div><p>{idea.text}</p><span>{selected ? "✓ ADOPTED" : "SELECT THIS IDEA"}</span>
          </button>;
        })}
      </div>
    </section>)}
    <section className="af-participation-review">
      <h2>Participation commitments</h2>
      <div className="af-commitments"><div><strong>Organizer</strong><p>{state.participation}</p></div>{state.contributors.map((person) => <div key={person.token}><strong>{person.name}</strong><p>{person.participation}</p></div>)}</div>
    </section>
    <section className="af-work-card">
      <h2>Anything else the group decided?</h2>
      <p>Capture decisions, constraints or context that should shape the final strategy.</p>
      <textarea rows={5} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Meeting decisions or additional context…" />
    </section>
    {error && <p className="af-error">{error}</p>}
    <div className="af-build-final"><button className="af-primary af-primary-wide" disabled={busy || !canBuild} onClick={build}>{busy ? "BUILDING YOUR STRATEGY…" : "BUILD OUR FINAL FUNDRAISING STRATEGY"} <span>→</span></button>{!canBuild && <p>Select at least one idea under each of the five questions.</p>}</div>
  </Shell>;
}
