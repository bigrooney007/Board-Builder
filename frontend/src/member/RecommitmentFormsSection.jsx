import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Copy, Mail, RefreshCw, Save } from "lucide-react";
import { memberApi } from "./api";
import RecommitmentInviteBoardMembers from "./RecommitmentInviteBoardMembers";

const VARIANTS = [
  ["active_advisory", "Active Board / Advisory Board", "Use this when you do not want to offer stepping down. The Board Member chooses between recommitting as an active Board Member and moving into an Advisory Board role."],
  ["full", "Full Recommitment / Transition", "Use this when you want to give the Board Member all three choices: remain active and step up, move into Advisory Board service, or step down gracefully."],
];

const insertLink = (body, link) => {
  const text=String(body||"");
  if (/\[[^\]]+\]/.test(text)) return text.replace(/\[[^\]]+\]/, link);
  return text+"\n\n"+link;
};

export default function RecommitmentFormsSection({ onChanged = () => {} }) {
  const [form,setForm]=useState(null);
  const [intro,setIntro]=useState("");
  const [variant,setVariant]=useState("active_advisory");
  const [email,setEmail]=useState(null);
  const [busy,setBusy]=useState("");
  const [message,setMessage]=useState("");
  const [copied,setCopied]=useState("");

  const loadForm=useCallback(async()=>{
    try{
      const response=await memberApi.get("/reactivation/recommitment-form");
      setForm(response.data);
      setIntro(response.data.intro_text||"");
    }catch(error){setMessage(error.response?.data?.detail||"We could not load the Recommitment Forms.");}
  },[]);

  const loadEmail=useCallback(async()=>{
    if(form?.status!=="Approved")return;
    try{
      const response=await memberApi.get("/reactivation/recommitment-email-draft",{params:{variant}});
      setEmail(response.data);
    }catch(error){setMessage(error.response?.data?.detail||"We could not prepare the email.");}
  },[form?.status,variant]);

  useEffect(()=>{loadForm()},[loadForm]);
  useEffect(()=>{loadEmail()},[loadEmail]);

  const generate=async()=>{
    setBusy("generate");setMessage("");
    try{
      const response=await memberApi.post("/reactivation/recommitment-form/generate");
      setForm(response.data);setIntro(response.data.intro_text||"");
      setMessage("Both Recommitment Form versions are prepared. Review the introduction and approve the forms.");
    }catch(error){setMessage(error.response?.data?.detail||"The forms could not be generated.");}
    setBusy("");
  };

  const saveIntro=async()=>{
    setBusy("form-save");setMessage("");
    try{
      await memberApi.put("/reactivation/recommitment-form",{text:intro});
      await loadForm();
      setMessage("Form introduction saved.");
    }catch(error){setMessage(error.response?.data?.detail||"The form could not be saved.");}
    setBusy("");
  };

  const approveForm=async()=>{
    setBusy("form-approve");setMessage("");
    try{
      await memberApi.post("/reactivation/recommitment-form/approve");
      await loadForm();
      setMessage("Recommitment Forms approved. Both links are now ready to use.");
      onChanged();
    }catch(error){setMessage(error.response?.data?.detail||"The form could not be approved.");}
    setBusy("");
  };

  const saveEmail=async()=>{
    if(!email)return;
    setBusy("email-save");setMessage("");
    try{
      const response=await memberApi.put("/reactivation/recommitment-email-draft",{variant,subject:email.subject,body:email.body});
      setEmail(response.data);
      setMessage("Email saved as a draft.");
    }catch(error){setMessage(error.response?.data?.detail||"The email could not be saved.");}
    setBusy("");
  };

  const approveEmail=async()=>{
    setBusy("email-approve");setMessage("");
    try{
      const response=await memberApi.post("/reactivation/recommitment-email-draft/approve",null,{params:{variant}});
      setEmail(response.data);
      setMessage("Email approved and ready to copy.");
    }catch(error){setMessage(error.response?.data?.detail||"The email could not be approved.");}
    setBusy("");
  };

  const copy=async(text,key)=>{
    try{await navigator.clipboard.writeText(text)}catch{window.prompt("Copy this:",text)}
    setCopied(key);setTimeout(()=>setCopied(""),2200);
  };

  if(!form)return <p>Opening your Recommitment Forms…</p>;

  return <div className="recommitment-forms-stage" data-testid="recommitment-forms-stage">
    <section className="member-card">
      <p className="eyebrow">THE FORM</p>
      <h2>Prepare The Two Recommitment Form Versions</h2>
      <p>Both forms use the same organization context and Board Member Profile questions. The only difference is whether stepping down is offered as a choice.</p>
      {form.status==="NONE"?(
        <button className="button" disabled={busy==="generate"} onClick={generate}>{busy==="generate"?"PREPARING…":"GENERATE MY RECOMMITMENT FORMS"}</button>
      ):(
        <>
          <label className="field"><span>Introduction Your Board Members Will See</span><textarea rows="9" value={intro} onChange={e=>setIntro(e.target.value)}/></label>
          <div className="sgr-row-actions">
            <button className="button button-outline" onClick={saveIntro} disabled={busy==="form-save"}><Save size={15}/> {busy==="form-save"?"SAVING…":"SAVE CHANGES"}</button>
            <button className="button" onClick={approveForm} disabled={busy==="form-approve"||form.status==="Approved"}><CheckCircle2 size={15}/> {form.status==="Approved"?"FORMS APPROVED":busy==="form-approve"?"APPROVING…":"APPROVE THE FORMS"}</button>
          </div>
        </>
      )}
    </section>

    {form.status==="Approved"&&(
      <>
        <section className="recommitment-form-variants">
          {VARIANTS.map(([key,title,description])=>{
            const link=key==="active_advisory"?form.active_advisory_link:form.full_link;
            return <article className="member-card" key={key}>
              <p className="eyebrow">{key==="active_advisory"?"NO STEP-DOWN OPTION":"INCLUDES STEP-DOWN OPTION"}</p>
              <h3>{title}</h3><p>{description}</p>
              <div className="recommitment-link-box">{link}</div>
              <button className="button button-outline" onClick={()=>copy(link,key)}><Copy size={14}/> {copied===key?"COPIED":"COPY FORM LINK"}</button>
            </article>
          })}
        </section>

        <section className="member-card">
          <p className="eyebrow">THE EMAIL</p>
          <h2>Prepare The Email To Send With The Form</h2>
          <p>Choose which form the email should lead to. The correct link is inserted automatically when you copy it.</p>
          <div className="choice-grid recommitment-variant-choice">
            {VARIANTS.map(([key,title])=><label className={`choice ${variant===key?"selected":""}`} key={key}><input type="radio" checked={variant===key} onChange={()=>setVariant(key)}/><span>{title}</span></label>)}
          </div>
          {email&&<>
            <label className="field"><span>Subject</span><input value={email.subject||""} onChange={e=>setEmail({...email,subject:e.target.value,status:"Draft"})}/></label>
            <label className="field"><span>Email</span><textarea rows="13" value={email.body||""} onChange={e=>setEmail({...email,body:e.target.value,status:"Draft"})}/></label>
            <p className="workspace-note"><strong>Form link inserted automatically:</strong> {email.form_link}</p>
            <div className="sgr-row-actions">
              <button className="button button-outline" onClick={saveEmail} disabled={busy==="email-save"}><Save size={14}/> SAVE EMAIL</button>
              <button className="button" onClick={approveEmail} disabled={busy==="email-approve"||email.status==="Approved"}><CheckCircle2 size={14}/> {email.status==="Approved"?"EMAIL APPROVED":"APPROVE EMAIL"}</button>
              <button className="button button-outline" disabled={email.status!=="Approved"} onClick={()=>copy(`Subject: ${email.subject}\n\n${insertLink(email.body,email.form_link)}`,"email")}><Copy size={14}/> {copied==="email"?"COPIED":"COPY APPROVED EMAIL"}</button>
            </div>
          </>}
        </section>

        <section className="member-card">
          <p className="eyebrow">SEND FROM THE PLATFORM</p>
          <h2>Send A Personal Recommitment Form Directly</h2>
          <p>Add a Board Member's name and email, choose the form they should receive and send it directly. You can resend the invitation later if needed.</p>
          <RecommitmentInviteBoardMembers onChanged={onChanged}/>
        </section>
      </>
    )}
    {message&&<p className={/approved|saved|prepared|ready/i.test(message)?"member-success":"submit-error"}>{message}</p>}
  </div>;
}
