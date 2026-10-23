import {useEffect,useRef,useState} from 'react';
import {Answer} from './GuidedServicePage';
import AudienceQuestionnaire from '@/game/AudienceQuestionnaire';
import {api,Button,problem,RichContent} from './shared';

export default function PaidLeaderQuestions({service,token,onComplete}){
 const base=`/services/${service}/customer/${token}`;
 const [data,setData]=useState(null),[answers,setAnswers]=useState({}),[index,setIndex]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState(''),[audience,setAudience]=useState(null);
 const saved=useRef({}),queue=useRef(Promise.resolve());
 const load=async()=>{const r=await api.get(base+'/leader-questions');setData(r.data);setAnswers(r.data.answers||{});saved.current=r.data.answers||{};if(r.data.completed){onComplete();return}if(r.data.audience_token){const a=await api.get('/game/play/'+r.data.audience_token+'/audience-response');setAudience({...a.data,token:r.data.audience_token})}};
 useEffect(()=>{let live=true;load().catch(e=>{if(live)setError(problem(e))});return()=>{live=false}; // eslint-disable-next-line react-hooks/exhaustive-deps
 },[base]);
 const save=value=>{const next=queue.current.catch(()=>{}).then(()=>api.put(base+'/leader-questions',{answers:value,submit:false}));queue.current=next;return next};
 useEffect(()=>{if(!data||data.details_completed)return;const timer=setTimeout(()=>{if(JSON.stringify(answers)!==JSON.stringify(saved.current))save(answers).then(()=>{saved.current=answers}).catch(e=>setError(problem(e)))},800);return()=>clearTimeout(timer); // eslint-disable-next-line react-hooks/exhaustive-deps
 },[answers,data?.details_completed]);
 const submit=async event=>{event.preventDefault();if(busy)return;setBusy(true);setError('');try{await queue.current.catch(()=>{});const last=index===data.questions.length-1;const r=await api.put(base+'/leader-questions',{answers,submit:last});saved.current=answers;if(last){if(r.data.completed)onComplete();else await load()}else{setIndex(index+1);window.scrollTo(0,0)}}catch(e){setError(problem(e))}finally{setBusy(false)}};
 const q=data?.questions[index];
 return <section data-testid="paid-leader-questionnaire">{error&&<p role="alert">{error}</p>}{!data?<p>Opening your saved leader questionnaire…</p>:audience?<><h2>Your Fundraising Ideas</h2><AudienceQuestionnaire configuration={audience.configuration} initial={audience.response} storageKey={'paid-quote-leader-'+token} context={data.context} save={value=>api.put('/game/play/'+audience.token+'/audience-response',value)} complete={async value=>{await api.post('/game/play/'+audience.token+'/audience-response/complete',value);await api.post(base+'/leader-complete');onComplete()}}/></>:<><h2>{data.copy.leader_heading}</h2><RichContent text={data.copy.leader_intro}/>{q&&<form onSubmit={submit}><p>Question {index+1} of {data.questions.length}</p><h3>{q.prompt}</h3><p className="service-question-subtitle">{q.help}</p><Answer question={q} value={answers[q.id]} onChange={v=>setAnswers({...answers,[q.id]:v})}/><div className="guided-actions"><Button secondary disabled={busy||index===0} onClick={()=>setIndex(index-1)}>Previous</Button><Button secondary disabled={busy} onClick={async()=>{setBusy(true);setError('');try{await save(answers);setError('');saved.current=answers}catch(e){setError(problem(e))}finally{setBusy(false)}}}>Save Progress</Button><button className="button" disabled={busy}>{index===data.questions.length-1?data.copy.leader_submit:'SAVE AND CONTINUE'}</button></div></form>}</>}</section>;
}
