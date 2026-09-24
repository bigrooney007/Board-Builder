import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { RefreshCw, Save, Volume2 } from "lucide-react";

const API=`${process.env.REACT_APP_BACKEND_URL}/api`;
const client=axios.create({baseURL:API,withCredentials:true});

const GROUPS=[
  {
    key:"recruitment", title:"Board Recruitment Dashboard Audio",
    ids:[
      "dash_rct_questions","dash_rct_identify","dash_rct_materials","dash_rct_launch","dash_rct_applicants",
      "dash_rct_interviews","dash_rct_references","dash_rct_background","dash_rct_onboarding_prep",
      "dash_rct_onboarding_session","dash_rct_portfolios",
    ],
  },
  {
    key:"fundraising", title:"Board Fundraising Game Dashboard Audio",
    ids:["dash_bfg_founder_game","dash_bfg_meeting","dash_bfg_board","dash_bfg_group","dash_bfg_strategy","dash_bfg_execution"],
  },
  {
    key:"recommitment", title:"Board Recommitment Dashboard Audio",
    ids:["dash_rec_questions","dash_rec_forms","dash_rec_responses","dash_rec_decisions"],
  },
  {
    key:"strategic", title:"Strategic Planning Dashboard Audio",
    ids:["dash_sp_organization","dash_sp_meeting","dash_sp_founder_form","dash_sp_board_forms","dash_sp_facilitation","dash_sp_session","dash_sp_plan"],
  },
];

const Status=({value})=>{
  const text=value==="ready"?"READY":value==="needs_regeneration"?"NEEDS REGENERATION":"MISSING";
  const color=value==="ready"?"#059669":value==="needs_regeneration"?"#92400e":"#b91c1c";
  return <strong style={{fontSize:11,color}}>{text}</strong>;
};

export default function DashboardSectionAudioAdmin(){
  const[assets,setAssets]=useState([]);
  const[busy,setBusy]=useState("");
  const[message,setMessage]=useState("");

  const load=useCallback(async()=>{
    setMessage("");
    try{
      const response=await client.get("/admin/game/voice/assets");
      const wanted=new Set(GROUPS.flatMap(group=>group.ids));
      setAssets((response.data.assets||[]).filter(asset=>wanted.has(asset.narration_id)));
    }catch(error){
      setMessage(error.response?.data?.detail||"Could not load dashboard audio scripts.");
    }
  },[]);

  useEffect(()=>{load()},[load]);

  const byId=useMemo(()=>Object.fromEntries(assets.map(asset=>[asset.narration_id,asset])),[assets]);

  const changeText=(id,text)=>setAssets(current=>current.map(asset=>asset.narration_id===id?{...asset,text}:asset));

  const save=async(asset)=>{
    setBusy("save:"+asset.narration_id);setMessage("");
    try{
      await client.put("/admin/game/voice/assets/"+asset.narration_id,{text:asset.text||""});
      setMessage("Dashboard audio script saved. Generate the live audio when you are happy with the script.");
      await load();
    }catch(error){setMessage(error.response?.data?.detail||"Could not save this script.");}
    setBusy("");
  };

  const generate=async(asset,environment)=>{
    setBusy(environment+":"+asset.narration_id);setMessage("");
    try{
      await client.post("/admin/game/voice/assets/"+asset.narration_id+"/generate",{
        environment,
        force:environment==="live"&&asset.live?.status==="ready",
      });
      setMessage((environment==="live"?"Live":"Test")+" dashboard audio generated. The app will use the updated asset without another deployment.");
      await load();
    }catch(error){setMessage(error.response?.data?.detail||"Audio generation failed.");}
    setBusy("");
  };

  return <section data-testid="admin-dashboard-section-audio" style={{marginTop:38}}>
    <div className="admin-funnel-numbers-head">
      <div>
        <h2>Contextual Audio For The 4 Dashboards</h2>
        <p>Edit each section script here, generate a Test clip if you want to hear it first, then generate Live audio with ElevenLabs. Audio is never generated automatically. Once Live audio is generated, the matching dashboard section uses it immediately from the database without a new deployment.</p>
      </div>
      <button className="button button-back button-small" onClick={load}><RefreshCw size={15}/> Refresh</button>
    </div>
    {message&&<p className="admin-message">{message}</p>}
    {GROUPS.map(group=><details key={group.key} open className="admin-import-panel" style={{marginTop:18}}>
      <summary style={{cursor:"pointer",fontWeight:800,fontSize:17}}>{group.title} · {group.ids.length} sections</summary>
      <div className="admin-preview-dashboard-grid" style={{marginTop:14}}>
        {group.ids.map((id,index)=>{
          const asset=byId[id];
          if(!asset)return <article className="member-card" key={id}><p className="eyebrow">SECTION {index+1}</p><h3>{id}</h3><p>Script asset is not available yet.</p></article>;
          return <article className="member-card" key={id} data-testid={"dashboard-audio-admin-"+id}>
            <p className="eyebrow">SECTION {index+1} AUDIO</p>
            <h3>{asset.label}</h3>
            <p className="material-meta">Script v{asset.script_version||1} · Test: <Status value={asset.test?.status}/> · Live: <Status value={asset.live?.status}/></p>
            <label className="admin-notes">Audio Script
              <textarea rows={9} value={asset.text||""} onChange={event=>changeText(id,event.target.value)}/>
            </label>
            <div className="material-actions">
              <button className="button button-small" disabled={!!busy} onClick={()=>save(asset)}><Save size={14}/> {busy==="save:"+id?"SAVING…":"SAVE SCRIPT"}</button>
              <button className="button button-back button-small" disabled={!!busy} onClick={()=>generate(asset,"test")}>
                <Volume2 size={14}/> {busy==="test:"+id?"GENERATING…":asset.test?.status==="ready"?"REGENERATE TEST AUDIO":"GENERATE TEST AUDIO"}
              </button>
              <button className="button button-small" disabled={!!busy} onClick={()=>generate(asset,"live")}>
                <Volume2 size={14}/> {busy==="live:"+id?"GENERATING…":asset.live?.status==="ready"?"REGENERATE LIVE AUDIO":"GENERATE LIVE AUDIO"}
              </button>
            </div>
            {asset.live?.status==="ready"&&<audio controls preload="none" style={{width:"100%",marginTop:10}}
              src={`${API}/game/voice/audio/${id}?v=live${asset.live?.version||0}`}/>}
          </article>;
        })}
      </div>
    </details>)}
  </section>;
}
