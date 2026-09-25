import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, ImagePlus, Plus, Trash2 } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "@/game/gameShared";
import "./strategic-planning-dashboard.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

const QUESTIONS=[
  {key:"mission",title:"Mission",prompt:"What is your organization's mission statement?",helper:"Use the organization's own words. Your Board will be able to test the mission later, but your present mission is the starting point."},
  {key:"goals",title:"Goals",prompt:"What are your present goals?",helper:"Tell us what the organization is trying to accomplish during the next 12 to 24 months."},
  {key:"objectives",title:"Objectives",prompt:"What objectives are you presently pursuing to achieve those goals?",helper:"Describe the specific results or milestones you are working towards."},
  {key:"program_details",title:"Programs",prompt:"Tell us about each program or service separately.",helper:"Each program becomes its own strategic planning discussion, so add them one at a time.",type:"programs"},
  {key:"team_building",title:"Team Structure",prompt:"Tell us about the people presently helping the organization execute.",helper:"Include staff, Board Members, volunteers, contractors and other important capacity."},
  {key:"technology",title:"Technology",prompt:"What technology and tools do you presently use?",helper:"Tell us what the tools help you do and where technology still needs to make work easier, faster or more reliable."},
  {key:"marketing",title:"Marketing",prompt:"How are you presently marketing and communicating the organization?",helper:"Who are you trying to reach, where are you visible now and what are you presently doing to attract attention and build trust?"},
  {key:"partnerships",title:"Partnerships",prompt:"Tell us about your present partnerships and the partnerships you are looking towards building.",helper:"Include important relationships with organizations, institutions, businesses, government, community groups or other partners."},
  {key:"fundraising",title:"Fundraising",prompt:"How are you presently raising money and what are you looking towards doing differently?",helper:"Tell us what is working, what is not working and what you believe needs to improve."},
  {key:"budget",title:"Budget",prompt:"What is your present budget or best current understanding of what it costs to operate and grow?",helper:"Use only numbers you actually know. You can explain uncertainty rather than inventing numbers."},
  {key:"action_planning",title:"Action Planning",prompt:"What are you presently doing, and what are you looking towards doing next?",helper:"Describe important actions already underway and what you believe needs to happen next so the Board can compare present execution with the future plan."},
];

const emptyProgram=()=>({name:"",description:"",present_work:""});

export default function StrategicOrganizationSetupPage(){
  const nav=useNavigate(),location=useLocation();
  const {member}=useMemberAuth();
  const sid=new URLSearchParams(location.search).get("session_id")||"";
  const[organization,setOrganization]=useState("");
  const[answers,setAnswers]=useState({program_details:[emptyProgram()]});
  const[logo,setLogo]=useState("");
  const[index,setIndex]=useState(-1);
  const[busy,setBusy]=useState(false);
  const[message,setMessage]=useState("");

  useEffect(()=>{
    if(!sid)return;
    axios.get(`${API}/guided/strategic-planning/workspace`,{params:{session_id:sid}}).then(r=>{
      setOrganization(r.data.organization_name||"");
      const existing=r.data.organization_answers||{};
      let programs=Array.isArray(existing.program_details)?existing.program_details:[];
      if(!programs.length&&existing.programs){
        programs=String(existing.programs).split("\n").filter(Boolean).map(name=>({name:name.trim(),description:"",present_work:""}));
      }
      setAnswers({...existing,program_details:programs.length?programs:[emptyProgram()]});
      setLogo(r.data.project?.logo_data_url||"");
    }).catch(e=>setMessage(e.response?.data?.detail||"We could not open your organization setup."));
  },[sid]);

  const completed=useMemo(()=>QUESTIONS.filter(q=>{
    if(q.type==="programs")return (answers.program_details||[]).some(p=>p.name?.trim());
    return String(answers[q.key]||"").trim();
  }).length,[answers]);

  const uploadLogo=file=>{
    if(!file)return;
    setMessage("");
    if(!file.type.startsWith("image/")){setMessage("Choose an image file for the organization logo.");return}
    if(file.size>1800000){setMessage("Use a logo image smaller than 1.8 MB.");return}
    const reader=new FileReader();reader.onload=()=>setLogo(reader.result);reader.readAsDataURL(file);
  };

  const normalizedAnswers=()=>{
    const programs=(answers.program_details||[]).map(p=>({
      name:String(p.name||"").trim(),
      description:String(p.description||"").trim(),
      present_work:String(p.present_work||"").trim(),
    })).filter(p=>p.name);
    return {...answers,program_details:programs,programs:programs.map(p=>p.name).join("\n")};
  };

  const validCurrent=()=>{
    if(index<0)return true;
    const q=QUESTIONS[index];
    if(q.type==="programs")return (answers.program_details||[]).some(p=>p.name?.trim());
    return Boolean(String(answers[q.key]||"").trim());
  };

  const save=async(finish=false)=>{
    const nextAnswers=normalizedAnswers();
    if(!String(nextAnswers.mission||"").trim()){setMessage("Complete the mission statement first so your organization information can be saved.");return}
    setBusy(true);setMessage("");
    try{
      await axios.put(`${API}/guided/strategic-planning/organization`,{
        session_id:sid,organization_name:organization,answers:nextAnswers,logo_data_url:logo
      });
      setAnswers(nextAnswers);
      if(finish)nav(member?.supported_service_product==="strategic-planning"?"/supported-service/thank-you":`/strategic-planning/dashboard?session_id=${encodeURIComponent(sid)}#sp-meeting`,{replace:true});
      else{setIndex(index+1);window.scrollTo({top:0,behavior:"smooth"});}
    }catch(e){setMessage(e.response?.data?.detail||"We could not save this information.");}
    setBusy(false);
  };

  const updateProgram=(i,key,value)=>setAnswers(a=>({...a,program_details:(a.program_details||[]).map((p,n)=>n===i?{...p,[key]:value}:p)}));
  const removeProgram=i=>setAnswers(a=>({...a,program_details:(a.program_details||[]).filter((_,n)=>n!==i)}));

  if(!sid)return <BfgShell><main className="guided-page"><section className="guided-section"><h1>Strategic Planning</h1><p>This Strategic Planning link is missing its session information.</p></section></main></BfgShell>;

  if(index<0)return <BfgShell><main className="guided-page sp-setup-page">
    <section className="sp-setup-intro">
      <p className="bfg-eyebrow">STRATEGIC PLANNING</p>
      <h1>Tell Us About Your Organization</h1>
      <p>This is the starting reality your Board will react to. Give us what is true now, in your own words. The planning process will help the Board test it, improve it and decide what should happen next.</p>
    </section>
    <section className="sp-dash-card sp-setup-logo-card">
      <div><p className="bfg-eyebrow">YOUR ORGANIZATION</p><h2>{organization||"Your Organization"}</h2><p>Add the logo once. It will carry through the Strategic Planning Form and the final Strategic Plan.</p></div>
      <div className="sp-setup-logo-control">
        {logo?<img src={logo} alt={`${organization||"Organization"} logo`}/>:<div className="sp-setup-logo-placeholder"><ImagePlus size={28}/><span>No logo added yet</span></div>}
        <label className="bfg-btn bfg-btn-ghost bfg-btn-sm">CHOOSE LOGO<input hidden type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>uploadLogo(e.target.files?.[0])}/></label>
      </div>
    </section>
    <section className="sp-dash-card sp-setup-start">
      <h2>One Area At A Time</h2>
      <p>Mission, goals, objectives, programs, team structure, technology, marketing, partnerships, fundraising, budget and action planning.</p>
      <p><strong>{completed} of {QUESTIONS.length}</strong> areas currently have information saved.</p>
      <button className="bfg-btn bfg-btn-primary" onClick={()=>setIndex(0)}>{completed?"CONTINUE ORGANIZATION SETUP":"START ORGANIZATION SETUP"} <ArrowRight size={16}/></button>
      <button className="bfg-btn bfg-btn-ghost" onClick={()=>nav(`/strategic-planning/dashboard?session_id=${encodeURIComponent(sid)}`)}>RETURN TO DASHBOARD</button>
      {message&&<p className="bfg-error">{message}</p>}
    </section>
  </main></BfgShell>;

  const q=QUESTIONS[index],last=index===QUESTIONS.length-1;
  return <BfgShell><main className="guided-page sp-setup-page">
    <section className="sp-dash-card sp-setup-question-card">
      <div className="sp-question-topline"><span>STRATEGIC PLANNING</span><span>{index+1} OF {QUESTIONS.length}</span></div>
      <div className="sp-question-progress">{QUESTIONS.map((_,i)=><span className={i<=index?"active":""} key={i}/>)}</div>
      <div className="sp-question-copy"><p className="bfg-eyebrow">{q.title}</p><h1>{q.prompt}</h1><p>{q.helper}</p></div>
      {q.type==="programs"?<div className="sp-program-builder">
        {(answers.program_details||[]).map((p,i)=><article key={i} className="sp-program-card">
          <div className="sp-program-card-head"><strong>Program {i+1}</strong>{(answers.program_details||[]).length>1&&<button onClick={()=>removeProgram(i)}><Trash2 size={15}/> Remove</button>}</div>
          <label>Name<input value={p.name||""} onChange={e=>updateProgram(i,"name",e.target.value)} placeholder="Program name"/></label>
          <label>Description<textarea rows="3" value={p.description||""} onChange={e=>updateProgram(i,"description",e.target.value)} placeholder="What is this program and who does it serve?"/></label>
          <label>What are you presently doing through this program?<textarea rows="3" value={p.present_work||""} onChange={e=>updateProgram(i,"present_work",e.target.value)} placeholder="Describe the present work, delivery or priorities."/></label>
        </article>)}
        <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={()=>setAnswers(a=>({...a,program_details:[...(a.program_details||[]),emptyProgram()]}))}><Plus size={15}/> ADD ANOTHER PROGRAM</button>
      </div>:<textarea className="sp-large-answer" rows="9" value={answers[q.key]||""} onChange={e=>setAnswers({...answers,[q.key]:e.target.value})} placeholder="Use your own words."/>}
      {message&&<p className="bfg-error">{message}</p>}
      <div className="sp-question-actions">
        <button className="bfg-btn bfg-btn-ghost" onClick={()=>index===0?setIndex(-1):setIndex(index-1)}><ArrowLeft size={16}/> BACK</button>
        <button className="bfg-btn bfg-btn-primary" disabled={busy||!validCurrent()} onClick={()=>save(last)}>{busy?"SAVING…":last?<><CheckCircle2 size={16}/> SAVE & RETURN TO DASHBOARD</>:<>SAVE & CONTINUE <ArrowRight size={16}/></>}</button>
      </div>
    </section>
  </main></BfgShell>;
}
