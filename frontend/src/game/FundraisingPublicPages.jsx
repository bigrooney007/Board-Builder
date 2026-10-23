import {quoteCta} from '@/services/landingContent';
import {publicContent} from '@/content/publicPresentation';
import {useServiceContact} from "@/services/ServiceContactDialog";
import {SiteBrand} from "@/components/SiteBrand";
import WrittenOfferContent from "./WrittenOfferContent";
import defaults from "@/content/fundraisingDefaults.json";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { memberApi, clearMemberToken } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { useLandingPageMeta } from "@/seo";
import "@/pages/MainHomePage.css";
import "./game.css";
import "./fundraisingSimplified.css";

export const visitorId=()=>{
 let value=localStorage.getItem('fundraisingVisitor');
 if(!value){value=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(36).slice(2)}`;localStorage.setItem('fundraisingVisitor',value)}
 return value;
};
export default function FundraisingPublicPage({how=false}){
 useLandingPageMeta(how?'/how-the-fundraising-game-works':'/board-fundraising-game');
 const navigate=useNavigate(),location=useLocation();const {openContact,contactDialog}=useServiceContact('board-fundraising');const {member,refresh}=useMemberAuth();
 const [content,setContent]=useState({...defaults,home:{...defaults.home,cta:'START MY BOARD FUNDRAISING FOR FREE'},how:{...defaults.how,cta:'START MY BOARD FUNDRAISING FOR FREE',sections:defaults.how.sections.map(s=>({...s,cta:s.cta?'START MY BOARD FUNDRAISING FOR FREE':''}))}}),[capture,setCapture]=useState(false);
 const [lead,setLead]=useState(()=>{try{return JSON.parse(localStorage.getItem('fundraisingLeadDetails')||'{}')}catch{return {}}});
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const token=new URLSearchParams(location.search).get('lead')||localStorage.getItem('fundraisingLeadToken')||'';
 useEffect(()=>{sessionStorage.removeItem('fundraisingCustomer');if(member?.internal_dashboard_preview){clearMemberToken();sessionStorage.removeItem('adminClientTest');localStorage.removeItem('fundraisingLeadToken');localStorage.removeItem('fundraisingLeadDetails');refresh()}},[member,refresh]);
 useEffect(()=>{let active=true;memberApi.get('/fundraising/content').then(r=>{if(active){setContent(publicContent(r.data.content))}}).catch(()=>setError('The latest page content could not load. Please refresh before continuing.'));return()=>{active=false}},[]);
 useEffect(()=>{document.title=how?'How The Fundraising Game Works | Nonprofit Board Builder':'The Fundraising Game | Nonprofit Board Builder';memberApi.post('/fundraising/events',{kind:how?'page_two':'homepage',visitor_id:visitorId(),lead_token:token}).catch(()=>{});if(how&&token)memberApi.get('/fundraising/leads/'+token).then(r=>setLead(r.data)).catch(()=>{})},[how,token]);
 useEffect(()=>{if(!capture)return;const close=e=>{if(e.key==='Escape')setCapture(false)};document.addEventListener('keydown',close);return()=>document.removeEventListener('keydown',close)},[capture]);
 const checkout=async saved=>{if(!saved){setCapture(true);return}setBusy(true);setError('');try{const r=await memberApi.post('/payments/game-checkout',{origin_url:window.location.origin,result_token:saved,cancel_path:'/how-the-fundraising-game-works'});window.location.assign(r.data.checkout_url)}catch(e){setError(typeof e.response?.data?.detail==='string'?e.response.data.detail:'Secure checkout could not open. Please try again.');setBusy(false)}};
 const submit=async e=>{e.preventDefault();setBusy(true);setError('');try{const r=await memberApi.post('/fundraising/leads',{name:lead.name||'',email:lead.email||'',organization:lead.organization||'',visitor_id:visitorId(),resume_token:token});localStorage.setItem('fundraisingLeadToken',r.data.token);localStorage.setItem('fundraisingLeadDetails',JSON.stringify(lead));setCapture(false);if(how)await checkout(r.data.token);else navigate(r.data.next)}catch(e){setError(typeof e.response?.data?.detail==='string'?e.response.data.detail:'We could not save your details. Please try again.')}setBusy(false)};
 const c=publicContent(content[how?'how':'home']),action=openContact;
 const cta=(label=c.cta)=><button className="nBB-home-primary" disabled={busy} onClick={action}>{busy?'Opening…':quoteCta(label)}</button>;
 return <div className="nBB-home fundraising-public-centered" data-testid={how?'fundraising-how-page':'fundraising-home-page'}>
 <header className="nBB-home-nav"><SiteBrand/><Link className="nBB-home-login" to="/blog">Blog</Link></header>
 <main><section className="nBB-home-hero"><p className="nBB-home-eyebrow">NONPROFIT BOARD BUILDER</p><h1>{c.title}</h1>{c.introduction&&<p className="nBB-home-lead">{c.introduction}</p>}{cta()}</section>
 {how?<>{(c.sections||[]).filter(s=>s.heading.trim()||s.body.trim()||s.cta.trim()).map((section,i)=><section className={`fundraising-offer-section ${i%2?'fundraising-section-light':'fundraising-section-navy'}`} key={section.id} data-section={section.id}><div className="fundraising-copy"><h2>{section.heading}</h2><WrittenOfferContent text={section.body}/>{section.cta&&<div className="fundraising-section-action">{cta(section.cta)}</div>}</div></section>)}{c.guarantee&&<p className="fundraising-guarantee">{c.guarantee}</p>}</>:<>
 {(c.explanation_heading||c.paragraphs?.some(p=>p.trim()))&&<section className="fundraising-offer-section fundraising-section-navy" data-testid="fundraising-explanation"><div className="fundraising-copy">{c.explanation_heading&&<h2>{c.explanation_heading}</h2>}{c.paragraphs.filter(p=>p.trim()).map((p,i)=><p key={i}>{p}</p>)}<div data-testid="fundraising-cta-after-explanation">{cta()}</div></div></section>}
 <section className="fundraising-offer-section fundraising-section-light" data-testid="fundraising-biography"><article className="fundraising-copy"><h2>{c.biography_heading}</h2><img src={process.env.REACT_APP_ROONEY_HOMEPAGE_PHOTO_URL||'https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/ezw4nj2a_InShot_20260413_074422056%20%281%29.webp'} alt="Rooney A." loading="lazy" width="280" height="330" className="fundraising-portrait"/>{c.biography.filter(p=>p.trim()).map((p,i)=><p key={i}>{p}</p>)}<div className="fundraising-section-action" data-testid="fundraising-cta-after-biography">{cta()}<a className="nBB-home-secondary fundraising-alone" href="https://autofundraiser.com" target="_blank" rel="noreferrer">{c.alone_cta}</a></div></article></section></>}
 <section className="nBB-home-proof"><TestimonialCarousel heading={c.testimonials_heading} idPrefix="fundraising-launch"/></section>
 {!how&&<section className="nBB-home-closing"><h2>{c.closing_heading}</h2>{cta()}</section>}{error&&<p role="alert" className="submit-error fundraising-copy">{error}</p>}</main>
 <footer className="bfg-footer"><p>© {new Date().getFullYear()} Nonprofit Board Builders, LLC.</p><Link to="/privacy-policy">Privacy Policy</Link><Link to="/terms">Terms</Link></footer>
 {contactDialog}
 {capture&&<div className="fundraising-capture" role="dialog" aria-modal="true" aria-labelledby="capture-heading"><form onSubmit={submit} className="bfg-panel fundraising-capture-card"><h2 id="capture-heading">See How The Board Fundraising Game Works</h2>{[['name','Full name'],['email','Email address'],['organization','Organization name']].map(([key,label],i)=><label className="bfg-field" key={key}>{label}<input autoFocus={i===0} type={key==='email'?'email':'text'} required autoComplete={key==='organization'?'organization':key} value={lead[key]||''} onChange={e=>setLead({...lead,[key]:e.target.value})}/></label>)}{error&&<p role="alert">{error}</p>}<button className="bfg-btn bfg-btn-primary" disabled={busy}>{busy?'Opening…':'See How The Board Fundraising Game Works'}</button><button type="button" className="bfg-btn bfg-btn-ghost" onClick={()=>setCapture(false)}>Close</button></form></div>}
 </div>;
}
