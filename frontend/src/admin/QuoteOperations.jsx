import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';

export default function QuoteOperations({client}){
 const [data,setData]=useState(null),[error,setError]=useState('');
 useEffect(()=>{client.get('/admin/service-overview').then(r=>setData(r.data)).catch(()=>setError('Administration could not load. Please refresh.'))},[client]);
 return <section className="member-card"><h2>Service Settings</h2>{error&&<p role="alert">{error}</p>}{data&&<><p>Payment and email settings are managed through each offer.</p>{data.services.map(row=><p key={row.service}><Link to={'/admin/services/'+row.service+'/settings/payment-booking'}>{row.name} Payment and Booking Settings</Link></p>)}</>}</section>;
}
