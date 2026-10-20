import {useEffect,useRef,useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {api,problem} from './shared';
import './services.css';

export default function ServiceContactDialog({service,open,onClose}) {
 const dialog=useRef(null),requestId=useRef(crypto.randomUUID()),navigate=useNavigate();
 const [form,setForm]=useState({name:'',email:'',organization:''});
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{
  if(!open)return;
  const element=dialog.current,previous=document.activeElement,overflow=document.body.style.overflow;
  element.showModal();document.body.style.overflow='hidden';
  return()=>{element.close();document.body.style.overflow=overflow;previous?.focus()};
 },[open]);
 const submit=async event=>{
  event.preventDefault();if(busy)return;setBusy(true);setError('');
  try {
   const response=await api.post(`/services/${service}/start`,{...form,request_id:requestId.current});
   onClose();navigate(`/services/${service}/start?lead=${response.data.token}`);window.scrollTo(0,0);
  } catch(e){setError(problem(e))}finally{setBusy(false)}
 };
 if(!open)return null;
 return <dialog ref={dialog} className="service-contact-dialog" aria-labelledby={`contact-title-${service}`} onCancel={event=>{event.preventDefault();if(!busy)onClose()}} onClick={event=>{if(event.target===dialog.current&&!busy){const r=dialog.current.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)onClose()}}}>
  <button type="button" className="service-dialog-close" aria-label="Close contact form" disabled={busy} onClick={onClose}>×</button>
  <h2 id={`contact-title-${service}`}>Let’s Get Started</h2>
  <form onSubmit={submit}>
   {[['name','Full name','text','name'],['email','Email address','email','email'],['organization','Organization name','text','organization']].map(([key,label,type,autoComplete])=><label key={key}>{label}<input required autoFocus={key==='name'} type={type} autoComplete={autoComplete} maxLength={key==='email'?254:200} value={form[key]} onChange={event=>setForm({...form,[key]:event.target.value})}/></label>)}
   {error&&<p role="alert">{error}</p>}
   <button type="submit" className="nBB-home-primary" disabled={busy}>{busy?'Opening…':'CONTINUE'}</button>
  </form>
 </dialog>;
}

export function useServiceContact(service,initiallyOpen=false){
 const [open,setOpen]=useState(initiallyOpen);
 return {openContact:()=>setOpen(true),contactDialog:<ServiceContactDialog service={service} open={open} onClose={()=>setOpen(false)}/>};
}
