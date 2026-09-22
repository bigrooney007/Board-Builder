import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import "@/game/game.css";
import "./guided-products.css";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CommunityNeedResearchPage(){
  const {token}=useParams();
  const [data,setData]=useState(null);
  const [name,setName]=useState("");
  const [email,setEmail]=useState("");
  const [answers,setAnswers]=useState(["","","","",""]);
  const [done,setDone]=useState(false);
  const [error,setError]=useState("");

  useEffect(()=>{
    axios.get(`${API}/guided/strategic-planning/community-research/${token}`)
      .then(response=>setData(response.data))
      .catch(err=>setError(err.response?.data?.detail||"This survey is not available."));
  },[token]);

  const submit=async()=>{
    try{
      await axios.post(`${API}/guided/strategic-planning/community-research/${token}`,{name,email,answers});
      setDone(true);
    }catch(err){setError(err.response?.data?.detail||"Please complete the survey.");}
  };

  return <main className="guided-page" data-testid="community-need-research-page">
    <section className="guided-section">
      {!data?<p>{error||"Loading…"}</p>:done?<><h1>Thank You For Sharing Your Perspective.</h1><p>Your response will help {data.organization_name}'s Board understand the community as it develops its Strategic Plan.</p></>:<>
        <p className="bfg-eyebrow">COMMUNITY NEED RESEARCH</p>
        <h1>Help Shape The Future Direction Of {data.organization_name}</h1>
        <p className="guided-intro">Before the Board agrees the organization's next Strategic Plan, we want to hear from people who understand the need, the community and the work. Speak from what you have observed, experienced or know personally.</p>
        {data.mission&&<div className="sp-contentbox" data-testid="community-research-mission"><p className="bfg-eyebrow">OUR MISSION</p><p>{data.mission}</p></div>}
        <div className="guided-intake">
          <label><span>Your Name</span><input value={name} onChange={event=>setName(event.target.value)}/></label>
          <label><span>Email Address (optional)</span><input value={email} onChange={event=>setEmail(event.target.value)}/></label>
          {data.questions.map((question,index)=><label key={question}><span>{question}</span><textarea rows={5} value={answers[index]} onChange={event=>{const next=[...answers];next[index]=event.target.value;setAnswers(next)}}/></label>)}
          {error&&<p className="bfg-error">{error}</p>}
          <button className="bfg-btn bfg-btn-primary" onClick={submit}>SUBMIT MY RESPONSE</button>
        </div>
      </>}
    </section>
  </main>;
}
