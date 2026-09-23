import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, ImagePlus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { MemberShell } from "./MemberShell";
import { useMemberAuth } from "./MemberAuthContext";
import { memberApi } from "./api";
import "./sgr.css";

const QUESTIONS = [
  {
    key: "mission",
    title: "Your Organization Mission",
    prompt: "What is your organization's mission statement?",
    helper: "Give us the mission in the organization's own words. This becomes the context behind every form, conversation and Board Member Portfolio.",
    type: "textarea",
  },
  {
    key: "why_recommit",
    title: "Why You Need The Board To Recommit",
    prompt: "Why do you want these Board Members to recommit and step up now?",
    helper: "Tell us what has changed, what is not working today, or why renewed commitment matters at this point in the organization's life.",
    type: "textarea",
  },
  {
    key: "board_help_accomplish",
    title: "What You Need The Board To Help Accomplish",
    prompt: "What do you need these Board Members to help the organization accomplish?",
    helper: "Be specific about the outcomes, priorities, work or leadership you need them to help carry if they recommit.",
    type: "textarea",
  },
  {
    key: "need_by",
    title: "When You Need This In Place",
    prompt: "By when do you need the Board to recommit and begin operating in these roles?",
    helper: "Choose the date that should guide the urgency of the conversations and the transition into active roles.",
    type: "date",
  },
];

export default function RecommitmentQuestionsPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [organization, setOrganization] = useState("");
  const [answers, setAnswers] = useState({ mission:"", why_recommit:"", board_help_accomplish:"", need_by:"", logo_data_url:"" });
  const [index, setIndex] = useState(-1);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!loading && !member) navigate("/login?next=/board-recommitment/questions", { replace: true });
  }, [loading, member, navigate]);

  useEffect(() => {
    if (!member) return;
    memberApi.get("/reactivation/setup").then((response) => {
      setOrganization(response.data.organization_name || "");
      setAnswers((current) => ({...current,...(response.data.answers || {})}));
    }).catch(() => {});
  }, [member]);

  const completed = useMemo(() => QUESTIONS.filter(q=>String(answers[q.key]||"").trim()).length, [answers]);

  const chooseLogo = (event) => {
    const file = event.target.files?.[0];
    setMessage("");
    if (!file) return;
    if (!file.type.startsWith("image/")) { setMessage("Choose an image file for your organization logo."); return; }
    if (file.size > 1800000) { setMessage("Use a logo image smaller than 1.8 MB."); return; }
    const reader = new FileReader();
    reader.onload = () => setAnswers((current)=>({...current,logo_data_url:reader.result}));
    reader.readAsDataURL(file);
  };

  const save = async (finish = false) => {
    setBusy(true); setMessage("");
    try {
      await memberApi.put("/reactivation/setup", answers);
      if (finish) {
        navigate("/board-recommitment/dashboard#recommitment-forms", { replace:true });
      } else {
        setIndex((value)=>value+1);
        window.scrollTo({top:0,behavior:"smooth"});
      }
    } catch (error) {
      setMessage(error.response?.data?.detail || "We could not save this answer.");
    }
    setBusy(false);
  };

  if (loading || !member) return null;

  if (index < 0) {
    return <MemberShell><main className="member-page sgr recommitment-questions-page">
      <header className="sgr-questions-intro">
        <p className="eyebrow">BOARD RECOMMITMENT</p>
        <h1>Answer Four Important Questions</h1>
        <p>Give us the context we need to prepare the Recommitment Forms, the response interpretation, the one-on-one conversation and each continuing Board Member's final role.</p>
      </header>
      <section className="member-card sgr-logo-card">
        <div className="sgr-logo-copy">
          <p className="eyebrow">YOUR ORGANIZATION</p>
          <h2>{organization || "Your Organization"}</h2>
          <p>Add the logo once. It will appear on the Board Recommitment experience your Board Members receive.</p>
        </div>
        <div className="sgr-logo-control">
          {answers.logo_data_url
            ? <img src={answers.logo_data_url} alt={`${organization || "Organization"} logo`}/>
            : <div className="sgr-logo-placeholder"><ImagePlus size={28}/><span>No logo added yet</span></div>}
          <label className="button button-outline">CHOOSE LOGO<input hidden type="file" accept="image/png,image/jpeg,image/webp" onChange={chooseLogo}/></label>
        </div>
      </section>
      <section className="member-card sgr-question-intro-card">
        <h2>What We Need From You</h2>
        <p>Mission. Why recommitment matters now. What you need the Board to help accomplish. When you need the new commitment in place.</p>
        <div className="sgr-question-start">
          <p>{completed ? `${completed} of 4 answers already saved.` : "You will answer one question at a time."}</p>
          <button className="button" onClick={()=>setIndex(0)}>{completed ? "CONTINUE MY ANSWERS" : "START THE FOUR QUESTIONS"} <ArrowRight size={16}/></button>
          <button className="button button-outline" onClick={()=>navigate("/board-recommitment/dashboard")}>RETURN TO DASHBOARD</button>
        </div>
      </section>
      {message&&<p className="submit-error">{message}</p>}
    </main></MemberShell>;
  }

  const q=QUESTIONS[index];
  const value=answers[q.key]||"";
  const last=index===QUESTIONS.length-1;

  return <MemberShell><main className="member-page sgr recommitment-questions-page">
    <section className="member-card sgr-question-stage">
      <div className="sgr-question-screen">
        <div className="sgr-question-topline"><span>BOARD RECOMMITMENT</span><span>QUESTION {index+1} OF 4</span></div>
        <div className="sgr-question-progress">{QUESTIONS.map((_,i)=><span key={i} className={i<=index?"active":""}/>)}</div>
        <div className="sgr-question-copy">
          <p className="eyebrow">{q.title}</p>
          <h1>{q.prompt}</h1>
          <p className="sgr-question-helper">{q.helper}</p>
        </div>
        <div className="sgr-question-answer">
          {q.type==="date"
            ? <input type="date" value={value} onChange={e=>setAnswers({...answers,[q.key]:e.target.value})}/>
            : <textarea rows="7" value={value} onChange={e=>setAnswers({...answers,[q.key]:e.target.value})} placeholder="Use your own words."/>}
        </div>
        {message&&<p className="submit-error">{message}</p>}
        <div className="sgr-question-actions">
          <button className="button button-outline" onClick={()=>index===0?setIndex(-1):setIndex(index-1)}><ArrowLeft size={16}/> BACK</button>
          <button className="button" disabled={busy||!String(value).trim()} onClick={()=>save(last)}>
            {busy?"SAVING…":last?<><CheckCircle2 size={16}/> SAVE AND RETURN TO DASHBOARD</>:<>SAVE & CONTINUE <ArrowRight size={16}/></>}
          </button>
        </div>
      </div>
    </section>
  </main></MemberShell>;
}
