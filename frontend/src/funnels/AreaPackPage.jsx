import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Download, Sparkles } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AreaPackPage() {
  const { token } = useParams();
  const [data,setData]=useState(null),[error,setError]=useState(""),[planText,setPlanText]=useState(""),[busy,setBusy]=useState("");
  const load=()=>axios.get(`${API}/area-pack/${token}`).then(r=>{setData(r.data);setPlanText(r.data.draft_text||r.data.submitted_plan||"")}).catch(e=>setError(e.response?.data?.detail||"This link is not valid."));
  useEffect(load,[token]);
  const act=async(key,fn)=>{setBusy(key);setError("");try{await fn();await load()}catch(e){setError(e.response?.data?.detail||"That action could not be completed.")}setBusy("")};
  if(error&&!data)return <main className="legal-page"><h1>Strategic Area Development</h1><p>{error}</p></main>;
  if(!data)return <main className="legal-page"><p>Loading…</p></main>;
  const approved=data.approved||data.draft_status==="Approved";
  return <main className="legal-page" data-testid="area-pack-page" style={{maxWidth:920,margin:"0 auto",padding:"32px 16px"}}>
    <p className="eyebrow">{data.organization_name}</p><h1>Strategic Plan Draft</h1>
    <p>This is the strategic direction your Board developed together. Your role is to turn <strong>{data.area}</strong> into a detailed, executable plan.</p>
    {data.foundational_plan&&<details style={{margin:"22px 0"}} open><summary style={{cursor:"pointer",fontWeight:700}}>STRATEGIC PLAN DRAFT</summary><pre style={{whiteSpace:"pre-wrap",background:"#f6f6f2",padding:16,borderRadius:10,maxHeight:520,overflow:"auto"}}>{data.foundational_plan}</pre></details>}
    <details style={{margin:"22px 0"}}><summary style={{cursor:"pointer",fontWeight:700}}>VIEW MY ROLE AND ASSIGNMENT</summary><pre style={{whiteSpace:"pre-wrap",background:"#f6f6f2",padding:16,borderRadius:10}}>{data.pack_text}</pre></details>
    {!planText&&!approved&&<button className="button" disabled={busy==="generate"} onClick={()=>act("generate",()=>axios.post(`${API}/area-pack/${token}/generate`))}><Sparkles size={16}/> {busy==="generate"?"BUILDING…":"START BUILDING MY DETAILED PLAN WITH AI"}</button>}
    {!!planText&&<section style={{marginTop:24}}>
      <h2>Your Detailed Plan: {data.area}</h2><p>AI has created the working draft from the Board's approved direction and your own planning response. Edit it directly. Nothing becomes part of the Final Strategic Plan until you approve it.</p>
      <textarea rows={30} style={{width:"100%",fontFamily:"Georgia, serif",fontSize:"1rem",lineHeight:1.65,padding:18,border:"1px solid #bbb",borderRadius:8}} value={planText} disabled={approved} onChange={e=>setPlanText(e.target.value)} data-testid="area-plan-editor"/>
      {error&&<p className="submit-error">{error}</p>}
      {!approved?<div style={{display:"flex",gap:10,flexWrap:"wrap",marginTop:14}}>
        <button className="button button-back" disabled={!!busy} onClick={()=>act("save",()=>axios.put(`${API}/area-pack/${token}/plan`,{plan_text:planText}))}>{busy==="save"?"SAVING…":"SAVE MY DRAFT"}</button>
        <button className="button" disabled={!!busy||!planText.trim()} onClick={()=>act("approve",async()=>{await axios.put(`${API}/area-pack/${token}/plan`,{plan_text:planText});await axios.post(`${API}/area-pack/${token}/approve`)})}>{busy==="approve"?"APPROVING…":"APPROVE MY DETAILED PLAN"}</button>
      </div>:<div style={{marginTop:14}}><h3>Approved</h3><p>This approved copy is saved as the authoritative plan for this strategic area and can now be used in the Final Strategic Plan.</p><a className="button" href={`${API}/area-pack/${token}/pdf`}><Download size={16}/> DOWNLOAD APPROVED PLAN</a></div>}
    </section>}
  </main>;
}
