import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { MemberShell } from "./MemberShell";
import { SupportBox } from "./CoursePages";
import { memberApi } from "./api";
import ReactivationStep2 from "./ReactivationStep2";
import ReactivationUnderstand from "./ReactivationUnderstand";
import ReactivationStep3 from "./ReactivationStep3";
import FounderBoardAudit from "./FounderBoardAudit";
import RecommitmentInviteBoardMembers from "./RecommitmentInviteBoardMembers";
import "./sgr.css";

const CompactSection=({n,title,open,onOpen,children})=><section className="member-card compact-flow-section"><button type="button" className="compact-flow-toggle" onClick={onOpen}><span>{n}</span><strong>{title}</strong>{open?<ChevronUp/>:<ChevronDown/>}</button>{open&&<div className="compact-flow-body">{children}</div>}</section>;

const ProgressSummary=({refreshKey})=>{
 const [data,setData]=useState(null);
 useEffect(()=>{memberApi.get("/reactivation/my-board").then(r=>setData(r.data)).catch(()=>setData(null))},[refreshKey]);
 if(!data)return <p>Loading progress…</p>;
 const rows=Object.values(data.groups||{}).flat(),summary=data.summary||{};
 const stats=[["Responded",rows.filter(r=>r.status==="COMPLETED").length],["Understood",rows.filter(r=>r.analyzed).length],["Conversations Done",rows.filter(r=>r.conversation_outcome&&(r.conversation_conclusion||"").trim()).length],["Stepped Up",summary.active||0],["Advisory Board",summary.advisory||0],["Stepped Down",summary.stepping_down||0]];
 return <div className="recommitment-progress" data-testid="recommitment-progress-summary">{stats.map(([label,count])=><div key={label}><strong>{count}</strong><span>{label}</span></div>)}</div>;
};

export default function BoardRecommitmentDashboard(){
 const [branding,setBranding]=useState({organization_name:"",logo_data_url:""});
 const [brandingMessage,setBrandingMessage]=useState("");
 const [open,setOpen]=useState("1");
 const [refreshKey,setRefreshKey]=useState(0);
 const loadBranding=useCallback(()=>memberApi.get("/reactivation/branding").then(r=>setBranding(r.data)).catch(()=>{}),[]);
 useEffect(()=>{loadBranding()},[loadBranding]);
 const uploadLogo=file=>{if(!file)return;const reader=new FileReader();reader.onload=()=>setBranding({...branding,logo_data_url:reader.result});reader.readAsDataURL(file)};
 const saveBranding=async()=>{setBrandingMessage("");try{const r=await memberApi.put("/reactivation/branding",branding);setBranding(r.data);setBrandingMessage("Organization details saved. Your forms will now carry this branding.")}catch(e){setBrandingMessage(e.response?.data?.detail||"We could not save your organization branding.")}};
 return <MemberShell><main className="member-page sgr" data-testid="board-recommitment-dashboard">
  <header className="member-page-heading"><p className="eyebrow">Nonprofit Board Builder</p><h1>BOARD RECOMMITMENT</h1><p><strong>Get clear answers from each Board Member, prepare the right conversation and move that person forward based on what you agree together.</strong></p></header>
  <CompactSection n="1" title="Enter Organization Details" open={open==="1"} onOpen={()=>setOpen(open==="1"?"":"1")}><div data-testid="recommitment-branding"><p>Add your organization name and logo. They will appear on both versions of the Recommitment Form.</p>{branding.logo_data_url&&<img src={branding.logo_data_url} alt={`${branding.organization_name||"Organization"} logo`} style={{maxWidth:180,maxHeight:100,objectFit:"contain",margin:"8px auto 18px",display:"block"}}/>}<label className="field"><span>Organization Name <b>*</b></span><input value={branding.organization_name||""} onChange={e=>setBranding({...branding,organization_name:e.target.value})}/></label><label className="field"><span>Organization Logo</span><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>uploadLogo(e.target.files?.[0])}/></label><button className="button" disabled={!branding.organization_name?.trim()} onClick={saveBranding}>SAVE ORGANIZATION BRANDING</button>{brandingMessage&&<p className="member-success">{brandingMessage}</p>}</div></CompactSection>
  <CompactSection n="2" title="Generate The Recommitment Forms And Email" open={open==="2"} onOpen={()=>setOpen(open==="2"?"":"2")}><p>Generate the branded form and email. You receive a full version with graceful transition choices and a continue-serving version without the step-down option.</p><ReactivationStep2/></CompactSection>
  <CompactSection n="3" title="Complete Your Founder / Executive Director Audit" open={open==="3"} onOpen={()=>setOpen(open==="3"?"":"3")}><FounderBoardAudit/></CompactSection>
  <CompactSection n="4" title="Invite Your Board Members" open={open==="4"} onOpen={()=>setOpen(open==="4"?"":"4")}><RecommitmentInviteBoardMembers onChanged={()=>setRefreshKey(value=>value+1)}/></CompactSection>
  <CompactSection n="5" title="See Responses, Understand Each Person And Generate Their Call Script" open={open==="5"} onOpen={()=>setOpen(open==="5"?"":"5")}><p>Each person appears once. Analyze their response, view the interpretation and full response, then generate their individual call script from the same card.</p><ReactivationUnderstand/></CompactSection>
  <CompactSection n="6" title="Record Each Conversation And Create The Correct Next Step" open={open==="6"} onOpen={()=>setOpen(open==="6"?"":"6")}><p>Open each person's card, record what you agreed and select the final outcome. The correct portfolio or transition email will appear for that person.</p><ReactivationStep3 conclusionsOnly/></CompactSection>
  <CompactSection n="7" title="Your Recommitment Progress" open={open==="7"} onOpen={()=>setOpen(open==="7"?"":"7")}><ProgressSummary refreshKey={refreshKey}/></CompactSection>
  <div id="recommitment-support" className="recommitment-support" data-testid="recommitment-support"><SupportBox productKey="reactivation_self_guided" moduleNumber={1} supportTypes={["I have a question about Board Recommitment","I need help interpreting a board member response","I need help preparing for a conversation","I need help using the platform"]}/></div>
 </main></MemberShell>;
}
