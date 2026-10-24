import {Link,Navigate,useSearchParams} from 'react-router-dom';
import {api,Shell,serviceNames} from '@/services/shared';
import {AdminAccess,offerPath} from '@/services/ServiceAdminShared';
import BlogAdminSection from './BlogAdminSection';
export function AdminBlogPage(){return <AdminAccess><Shell title="Blog & Content" admin><p><Link to="/admin">Back to Administration</Link></p><BlogAdminSection client={api}/></Shell></AdminAccess>}
export default function ServiceAdminHome(){
 const [query]=useSearchParams();
 if(query.get('tab')==='blog')return <Navigate replace to="/admin/blog"/>;
 if(query.get('tab'))return <Navigate replace to={'/admin/website?'+query.toString()}/>;
 return <AdminAccess><Shell title="Nonprofit Board Builder Administration" admin><div className="service-admin-home" data-testid="service-admin-home">{Object.entries(serviceNames).map(([key,label])=><Link className="guided-card service-admin-offer" key={key} to={offerPath(key)}><h2>{label}</h2><p>Manage this offer and its customers</p></Link>)}</div><div className="guided-actions"><Link className="button" to="/admin/blog">Blog &amp; Content</Link><Link className="button button-outline" to="/admin/website">Website Management</Link><Link className="button button-outline" to="/admin/website?tab=help">Help Requests</Link></div></Shell></AdminAccess>;
}
