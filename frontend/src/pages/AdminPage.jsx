import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Download, LogOut, RefreshCw, Search, Users } from "lucide-react";
import { StrategicPlanningSection } from "@/admin/StrategicPlanningSection";
import {
  BoardBuilderPathwaysSection,
  HomepageTextSection,
  PlatformAnalyticsSection,
  PlatformVideosSection,
} from "@/admin/CleanPlatformSection";
import { adminPageText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const client = axios.create({ baseURL: API, withCredentials: true });
const statuses = ["New Applicant", "Active", "Under Review", "Contacted", "Presented to Nonprofit", "Interviewing", "Placed on Board", "Paused", "Withdrawn"];
const blankFilters = { search: "", country: "", state_region: "", cause: "", skill: "", board_type: "", fundraising: "", availability: "" };

function Login({ onLogin }) {
  const [email,setEmail]=useState("");
  const [password,setPassword]=useState("");
  const [error,setError]=useState("");
  const submit=async(event)=>{
    event.preventDefault();setError("");
    try{const response=await client.post("/auth/login",{email,password});onLogin(response.data)}
    catch(err){setError(typeof err.response?.data?.detail==="string"?err.response.data.detail:"Login failed.")}
  };
  return <main className="admin-login-page" data-testid="admin-login-page"><form className="admin-login-card" onSubmit={submit}>
    <div className="admin-login-icon"><Users size={27}/></div><p className="eyebrow">Owner access</p>
    <h1>Nonprofit Board Builder Administration</h1><p>{adminPageText.privateAccessForTheNonprofit}</p>
    <label>Email<input type="email" value={email} onChange={event=>setEmail(event.target.value)} required data-testid="admin-email-input"/></label>
    <label>Password<input type="password" value={password} onChange={event=>setPassword(event.target.value)} required data-testid="admin-password-input"/></label>
    {error&&<p className="submit-error" data-testid="admin-login-error">{error}</p>}
    <button className="button" type="submit" data-testid="admin-login-button">Log In</button>
  </form></main>;
}

function ImportApplicants({ refresh }) {
  const [open,setOpen]=useState(false);
  const [file,setFile]=useState(null);
  const [consent,setConsent]=useState(false);
  const [preview,setPreview]=useState(null);
  const [result,setResult]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");

  const send=async(commit)=>{
    setError("");
    if(!file){setError("Choose a CSV file first.");return}
    if(!consent){setError("Please confirm you have permission to contact these people.");return}
    setBusy(true);
    const form=new FormData();form.append("file",file);
    try{
      const response=await client.post(`/admin/applicants-import?confirmed=true&commit=${commit}`,form);
      if(commit){setResult(response.data.summary);setPreview(null);refresh()}else{setResult(null);setPreview(response.data)}
    }catch(err){setError(typeof err.response?.data?.detail==="string"?err.response.data.detail:"Import failed.")}
    setBusy(false);
  };
  const rows=(summary,isPreview)=>[
    [isPreview?"New applicants to import":"Imported",summary.imported],
    [isPreview?"Existing applicants to update":"Updated",summary.updated],
    ["Skipped duplicate",summary.skipped_duplicate],
    ["Skipped invalid email",summary.skipped_invalid_email],
    ["Skipped unsubscribed or withdrawn",summary.skipped_unsubscribed],
    ...(isPreview?[]:[["Failed",summary.failed],["Synced to Resend",summary.resend_synced]]),
  ];

  return <>
    <button className="button button-back button-small" onClick={()=>setOpen(!open)} data-testid="admin-import-toggle">Import Board Applicants</button>
    {open&&<div className="admin-import-panel" data-testid="admin-import-panel">
      <h3>Import Existing Board Applicants</h3>
      <p>Upload your CSV, preview what will happen, then confirm the import.</p>
      <input type="file" accept=".csv,text/csv" onChange={event=>{setFile(event.target.files[0]);setPreview(null);setResult(null)}} data-testid="admin-import-file"/>
      <label className="terms-check"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)} data-testid="admin-import-consent"/><span>I confirm these people gave permission to be contacted about board opportunities.</span></label>
      {error&&<p className="submit-error">{error}</p>}
      {preview&&<div className="admin-import-summary"><h4>Preview. Nothing has been imported yet.</h4><ul>{rows(preview.summary,true).map(([label,value])=><li key={label}>{label}: <strong>{value}</strong></li>)}</ul></div>}
      {result&&<div className="admin-import-summary"><h4>Import complete</h4><ul>{rows(result,false).map(([label,value])=><li key={label}>{label}: <strong>{value}</strong></li>)}</ul></div>}
      <div className="material-actions">
        {!preview&&<button className="button button-small" disabled={busy} onClick={()=>send(false)}>{busy?"Reading…":"Preview Import"}</button>}
        {preview&&<button className="button button-small" disabled={busy} onClick={()=>send(true)}>{busy?"Importing…":"Confirm Import"}</button>}
        <button className="button button-back button-small" onClick={()=>{setOpen(false);setPreview(null);setResult(null)}}>Close</button>
      </div>
    </div>}
  </>;
}

function Profile({ applicant, close, refresh }) {
  const [status,setStatus]=useState(applicant.status);
  const [notes,setNotes]=useState(applicant.internal_notes||"");
  const [message,setMessage]=useState("");
  const save=async()=>{await client.patch(`/admin/applicants/${applicant.applicant_id}`,{status,internal_notes:notes});setMessage("Profile updated.");refresh()};
  const retry=async()=>{setMessage("Syncing…");try{await client.post(`/admin/applicants/${applicant.applicant_id}/retry-resend`);setMessage("Resend sync complete.");refresh()}catch{setMessage("Resend sync failed.")}};
  const groups=[
    ["Contact",["applicant_id","email","phone","linkedin_url","country","city","state_region","postal_code"]],
    ["Professional Background",["job_title","employer","professional_field","years_experience","skills","other_skill","professional_summary"]],
    ["Board Preferences",["causes","other_cause","board_types","participation_preferences","geographic_preferences","availability","monthly_commitment"]],
    ["Contribution",["previous_board_experience","board_experience_details","fundraising_activities","professional_relationships","reason_for_joining","commitment_answer","understands_unpaid"]],
    ["Permissions",["profile_sharing_permission","board_opportunity_consent","other_offers_consent","privacy_accepted","consent_at"]],
  ];
  const label=key=>key.replaceAll("_"," ").replace(/\b\w/g,letter=>letter.toUpperCase());
  const display=value=>Array.isArray(value)?value.join(", "):typeof value==="boolean"?(value?"Yes":"No"):(value||"Not provided");

  return <div className="admin-profile-overlay" data-testid="admin-applicant-profile"><div className="admin-profile-panel">
    <button className="profile-close" onClick={close}>×</button><p className="eyebrow">Applicant profile</p><h2>{applicant.first_name} {applicant.last_name}</h2>
    <div className="admin-profile-actions">
      <label>Status<select value={status} onChange={event=>setStatus(event.target.value)}>{statuses.map(item=><option value={item} key={item}>{item}</option>)}</select></label>
      {applicant.resume_file_id&&<a className="button button-back" href={`${API}/admin/applicants/${applicant.applicant_id}/resume`}><Download size={16}/> Download résumé</a>}
      <button className="button button-back" onClick={retry}><RefreshCw size={16}/> Retry Resend</button>
    </div>
    {groups.map(([title,keys])=><section className="profile-group" key={title}><h3>{title}</h3><dl>{keys.map(key=><div key={key}><dt>{label(key)}</dt><dd>{display(applicant[key])}</dd></div>)}</dl></section>)}
    <label className="admin-notes">Internal notes<textarea value={notes} onChange={event=>setNotes(event.target.value)} rows="5"/></label>
    {message&&<p className="admin-message">{message}</p>}<button className="button" onClick={save}>Save Applicant Changes</button>
  </div></div>;
}

function ApplicantsSection({ applicants, filters, setFilters, selected, setSelected, filterOptions, loadApplicants, openProfile }) {
  return <section data-testid="admin-board-applicants">
    <div className="admin-funnel-numbers-head"><div><h2>Board Applicant Network</h2><p>Every saved applicant profile is available here. Search, review, export or update applicant status.</p></div></div>
    <div className="admin-filters">
      <label className="search-filter"><Search size={15}/><input placeholder="Search name or email" value={filters.search} onChange={event=>setFilters({...filters,search:event.target.value})}/></label>
      <select value={filters.country} onChange={event=>setFilters({...filters,country:event.target.value})}><option value="">All countries</option><option value="United States">United States</option><option value="United Kingdom">United Kingdom</option></select>
      {Object.entries(filterOptions).map(([key,options])=><select key={key} value={filters[key]} onChange={event=>setFilters({...filters,[key]:event.target.value})}><option value="">All {key.replace("_"," ")}</option>{options.map(option=><option value={option} key={option}>{option}</option>)}</select>)}
      <button className="button button-small" onClick={loadApplicants}>Apply Filters</button>
      <a className="button button-back button-small" href={`${API}/admin/applicants-export.csv?ids=${selected.join(",")}`}><Download size={15}/> Export {selected.length?"Selected":"All"}</a>
      <ImportApplicants refresh={loadApplicants}/>
    </div>
    <div className="admin-table-wrap"><table className="admin-table"><thead><tr>
      <th><input type="checkbox" aria-label="Select all applicants" checked={applicants.length>0&&selected.length===applicants.length} onChange={event=>setSelected(event.target.checked?applicants.map(item=>item.applicant_id):[])}/></th>
      {["Applicant ID","Name","Email","Phone","Country / City","Job title","Professional field","Main expertise","Preferred causes","Preferred board type","Availability","Status","Resend","Created"].map(heading=><th key={heading}>{heading}</th>)}
    </tr></thead><tbody>{applicants.map(item=><tr key={item.applicant_id}>
      <td><input type="checkbox" checked={selected.includes(item.applicant_id)} onChange={()=>setSelected(current=>current.includes(item.applicant_id)?current.filter(id=>id!==item.applicant_id):[...current,item.applicant_id])}/></td>
      <td><button className="table-link" onClick={()=>openProfile(item.applicant_id)}>{item.applicant_id}</button></td>
      <td>{item.first_name} {item.last_name}</td><td>{item.email}</td><td>{item.phone}</td><td>{item.country}<small>{item.city}</small></td><td>{item.job_title}</td><td>{item.professional_field}</td><td>{item.skills?.[0]}</td><td>{item.causes?.[0]}</td><td>{item.board_types?.[0]}</td><td>{item.availability}</td><td>{item.status}</td><td><span className={`sync-badge ${item.resend_segment_status?.toLowerCase()}`}>{item.resend_segment_status}</span></td><td>{item.created_at?.slice(0,10)}</td>
    </tr>)}</tbody></table></div>
  </section>;
}

export default function AdminPage() {
  const [user,setUser]=useState(null);
  const [checking,setChecking]=useState(true);
  const [tab,setTab]=useState("pathways");
  const [applicants,setApplicants]=useState([]);
  const [filters,setFilters]=useState(blankFilters);
  const [selected,setSelected]=useState([]);
  const [profile,setProfile]=useState(null);

  useEffect(()=>{client.get("/auth/me").then(response=>setUser(response.data)).catch(()=>setUser(false)).finally(()=>setChecking(false))},[]);
  const loadApplicants=useCallback(async()=>{const response=await client.get("/admin/applicants",{params:filters});setApplicants(response.data)},[filters]);
  useEffect(()=>{if(user)loadApplicants()},[user,loadApplicants]);
  const filterOptions=useMemo(()=>({
    state_region:[...new Set(applicants.map(item=>item.state_region).filter(Boolean))],
    cause:[...new Set(applicants.flatMap(item=>item.causes||[]))],
    skill:[...new Set(applicants.flatMap(item=>item.skills||[]))],
    board_type:[...new Set(applicants.flatMap(item=>item.board_types||[]))],
    fundraising:[...new Set(applicants.flatMap(item=>item.fundraising_activities||[]))],
    availability:[...new Set(applicants.map(item=>item.availability).filter(Boolean))],
  }),[applicants]);
  const openProfile=async(id)=>{const response=await client.get(`/admin/applicants/${id}`);setProfile(response.data)};
  const logout=async()=>{await client.post("/auth/logout");setUser(false)};

  if(checking)return <div className="admin-loading" data-testid="admin-loading">Checking administrator access…</div>;
  if(!user)return <Login onLogin={setUser}/>;

  const tabs=[
    ["pathways","4 Board Builder Pathways"],
    ["videos","8 Platform Videos"],
    ["homepages","6 Home Page Text"],
    ["analytics","Platform Analytics"],
    ["applicants","Board Applicant Network"],
    ["strategic","Strategic Planning"],
  ];

  return <main className="admin-page" data-testid="admin-dashboard">
    <header className="admin-header"><div><p className="eyebrow">Private administrator area</p><h1>Nonprofit Board Builder</h1></div><div className="admin-header-actions"><a className="button button-small" href="/">Open Main Home Page</a><button onClick={logout}><LogOut size={17}/> Log out</button></div></header>
    <nav className="admin-tabs">{tabs.map(([key,label])=><button key={key} className={tab===key?"active":""} onClick={()=>setTab(key)}>{label}</button>)}</nav>
    {tab==="pathways"&&<BoardBuilderPathwaysSection/>}
    {tab==="videos"&&<PlatformVideosSection/>}
    {tab==="homepages"&&<HomepageTextSection/>}
    {tab==="analytics"&&<PlatformAnalyticsSection/>}
    {tab==="strategic"&&<StrategicPlanningSection/>}
    {tab==="applicants"&&<ApplicantsSection applicants={applicants} filters={filters} setFilters={setFilters} selected={selected} setSelected={setSelected} filterOptions={filterOptions} loadApplicants={loadApplicants} openProfile={openProfile}/>}
    {profile&&<Profile applicant={profile} close={()=>setProfile(null)} refresh={loadApplicants}/>}
  </main>;
}
