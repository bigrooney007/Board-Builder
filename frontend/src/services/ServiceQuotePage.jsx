import {useEffect,useRef,useState} from 'react';
import {useNavigate,useParams} from 'react-router-dom';
import {Answer} from './GuidedServicePage';
import {api,Field,Shell,problem,serviceNames} from './shared';

export function QuoteFields({copy,questions,contact,answers,setContact,setAnswers}){
 return <>{[['name',copy.quote_name_label||'Your name','text','name'],['email',copy.quote_email_label||'Email address','email','email'],['organization',copy.quote_organization_label||'Organization name','text','organization']].map(([key,label,type,autoComplete])=><Field key={key} label={label} type={type} autoComplete={autoComplete} maxLength={key==='email'?254:300} required value={contact[key]||''} onChange={value=>setContact({...contact,[key]:value})}/>)}{questions.map(q=><div key={q.id} className="service-quote-question"><Answer question={q} label={q.prompt} allowVoice={false} value={answers[q.id]} onChange={value=>setAnswers({...answers,[q.id]:value})}/>{q.help&&<p className="service-question-subtitle">{q.help}</p>}</div>)}</>;
}
export default function ServiceQuotePage(){
 const {service}=useParams(),navigate=useNavigate(),key='quote-form-'+service;
 const readDraft=()=>{try{return JSON.parse(sessionStorage.getItem(key)||'{}')}catch{return {}}};
 const initial=useRef(readDraft()),requestId=useRef(initial.current.request_id||crypto.randomUUID());
 const [data,setData]=useState(null),[contact,setContact]=useState(initial.current.contact||{}),[answers,setAnswers]=useState(initial.current.answers||{}),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{let active=true;api.get('/services/'+service+'/questions').then(r=>{if(active)setData(r.data)}).catch(e=>{if(active)setError(problem(e))});return()=>{active=false}},[service]);
 useEffect(()=>{sessionStorage.setItem(key,JSON.stringify({request_id:requestId.current,contact,answers}));},[key,contact,answers]);
 const submit=async event=>{event.preventDefault();if(busy||!data)return;setBusy(true);setError('');try{const r=await api.post('/services/'+service+'/quote',{...contact,answers,request_id:requestId.current,question_version:data.version});sessionStorage.removeItem(key);navigate(r.data.url);window.scrollTo(0,0)}catch(e){setError(problem(e))}finally{setBusy(false)}};
 if(!serviceNames[service])return <Shell title="Quote Form Not Found"/>;
 return <Shell title={data?.copy.quote_heading||'Request Your '+serviceNames[service]+' Quote'} minimal>{error&&<p role="alert">{error}</p>}{!data?<p>Opening the quote form...</p>:<><p>{data.copy.quote_subtitle}</p><form className="service-quote-form guided-card" data-testid="service-quote-form" onSubmit={submit}><QuoteFields copy={data.copy} questions={data.questions} contact={contact} answers={answers} setContact={setContact} setAnswers={setAnswers}/><button className="button" disabled={busy}>{busy?'Submitting...':data.copy.question_submit}</button></form></>}</Shell>;
}
