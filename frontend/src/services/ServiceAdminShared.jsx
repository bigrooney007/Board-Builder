import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {Login} from '@/pages/AdminPage';
import {api,Shell,serviceNames} from './shared';

export function AdminAccess({children}){
 const [user,setUser]=useState(null),[checking,setChecking]=useState(true);
 useEffect(()=>{let active=true;api.get('/auth/me').then(r=>{if(active)setUser(r.data)}).catch(()=>{if(active)setUser(false)}).finally(()=>{if(active)setChecking(false)});return()=>{active=false}},[]);
 if(checking)return <Shell title="Administration" admin><p>Checking administrator access...</p></Shell>;
 if(!user)return <Login onLogin={setUser}/>;
 return children;
}
export const offerPath=service=>'/admin/services/'+service;
export const customerPath=(service,id)=>offerPath(service)+'/customers/'+id;
export const offerEditors=[['landing','Edit Landing Page'],['quote','Edit Quote Form'],['confirmation','Edit Confirmation Message'],['first-email','Edit First Email'],['followups','Edit Follow-Up Emails'],['post-payment','Edit Post-Payment Form'],['payment-booking','Payment and Booking']];
export function OfferFrame({service,title,children}){
 return <Shell title={title||serviceNames[service]} admin><nav className="guided-nav" aria-label="Service administration">{Object.entries(serviceNames).map(([key,label])=><Link key={key} className="button button-outline" to={offerPath(key)}>{label}</Link>)}<Link className="button button-outline" to="/admin/blog">Blog &amp; Content</Link></nav>{children}</Shell>;
}
export function deliveryLabel(row){
 const labels={captured:'Captured sample',delivered:'Delivered',failed:'Failed',bounced:'Bounced',complained:'Suppressed',delayed:'Delayed',sending:'Sending',pending:'Queued',sent:'Provider accepted'};
 return labels[row.first_email_delivery_status]||(row.first_email_sent_at?'Provider accepted':row.first_email_due_at?'Scheduled':'Not scheduled');
}
