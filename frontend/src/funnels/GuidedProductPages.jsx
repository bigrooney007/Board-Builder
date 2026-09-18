import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { ArrowRight, CheckCircle2, Map, RefreshCw, Video } from "lucide-react";
import { BfgShell } from "@/game/gameShared";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import "@/game/game.css";
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
      ["mission","What is your organization's mission?","textarea"],["direction","What must your organization accomplish over the next 12–24 months?","textarea"],
      ["areas","What major areas of the organization need stronger plans, structures or leadership?","textarea"],["current_plan","Do you already have a strategic plan? If yes, what needs to change?","textarea"],
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
      ["situation","What does disengagement currently look like on your board?","textarea"],["history","What do you believe caused board members to become passive or disengaged?","textarea"],
      ["attempts","What have you already tried to get them involved again?","textarea"],["responsibilities","What responsibilities do you need board members to step back into?","textarea"],
      ["next_meeting","When is your next board meeting?","text"],
    ],
  }
};
const useProduct=()=>{const p=window.location.pathname.startsWith("/strategic-planning")?"strategic-planning":"board-recommitment";return [p,CONFIG[p]]};

export function GuidedLandingPage(){
 const [product,c]=useProduct();const Icon=c.icon;const nav=useNavigate();const [form,setForm]=useState({name:"",email:"",organization:"",board_count:""});const [busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{document.title=`${c.eyebrow} | Nonprofit Board Builder`},[c]);
 const start=async()=>{if(!form.name||!form.email||!form.board_count){setError("Complete your name, email and number of board members.");return}setBusy(true);setError("");try{let r=await axios.post(`${API}/guided/lead`,{product,...form,board_count:Number(form.board_count)});nav(`/${product}/video?token=${r.data.token}`)}catch{setError("We could not start this process. Please check your details and try again.")}setBusy(false)};
 return <BfgShell><main className="guided-page">
  <section className="guided-hero"><span className="bfg-badge"><Icon size={15}/>{c.eyebrow}</span><h1>{c.headline}</h1><p>{c.sub}</p><a className="bfg-btn bfg-btn-primary" href="#guided-start">SHOW ME THE PROCESS <ArrowRight size={17}/></a></section>
  <section className="guided-principle"><h2>{c.promise}</h2></section>
  <section className="guided-section"><p className="bfg-eyebrow">THE PROCESS</p><h2>{product==="strategic-planning"?"Turn Your Next Board Meetings Into The Beginning Of Real Delegation.":"Give Every Board Member A Clear Choice About How They Move Forward."}</h2><div className="guided-steps">{c.steps.map(([n,t,x])=><article key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p></article>)}</div></section>
  <section className="guided-section guided-soft"><p className="bfg-eyebrow">WHAT YOU GET</p><h2>A Guided Process You Can Actually Use With Your Board.</h2><div className="guided-outcomes">{c.outcomes.map(x=><div key={x}>✓ {x}</div>)}</div></section>
  <TestimonialCarousel heading="What Nonprofit Leaders We Have Worked With Are Saying" idPrefix={product}/>
  <section id="guided-start" className="guided-section"><div className="guided-form-card"><h2>{c.formTitle}</h2><p>{c.formText}</p><input placeholder="Your Name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><input type="email" placeholder="Email Address" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/><input placeholder="Organization Name" value={form.organization} onChange={e=>setForm({...form,organization:e.target.value})}/><input inputMode="numeric" placeholder={product==="strategic-planning"?"How many board members do you have?":"How many board members do you need to recommit?"} value={form.board_count} onChange={e=>setForm({...form,board_count:e.target.value.replace(/\D/g,"")})}/>{error&&<p className="bfg-error">{error}</p>}<button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={start}>{busy?"Opening…":"SHOW ME THE STEP-BY-STEP PROCESS"}</button></div></section>
 </main></BfgShell>
}

export function GuidedVideoPage(){
 const [product,c]=useProduct();const q=new URLSearchParams(useLocation().search);const token=q.get("token")||"";const [busy,setBusy]=useState(false),[error,setError]=useState("");
 const buy=async()=>{setBusy(true);setError("");try{let r=await axios.post(`${API}/payments/guided-checkout`,{origin_url:window.location.origin,result_token:token,product});window.location.href=r.data.checkout_url}catch{setError("We could not open secure checkout. Please try again.");setBusy(false)}};
 return <BfgShell><main className="guided-page"><section className="guided-video-page"><p className="bfg-eyebrow">{c.eyebrow}</p><h1>{c.videoTitle}</h1><h2>{c.videoSub}</h2><div className="guided-video"><Video size={38}/><strong>Short walkthrough video</strong><span>Video URL can be added before launch.</span></div><div className="guided-pay-card"><h2>{c.payTitle}</h2><div className="guided-price">$497 <small>ONE TIME</small></div><p>You see the process step by step, use the forms, scripts and materials we provide, and get guided support throughout the process.</p><button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={buy}>{busy?"OPENING SECURE CHECKOUT…":product==="strategic-planning"?"START MY STRATEGIC PLANNING PROCESS — $497":"START MY BOARD RECOMMITMENT — $497"}</button>{error&&<p className="bfg-error">{error}</p>}</div></section></main></BfgShell>
}

export function GuidedPaymentConfirmedPage(){
 const [product]=useProduct();const loc=useLocation();const nav=useNavigate();const sid=new URLSearchParams(loc.search).get("session_id")||"";const [state,setState]=useState("checking");
 useEffect(()=>{let n=0,t;const poll=async()=>{n++;try{let r=await axios.get(`${API}/payments/status/${sid}`);if(r.data.payment_status==="paid"){setState("paid");return}}catch{}if(n<8)t=setTimeout(poll,2200);else setState("waiting")};poll();return()=>clearTimeout(t)},[sid]);
 return <BfgShell><main className="guided-page"><section className="guided-confirm"><CheckCircle2 size={54}/><h1>{state==="paid"?"Payment Confirmed":"Confirming Your Payment…"}</h1><p>{state==="paid"?"Your guided process is ready.":"Please keep this page open while we confirm your payment."}</p>{state==="paid"&&<button className="bfg-btn bfg-btn-primary" onClick={()=>nav(`/${product}/welcome?session_id=${sid}`)}>CONTINUE</button>}</section></main></BfgShell>
}

export function GuidedWelcomePage(){
 const [product,c]=useProduct();const sid=new URLSearchParams(useLocation().search).get("session_id")||"";const nav=useNavigate();
 return <BfgShell><main className="guided-page"><section className="guided-video-page"><p className="bfg-eyebrow">WELCOME</p><h1>{c.onboardingTitle}</h1><p>Watch this short onboarding before completing your intake. It will show you what happens next and how to get the most from the process.</p><div className="guided-video"><Video size={38}/><strong>Onboarding video</strong><span>Video URL can be added before launch.</span></div><button className="bfg-btn bfg-btn-primary" onClick={()=>nav(`/${product}/intake?session_id=${sid}`)}>CONTINUE TO MY INTAKE</button></section></main></BfgShell>
}

export function GuidedIntakePage(){
 const [product,c]=useProduct();const nav=useNavigate();const sid=new URLSearchParams(useLocation().search).get("session_id")||"";const [answers,setAnswers]=useState({});const [busy,setBusy]=useState(false),[error,setError]=useState("");
 const submit=async()=>{if(c.intakeFields.some(([k])=>!String(answers[k]||"").trim())){setError("Please answer each question so we can prepare your workspace.");return}setBusy(true);try{let r=await axios.post(`${API}/guided/intake`,{session_id:sid,product,answers});nav(r.data.dashboard_url)}catch(e){setError(e.response?.data?.detail||"We could not save your intake.")}setBusy(false)};
 return <BfgShell><main className="guided-page"><section className="guided-section"><p className="bfg-eyebrow">YOUR INTAKE</p><h1>{c.intakeTitle}</h1><p className="guided-intro">Give us the context we need to prepare the guided process around your organization.</p><div className="guided-intake">{c.intakeFields.map(([k,label,type])=><label key={k}><span>{label}</span>{type==="textarea"?<textarea rows={5} value={answers[k]||""} onChange={e=>setAnswers({...answers,[k]:e.target.value})}/>:<input value={answers[k]||""} onChange={e=>setAnswers({...answers,[k]:e.target.value})}/>}</label>)}{error&&<p className="bfg-error">{error}</p>}<button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={submit}>{busy?"SAVING…":"BUILD MY WORKSPACE"}</button></div></section></main></BfgShell>
}

export function GuidedDashboardPage(){
 const [product,c]=useProduct();const sid=new URLSearchParams(useLocation().search).get("session_id")||"";const [ctx,setCtx]=useState(null);
 useEffect(()=>{axios.get(`${API}/guided/dashboard`,{params:{session_id:sid,product}}).then(r=>setCtx(r.data)).catch(()=>setCtx({error:true}))},[sid,product]);
 const strategic=product==="strategic-planning";
 return <BfgShell><main className="guided-page"><section className="guided-section"><p className="bfg-eyebrow">{c.eyebrow}</p><h1>{c.dashboardTitle}</h1><p className="guided-intro">{strategic?"Start by preparing the individual strategic planning form for every board member. Their responses will become your first draft.":"Start by preparing the board members you need to recommit. Each response will help you decide the right one-on-one conversation."}</p><div className="guided-dashboard-grid">{(strategic?[["1","Invite Your Board","Prepare and send the individual strategic planning form."],["2","First Strategic Plan Draft","Combine board member ideas into the first working draft."],["3","Assign Leadership Areas","Match board members to the areas they said they can help lead."],["4","Area Plans & Adoption","Build, review and adopt each deeper area plan."],["5","Build The Structures","Move from adopted plans into teams, technology, materials and oversight."]]:[["1","Prepare Board Members","Add the board members you need to recommit."],["2","Send Recommitment Forms","Send the provided email and individual form."],["3","Review Their Responses","See who will recommit, who is unsure and who wants to step down."],["4","Prepare One-On-One Conversations","Use the interpretation and conversation script for each board member."],["5","Confirm The Way Forward","Record recommitments, responsibilities and graceful transitions."]]).map(([n,t,x])=><article key={n}><span>{n}</span><h3>{t}</h3><p>{x}</p><button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled>{n==="1"?"NEXT BUILD STEP":"COMING NEXT"}</button></article>)}</div>{ctx?.error&&<p className="bfg-error">We could not confirm this workspace.</p>}</section></main></BfgShell>
}
