import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import "@/member/sgr.css";
import { Send } from "lucide-react";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;

export default function RecommitmentAssistantPage(){
  const{token}=useParams();
  const[data,setData]=useState(null);
  const[message,setMessage]=useState("");
  const[busy,setBusy]=useState(false);
  const[error,setError]=useState("");
  const bottomRef=useRef(null);

  useEffect(()=>{
    document.title="My Board Execution Assistant | Nonprofit Board Builder";
    axios.get(`${API}/portfolio-assistant/${token}`).then(r=>setData(r.data)).catch(()=>setError("This Executive Assistant is not available."));
  },[token]);

  useEffect(()=>{bottomRef.current?.scrollIntoView({behavior:"smooth"})},[data?.messages?.length]);

  const send=async(materialType="")=>{
    if(!materialType&&!message.trim())return;
    setBusy(true);setError("");
    const userText=materialType?materialType:message.trim();
    setData(current=>current?{...current,messages:[...(current.messages||[]),{role:"user",text:userText}]}:current);
    const typed=message.trim();setMessage("");
    try{
      const r=await axios.post(`${API}/portfolio-assistant/${token}`,{message:typed,material_type:materialType});
      setData(current=>({...current,messages:[...(current.messages||[]),{role:"assistant",text:r.data.answer}]}));
    }catch(e){setError(e.response?.data?.detail||"The Executive Assistant could not respond right now.")}
    setBusy(false);
  };

  if(error&&!data)return <main className="recommitment-assistant-page"><section className="recommitment-assistant-shell"><h1>Executive Assistant Unavailable</h1><p>{error}</p></section></main>;
  if(!data)return <main className="recommitment-assistant-page"><section className="recommitment-assistant-shell"><p>Opening your Executive Assistant…</p></section></main>;

  return <main className="recommitment-assistant-page" data-testid="recommitment-assistant-page">
    <section className="recommitment-assistant-shell">
      <header className="recommitment-assistant-header">
        <p className="eyebrow">MY BOARD EXECUTION ASSISTANT</p>
        <h1>{data.member_name}</h1>
        <p>{data.confirmed_role&&<strong>{data.confirmed_role}</strong>}{data.organization_name&&<> · {data.organization_name}</>}</p>
        <p>This assistant works from your approved Board Member Portfolio and the responsibility you agreed with the organization. Ask it to help you turn that responsibility into action.</p>
      </header>

      {data.suggested_actions?.length>0&&<section className="recommitment-assistant-suggestions">
        <p className="eyebrow">QUICK START</p>
        <div>{data.suggested_actions.map(item=><button key={item} disabled={busy} onClick={()=>send(item)}>{item}</button>)}</div>
      </section>}

      <section className="recommitment-assistant-chat">
        {(data.messages||[]).length===0&&<div className="recommitment-assistant-empty"><p>Choose a quick action above or tell me what you are trying to execute from your Portfolio.</p></div>}
        {(data.messages||[]).map((item,index)=><div key={index} className={`recommitment-chat-message ${item.role}`}><strong>{item.role==="assistant"?"Executive Assistant":"You"}</strong><p>{item.text}</p></div>)}
        {busy&&<div className="recommitment-chat-message assistant"><strong>Executive Assistant</strong><p>Preparing this for you…</p></div>}
        {error&&<p className="submit-error">{error}</p>}
        <div ref={bottomRef}/>
      </section>

      <section className="recommitment-assistant-compose">
        <textarea rows="4" value={message} onChange={e=>setMessage(e.target.value)} placeholder="What do you need help executing?"/>
        <button disabled={busy||!message.trim()} onClick={()=>send()}><Send size={17}/> SEND</button>
      </section>
    </section>
  </main>;
}
