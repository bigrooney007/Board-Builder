import {useEffect,useState} from 'react';
import {Link,Navigate,useParams,useSearchParams} from 'react-router-dom';
import {api,Button,Field,problem,serviceNames} from './shared';
import {AdminAccess,OfferFrame,offerEditors,offerPath,customerPath,deliveryLabel} from './ServiceAdminShared';
export {QuestionEditor,EmailSettings} from './ServiceEditors';

const oldEditors={'Landing Page Copy':'landing','Entry Questions':'quote','Free Entry Questions':'quote','First Response Email':'first-email','Five-Email Follow-up Sequence':'followups','Post-Payment Questions':'post-payment','Lead User Planning Questions':'post-payment','Payment and Booking':'payment-booking','Customer Page Text':'confirmation'};
function CustomerList({service}){
 const [records,setRecords]=useState([]),[total,setTotal]=useState(0),[skip,setSkip]=useState(0),[search,setSearch]=useState(''),[status,setStatus]=useState(''),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 const load=async(offset=skip)=>{setLoading(true);setError('');try{const r=await api.get('/admin/services/'+service+'/customers',{params:{skip:offset,search,status}});setRecords(r.data.customers);setTotal(r.data.total);setSkip(offset)}catch(e){setError(problem(e))}finally{setLoading(false)}};
 useEffect(()=>{setSkip(0);load(0); // eslint-disable-next-line react-hooks/exhaustive-deps
 },[service]);
 return <OfferFrame service={service} title={serviceNames[service]}><section className="guided-card"><h2>Manage This Offer</h2><div className="service-shortcuts">{offerEditors.map(([section,label])=><Link className="button button-outline" key={section} to={offerPath(service)+'/settings/'+section}>{label}</Link>)}</div></section><section className="guided-card" data-testid="service-customer-list"><h2>Customers</h2><form className="guided-actions" onSubmit={e=>{e.preventDefault();load(0)}}><Field label="Search name, email or organization" value={search} onChange={setSearch}/><label className="guided-field">Payment status<select value={status} onChange={e=>setStatus(e.target.value)}><option value="">All customers</option>{['paid','unpaid','pending','failed'].map(v=><option key={v}>{v}</option>)}</select></label><button className="button" disabled={loading}>Search Customers</button></form>{error&&<p role="alert">{error}</p>}{loading&&<p>Loading customers...</p>}<div className="service-customer-table-wrap"><table className="service-customer-table"><thead><tr><th>Customer</th><th>Organization</th><th>First Email</th><th>Payment</th></tr></thead><tbody>{records.map(row=><tr key={row.customer_id}><td><Link className="service-customer-name" to={customerPath(service,row.customer_id)}>{row.name}</Link><small>{row.email}</small></td><td>{row.organization}</td><td>{deliveryLabel(row)}<small>{row.first_email_sent_at||row.first_email_due_at||''}</small></td><td>{row.payment_status}</td></tr>)}</tbody></table></div>{!loading&&!records.length&&<p>No quote requests to show.</p>}<div className="guided-actions"><Button secondary disabled={loading||skip===0} onClick={()=>load(Math.max(0,skip-50))}>Previous Customers</Button><p>{total?Math.min(skip+1,total):0}–{Math.min(skip+50,total)} of {total}</p><Button secondary disabled={loading||skip+50>=total} onClick={()=>load(skip+50)}>Next Customers</Button></div></section></OfferFrame>;
}
export default function ServiceAdminPage(){
 const {service}=useParams(),[query]=useSearchParams();
 if(query.get('customer'))return <Navigate replace to={customerPath(service,query.get('customer'))}/>;
 if(oldEditors[query.get('tab')])return <Navigate replace to={offerPath(service)+'/settings/'+oldEditors[query.get('tab')]}/>;
 return <AdminAccess><CustomerList service={service}/></AdminAccess>;
}
