import {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {api,Button,problem} from './shared';

export default function PostPaymentTestButton({service}){
 const navigate=useNavigate();
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const start=async()=>{if(busy)return;setBusy(true);setError('');try{const r=await api.post('/admin/services/'+service+'/test-post-payment');navigate(r.data.url)}catch(e){setError(problem(e));setBusy(false)}};
 return <><Button secondary disabled={busy} onClick={start}>{busy?'Opening Test...':'Test Post-Payment Flow'}</Button>{error&&<p role="alert">{error}</p>}</>;
}
