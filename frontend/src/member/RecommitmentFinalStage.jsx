import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { memberApi } from "./api";
import { OutcomeEmailWorkflow, PortfolioWorkflow } from "./ReactivationStep5";

const OUTCOMES = [
  "Continuing as an Active Board Member",
  "Transitioning to an Advisory Role",
  "Stepping Down From the Board",
];

const MemberDecision = ({ row, reload }) => {
  const id=row.member_record_id;
  const [conclusion,setConclusion]=useState(row.conversation_conclusion||"");
  const [outcome,setOutcome]=useState(row.conversation_outcome||"");
  const [role,setRole]=useState(row.confirmed_role||row.role||"");
  const [busy,setBusy]=useState("");
  const [message,setMessage]=useState("");

  useEffect(()=>{
    setConclusion(row.conversation_conclusion||"");
    setOutcome(row.conversation_outcome||"");
    setRole(row.confirmed_role||row.role||"");
  },[row.conversation_conclusion,row.conversation_outcome,row.confirmed_role,row.role]);

  const saveDecision=async()=>{
    setBusy("decision");setMessage("");
    try{
      if(!conclusion.trim()||!outcome){setMessage("Record what you agreed and choose the final outcome.");setBusy("");return}
      if(["Continuing as an Active Board Member","Transitioning to an Advisory Role"].includes(outcome)&&!role.trim()){
        setMessage("Confirm or edit this person's final role before continuing.");setBusy("");return;
      }
      await memberApi.put(`/reactivation/board-members/${id}/conclusion`,{conclusion:conclusion.trim()});
      await memberApi.put(`/reactivation/board-members/${id}/outcome`,{outcome});
      if(["Continuing as an Active Board Member","Transitioning to an Advisory Role"].includes(outcome)){
        await memberApi.put(`/reactivation/board-members/${id}/confirmed-role`,{role:role.trim()});
      }
      setMessage("Final outcome saved.");
      await reload();
    }catch(error){setMessage(error.response?.data?.detail||"We could not save the final outcome.");}
    setBusy("");
  };

  const decisionReady=Boolean(row.conversation_conclusion&&row.conversation_outcome);
  const continuing=["Continuing as an Active Board Member","Transitioning to an Advisory Role"].includes(row.conversation_outcome);
  const roleReady=!continuing||Boolean(row.confirmed_role);

  return <article className="member-card recommitment-decision-card" data-testid={`recommitment-decision-${id}`}>
    <div className="recommitment-decision-head">
      <div><h3>{row.name}</h3><p>{row.email}</p></div>
      {row.conversation_outcome&&<span className="sgr-stage-status complete">{row.conversation_outcome}</span>}
    </div>
    <div className="recommitment-response-choice">
      <span>What they chose on the form</span>
      <strong>{row.response?.recommitment||row.recommitment||"Response received"}</strong>
    </div>

    <label className="field"><span>What did you and {row.name.split(" ")[0]} actually agree in the conversation?</span>
      <textarea rows="5" value={conclusion} onChange={e=>setConclusion(e.target.value)} placeholder="Record the actual agreement, responsibilities, transition details and next steps. This becomes the authoritative record."/>
    </label>
    <label className="field"><span>Final Path</span>
      <select value={outcome} onChange={e=>setOutcome(e.target.value)}>
        <option value="">Choose the final outcome…</option>
        {OUTCOMES.map(option=><option key={option}>{option}</option>)}
      </select>
    </label>

    {["Continuing as an Active Board Member","Transitioning to an Advisory Role"].includes(outcome)&&(
      <label className="field"><span>{outcome==="Transitioning to an Advisory Role"?"Confirmed Advisory Role":"Confirmed Board Role / Responsibility"}</span>
        <input value={role} onChange={e=>setRole(e.target.value)} placeholder="Edit this until it reflects the role you actually agreed."/>
      </label>
    )}

    <button className="button" onClick={saveDecision} disabled={busy==="decision"}>
      <CheckCircle2 size={15}/> {busy==="decision"?"SAVING…":"SAVE FINAL DECISION"}
    </button>
    {message&&<p className={message.includes("saved")?"member-success":"submit-error"}>{message}</p>}

    {decisionReady&&roleReady&&row.conversation_outcome==="Continuing as an Active Board Member"&&(
      <div className="recommitment-next-output">
        <h4>Active Board Member Next Step</h4>
        <p>Generate the Portfolio only after the role above reflects what you actually agreed. Then prepare the Portfolio email, copy it or send it directly from the platform.</p>
        <PortfolioWorkflow row={row} reload={reload}/>
      </div>
    )}
    {decisionReady&&roleReady&&row.conversation_outcome==="Transitioning to an Advisory Role"&&(
      <div className="recommitment-next-output">
        <h4>Advisory Board Next Step</h4>
        <p>Generate an Advisory Board Member Portfolio around the role you confirmed, then prepare the transition email.</p>
        <PortfolioWorkflow row={row} reload={reload}/>
        <OutcomeEmailWorkflow row={row} label="GENERATE ADVISORY BOARD TRANSITION EMAIL" reload={reload}/>
      </div>
    )}
    {decisionReady&&row.conversation_outcome==="Stepping Down From the Board"&&(
      <div className="recommitment-next-output">
        <h4>Graceful Board Departure</h4>
        <p>No Board Portfolio is required. Generate the departure email using the agreement you recorded above.</p>
        <OutcomeEmailWorkflow row={row} label="GENERATE BOARD DEPARTURE EMAIL" reload={reload}/>
      </div>
    )}
  </article>;
};

export default function RecommitmentFinalStage(){
  const[data,setData]=useState(null);
  const[error,setError]=useState("");
  const load=useCallback(async()=>{
    try{setData((await memberApi.get("/reactivation/my-board")).data);setError("")}
    catch(error){setError(error.response?.data?.detail||"We could not load the final Board decisions.")}
  },[]);
  useEffect(()=>{load()},[load]);

  const rows=useMemo(()=>data?Object.values(data.groups||{}).flat().filter((row)=>row.status==="COMPLETED"):[],[data]);

  if(error)return <p className="submit-error">{error}</p>;
  if(!data)return <p>Opening final Board decisions…</p>;

  return <div className="recommitment-final-stage" data-testid="recommitment-final-stage">
    {!rows.length&&<section className="member-card"><p><strong>No Recommitment responses have been received yet.</strong></p><p>Board Members appear here automatically after completing a form.</p></section>}
    {rows.map(row=><MemberDecision key={row.member_record_id} row={row} reload={load}/>)}
  </div>;
}
