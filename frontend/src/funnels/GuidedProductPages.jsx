import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { ArrowRight, CheckCircle2, Map, RefreshCw, Video } from "lucide-react";
import { BfgShell } from "@/game/gameShared";
import { memberApi, storeMemberToken } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import "@/game/game.css";
import BoardRecommitmentDashboard from "@/member/BoardRecommitmentDashboard";
import StrategicPlanningDashboard from "@/funnels/StrategicPlanningDashboard";
import "./guided-products.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;
const CONFIG={
  "strategic-planning":{
    eyebrow:"STRATEGIC PLANNING WITH YOUR BOARD", icon:Map,
    headline:"Have Your Strategic Plan Reviewed And Adopted By Your Next Board Meeting.",
    sub:"Build the roadmap with your board, create real ownership and begin delegating leadership responsibility for building the organization your mission needs.",
    promise:"Your responsibility, and your board's responsibility, is to create the roadmap and build the team that does the job. Strategic planning is how you create the roadmap.",
    formTitle:"See The Exact Step-By-Step Process",
    formText:"Enter your details and we will show you the exact process to build or review your next strategic plan with your board and get board members working with you to build the structures your organization needs.",
    videoTitle:"See How To Build And Adopt Your Strategic Plan With Your Board",
    videoSub:"Press Play And Watch The Short Video",
    payTitle:"Build The Roadmap. Give Your Board Ownership. Start Delegating Leadership.",
    onboardingTitle:"Welcome To Strategic Planning With Your Board",
    intakeTitle:"Tell Us Where Your Organization Is Going",
    dashboardTitle:"Your Strategic Planning Dashboard",
    steps:[
      ["1","Every Board Member Contributes","Each board member completes the strategic planning form individually, giving you perspectives from across the board."],
      ["2","Your First Draft Is Built","Everyone's ideas are combined into the first strategic planning draft for the organization."],
      ["3","Board Members Take Ownership","At the board meeting, members choose areas they can help lead and build a deeper plan for that part of the organization."],
      ["4","Each Leader Builds Their Area","Their plan defines what must be done, the people and technology needed, their leadership role and the full cost of executing that area over the planning period."],
      ["5","The Board Reviews And Adopts","Board members present their plans, improve them together and adopt the completed areas as the organization's strategic plan."],
      ["6","Move From Plan To Structure","The leader works with each board member to build the team, materials and operating structure until the board can step back into oversight."],
    ],
    outcomes:["A board-built strategic roadmap","Clear ownership across major organizational areas","Board members leading deeper planning in the areas they can support","A costed plan showing what 100% execution requires","A pathway from founder-led work to delegated structures and board oversight"],
    intakeFields:[
      ["mission","What is your organization's mission statement?","textarea"],
      ["goals","What are your organization's present goals for the next 12–24 months?","textarea"],
      ["objectives","What objectives are you presently working toward under those goals?","textarea"],
      ["programs","List your present programs or services, one per line.","textarea"],
      ["team_building","What team, staff, volunteer or leadership capacity are you currently trying to build?","textarea"],
      ["operations","What operational systems or processes are most important to how the organization works today?","textarea"],
      ["marketing","How are you presently marketing the organization and building visibility?","textarea"],
      ["partnerships","What partnerships do you currently have or need to strengthen?","textarea"],
      ["fundraising","How are you presently raising money, and what needs to improve?","textarea"],
      ["technology","What technology or tools does the organization currently use or need?","textarea"],
      ["budget","What is the organization's present budget or best current understanding of the cost of operating and growing?","textarea"],
      ["priorities","What are the organization's most important priorities right now?","textarea"],
      ["action_planning","What major actions are already planned or underway?","textarea"],
      ["next_meeting","When is your next board meeting?","text"],
    ],
  },
  "board-recommitment":{
    eyebrow:"BOARD RECOMMITMENT", icon:RefreshCw,
    headline:"Your Next Board Meeting Can Be The Meeting Where Passive Board Members Step Up Or Step Down Gracefully.",
    sub:"Give disengaged or inactive board members a structured opportunity to recommit, clarify how they can contribute and have the one-on-one conversation needed to move forward.",
    promise:"Stop guessing who is still committed. Give every board member the opportunity to tell you where they stand, then have the right conversation from there.",
    formTitle:"Start Your Board Recommitment Process",
    formText:"Tell us who you are and how many board members you need to recommit. We will show you the guided process for getting clear answers and moving each person forward.",
    videoTitle:"See How To Recommit Your Board Members",
    videoSub:"Press Play And Watch The Short Video",
    payTitle:"Get Clear Answers. Have The Right Conversation. Rebuild An Active Board.",
    onboardingTitle:"Welcome To Your Board Recommitment Process",
    intakeTitle:"Tell Us About The Board You Need To Recommit",
    dashboardTitle:"Your Board Recommitment Dashboard",
    steps:[
      ["1","Send The Recommitment Form","Use the email and form we provide to invite each disengaged, inactive or passive board member to respond."],
      ["2","Let Them Tell You The Truth","They explain why they disengaged, whether they are ready to recommit, how they can contribute satisfactorily or whether they want to step down."],
      ["3","Understand Their Response","We help you interpret what each response means for the organization and the conversation you need to have next."],
      ["4","Have The One-On-One Conversation","Use the conversation script we provide to help each board member recommit with clarity or step down gracefully."],
      ["5","Move Forward With Clarity","You leave knowing who is ready to serve actively, what they can take responsibility for and where a transition is needed."],
    ],
    outcomes:["Board Recommitment Form","Ready-to-send board member email","Clear interpretation of each response","Personalized one-on-one conversation script","A practical pathway for recommitment or graceful transition"],
    intakeFields:[
      ["mission","What is your organization's mission statement?","textarea"],
      ["goals","What is your organization trying to accomplish or grow into right now?","textarea"],
    ],
  }
};
const useProduct=(explicitProduct)=>{const p=explicitProduct; if(!CONFIG[p]) throw new Error("Guided product route is not bound to a valid flow"); return [p,CONFIG[p]]};
const usePaidFlow=(sessionId,product)=>{const [allowed,setAllowed]=useState(null);useEffect(()=>{if(!sessionId){setAllowed(false);return}axios.get(`${API}/payments/flow-status/${sessionId}`,{params:{flow:product}}).then(r=>setAllowed(r.data.payment_status==="paid")).catch(()=>setAllowed(false))},[sessionId,product]);return allowed};

export function GuidedLandingPage({ product: explicitProduct }){
 const [product,c]=useProduct(explicitProduct);const Icon=c.icon;const nav=useNavigate();const [form,setForm]=useState({name:"",email:"",organization:"",board_count:""});const [busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{document.title=`${c.eyebrow} | Nonprofit Board Builder`},[c]);
 const start=async()=>{if(!form.name||!form.email||!form.organization||!form.board_count){setError("Complete your name, email, organization and number of board members.");return}setBusy(true);setError("");try{const auth=await memberApi.post("/members/guided-free-start",{name:form.name,email:form.email});if(auth.data.token)storeMemberToken(auth.data.token);let r=await axios.post(`${API}/guided/lead`,{product,...form,board_count:Number(form.board_count),origin_url:window.location.origin});nav(`/${product}/video?token=${r.data.token}`)}catch{setError("We could not start this process. Please check your details and try again.")}setBusy(false)};
 const scrollToForm=()=>document.getElementById(`${product}-lead-form`)?.scrollIntoView({behavior:"smooth",block:"start"});
 return <BfgShell><main className="guided-page">
  <section className="guided-hero"><span className="bfg-badge"><Icon size={15}/>{c.eyebrow}</span><h1>{c.headline}</h1><p>{c.sub}</p><button className="bfg-btn bfg-btn-primary guided-hero-cta" onClick={scrollToForm}>START MY PROCESS <ArrowRight size={17}/></button></section>
  <section className="guided-principle"><h2>{c.promise}</h2></section>
  <section id={`${product}-lead-form`} className="guided-lead-section"><div className="guided-form-card"><h2>{c.formTitle}</h2><p>{c.formText}</p><input placeholder="Your Name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><input type="email" placeholder="Email Address" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/><input placeholder="Organization Name" value={form.organization} onChange={e=>setForm({...form,organization:e.target.value})}/><input inputMode="numeric" placeholder={product==="strategic-planning"?"How many board members do you have?":"How many board members do you need to recommit?"} value={form.board_count} onChange={e=>setForm({...form,board_count:e.target.value.replace(/\D/g,"")})}/>{error&&<p className="bfg-error">{error}</p>}<button className="bfg-btn bfg-btn-primary guided-lead-submit" disabled={busy} onClick={start}>{busy?"OPENING…":"SHOW ME THE STEP-BY-STEP PROCESS"}</button></div></section>
  <section className="guided-section"><p className="bfg-eyebrow">THE PROCESS</p><h2>{product==="strategic-planning"?"Turn Your Next Board Meetings Into The Beginning Of Real Delegation.":"Give Every Board Member A Clear Choice About How They Move Forward."}</h2><div className="guided-steps">{c.steps.map(([n,t,x])=><article key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></section>
  <section className="guided-section guided-soft"><p className="bfg-eyebrow">WHAT YOU GET</p><h2>A Guided Process You Can Actually Use With Your Board.</h2><div className="guided-outcomes">{c.outcomes.map(x=><div key={x}>✓ {x}</div>)}</div></section>
  <TestimonialCarousel heading="What Nonprofit Leaders We Have Worked With Are Saying" idPrefix={product}/>
  <section className="guided-final-cta"><h2>{product==="strategic-planning"?"Ready To Build Your Strategic Plan With Your Board?":"Ready To Start Your Board Recommitment Process?"}</h2><button className="bfg-btn bfg-btn-primary guided-final-button" onClick={scrollToForm}>START MY PROCESS <ArrowRight size={17}/></button></section>
 </main></BfgShell>
}
export function GuidedVideoPage({ product: explicitProduct }){
 const [product,c]=useProduct(explicitProduct);const q=new URLSearchParams(useLocation().search);const token=q.get("token")||"";const [busy,setBusy]=useState(false),[error,setError]=useState(""),[validToken,setValidToken]=useState(false);
 useEffect(()=>{if(!token){setError("This link is missing its journey token.");return}axios.get(`${API}/guided/context/${token}`).then(r=>{if(r.data.product!==product)throw new Error("wrong flow");setValidToken(true)}).catch(()=>setError("This link belongs to a different product flow or is no longer valid."))},[token,product]);
 const buy=async()=>{setBusy(true);setError("");try{let r=await axios.post(`${API}/payments/guided-checkout`,{origin_url:window.location.origin,result_token:token,product});window.location.href=r.data.checkout_url}catch{setError("We could not open secure checkout. Please try again.");setBusy(false)}};
 return <BfgShell><main className="guided-page"><section className="guided-video-page"><p className="bfg-eyebrow">{c.eyebrow}</p><h1>{c.videoTitle}</h1><h2>{c.videoSub}</h2><div className="guided-video"><Video size={38}/><strong>Short walkthrough video</strong><span>Video URL can be added before launch.</span></div><div className="guided-pay-card"><h2>{c.payTitle}</h2><div className="guided-price">$497 <small>ONE TIME</small></div><p>You see the process step by step, use the forms, scripts and materials we provide, and get guided support throughout the process.</p><button className="bfg-btn bfg-btn-primary" disabled={busy||!validToken} onClick={buy}>{busy?"OPENING SECURE CHECKOUT…":product==="strategic-planning"?"START MY STRATEGIC PLANNING PROCESS — $497":"START MY BOARD RECOMMITMENT — $497"}</button>{error&&<p className="bfg-error">{error}</p>}</div></section></main></BfgShell>
}

export function GuidedPaymentConfirmedPage({ product: explicitProduct }){
 const [product]=useProduct(explicitProduct);const loc=useLocation();const nav=useNavigate();const sid=new URLSearchParams(loc.search).get("session_id")||"";const [state,setState]=useState("checking");
 useEffect(()=>{let n=0,t;const poll=async()=>{n++;try{let r=await axios.get(`${API}/payments/status/${sid}`);if(r.data.payment_status==="paid"){await axios.get(`${API}/payments/flow-status/${sid}`,{params:{flow:product}});setState("paid");axios.post(`${API}/guided/access-email`,{session_id:sid,product,origin_url:window.location.origin}).catch(()=>{});return}}catch{}if(n<8)t=setTimeout(poll,2200);else setState("waiting")};poll();return()=>clearTimeout(t)},[sid,product]);
 return <BfgShell><main className="guided-page"><section className="guided-confirm"><CheckCircle2 size={54}/><h1>{state==="paid"?"Payment Confirmed":"Confirming Your Payment…"}</h1><p>{state==="paid"?"Your guided process is ready.":"Please keep this page open while we confirm your payment."}</p>{state==="paid"&&<button className="bfg-btn bfg-btn-primary" onClick={()=>nav(`/${product}/welcome?session_id=${sid}`)}>CONTINUE</button>}</section></main></BfgShell>
}

export function GuidedWelcomePage({ product: explicitProduct }){
 const [product,c]=useProduct(explicitProduct);const sid=new URLSearchParams(useLocation().search).get("session_id")||"";const nav=useNavigate();
 const allowed=usePaidFlow(sid,product);
 if(allowed===null)return <BfgShell><main className="guided-page"><section className="guided-confirm"><p>Confirming your product access…</p></section></main></BfgShell>;
 if(!allowed)return <BfgShell><main className="guided-page"><section className="guided-confirm"><h1>This Link Does Not Belong To This Product Flow.</h1><button className="bfg-btn bfg-btn-primary" onClick={()=>nav(`/${product}`)}>RETURN TO THIS PRODUCT</button></section></main></BfgShell>;
 return <BfgShell><main className="guided-page"><section className="guided-video-page"><p className="bfg-eyebrow">WELCOME</p><h1>{c.onboardingTitle}</h1><p>Watch this short onboarding before opening your dashboard. Everything you need, beginning with information about your organization, is inside the dashboard.</p><div className="guided-video"><Video size={38}/><strong>Onboarding video</strong><span>Video URL can be added before launch.</span></div><button className="bfg-btn bfg-btn-primary" onClick={()=>nav(`/${product}/dashboard?session_id=${sid}`)}>GO TO MY DASHBOARD</button></section></main></BfgShell>
}

export function GuidedIntakePage({ product: explicitProduct }){
 const [product]=useProduct(explicitProduct);const sid=new URLSearchParams(useLocation().search).get("session_id")||"";
 return <Navigate replace to={`/${product}/dashboard?session_id=${encodeURIComponent(sid)}`}/>;
}

export function GuidedDashboardPage({ product: explicitProduct }){
 const [product,c]=useProduct(explicitProduct);const sid=new URLSearchParams(useLocation().search).get("session_id")||"";const nav=useNavigate();const {member,loading}=useMemberAuth();const allowed=usePaidFlow(sid,product);const [context,setContext]=useState(null);const [answers,setAnswers]=useState({});const [busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{if(!allowed||loading||!member)return;if(product==="board-recommitment"){memberApi.post("/guided/board-recommitment/initialize",{session_id:sid}).then(()=>memberApi.get("/guided/dashboard",{params:{session_id:sid,product}})).then(r=>{setContext(r.data);setAnswers(r.data.intake?.answers||{})}).catch(e=>{setError(e.response?.data?.detail||"We could not prepare your Board Recommitment dashboard.");setContext({intake:{answers:{}}})});return}memberApi.get("/guided/dashboard",{params:{session_id:sid,product}}).then(r=>{setContext(r.data);setAnswers(r.data.intake?.answers||{})}).catch(e=>setError(e.response?.data?.detail||"We could not open your Strategic Planning dashboard."))},[allowed,sid,product,loading,member]);
 if(allowed===null)return <BfgShell><main className="guided-page"><section className="guided-confirm"><p>Confirming your product access…</p></section></main></BfgShell>;
 if(!allowed)return <BfgShell><main className="guided-page"><section className="guided-confirm"><h1>This Link Does Not Belong To This Product Flow.</h1><button className="bfg-btn bfg-btn-primary" onClick={()=>nav(`/${product}`)}>RETURN TO THIS PRODUCT</button></section></main></BfgShell>;
 if(!loading&&!member)return <BfgShell><main className="guided-page"><section className="guided-confirm"><h1>Log In To Open {c.dashboardTitle}.</h1><p>Use the account email from your purchase. If you have not chosen a password yet, use the setup link in your access email or Forgot Password.</p><button className="bfg-btn bfg-btn-primary" onClick={()=>nav("/login?next="+encodeURIComponent(`/${product}/dashboard?session_id=${sid}`))}>LOG IN</button></section></main></BfgShell>;
 if(error&&!context)return <BfgShell><main className="guided-page"><section className="guided-confirm"><h1>We Could Not Open Your Dashboard.</h1><p className="bfg-error">{error}</p></section></main></BfgShell>;
 if(!context)return <BfgShell><main className="guided-page"><section className="guided-confirm"><p>Preparing your dashboard…</p></section></main></BfgShell>;
 if(!context.intake?.answers){const submit=async()=>{if(c.intakeFields.some(([k])=>!String(answers[k]||"").trim())){setError("Please answer each question so the complete process can use your organization information.");return}setBusy(true);try{const r=await memberApi.post("/guided/intake",{session_id:sid,product,answers});setContext({product,intake:{answers}});if(r.data.dashboard_url!==window.location.pathname+window.location.search)window.history.replaceState({},"",r.data.dashboard_url)}catch(e){setError(e.response?.data?.detail||"We could not save your organization information.")}setBusy(false)};return <BfgShell><main className="guided-page"><section className="guided-section" data-testid={`${product}-dashboard-intake`}><p className="bfg-eyebrow">DASHBOARD STEP 1</p><h1>Tell Us About Your Organization</h1><p className="guided-intro">This information becomes the foundation used by every section and every individual output that follows.</p><div className="guided-intake">{c.intakeFields.map(([k,label,type])=><label key={k}><span>{label}</span>{type==="textarea"?<textarea rows={5} value={answers[k]||""} onChange={e=>setAnswers({...answers,[k]:e.target.value})}/>:<input value={answers[k]||""} onChange={e=>setAnswers({...answers,[k]:e.target.value})}/>}</label>)}{error&&<p className="bfg-error">{error}</p>}<button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={submit}>{busy?"SAVING…":"SAVE AND BUILD MY DASHBOARD"}</button></div></section></main></BfgShell>}
 if(product==="board-recommitment") return <BoardRecommitmentDashboard/>;
 return <StrategicPlanningDashboard/>;
}
