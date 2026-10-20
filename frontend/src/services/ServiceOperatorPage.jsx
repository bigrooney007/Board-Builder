import {useEffect,useState} from 'react';
import {useNavigate,useParams} from 'react-router-dom';
import {api,Button,Field,Shell,problem,RichContent} from './shared';
import PlanningWorkspace from './PlanningWorkspace';
import FundraisingWorkspace from '@/game/FundraisingWorkspace';
import {useMemberAuth} from '@/member/MemberAuthContext';

export default function ServiceOperatorPage({handover=false}){
 const {service,token,ident}=useParams(),navigate=useNavigate(),{refresh}=useMemberAuth();
 const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[help,setHelp]=useState(''),[notice,setNotice]=useState('');
 const base=`/services/${service}/operator/${ident}`,routeKey=service+":"+(handover?token:ident)+":"+handover;
 const run=async fn=>{setBusy(true);setError('');try{await fn()}catch(e){setError(problem(e))}finally{setBusy(false)}};
 useEffect(()=>{let active=true;sessionStorage.removeItem('fundraisingCustomer');sessionStorage.removeItem('operateAsUserId');const path=handover?`/services/${service}/handover/${token}`:base;api.get(path).then(async r=>{if(!handover&&service==='board-fundraising')await refresh();if(active)setData({...r.data,routeKey})}).catch(e=>{if(active)setError(problem(e))});return()=>{active=false}; // eslint-disable-next-line react-hooks/exhaustive-deps
 },[service,token,ident,handover]);
 if(!data||data.routeKey!==routeKey||(!handover&&!data.customer))return <Shell title="Your Service Dashboard">{error?<p role="alert">{error}</p>:<p>Opening your saved project…</p>}</Shell>;
 if(handover)return <Shell title={data.copy.handover_heading}><h2>{data.organization}</h2><RichContent text={data.copy.handover_description}/>{error&&<p role="alert">{error}</p>}<Button disabled={busy} onClick={()=>run(async()=>{const r=await api.post(`/services/${service}/handover/${token}`,{confirmed:true});navigate(r.data.url)})}>{data.copy.handover_cta}</Button></Shell>;
 if(service==='board-fundraising')return <FundraisingWorkspace/>;
 return <Shell title={data.copy.dashboard_heading}><h2>{data.customer.organization}</h2><p className="service-operator-label">SELF-FACILITATED: ORGANIZATION IN CONTROL</p>{error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}<PlanningWorkspace base={base} record={data.customer} run={run} busy={busy}/><section className="guided-card"><h2>Ask for Support</h2><Field label="Your support request" large value={help} onChange={setHelp}/><Button disabled={busy||help.trim().length<5} onClick={()=>run(async()=>{await api.post(base+'/support',{message:help});setHelp('');setNotice('Your support request is saved for Rooney.')})}>Send Support Request</Button></section></Shell>;
}
