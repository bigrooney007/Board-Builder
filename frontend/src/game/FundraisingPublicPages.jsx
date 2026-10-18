import WrittenOfferContent from "./WrittenOfferContent";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { useLandingPageMeta } from "@/seo";
import "@/pages/MainHomePage.css";
import "./game.css";
import "./fundraisingSimplified.css";

export const visitorId = () => {
  let value=localStorage.getItem("fundraisingVisitor");
  if(!value){value=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(36).slice(2)}`;localStorage.setItem("fundraisingVisitor",value)}
  return value;
};
export default function FundraisingPublicPage({ how=false }) {
  useLandingPageMeta(how?"/how-the-fundraising-game-works":"/");
  const navigate=useNavigate();const location=useLocation();const {member,loading}=useMemberAuth();
  const [content,setContent]=useState(null);const [price,setPrice]=useState(null);const [capture,setCapture]=useState(false);const [lead,setLead]=useState(()=>{try{return JSON.parse(localStorage.getItem("fundraisingLeadDetails")||"{}")}catch{return {}}});
  const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  const token=new URLSearchParams(location.search).get("lead")||localStorage.getItem("fundraisingLeadToken")||"";
  useEffect(()=>{let active=true;memberApi.get("/fundraising/content").then(r=>{if(active){setContent(r.data.content);setPrice(r.data.price)}}).catch(()=>setError("The page could not load. Please refresh to try again."));return()=>{active=false}},[]);
  useEffect(()=>{
    document.title=how?"How The Fundraising Game Works | Nonprofit Board Builder":"The Fundraising Game | Nonprofit Board Builder";
    const canonical=window.location.origin+(how?"/how-the-fundraising-game-works":"/");
    let node=document.querySelector('link[rel="canonical"]');if(!node){node=document.createElement("link");node.rel="canonical";document.head.appendChild(node)}node.href=canonical;
    const meta=document.querySelector('meta[name="description"]')||document.createElement("meta");meta.name="description";meta.content="Get your board involved in developing, adopting and executing your organization's fundraising strategy by your next board meeting. The Fundraising Game costs $997 once.";if(!meta.parentNode)document.head.appendChild(meta);
    memberApi.post("/fundraising/events",{kind:how?"page_two":"homepage",visitor_id:visitorId(),lead_token:token}).catch(()=>{});
    if(how&&token)memberApi.get("/fundraising/leads/"+token).then(r=>setLead(r.data)).catch(()=>{});
  },[how,token]);
  const submit=async e=>{e.preventDefault();setBusy(true);setError("");try{
    const r=await memberApi.post("/fundraising/leads",{name:lead.name||"",email:lead.email||"",organization:lead.organization||"",visitor_id:visitorId(),resume_token:token});
    localStorage.setItem("fundraisingLeadToken",r.data.token);localStorage.setItem("fundraisingLeadDetails",JSON.stringify(lead));setCapture(false);
    if(how){await checkout(r.data.token)}else navigate(r.data.next);
  }catch(e){setError(typeof e.response?.data?.detail==="string"?e.response.data.detail:"We could not save your details. Please try again.")}setBusy(false)};
  const checkout=async savedToken=>{if(!savedToken){setCapture(true);return}setBusy(true);setError("");try{
    const r=await memberApi.post("/payments/game-checkout",{origin_url:window.location.origin,result_token:savedToken,cancel_path:"/how-the-fundraising-game-works"});
    if(r.data.simulated){window.location.assign(r.data.checkout_url)}else window.location.assign(r.data.checkout_url);
  }catch(e){setError(typeof e.response?.data?.detail==="string"?e.response.data.detail:"Secure checkout could not open. Please try again.");setBusy(false)}};
  const action=()=>how?checkout(token):setCapture(true);
  const c=content?.[how?"how":"home"];
  return <div className="nBB-home fundraising-public-centered" data-testid={how?"fundraising-how-page":"fundraising-home-page"}>
    <header className="nBB-home-nav" style={{justifyContent:"flex-end",gap:20}}><Link className="nBB-home-login" to="/">Nonprofit Board Builder</Link>{!loading&&<Link className="nBB-home-login" to={member?"/game/dashboard":"/login"}>{member?"My Workspace":"Log In"}</Link>}<Link className="nBB-home-login" to="/blog">Blog</Link></header>
    <main>{!c?<section className="nBB-home-problem"><p>{error||"Opening The Fundraising Game…"}</p></section>:<>
      <section className="nBB-home-hero"><p className="nBB-home-eyebrow">NONPROFIT BOARD BUILDER</p><h1>{c.title}</h1>{c.introduction&&<p className="nBB-home-lead">{c.introduction}</p>}<button className="nBB-home-primary" disabled={busy} onClick={action}>{busy?"Opening…":c.cta}</button>{price&&<p>One-time payment: ${price} per organization.</p>}</section>
      <section className="nBB-home-problem" style={{textAlign:"center",maxWidth:800,margin:"0 auto",padding:"42px 24px",lineHeight:1.85,fontSize:19}}>
        {how?<><WrittenOfferContent text={c.article}/><div style={{textAlign:"center",marginTop:36}}><p>{c.guarantee}</p><button className="nBB-home-primary" disabled={busy} onClick={action}>{busy?"Opening checkout…":c.cta}</button></div></>:<>
        {c.paragraphs.map((p,i)=><p key={i} style={{marginBottom:20,textAlign:"center"}}>{p}</p>)}
        <div data-testid="fundraising-cta-after-explanation"><button className="nBB-home-primary" disabled={busy} onClick={action}>{c.cta}</button></div><article style={{marginTop:44}}><h2>{c.biography_heading}</h2><img src={process.env.REACT_APP_ROONEY_HOMEPAGE_PHOTO_URL||"https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/ezw4nj2a_InShot_20260413_074422056%20%281%29.webp"} alt="Rooney A." loading="lazy" style={{width:"100%",maxWidth:280,borderRadius:16,display:"block",margin:"20px auto"}}/>{c.biography.map((p,i)=><p key={i} style={{textAlign:"center"}}>{p}</p>)}<div data-testid="fundraising-cta-after-biography"><button className="nBB-home-primary" disabled={busy} onClick={action}>{c.cta}</button></div></article></>}
        {error&&<p role="alert" className="submit-error">{error}</p>}
      </section>
      <section className="nBB-home-proof"><TestimonialCarousel heading="What Nonprofit Leaders Have Said" idPrefix="fundraising-launch"/></section>
      {!how&&<section className="nBB-home-closing"><h2>{c.closing_heading}</h2><button className="nBB-home-primary" onClick={action}>{c.cta}</button></section>}
    </>}</main>
    <footer className="bfg-footer"><p>© {new Date().getFullYear()} Nonprofit Board Builders, LLC.</p><Link to="/privacy-policy">Privacy Policy</Link><Link to="/terms">Terms</Link></footer>
    {capture&&<div role="dialog" aria-modal="true" aria-labelledby="capture-heading" style={{position:"fixed",inset:0,background:"#0009",display:"grid",placeItems:"center",padding:16,zIndex:1000,overflowY:"auto"}}><form onSubmit={submit} className="bfg-panel" style={{width:"100%",maxWidth:540,maxHeight:"90vh",overflowY:"auto",background:"white",color:"#10132d"}}><h2 id="capture-heading">See How The Fundraising Game Works</h2>{[["name","Full name"],["email","Email address"],["organization","Organization name"]].map(([key,label])=><label className="bfg-field" key={key}>{label}<input type={key==="email"?"email":"text"} required autoComplete={key==="organization"?"organization":key} value={lead[key]||""} onChange={e=>setLead({...lead,[key]:e.target.value})}/></label>)}<p>We will email you follow-up guidance about The Fundraising Game. You can unsubscribe from any of these emails.</p><p>Your details will be used to save your journey and set up your organization if you purchase.</p>{error&&<p role="alert">{error}</p>}<button className="bfg-btn bfg-btn-primary" disabled={busy}>{busy?"Saving…":"See How The Fundraising Game Works"}</button><button type="button" className="bfg-btn bfg-btn-ghost" onClick={()=>setCapture(false)}>Close</button></form></div>}
  </div>;
}
