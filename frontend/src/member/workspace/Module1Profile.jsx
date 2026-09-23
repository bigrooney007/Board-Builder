import React, { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Plus, Trash2 } from "lucide-react";
import { memberApi } from "../api";
import { MaterialCard } from "./MaterialCard";
import { useMaterials } from "./WorkspaceModules";

const emptyRole = () => ({
  role_name: "",
  why_this_person_is_important: "",
  how_this_person_can_support: "",
});

export const Module1Profile = ({ onConfirmed }) => {
  const { byType, refresh } = useMaterials();
  const [roles,setRoles]=useState([]);
  const [desiredCount,setDesiredCount]=useState(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState("");
  const [message,setMessage]=useState("");
  const [error,setError]=useState("");

  const load=useCallback(async()=>{
    setLoading(true);
    try{
      const response=await memberApi.get("/workspace/board-profiles");
      setRoles(response.data.priority_roles||[]);
      setDesiredCount(response.data.desired_count||null);
      setError("");
    }catch(err){
      setError(err.response?.data?.detail||"We could not load the recommended Board Members.");
    }
    setLoading(false);
  },[]);

  useEffect(()=>{load()},[load,byType.powerhouse_board_blueprint?.material_id,byType.powerhouse_board_blueprint?.current_version]);

  const ensureSixQuestions=async()=>{
    const assessment=(await memberApi.get("/recruit/free/member-assessment/current")).data;
    const answers=assessment?.answers||{};
    const required=["mission","current_board","desired_board_members","support_needs","board_type","why_join"];
    if(required.some(key=>!String(answers[key]||"").trim()))throw new Error("Complete all six Recruitment Questions first.");
    await memberApi.post("/recruit/free/"+assessment.token+"/result");
    await memberApi.post("/workspace/profile/confirm");
    await refresh();
    await load();
    if(onConfirmed)onConfirmed();
    return false;
  };

  const change=(index,key,value)=>setRoles(current=>current.map((role,i)=>i===index?{...role,[key]:value}:role));
  const remove=(index)=>setRoles(current=>current.filter((_,i)=>i!==index));
  const add=()=>setRoles(current=>[...current,emptyRole()]);

  const save=async()=>{
    setBusy("save");setMessage("");setError("");
    try{
      const response=await memberApi.put("/workspace/board-profiles",{priority_roles:roles});
      setRoles(response.data.priority_roles||[]);
      await refresh();
      setMessage("Your Board Member profiles are saved.");
      return response.data.material;
    }catch(err){
      setError(err.response?.data?.detail||"We could not save these Board Member profiles.");
      return null;
    }finally{setBusy("")}
  };

  const approve=async()=>{
    setBusy("approve");setMessage("");setError("");
    try{
      const response=await memberApi.put("/workspace/board-profiles",{priority_roles:roles});
      const material=response.data.material;
      await memberApi.post("/workspace/materials/"+material.material_id+"/approve");
      await refresh();
      await load();
      setMessage("Approved. We are already preparing your Board Application and recruitment campaign materials underneath.");
      if(onConfirmed)onConfirmed();
    }catch(err){
      setError(err.response?.data?.detail||"We could not approve these Board Member profiles.");
    }
    setBusy("");
  };

  const material=byType.powerhouse_board_blueprint;
  const approved=material?.status==="Approved";
  const exactCountReady=!desiredCount||roles.length===desiredCount;

  if(loading&&!material)return <p>Opening your Board Member recommendations…</p>;

  if(!roles.length){
    return <div data-testid="module1-workspace">
      <section className="workspace-panel">
        <h2>Identify The Board Members Your Organization Needs</h2>
        <p className="material-description">We use your mission, present Board, the people you believe you need, the areas needing support, the Board model you want to build and your reason someone should join.</p>
        <MaterialCard
          type="powerhouse_board_blueprint"
          title="The Board Members Your Organization Needs"
          buttonLabel="PREPARE MY BOARD MEMBER RECOMMENDATIONS"
          description="The platform should already be preparing this result after your sixth answer. Use this button only if preparation needs to be restarted."
          material={material}
          refresh={async()=>{await refresh();await ensureSixQuestions();}}
          beforeGenerate={ensureSixQuestions}
          approvable
        />
        {error&&<p className="submit-error">{error}</p>}
      </section>
    </div>;
  }

  return <div data-testid="module1-workspace">
    <section className="workspace-panel sgr-board-profile-review">
      <div className="sgr-board-profile-head">
        <div>
          <p className="eyebrow">YOUR RECOMMENDED BOARD</p>
          <h2>The Board Members Your Organization Needs</h2>
          <p className="material-description">Review each recommendation. Change the role, sharpen the reasoning, replace a person or add your own idea. The approved list becomes the foundation for your recruitment campaign.</p>
        </div>
        <div className={"sgr-profile-count "+(exactCountReady?"ready":"warning")}>
          <strong>{roles.length}{desiredCount?"/"+desiredCount:""}</strong>
          <span>{desiredCount?"Board Members Requested":"Recommended Profiles"}</span>
        </div>
      </div>

      {roles.map((role,index)=><article className="sgr-board-profile-card" key={index}>
        <div className="sgr-board-profile-card-top">
          <span>{String(index+1).padStart(2,"0")}</span>
          <button className="button button-back button-small" onClick={()=>remove(index)} disabled={roles.length===1||approved}><Trash2 size={14}/> REMOVE</button>
        </div>
        <label className="field"><span>Board Member Profile / Role</span>
          <input value={role.role_name||""} disabled={approved} onChange={event=>change(index,"role_name",event.target.value)}/>
        </label>
        <label className="field"><span>Why Your Organization Needs This Person</span>
          <textarea rows="3" value={role.why_this_person_is_important||""} disabled={approved} onChange={event=>change(index,"why_this_person_is_important",event.target.value)}/>
        </label>
        <label className="field"><span>The Role They Can Play</span>
          <textarea rows="3" value={role.how_this_person_can_support||""} disabled={approved} onChange={event=>change(index,"how_this_person_can_support",event.target.value)}/>
        </label>
      </article>)}

      {!approved&&<div className="sgr-row-actions">
        <button className="button button-back" onClick={add}><Plus size={15}/> ADD MY OWN BOARD MEMBER PROFILE</button>
        <button className="button button-back" disabled={busy==="save"} onClick={save}>{busy==="save"?"SAVING…":"SAVE MY CHANGES"}</button>
        <button className="button" disabled={busy==="approve"||!exactCountReady||roles.some(role=>!String(role.role_name||"").trim())} onClick={approve}>
          <CheckCircle2 size={15}/> {busy==="approve"?"APPROVING…":"APPROVE THESE BOARD MEMBERS"}
        </button>
      </div>}
      {!exactCountReady&&desiredCount&&<p className="workspace-note">You told us you want to recruit {desiredCount} new Board Members. Keep exactly {desiredCount} profiles by replacing, editing, adding or removing profiles before approval.</p>}
      {approved&&<p className="member-success"><CheckCircle2 size={15}/> Approved. These profiles now drive your Board Application and recruitment campaign materials.</p>}
      {message&&<p className="member-success">{message}</p>}
      {error&&<p className="submit-error">{error}</p>}
    </section>
  </div>;
};
