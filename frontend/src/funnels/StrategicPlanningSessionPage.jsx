import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, Copy, Mic, MicOff } from "lucide-react";
import { BfgShell } from "@/game/gameShared";
import "@/game/game.css";
import "./guided-products.css";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategicPlanningSessionPage(){
 const sid=new URLSearchParams(window.location.search).get("session_id")||"";
 const navigate=useNavigate();
 const [session,setSession]=useState(null),[decisions,setDecisions]=useState({}),[transcript,setTranscript]=useState(""),[shareUrl,setShareUrl]=useState(""),[listening,setListening]=useState(false),[busy,setBusy]=useState(""),[message,setMessage]=useState("");
 const recognition=useRef(null);

 const load=useCallback(async()=>{
  try{
   const r=await axios.get(`${API}/guided/strategic-planning/session`,{params:{session_id:sid}});
   setSession(r.data);
   const savedTranscript=r.data.transcript||localStorage.getItem(`sp-transcript-${sid}`)||"";
   setTranscript(savedTranscript);
   if(r.data.share_token)setShareUrl(`${window.location.origin}/strategic-session/${r.data.share_token}`);
   const next={};
   (r.data.sections||[]).forEach(section=>{
    next[section.key]=["__keep_current__","__use_all_ideas__"].includes(section.decision_mode)?section.decision_mode:(section.selected_idea_ids||[]);
   });
   setDecisions(next);
  }catch(e){setMessage(e.response?.data?.detail||"We could not open the Strategic Planning Session.");}
 },[sid]);

 useEffect(()=>{load();},[load]);
 useEffect(()=>()=>recognition.current?.stop(),[]);

 const persistTranscript=async(value=transcript)=>{
  localStorage.setItem(`sp-transcript-${sid}`,value);
  try{await axios.post(`${API}/guided/strategic-planning/session/transcript`,{session_id:sid,transcript:value});}catch{}
 };

 const startListening=()=>{
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){setMessage("Live microphone transcription is not supported in this browser. Paste or type the meeting transcript into the backup box instead.");return;}
  const r=new SR();r.continuous=true;r.interimResults=true;
  r.onresult=e=>{
   let added="";
   for(let i=e.resultIndex;i<e.results.length;i++)if(e.results[i].isFinal)added+=e.results[i][0].transcript+" ";
   if(added)setTranscript(current=>{const next=(current+" "+added).trim();localStorage.setItem(`sp-transcript-${sid}`,next);return next;});
  };
  r.onend=()=>setListening(false);
  r.start();recognition.current=r;setListening(true);setMessage("");
 };
 const stopListening=()=>{recognition.current?.stop();setListening(false);persistTranscript();};

 const createShare=async()=>{
  setBusy("share");setMessage("");
  try{const r=await axios.post(`${API}/guided/strategic-planning/session/share`,{session_id:sid});setShareUrl(`${window.location.origin}/strategic-session/${r.data.share_token}`);await load();}
  catch(e){setMessage(e.response?.data?.detail||"The shared Board screen could not be created.");}
  setBusy("");
 };

 const startSession=async()=>{
  setBusy("start");setMessage("");
  try{await persistTranscript();await axios.post(`${API}/guided/strategic-planning/session/start`,{session_id:sid});await load();}
  catch(e){setMessage(e.response?.data?.detail||"The session could not be started.");}
  setBusy("");
 };

 const saveDecision=async(key,value)=>{
  setDecisions(current=>({...current,[key]:value}));
  try{await axios.post(`${API}/guided/strategic-planning/session/decision`,{session_id:sid,section_key:key,decision:value});}
  catch(e){setMessage(e.response?.data?.detail||"That Board decision could not be saved.");}
 };

 const toggleIdea=(section,ideaId)=>{
  const current=Array.isArray(decisions[section.key])?decisions[section.key]:[];
  const next=current.includes(ideaId)?current.filter(id=>id!==ideaId):[...current,ideaId];
  saveDecision(section.key,next);
 };

 const move=async index=>{
  await persistTranscript();
  await axios.post(`${API}/guided/strategic-planning/session/progress`,{session_id:sid,current_section_index:index});
  setSession(current=>({...current,current_section_index:index,status:"IN PROGRESS"}));
  window.scrollTo({top:0,behavior:"smooth"});
 };

 const ready=value=>Array.isArray(value)?value.length>0:Boolean(value);

 const finish=async()=>{
  setBusy("finish");setMessage("");
  try{
   if(listening){recognition.current?.stop();setListening(false);}
   await axios.post(`${API}/guided/strategic-planning/session/complete`,{session_id:sid,decisions,transcript});
   localStorage.removeItem(`sp-transcript-${sid}`);
   navigate(`/strategic-planning/dashboard?session_id=${encodeURIComponent(sid)}#generate-strategy`);
  }catch(e){setMessage(e.response?.data?.detail||"The Strategic Planning Session could not be completed.");}
  setBusy("");
 };

 if(!session)return <BfgShell><main className="guided-page"><section className="guided-section"><h1>Strategic Planning Session</h1><p>{message||"Preparing your session…"}</p></section></main></BfgShell>;

 if(session.status==="COMPLETED")return <BfgShell><main className="guided-page sp-live-session"><section className="sp-session-finished"><CheckCircle2 size={48}/><h1>Strategic Planning Session Complete</h1><p>Your Board decisions and transcript are saved. Return to the dashboard to generate the professional Strategic Plan.</p><button className="bfg-btn bfg-btn-primary" onClick={()=>navigate(`/strategic-planning/dashboard?session_id=${encodeURIComponent(sid)}#generate-strategy`)}>RETURN TO DASHBOARD</button></section></main></BfgShell>;

 if(session.status!=="IN PROGRESS")return <BfgShell><main className="guided-page sp-live-session"><section className="sp-session-prep">
  <p className="bfg-eyebrow">BEFORE YOU START</p><h1>Prepare Your Strategic Planning Session</h1><p className="sp-session-lead">Set up the shared Board screen and start transcription before moving into the first strategic section.</p>
  <div className="sp-prep-grid">
   <article><span className="sp-prep-number">1</span><h2>Create The Shared Board Screen</h2><p>Create one no-login link and paste it into your Zoom, Teams or meeting chat. Board Members open it once and their screen follows you automatically.</p>{!shareUrl?<button className="bfg-btn bfg-btn-primary" disabled={busy==="share"} onClick={createShare}>{busy==="share"?"CREATING…":"CREATE SHARED SCREEN LINK"}</button>:<div className="sp-session-link"><span>{shareUrl}</span><button onClick={()=>navigator.clipboard?.writeText(shareUrl)}><Copy size={15}/> COPY LINK</button></div>}</article>
   <article><span className="sp-prep-number">2</span><h2>Start Microphone Transcription</h2><p>Tell everyone the session needs to be transcribed so the Strategic Plan and agreed responsibilities reflect what the Board actually decides. Ask for consent before starting.</p><button className="bfg-btn bfg-btn-primary" onClick={listening?stopListening:startListening}>{listening?<><MicOff size={16}/> STOP TRANSCRIPTION</>:<><Mic size={16}/> START MICROPHONE TRANSCRIPTION</>}</button>{listening&&<p className="sp-listening">Listening. Keep this page open during the session.</p>}</article>
   <article><span className="sp-prep-number">3</span><h2>Start The Strategic Planning Session</h2><p>Once the Board has the shared screen and transcription is ready, start the session. You will move through one strategic section at a time.</p><button className="bfg-btn bfg-btn-primary" disabled={!shareUrl||busy==="start"} onClick={startSession}>{busy==="start"?"STARTING…":"START STRATEGIC PLANNING SESSION"}</button></article>
  </div>
  <details className="sp-transcript-fallback"><summary>Transcript backup / manual transcript</summary><textarea rows={8} value={transcript} onChange={e=>{setTranscript(e.target.value);localStorage.setItem(`sp-transcript-${sid}`,e.target.value)}} placeholder="If microphone transcription is unavailable, paste or type the meeting transcript here."/></details>
  {message&&<p className="bfg-error">{message}</p>}
 </section></main></BfgShell>;

 const index=Math.min(session.current_section_index||0,Math.max(0,(session.sections||[]).length-1));
 const section=session.sections[index],value=decisions[section?.key],selected=Array.isArray(value)?value:[],isLast=index===session.sections.length-1;

 return <BfgShell><main className="guided-page sp-live-session"><section className="sp-session-screen">
  <div className="sp-session-topline"><span>Section {index+1} of {session.sections.length}</span><span>{listening?"● TRANSCRIPTION ON":"TRANSCRIPTION OFF"}</span></div>
  <p className="bfg-eyebrow">LIVE STRATEGIC PLANNING SESSION</p><h1>{section.title}</h1>
  {section.current_context&&<div className="sp-current-context"><span>WHERE THE ORGANIZATION IS STARTING</span><p>{section.current_context}</p></div>}
  <div className="sp-facilitator-prompt" data-testid="section-facilitator-prompt">
    <strong>{section.facilitator_prompt?.title || "Discuss this with the Board."}</strong>
    <p>{section.facilitator_prompt?.say || "Review the ideas shared before the meeting. Let people explain what they mean, then click every idea the Board agrees should shape this section."}</p>
    {(section.facilitator_prompt?.questions||[]).length>0&&<ul>{section.facilitator_prompt.questions.map((question,index)=><li key={index}>{question}</li>)}</ul>}
    {section.facilitator_prompt?.decision&&<p><strong>Before you move on:</strong> {section.facilitator_prompt.decision}</p>}
  </div>
  <div className="sp-idea-grid">{section.ideas.map(idea=>{const chosen=selected.includes(idea.idea_id);return <button type="button" className={`sp-idea-card ${chosen?"selected":""}`} key={idea.idea_id} onClick={()=>toggleIdea(section,idea.idea_id)}><span className="sp-idea-person">{idea.participant_name}</span><p>{idea.idea}</p><small>{chosen?"SELECTED BY THE BOARD":"CLICK IF THE BOARD AGREES"}</small></button>})}</div>
  {section.allow_keep_current_mission&&<button className={`sp-keep-current ${value==="__keep_current__"?"selected":""}`} onClick={()=>saveDecision(section.key,"__keep_current__")}>LEAVE THE MISSION STATEMENT THE WAY IT IS</button>}
  {section.ideas.length>1&&<button className={`sp-use-all ${value==="__use_all_ideas__"?"selected":""}`} onClick={()=>saveDecision(section.key,"__use_all_ideas__")}>USE ALL IDEAS FROM THIS DISCUSSION</button>}
  {(section.recommendations||[]).length>0&&<details className="sp-nbb-perspective"><summary>Nonprofit Board Builder perspective</summary><ul>{section.recommendations.map((item,i)=><li key={i}>{item}</li>)}</ul><p>If the Board adopts one of these recommendations, say the decision aloud so it is captured in the transcript.</p></details>}
  {section.is_action_planning&&<div className="sp-action-planning-callout"><h2>Build The First Execution Cycle</h2><p>Agree what should happen first, next and after that. Keep this screen focused on priorities, sequence, decisions and resources. The next screen is where you discuss who is actually willing to help carry the work.</p></div>}
  {section.is_role_planning&&<div className="sp-action-planning-callout"><h2>Roles We Will Play</h2><p>Start with what each person volunteered before the meeting. Confirm it together if appropriate. If someone agrees to a different or additional role, say their name and exact responsibility aloud. If the Board prefers to confirm roles after the meeting, that is also fine: the lead user will still receive these stated preferences as editable proposals before anything is sent.</p></div>}
  <div className="sp-session-controls">{index>0&&<button className="bfg-btn bfg-btn-ghost" onClick={()=>move(index-1)}>BACK</button>}{!isLast&&<button className="bfg-btn bfg-btn-primary" disabled={!ready(value)} onClick={()=>move(index+1)}>SAVE BOARD DECISION & NEXT</button>}{isLast&&<button className="bfg-btn bfg-btn-primary" disabled={!ready(value)||busy==="finish"} onClick={finish}>{busy==="finish"?"SAVING SESSION…":"SAVE & END STRATEGIC PLANNING SESSION"}</button>}</div>
  <details className="sp-transcript-fallback"><summary>View / edit session transcript</summary><textarea rows={9} value={transcript} onChange={e=>{setTranscript(e.target.value);localStorage.setItem(`sp-transcript-${sid}`,e.target.value)}}/></details>
  {message&&<p className="bfg-error">{message}</p>}
 </section></main></BfgShell>;
}
