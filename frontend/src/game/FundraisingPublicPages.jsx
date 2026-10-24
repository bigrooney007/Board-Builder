import {quoteCta} from '@/services/landingContent';
import {publicContent} from '@/content/publicPresentation';
import {useServiceContact} from "@/services/ServiceContactDialog";
import {SiteBrand} from "@/components/SiteBrand";
import WrittenOfferContent from "./WrittenOfferContent";
import defaults from "@/content/fundraisingDefaults.json";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
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
 const location=useLocation();const {openContact,contactDialog}=useServiceContact('board-fundraising');const {member,refresh}=useMemberAuth();
 const [content,setContent]=useState({...defaults,home:{...defaults.home,cta:'GET A FREE QUOTE'},how:{...defaults.how,cta:'GET A FREE QUOTE',sections:defaults.how.sections.map(s=>({...s,cta:s.cta?'GET A FREE QUOTE':''}))}});
 const busy=false;const [error,setError]=useState('');
 const token=new URLSearchParams(location.search).get('lead')||localStorage.getItem('fundraisingLeadToken')||'';
 useEffect(()=>{sessionStorage.removeItem('fundraisingCustomer');if(member?.internal_dashboard_preview){clearMemberToken();sessionStorage.removeItem('adminClientTest');localStorage.removeItem('fundraisingLeadToken');localStorage.removeItem('fundraisingLeadDetails');refresh()}},[member,refresh]);
 useEffect(()=>{let active=true;memberApi.get('/fundraising/content').then(r=>{if(active){setContent(publicContent(r.data.content))}}).catch(()=>setError('The latest page content could not load. Please refresh before continuing.'));return()=>{active=false}},[]);
 useEffect(()=>{document.title=how?'How The Fundraising Game Works | Nonprofit Board Builder':'The Fundraising Game | Nonprofit Board Builder';memberApi.post('/fundraising/events',{kind:how?'page_two':'homepage',visitor_id:visitorId(),lead_token:token}).catch(()=>{});},[how,token]);
 const c=publicContent(content[how?'how':'home']),action=openContact;
 const cta=(label=c.cta)=><button className="nBB-home-primary" disabled={busy} onClick={action}>{busy?'Opening…':quoteCta(label)}</button>;
 return <div className="nBB-home fundraising-public-centered" data-testid={how?'fundraising-how-page':'fundraising-home-page'}>
 <header className="nBB-home-nav"><SiteBrand/><Link className="nBB-home-login" to="/blog">Blog</Link></header>
 <main><section className="nBB-home-hero"><p className="nBB-home-eyebrow">NONPROFIT BOARD BUILDER</p><h1>{c.title}</h1>{c.introduction&&<p className="nBB-home-lead">{c.introduction}</p>}{cta()}</section>
 {how?<>{(c.sections||[]).filter(s=>s.heading.trim()||s.body.trim()||s.cta.trim()).map((section,i)=><section className={`fundraising-offer-section ${i%2?'fundraising-section-light':'fundraising-section-navy'}`} key={section.id} data-section={section.id}><div className="fundraising-copy"><h2>{section.heading}</h2><WrittenOfferContent text={section.body}/>{section.cta&&<div className="fundraising-section-action">{cta(section.cta)}</div>}</div></section>)}{c.guarantee&&<p className="fundraising-guarantee">{c.guarantee}</p>}</>:<>
 {(c.explanation_heading||c.paragraphs?.some(p=>p.trim()))&&<section className="fundraising-offer-section fundraising-section-navy" data-testid="fundraising-explanation"><div className="fundraising-copy">{c.explanation_heading&&<h2>{c.explanation_heading}</h2>}{c.paragraphs.filter(p=>p.trim()).map((p,i)=><p key={i}>{p}</p>)}<div data-testid="fundraising-cta-after-explanation">{cta()}</div></div></section>}
 <div data-testid="fundraising-how-it-works">{(content.how.sections||[]).filter(s=>s.heading.trim()||s.body.trim()).map((section,i)=><section className={'fundraising-offer-section '+(i%2?'fundraising-section-navy':'fundraising-section-light')} key={section.id} data-section={section.id}><div className="fundraising-copy"><h2>{publicContent(section.heading)}</h2><WrittenOfferContent text={publicContent(section.body)}/>{section.cta&&<div className="fundraising-section-action">{cta(section.cta)}</div>}</div></section>)}</div>
 <section className="fundraising-offer-section fundraising-section-light" data-testid="fundraising-biography"><article className="fundraising-copy"><h2>{c.biography_heading}</h2><img src={process.env.REACT_APP_ROONEY_HOMEPAGE_PHOTO_URL||'https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/ezw4nj2a_InShot_20260413_074422056%20%281%29.webp'} alt="Rooney A." loading="lazy" width="280" height="330" className="fundraising-portrait"/>{c.biography.filter(p=>p.trim()).map((p,i)=><p key={i}>{p}</p>)}<div className="fundraising-section-action" data-testid="fundraising-cta-after-biography">{cta()}<a className="nBB-home-secondary fundraising-alone" href="https://autofundraiser.com" target="_blank" rel="noreferrer">{c.alone_cta}</a></div></article></section></>}
 <section className="nBB-home-proof"><TestimonialCarousel heading={c.testimonials_heading} idPrefix="fundraising-launch"/></section>
 {!how&&<section className="nBB-home-closing"><h2>{c.closing_heading}</h2>{cta()}</section>}{error&&<p role="alert" className="submit-error fundraising-copy">{error}</p>}</main>
 <footer className="bfg-footer"><p>© {new Date().getFullYear()} Nonprofit Board Builders, LLC.</p><Link to="/privacy-policy">Privacy Policy</Link><Link to="/terms">Terms</Link></footer>
 {contactDialog}

 </div>;
}
