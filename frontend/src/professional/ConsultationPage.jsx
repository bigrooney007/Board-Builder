import {useEffect,useRef,useState} from 'react';
import {Link,useParams,useSearchParams} from 'react-router-dom';
import {professionalApi as api,useProfessionalContent,logoUrl} from './content';
import RichContent from './RichContent';
import '@/pages/MainHomePage.css';
import './professional.css';

export default function ConsultationPage(){
 const c=useProfessionalContent('consultation');
 const params=useParams(),[query]=useSearchParams(),token=params.token||query.get('token')||'';
 const [form,setForm]=useState({name:'',email:'',organization:'',website:'',role:'',topic:''}),[row,setRow]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[recover,setRecover]=useState(false),[notice,setNotice]=useState(''),[email,setEmail]=useState('');
 const requestId=useRef(crypto.randomUUID());
 const confirming=useRef('');
 useEffect(()=>{
  const robots=document.createElement('meta');robots.name='robots';robots.content='noindex, nofollow';document.head.appendChild(robots);
  const referrer=document.createElement('meta');referrer.name='referrer';referrer.content='no-referrer';document.head.appendChild(referrer);
  const old=document.title;document.title='Professional Consultation | Nonprofit Board Builder';
  return()=>{robots.remove();referrer.remove();document.title=old};
 },[]);
 const attempt=async(fn)=>{setBusy(true);setError('');try{await fn()}catch(e){setError(typeof e.response?.data?.detail==='string'?e.response.data.detail:'This action could not be completed. Please try again.')}finally{setBusy(false)}};
 const confirm=()=>attempt(async()=>{const r=await api.post(`/consultations/${encodeURIComponent(token)}/confirm`,{session_id:query.get('session_id')||''});setRow(r.data)});
 useEffect(()=>{if(token&&confirming.current!==token){confirming.current=token;confirm()} // eslint-disable-next-line react-hooks/exhaustive-deps
 },[token]);
 const checkout=async saved=>{const r=await api.post(`/consultations/${encodeURIComponent(saved)}/checkout`);window.location.assign(r.data.checkout_url||r.data.resume_url)};
 const submit=e=>{e.preventDefault();attempt(async()=>{const r=await api.post('/consultations/intake',{...form,request_id:requestId.current});await checkout(r.data.token)})};
 const booking=()=>attempt(async()=>{const response=await api.get(`/consultations/${encodeURIComponent(token)}`);if(response.data.payment_status!=='paid')throw new Error('Payment is required');window.location.assign(`${api.defaults.baseURL}/consultations/${encodeURIComponent(token)}/book`)});
 return <div className="nBB-home professional-page"><header className="nBB-home-nav professional-nav"><Link className="nBB-home-brand" to="/"><img src={logoUrl} alt="Nonprofit Board Builder" style={{width:130,height:68,objectFit:"contain"}}/></Link><Link to="/meet-rooney">Meet Rooney</Link></header><main className="professional-copy consultation-card">
  {token?<><h1>{row?.payment_status==='paid'?c.confirmedHeading:c.formHeading}</h1>{busy&&!row&&<p role="status">{c.checkingMessage}</p>}{row?.payment_status==='paid'?<><RichContent text={c.confirmationMessage}/>{c.duration&&<p>{c.duration}</p>}{row.booking_status==='booked'&&<p>{c.bookedMessage}</p>}{row.booking_status==='link_opened'&&<p>{c.openedMessage}</p>}{row.booking_status==='cancelled'&&<p>{c.cancelledMessage}</p>}<button className="nBB-home-primary" disabled={busy} onClick={booking}>{c.bookingCta} →</button></>:row&&<><p>{query.get('checkout')==='cancelled'?c.cancelMessage:c.unpaidMessage}</p><p>{c.pendingMessage}</p><button className="nBB-home-primary" disabled={busy} onClick={()=>attempt(()=>checkout(token))}>{c.checkoutCta} · $197</button><button className="professional-text-button" disabled={busy} onClick={confirm}>{c.retryCta}</button></>}</>:<><h1>{c.formHeading}</h1><RichContent text={c.formIntroduction}/>{c.duration&&<p>{c.duration}</p>}<form onSubmit={submit} className="professional-form">{[['name','nameLabel'],['email','emailLabel'],['organization','organizationLabel'],['website','websiteLabel'],['role','roleLabel'],['topic','topicLabel']].map(([key,label])=><label key={key}>{c[label]}{key==='topic'?<textarea required minLength={5} maxLength={6000} rows={5} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/>:<input required={key!=='website'} type={key==='email'?'email':'text'} autoComplete={{name:'name',email:'email',organization:'organization',website:'url',role:'organization-title'}[key]} maxLength={key==='website'?2000:key==='email'?254:200} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/>}</label>)}<button className="nBB-home-primary" disabled={busy}>{c.checkoutCta} · $197</button></form></>}
  {error&&<p role="alert" className="professional-error">{error}</p>}{token&&!row&&!busy&&<button className="professional-text-button" onClick={confirm}>{c.retryCta}</button>}
  <button className="professional-text-button" onClick={()=>setRecover(!recover)}>{c.recoveryLinkLabel}</button>{recover&&<form className="professional-form professional-recovery" onSubmit={e=>{e.preventDefault();attempt(async()=>{await api.post('/consultations/recover',{email});setNotice(c.recoveryNotice)})}}><h2>{c.recoveryHeading}</h2><p>{c.recoveryDescription}</p><label>{c.emailLabel}<input required type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label><button className="nBB-home-primary" disabled={busy}>{c.recoveryCta}</button>{notice&&<p role="status">{notice}</p>}</form>}
 </main><footer className="nBB-home-footer"><Link to="/meet-rooney">{c.returnCta}</Link><Link to="/privacy-policy">Privacy</Link></footer></div>;
}
