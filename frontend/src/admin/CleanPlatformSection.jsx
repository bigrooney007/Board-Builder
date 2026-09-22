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

export function HomepageTextSection(){
  const [pageKey,setPageKey]=useState(HOMEPAGE_KEYS[0][0]);
  const [draft,setDraft]=useState("{}");
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
      setDraft(JSON.stringify({...defaults,...stored},null,2));
    }catch(error){setMessage(error.response?.data?.detail||"Could not load this home page text.");}
  },[]);

  useEffect(()=>{load(pageKey)},[pageKey,load]);

  const save=async()=>{
    setSaving(true);setMessage("");
    try{
      const content=JSON.parse(draft);
      await client.put(`/admin/platform/homepages/${pageKey}`,{content});
      setMessage("Home page text saved.");
    }catch(error){
      setMessage(error instanceof SyntaxError?"The text editor contains invalid JSON. Check brackets, commas and quotation marks.":error.response?.data?.detail||"Could not save this home page.");
    }
    setSaving(false);
  };

  return <section data-testid="clean-homepage-editor">
    <div className="admin-funnel-numbers-head"><div><h2>Home Page Text Edit</h2><p>These are the six public home pages in the clean house. The saved copy becomes the live copy for that page without changing its route or product connection.</p></div></div>
    <div className="admin-filters">
      <label>Home Page<select value={pageKey} onChange={event=>setPageKey(event.target.value)}>{HOMEPAGE_KEYS.map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></label>
      <button className="button button-back button-small" onClick={()=>load(pageKey)}><RefreshCw size={15}/> Reload</button>
    </div>
    <label className="admin-notes"><strong>Page text</strong><textarea rows={34} spellCheck="false" value={draft} onChange={event=>setDraft(event.target.value)} style={{fontFamily:"ui-monospace, SFMono-Regular, Menlo, monospace",fontSize:13,lineHeight:1.5}} /></label>
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
        {["Flow","Home/Page Visitors","Contact Details","Checkout Clicks","Stripe Sessions","Paid","Dashboard Entries","Completed","Avg. Platform Use"].map(x=><th key={x}>{x}</th>)}
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
