import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { QUESTIONS as RECRUITMENT_QUESTIONS } from "@/member/RecruitmentGameIntake";
import { RECOMMITMENT, STRATEGIC } from "@/funnels/GuidedPrepaymentQuestionsPage";
import { FIVE_QUESTIONS, fiveQuestionText } from "@/game/gameFiveQuestions";
import SpeakButton from "@/game/SpeakButton";
import { errorMessage, readSessionValue, saveDraftAccess, v2Api } from "./api";
import V2Shell, { AssistanceLink, ErrorNotice, Loading } from "./V2Shell";
import { PRODUCTS, SELF_SERVICE_PRICE } from "./content";

const blankProgram = () => ({ name: "", description: "", present_work: "" });
export const intakeQuestions = (product) => product === "recruit" ? RECRUITMENT_QUESTIONS
  : product === "strategic-planning" ? STRATEGIC : product === "board-recommitment" ? RECOMMITMENT
  : FIVE_QUESTIONS.map((q, i) => ({ key: String(i + 1), prompt: q.title, help: q.hint, title: `Your fundraising thinking, question ${i + 1}` }));
const expandSteps = (product, answers) => intakeQuestions(product).flatMap((q) => q.type === "programs"
  ? (answers.program_details || [blankProgram()]).map((_, programIndex) => ({ ...q, programIndex })) : [q]);
const validAnswer = (question, answers) => question?.type === "programs"
  ? Boolean(answers.program_details?.[question.programIndex]?.name?.trim())
  : Boolean(String(answers[question?.key] || "").trim());

export function ProductIndexPage() {
  return <V2Shell title="Choose your board process"><section className="v2-intro"><p className="v2-eyebrow">NONPROFIT BOARD BUILDER</p><h1>Practical tools for the work your board needs to do.</h1><p>Choose the process you need. Learn how it works, share your starting information and decide whether the self-service tools are right for your organization.</p></section><div className="v2-product-grid">{Object.entries(PRODUCTS).map(([slug, product]) => <article className="v2-card" key={slug}><h2>{product.name}</h2><p>{product.outcome}</p><Link className="v2-button" to={`/v2/${slug}`}>Learn the process<ArrowRight size={17} /></Link></article>)}</div></V2Shell>;
}

export function ProductLandingPage() {
  const { product } = useParams();
  const content = PRODUCTS[product];
  if (!content) return <NotFoundPage />;
  const start = `/v2/${product}/start`;
  return <V2Shell title={content.name}>
    <section className="v2-hero"><div className="v2-hero-copy"><p className="v2-eyebrow">{content.eyebrow}</p><h1>{content.headline}</h1><p>{content.intro}</p><Link className="v2-button" to={start}>Start for Free<ArrowRight size={18} aria-hidden="true" /></Link><span className="v2-hero-note">Learn the process and share your starting information before you decide to purchase.</span></div><img className="v2-product-image" src={content.image} alt={`${content.name} from Nonprofit Board Builder`} /></section>
    <section className="v2-education" aria-labelledby="v2-process"><p className="v2-eyebrow">HOW TO CARRY OUT THE PROCESS</p><h2 id="v2-process">What you and your organization will do</h2><ol className="v2-steps">{content.teaching.map(([heading, paragraph], index) => <li key={heading}><span className="v2-step-number" aria-hidden="true">{index + 1}</span><div><h3>{heading}</h3><p>{paragraph}</p></div></li>)}</ol><Link className="v2-button" to={start}>Start for Free<ArrowRight size={18} aria-hidden="true" /></Link></section>
    <section className="v2-service-explanation"><h2>Get the tools and carry out the work yourself.</h2><p>{content.outcome}</p><p>You can follow this process without necessarily spending thousands of dollars on consultants. The self-service service costs ${SELF_SERVICE_PRICE} for this product. If you want us to work with you or provide more direct help, book a conversation and we will discuss a separate quotation.</p></section>
    <TestimonialCarousel heading="What Nonprofit Leaders We Have Worked With Are Saying" idPrefix={`v2-${product}`} />
    <section className="v2-closing"><h2>Start with what you know about your organization.</h2><p>The free questions help us understand your situation. You will then see exactly what happens next and what your purchase includes.</p><Link className="v2-button" to={start}>Start for Free<ArrowRight size={18} aria-hidden="true" /></Link></section>
  </V2Shell>;
}

export function FreeIntakePage() {
  const { product } = useParams();
  const content = PRODUCTS[product];
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const journeyId = params.get("journey") || params.get("journey_id") || "";
  const [journey, setJourney] = useState(null);
  const [answers, setAnswers] = useState({});
  const [index, setIndex] = useState(0);
  const [lead, setLead] = useState({ name: "", email: "", organization: "", desired_count: "not_sure", board_count: "", goal_amount: "" });
  const [loading, setLoading] = useState(Boolean(journeyId));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saveState, setSaveState] = useState("");
  const ready = useRef(false);
  const chain = useRef(Promise.resolve());
  const steps = useMemo(() => content ? expandSteps(product, answers) : [], [product, answers, content]);
  const persist = useCallback((current) => {
    const request = chain.current.catch(() => {}).then(() => v2Api.put(`/journeys/${journeyId}/answers`, { answers: current }));
    chain.current = request;
    return request;
  }, [journeyId]);

  useEffect(() => {
    ready.current = false;
    if (!journeyId || !content) { setJourney(null); setLoading(false); return; }
    let active = true; setLoading(true); setError("");
    v2Api.get(`/journeys/${journeyId}`).then(({ data }) => {
      if (data.product !== product) throw new Error("Please use the link for the product you started.");
      if (!active) return;
      if (data.state === "paid") { navigate(data.setup_complete ? `/v2/resources/${journeyId}` : `/v2/setup/${journeyId}`, { replace: true }); return; }
      const restored = product === "strategic-planning"
        ? { ...data.answers, program_details: data.answers?.program_details?.length ? data.answers.program_details : [blankProgram()] }
        : data.answers || {};
      setJourney(data); setAnswers(restored);
      const sequence = expandSteps(product, restored);
      const missing = sequence.findIndex((q) => !validAnswer(q, restored));
      setIndex(missing < 0 ? sequence.length - 1 : missing);
      ready.current = true;
    }).catch((err) => { if (active) setError(errorMessage(err, err.message || "We could not open your saved questions.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [journeyId, product, content, navigate]);

  useEffect(() => {
    if (!ready.current || !journey) return undefined;
    setSaveState("Your changes will be saved.");
    const timer = setTimeout(() => {
      setSaveState("Saving your answers…");
      persist(answers).then(() => setSaveState("Your answers are saved.")).catch(() => setSaveState("Your latest changes could not be saved. Select Save and continue to retry."));
    }, 900);
    return () => clearTimeout(timer);
  }, [answers, journey, persist]);

  if (!content) return <NotFoundPage />;
  const start = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const payload = { product, name: lead.name.trim(), email: lead.email.trim(), organization: lead.organization.trim() };
      if (product === "recruit") payload.desired_count = lead.desired_count;
      else if (product === "board-fundraising-game") payload.goal_amount = Number(lead.goal_amount);
      else payload.board_count = Number(lead.board_count);
      const { data } = await v2Api.post("/journeys", payload);
      saveDraftAccess(data.journey_id, data.draft_token, product);
      navigate(`/v2/${product}/start?journey=${encodeURIComponent(data.journey_id)}`);
    } catch (err) { setError(errorMessage(err, "We could not save your details. Please check them and try again.")); }
    finally { setBusy(false); }
  };
  const continueQuestion = async () => {
    const question = steps[index];
    if (!validAnswer(question, answers)) { setError(question.type === "programs" ? "Give this program a name before continuing." : "Share your answer before continuing."); return; }
    setBusy(true); setError("");
    try {
      const { data } = await persist(answers); setSaveState("Your answers are saved.");
      if (index === steps.length - 1) {
        if (!data.complete) { setError("Please complete the remaining questions before continuing."); const missing = steps.findIndex((q) => !validAnswer(q, answers)); if (missing >= 0) setIndex(missing); return; }
        navigate(`/v2/${product}/offer?journey=${encodeURIComponent(journeyId)}`);
      } else { setIndex(index + 1); window.scrollTo({ top: 0, behavior: "smooth" }); }
    } catch (err) { setError(errorMessage(err, "We could not save this answer. Please try again.")); }
    finally { setBusy(false); }
  };
  const current = steps[index];
  const value = current?.type === "programs" ? answers.program_details?.[current.programIndex] || blankProgram() : answers[current?.key] || "";
  const updateProgram = (key, text) => setAnswers((previous) => ({ ...previous, program_details: previous.program_details.map((p, i) => i === current.programIndex ? { ...p, [key]: text } : p) }));
  const savedJourney = readSessionValue(`nbb:v2:current:${product}`);
  return <V2Shell title={`Your ${content.name} questions`} narrow>
    <Link className="v2-back-link" to={`/v2/${product}`}>Read about {content.name}</Link>
    {loading ? <Loading>Opening your saved questions…</Loading> : journeyId && !journey ? <><ErrorNotice error={error || "We could not open your questions."} /><Link className="v2-button" to="/v2/recover">Recover access</Link><p><Link to={`/v2/${product}/start`}>Start a new process</Link></p></> : !journey ? <form className="v2-card" onSubmit={start}>
      <p className="v2-eyebrow">START FOR FREE</p><h1>Tell us about your organization.</h1><p>Enter your details, then answer the {content.name.toLowerCase()} questions. Your answers are saved as you work, and you will see the next steps before deciding to pay.</p>
      <label>Your name<input required autoComplete="name" maxLength={160} value={lead.name} onChange={(e) => setLead({ ...lead, name: e.target.value })} /></label>
      <label>Email address<input required type="email" autoComplete="email" maxLength={254} value={lead.email} onChange={(e) => setLead({ ...lead, email: e.target.value })} /></label>
      <label>Organization name<input required autoComplete="organization" maxLength={200} value={lead.organization} onChange={(e) => setLead({ ...lead, organization: e.target.value })} /></label>
      {product === "recruit" ? <label>How many new Board Members do you want to recruit?<select value={lead.desired_count} onChange={(e) => setLead({ ...lead, desired_count: e.target.value })}><option value="not_sure">I'm not sure yet</option>{Array.from({ length: 50 }, (_, i) => <option key={i + 1} value={String(i + 1)}>{i + 1}</option>)}</select></label>
        : product === "board-fundraising-game" ? <label>Your fundraising goal in US dollars<input required type="number" min="1" step="1" inputMode="numeric" value={lead.goal_amount} onChange={(e) => setLead({ ...lead, goal_amount: e.target.value })} /></label>
        : <label>{product === "strategic-planning" ? "How many board members do you have?" : "How many board members do you need to recommit?"}<input required type="number" min="1" max="200" step="1" inputMode="numeric" value={lead.board_count} onChange={(e) => setLead({ ...lead, board_count: e.target.value })} /></label>}
      <ErrorNotice error={error} /><button className="v2-button" disabled={busy}>{busy ? "Saving your details…" : "Continue for Free"}<ArrowRight size={18} /></button>
      {savedJourney && <p><Link to={`/v2/${product}/start?journey=${encodeURIComponent(savedJourney)}`}>Continue my saved questions</Link></p>}
    </form> : <section className="v2-card v2-question"><p className="v2-eyebrow">{content.name} · QUESTION {index + 1} OF {steps.length}</p>
      <h1>{product === "board-fundraising-game" ? fiveQuestionText(index, answers["1"]) : current?.prompt || current?.question}</h1><p>{current?.help || current?.helper}</p>
      {current?.type === "programs" ? <><p className="v2-eyebrow">PROGRAM {current.programIndex + 1}</p><label>Program name<input required value={value.name} placeholder="What do you call this program?" onChange={(e) => updateProgram("name", e.target.value)} /></label><label>What does this program or service do?<textarea rows={4} maxLength={12000} value={value.description} onChange={(e) => updateProgram("description", e.target.value)} /></label><SpeakButton value={value.description} onChange={(text) => updateProgram("description", text)} /><label>What is happening with it today?<textarea rows={4} maxLength={12000} value={value.present_work} onChange={(e) => updateProgram("present_work", e.target.value)} /></label><SpeakButton value={value.present_work} onChange={(text) => updateProgram("present_work", text)} /><div className="v2-actions"><button type="button" className="v2-button v2-button-secondary" disabled={busy || !value.name.trim()} onClick={() => { setAnswers((old) => ({ ...old, program_details: [...old.program_details.slice(0, current.programIndex + 1), blankProgram(), ...old.program_details.slice(current.programIndex + 1)] })); setIndex(index + 1); }}>Add another program</button>{answers.program_details.length > 1 && <button type="button" className="v2-text-button" disabled={busy} onClick={() => { setAnswers((old) => ({ ...old, program_details: old.program_details.filter((_, i) => i !== current.programIndex) })); setIndex(Math.max(0, index - 1)); }}>Remove this program</button>}</div></>
        : current?.type === "date" ? <label>Your deadline<input type="date" value={value} onChange={(e) => setAnswers({ ...answers, [current.key]: e.target.value })} /></label>
        : <><label htmlFor="v2-intake-answer">Your answer</label><textarea id="v2-intake-answer" rows={7} maxLength={12000} value={value} placeholder="Share your answer in your own words." onChange={(e) => setAnswers({ ...answers, [current.key]: e.target.value })} /><SpeakButton value={value} onChange={(text) => setAnswers((old) => ({ ...old, [current.key]: text }))} /></>}
      <ErrorNotice error={error} /><p className="v2-save-status" role="status">{saveState}</p><div className="v2-actions">{index > 0 && <button type="button" className="v2-button v2-button-secondary" disabled={busy} onClick={() => setIndex(index - 1)}>Back</button>}<button type="button" className="v2-button" disabled={busy || !validAnswer(current, answers)} onClick={continueQuestion}>{busy ? "Saving…" : index === steps.length - 1 ? "Save and see what happens next" : "Save and continue"}<ArrowRight size={17} /></button></div>
    </section>}
  </V2Shell>;
}

export function OfferPage() {
  const { product } = useParams(); const content = PRODUCTS[product];
  const [params] = useSearchParams(); const journeyId = params.get("journey") || params.get("journey_id") || "";
  const [journey, setJourney] = useState(null); const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const navigate = useNavigate();
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    if (!journeyId) { setError("Please open this page from your saved introductory questions."); setLoading(false); return undefined; }
    v2Api.get(`/journeys/${journeyId}`).then(({ data }) => {
      if (data.product !== product) throw new Error("This link belongs to a different product.");
      if (!active) return;
      if (data.state === "paid") { navigate(data.setup_complete ? `/v2/resources/${journeyId}` : `/v2/setup/${journeyId}`, { replace: true }); return; }
      setJourney(data);
    }).catch((problem) => { if (active) setError(errorMessage(problem, problem.message)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [journeyId, product, navigate]);
  const buy = async () => {
    if (busy) return; setBusy(true); setError("");
    try {
      const { data } = await v2Api.post(`/journeys/${journeyId}/checkout`);
      if (!data.checkout_url) throw new Error("Checkout is not available yet. Please try again.");
      window.location.assign(data.checkout_url);
    } catch (problem) { setError(errorMessage(problem, problem.message)); }
    finally { setBusy(false); }
  };
  if (!content) return <NotFoundPage />;
  const source = journey?.answers || {};
  const contextKey = product === "recruit" ? "support_needs" : product === "strategic-planning" ? "goals" : product === "board-recommitment" ? "why_recommit" : "1";
  return <V2Shell title={`Your ${content.name} next steps`}>
    {loading ? <Loading>Opening your next steps…</Loading> : !journey ? <section className="v2-card"><ErrorNotice error={error} /><Link className="v2-button" to={`/v2/${product}/start`}>Open the free questions</Link></section> : <>
      <section className="v2-intro"><p className="v2-eyebrow">YOUR INTRODUCTORY ANSWERS ARE SAVED</p><h1>{content.offerHeading}</h1><p>{journey.name}, you've shared the starting information for {journey.organization}. Read the steps below and choose the support you want.</p></section>
      <div className="v2-offer-context"><h2>Building from what you told us</h2>{source.mission && <><h3>Your mission</h3><blockquote>{source.mission}</blockquote></>}{source[contextKey] && <><h3>What you want to work on</h3><blockquote>{source[contextKey]}</blockquote></>}<Link to={`/v2/${product}/start?journey=${encodeURIComponent(journeyId)}`}>Review or change your introductory answers</Link></div>
      <section className="v2-education v2-next-steps"><h2>What happens next</h2>{content.next.map(([heading, paragraph]) => <article key={heading}><h3>{heading}</h3><p>{paragraph}</p></article>)}</section>
      <section className="v2-purchase-options" aria-label="Your two options"><article className="v2-purchase-card v2-purchase-primary"><p className="v2-eyebrow">SELF-GUIDED</p><h2>Get Everything I Need and Guide the Process Myself</h2><p className="v2-price">${SELF_SERVICE_PRICE}<span>One purchase for {content.name}</span></p><p>{content.outcome}</p><p>After payment, confirm your organization details and begin the guided process. Your approved resources will remain available in a secure collection.</p><button type="button" className="v2-button" disabled={busy} onClick={buy}>{busy ? "Opening secure checkout…" : `Get my ${content.name} tools for $${SELF_SERVICE_PRICE}`}</button></article><article className="v2-purchase-card"><p className="v2-eyebrow">PROFESSIONAL ASSISTANCE</p><h2>Let Us Work With You or Do It for You</h2><p>Book a conversation to explain where you want help. We will discuss the support your organization needs and a separate quotation.</p><AssistanceLink /></article></section><ErrorNotice error={error} />
      <p className="v2-email-reminder">We will email you when someone responds and when your approved collection is ready. Add our sending address to your contacts and mark important emails as favorites.</p>
    </>}
  </V2Shell>;
}

export function PaymentPage() {
  const { product } = useParams(); const [params] = useSearchParams(); const navigate = useNavigate();
  const journeyId = params.get("journey") || params.get("journey_id") || ""; const sessionId = params.get("session_id") || "";
  const [state, setState] = useState("checking"); const [error, setError] = useState(""); const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!journeyId || !sessionId) { setState("missing"); return undefined; }
    let active = true; let timer; let tries = 0; setState("checking"); setError("");
    const check = async () => {
      tries += 1;
      try {
        const { data } = await v2Api.get(`/journeys/${journeyId}/payment`, { params: { session_id: sessionId } });
        if (!active) return;
        if (data.payment_status === "paid" && data.state === "paid") { navigate(`/v2/setup/${data.journey_id || journeyId}`, { replace: true }); return; }
        if (["failed", "expired", "cancelled"].includes(data.payment_status)) { setState("failed"); return; }
      } catch (err) { if (!active) return; if ([401, 403, 404].includes(err.response?.status)) { setError(errorMessage(err)); setState("failed"); return; } }
      if (tries < 10) timer = setTimeout(check, 2000); else if (active) setState("waiting");
    };
    check(); return () => { active = false; clearTimeout(timer); };
  }, [journeyId, sessionId, navigate, retry]);
  return <V2Shell title="Confirming your purchase" narrow><section className="v2-card"><CheckCircle2 size={40} className="v2-confirm-icon" aria-hidden="true" /><h1>{state === "checking" ? "Confirming your payment" : "Your payment confirmation"}</h1>{state === "checking" ? <Loading>Please keep this page open while we verify your payment and prepare your resources.</Loading> : <><p>{state === "waiting" ? "Your payment is still being confirmed. Your resources become available after the payment provider confirms the purchase. We will email your secure access link when they are ready." : state === "missing" ? "This page needs the secure return link from your checkout. Recover your resources if you have already paid." : "We could not confirm a successful purchase from this checkout link."}</p><ErrorNotice error={error} /><div className="v2-actions">{state === "waiting" && <button className="v2-button" onClick={() => setRetry((n) => n + 1)}>Check confirmation again</button>}<Link className="v2-button v2-button-secondary" to="/v2/recover">Recover my resources</Link></div>{PRODUCTS[product] && journeyId && <p><Link to={`/v2/${product}/offer?journey=${encodeURIComponent(journeyId)}`}>Return to your product explanation</Link></p>}</>}</section></V2Shell>;
}

export function RecoveryPage() {
  const [email, setEmail] = useState(""); const [busy, setBusy] = useState(false); const [sent, setSent] = useState(false); const [error, setError] = useState("");
  const recover = async (event) => { event.preventDefault(); setBusy(true); setError(""); try { await v2Api.post("/recover", { email: email.trim() }); setSent(true); } catch (err) { setError(errorMessage(err, "We could not request your access email. Please try again.")); } finally { setBusy(false); } };
  return <V2Shell title="Recover your resources" narrow><section className="v2-card"><p className="v2-eyebrow">SECURE RESOURCE ACCESS</p><h1>Find your purchased resources.</h1>{sent ? <p role="status">If this email address has saved Board Builder V2 resources, we will send the appropriate secure links. Please check your inbox and spam folder. Add our sending address to your contacts and mark the message as a favorite.</p> : <><p>Enter the email address you used for your purchase. We will send secure links so you can return directly to your resources.</p><form onSubmit={recover}><label>Email address<input type="email" required autoComplete="email" maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} /></label><ErrorNotice error={error} /><button className="v2-button" disabled={busy}>{busy ? "Requesting your email…" : "Send my secure access links"}</button></form></>}</section></V2Shell>;
}

export function MarketplacePage() {
  const [opportunities, setOpportunities] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { let active = true; v2Api.get("/marketplace").then(({ data }) => { if (active) setOpportunities(data.opportunities || []); }).catch((err) => { if (active) setError(errorMessage(err)); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, []);
  return <V2Shell title="Board Applicant Marketplace"><section className="v2-intro"><p className="v2-eyebrow">BOARD APPLICANT MARKETPLACE</p><h1>Find an opportunity to serve on a board</h1><p>Review the organization's approved board opportunity and use its application link to express your interest.</p></section>{loading ? <Loading /> : error ? <ErrorNotice error={error} /> : !opportunities.length ? <p>No active opportunities have been published yet.</p> : <div className="v2-product-grid">{opportunities.map((item) => <article key={item.slug} className="v2-card">{item.branding?.logo_data && <img className="v2-marketplace-logo" src={item.branding.logo_data} alt={`${item.organization_name} logo`} />}<h2>{item.organization_name}</h2><p className="v2-preserve-text">{item.summary}</p>{item.application_path?.startsWith("/v2/forms/") && <Link className="v2-button" to={item.application_path}>Review the opportunity and apply<ArrowRight size={17} /></Link>}</article>)}</div>}</V2Shell>;
}

export function NotFoundPage() {
  return <V2Shell title="Page unavailable" narrow><section className="v2-card"><h1>We could not find this page.</h1><p>Use the secure link from your email or recover your purchased resources.</p><Link className="v2-button" to="/v2/recover">Recover my resources</Link><p><Link to="/v2">Explore the board processes</Link></p></section></V2Shell>;
}
