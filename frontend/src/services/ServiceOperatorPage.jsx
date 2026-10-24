import {useEffect,useState} from 'react';
import {useLocation,useNavigate,useParams} from 'react-router-dom';
import {api,Button,Field,Shell,problem,RichContent} from './shared';
import PlanningWorkspace from './PlanningWorkspace';
import RecruitmentWorkspace from './RecruitmentWorkspace';
import RecommitmentWorkspace from './RecommitmentWorkspace';
import FundraisingWorkspace from '@/game/FundraisingWorkspace';
import {useMemberAuth} from '@/member/MemberAuthContext';

export default function ServiceOperatorPage({handover=false}){
 const {service,token,ident}=useParams(),navigate=useNavigate(),location=useLocation(),{refresh}=useMemberAuth();
 const access=new URLSearchParams(location.hash.replace(/^#/,'' )).get('access');
 const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[help,setHelp]=useState(''),[notice,setNotice]=useState('');
 const [owner,setOwner]=useState(false);
 const operatorBase='/services/'+service+'/operator/'+ident,base=owner?'/admin/services/'+service+'/customers/'+ident:operatorBase,routeKey=service+':'+(handover?token:ident)+':'+handover+':'+(access||'');
 const run=async fn=>{setBusy(true);setError('');try{await fn()}catch(e){setError(problem(e))}finally{setBusy(false)}};
 useEffect(()=>{let active=true;sessionStorage.removeItem('fundraisingCustomer');sessionStorage.removeItem('operateAsUserId');setError('');
  const open=async()=>{
   if(access&&!handover)await api.post('/services/'+service+'/dashboard-access',{token:access,customer_id:ident});
   const r=await api.get(handover?'/services/'+service+'/handover/'+token:operatorBase);
   if(!handover&&service==='board-fundraising')await refresh();
   if(active)setData({...r.data,routeKey});
   api.get('/auth/me').then(()=>{if(active)setOwner(true)}).catch(()=>{});
  };
  open().catch(e=>{if(active)setError(problem(e))});return()=>{active=false}; // eslint-disable-next-line react-hooks/exhaustive-deps
 },[service,token,ident,handover,access]);

 if(!data||data.routeKey!==routeKey||(!handover&&!data.customer))return <Shell title="Your Service Dashboard">{error?<p role="alert">{error}</p>:<p>Opening your saved project…</p>}</Shell>;
 if(handover)return <Shell title={data.copy.handover_heading}><h2>{data.organization}</h2><RichContent text={data.copy.handover_description}/>{error&&<p role="alert">{error}</p>}<Button disabled={busy} onClick={()=>run(async()=>{const r=await api.post(`/services/${service}/handover/${token}`,{confirmed:true});navigate(r.data.url)})}>{data.copy.handover_cta}</Button></Shell>;
 if(service==='board-fundraising')return <FundraisingWorkspace/>;
 const reload=async()=>setData({...((await api.get(operatorBase)).data),routeKey});
 return <Shell title={data.copy.dashboard_heading}><h2>{data.customer.organization}</h2>{owner&&<p><a href={'/admin/services/'+service+'/customers/'+ident}>Back to Customer</a></p>}<p className="service-operator-label">YOUR ORGANIZATION IS IN CONTROL</p>{error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}{service==='recruitment'?<RecruitmentWorkspace base={base} record={data.customer} run={run} busy={busy} onRefresh={reload} operator={!owner}/>:service==='board-recommitment'?<RecommitmentWorkspace base={base} record={data.customer} run={run} busy={busy} onRefresh={reload}/>:<PlanningWorkspace base={base} record={data.customer} run={run} busy={busy}/>}<section className="guided-card"><h2>Ask for Support</h2><Field label="Your support request" large value={help} onChange={setHelp}/><Button disabled={busy||help.trim().length<5} onClick={()=>run(async()=>{await api.post(base+'/support',{message:help});setHelp('');setNotice('Your support request is saved for Rooney.')})}>Send Support Request</Button></section></Shell>;
}
