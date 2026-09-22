import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { RefreshCw, Save } from "lucide-react";
import { DashboardPreviewSection } from "@/admin/DashboardPreviewSection";
import { HOMEPAGE_KEYS, VIDEO_KEYS } from "@/clean/platform";
import { MAIN_HOME_DEFAULTS } from "@/pages/MainHomePage";
import { FACILITATED_GAME_HOME_DEFAULTS } from "@/game/FacilitatedGamePage";
import { recruitmentHomeContent } from "@/content/siteContent";
import { GUIDED_PRODUCT_CONFIG } from "@/funnels/GuidedProductPages";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });

const stripIcon = (value) => {
  const { icon, ...copy } = value || {};
  return copy;
};

const LOCAL_DEFAULTS = {
  main: MAIN_HOME_DEFAULTS,
  recruitment: recruitmentHomeContent,
  "strategic-planning": stripIcon(GUIDED_PRODUCT_CONFIG["strategic-planning"]),
  "board-recommitment": stripIcon(GUIDED_PRODUCT_CONFIG["board-recommitment"]),
  "facilitated-game": FACILITATED_GAME_HOME_DEFAULTS,
};

export const BoardBuilderPathwaysSection = () => (
  <section data-testid="clean-board-builder-pathways">
    <div className="admin-funnel-numbers-head">
      <div>
        <h2>The 4 Board Builder Pathways</h2>
        <p>Open the real customer dashboard for each product. These are the four paid product houses preserved in the clean rebuild.</p>
      </div>
    </div>
    <DashboardPreviewSection />
  </section>
);

export function PlatformVideosSection() {
  const [videos,setVideos]=useState([]);
  const [drafts,setDrafts]=useState({});
  const [saving,setSaving]=useState("");
  const [message,setMessage]=useState("");

  const load=useCallback(async()=>{
    setMessage("");
    try{
      const response=await client.get("/admin/platform/videos");
      setVideos(response.data.videos||[]);
      setDrafts(Object.fromEntries((response.data.videos||[]).map(item=>[item.key,item.url||""])));
    }catch(error){setMessage(error.response?.data?.detail||"Could not load platform videos.");}
  },[]);
  useEffect(()=>{load()},[load]);

  const save=async(key)=>{
    setSaving(key);setMessage("");
    try{
      await client.put(`/admin/platform/videos/${key}`,{url:drafts[key]||""});
      setMessage("Video saved.");
      await load();
    }catch(error){setMessage(error.response?.data?.detail||"Could not save video.");}
    setSaving("");
  };

  const ordered=VIDEO_KEYS.map(([key,name,flow])=>videos.find(row=>row.key===key)||{key,name,flow,url:"",youtube_id:""});
  return <section data-testid="clean-platform-videos">
    <div className="admin-funnel-numbers-head"><div><h2>The 8 Videos Within The Platform</h2><p>Each of the four paid pathways has one demonstration video before Stripe and one onboarding video after payment.</p></div><button className="button button-back button-small" onClick={load}><RefreshCw size={15}/> Refresh</button></div>
    {message&&<p className="admin-message">{message}</p>}
    <div className="admin-preview-dashboard-grid">
      {ordered.map((video,index)=><article className="member-card" key={video.key}>
        <p className="eyebrow">VIDEO {index+1}</p>
        <h3>{video.name}</h3>
        <p>{video.flow}</p>
        <label className="admin-notes">YouTube URL or Video ID
          <input value={drafts[video.key]??""} onChange={event=>setDrafts({...drafts,[video.key]:event.target.value})} placeholder="https://youtu.be/..." />
        </label>
        <button className="button button-small" disabled={saving===video.key} onClick={()=>save(video.key)}><Save size={14}/> {saving===video.key?"SAVING…":"SAVE VIDEO"}</button>
      </article>)}
    </div>
  </section>;
}

const prettyLabel=(value)=>String(value)
  .replace(/_/g," ")
  .replace(/([a-z])([A-Z])/g,"$1 $2")
  .replace(/\b\w/g,letter=>letter.toUpperCase());

const cloneContent=(value)=>JSON.parse(JSON.stringify(value??{}));

const setContentAtPath=(content,path,value)=>{
  const next=cloneContent(content);
  let cursor=next;
  path.slice(0,-1).forEach(segment=>{cursor=cursor[segment]});
  cursor[path[path.length-1]]=value;
  return next;
};

const lockedTextKey=(key)=>/(?:_url|_href|_route|_path|_link)$/i.test(String(key));

function HomepageContentFields({value,path=[],label="",onChange}){
  if(Array.isArray(value)){
    return <fieldset className="member-card" style={{margin:"14px 0",padding:18}}>
      {label&&<legend style={{fontWeight:800,padding:"0 8px"}}>{label}</legend>}
      {value.map((item,index)=><HomepageContentFields key={index} value={item} path={[...path,index]} label={`${label||"Item"} ${index+1}`} onChange={onChange}/>)}
    </fieldset>;
  }
  if(value&&typeof value==="object"){
    return <div className="admin-homepage-field-group">
      {label&&<h3 style={{marginTop:20}}>{label}</h3>}
      {Object.entries(value).filter(([key])=>!lockedTextKey(key)).map(([key,item])=>
        <HomepageContentFields key={key} value={item} path={[...path,key]} label={prettyLabel(key)} onChange={onChange}/>
      )}
    </div>;
  }
  if(typeof value==="boolean"){
    return <label className="terms-check" style={{margin:"12px 0"}}><input type="checkbox" checked={value} onChange={event=>onChange(path,event.target.checked)}/><span>{label}</span></label>;
  }
  if(typeof value==="number"){
    return <label className="admin-notes"><strong>{label}</strong><input type="number" value={value} onChange={event=>onChange(path,Number(event.target.value))}/></label>;
  }
  const text=value==null?"":String(value);
  const long=text.length>90 || /text|headline|heading|sub|promise|description|title|outcome|step|intro|note/i.test(label);
  return <label className="admin-notes" style={{margin:"12px 0"}}><strong>{label}</strong>
    {long
      ? <textarea rows={Math.min(8,Math.max(2,Math.ceil(Math.max(text.length,80)/90)))} value={text} onChange={event=>onChange(path,event.target.value)}/>
      : <input value={text} onChange={event=>onChange(path,event.target.value)}/>}
  </label>;
}

export function HomepageTextSection(){
  const [pageKey,setPageKey]=useState(HOMEPAGE_KEYS[0][0]);
  const [content,setContent]=useState({});
  const [saving,setSaving]=useState(false);
  const [message,setMessage]=useState("");

  const load=useCallback(async(key)=>{
    setMessage("");
    try{
      const stored=(await axios.get(`${API}/platform/homepages/${key}`)).data.content||{};
      let defaults=LOCAL_DEFAULTS[key]||{};
      if(key==="board-fundraising-game"){
        defaults=(await axios.get(`${API}/game/content`)).data.content||{};
      }
      setContent({...cloneContent(defaults),...cloneContent(stored)});
    }catch(error){setMessage(error.response?.data?.detail||"Could not load this home page text.");}
  },[]);

  useEffect(()=>{load(pageKey)},[pageKey,load]);

  const updateField=(path,value)=>setContent(current=>setContentAtPath(current,path,value));

  const save=async()=>{
    setSaving(true);setMessage("");
    try{
      await client.put(`/admin/platform/homepages/${pageKey}`,{content});
      setMessage("Home page text saved.");
    }catch(error){
      setMessage(error.response?.data?.detail||"Could not save this home page.");
    }
    setSaving(false);
  };

  return <section data-testid="clean-homepage-editor">
    <div className="admin-funnel-numbers-head"><div><h2>Home Page Text Edit</h2><p>Choose one of the six public home pages and edit its words directly. Routes, dashboard destinations and product connections stay locked outside this editor.</p></div></div>
    <div className="admin-filters">
      <label>Home Page<select value={pageKey} onChange={event=>setPageKey(event.target.value)}>{HOMEPAGE_KEYS.map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></label>
      <button className="button button-back button-small" onClick={()=>load(pageKey)}><RefreshCw size={15}/> Reload Saved Text</button>
    </div>
    <div className="admin-homepage-text-fields">
      <HomepageContentFields value={content} onChange={updateField}/>
    </div>
    {message&&<p className="admin-message">{message}</p>}
    <button className="button" disabled={saving} onClick={save}><Save size={15}/> {saving?"SAVING…":"SAVE HOME PAGE TEXT"}</button>
  </section>;
}

const LABELS={
  main:"Main Home Page",
  recruitment:"Board Recruitment",
  "board-fundraising-game":"Board Fundraising Game",
  "strategic-planning":"Strategic Planning",
  "board-recommitment":"Board Recommitment",
  "facilitated-game":"Let's Organize Your Board Fundraising Game",
  "board-applicant-network":"Board Applicant Network",
};

const duration=(seconds)=>{
  const value=Number(seconds||0);
  if(value<60)return `${Math.round(value)} sec`;
  return `${Math.floor(value/60)}m ${Math.round(value%60)}s`;
};

export function PlatformAnalyticsSection(){
  const [data,setData]=useState(null);
  const [error,setError]=useState("");
  const load=useCallback(async()=>{
    setError("");
    try{setData((await client.get("/admin/platform-analytics")).data)}
    catch(err){setError(err.response?.data?.detail||"Could not load platform analytics.");}
  },[]);
  useEffect(()=>{load()},[load]);
  const flows=useMemo(()=>data?.flows||[],[data]);

  return <section data-testid="clean-platform-analytics">
    <div className="admin-funnel-numbers-head"><div><h2>Platform Funnel Analytics</h2><p>One view of traffic, contact capture, video engagement, Stripe movement, dashboard entry, completion and average active use.</p></div><button className="button button-back button-small" onClick={load}><RefreshCw size={15}/> Refresh</button></div>
    {error&&<p className="submit-error">{error}</p>}
    {!data?<p>Loading analytics…</p>:<>
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr>
        {["Flow","Unique Home Visitors","Contact Details","Checkout Clicks","Stripe Sessions","Paid","Dashboard Entries","Completed","Avg. Platform Use"].map(x=><th key={x}>{x}</th>)}
      </tr></thead><tbody>{flows.map(row=><tr key={row.flow}>
        <td><strong>{LABELS[row.flow]||row.flow}</strong></td>
        <td>{row.homepage_visitors}</td><td>{row.contacts_entered}</td><td>{row.checkout_started}</td><td>{row.stripe_sessions}</td><td>{row.purchases}</td><td>{row.dashboard_entered}</td><td>{row.platform_completed}</td><td>{duration(row.average_use_seconds)}</td>
      </tr>)}</tbody></table></div>

      <h3 style={{marginTop:32}}>Video Watch Rates</h3>
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Video</th><th>Flow</th><th>Started</th><th>Completed</th><th>Average Watch Rate</th></tr></thead><tbody>
        {VIDEO_KEYS.map(([key,name,flow])=>{
          const row=(data.videos||[]).find(item=>item.video_key===key)||{};
          return <tr key={key}><td>{name}</td><td>{LABELS[flow]||flow}</td><td>{row.viewers||0}</td><td>{row.completed||0}</td><td>{Number(row.average_watch_rate||0).toFixed(1)}%</td></tr>;
        })}
      </tbody></table></div>
    </>}
  </section>;
}
