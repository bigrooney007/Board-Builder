import axios from 'axios';
import {useEffect} from 'react';
import {Link} from 'react-router-dom';
import {SiteBrand} from '@/components/SiteBrand';
import RichContent from '@/professional/RichContent';
import '@/pages/MainHomePage.css';
import '@/professional/professional.css';
import './services.css';
export {RichContent};
export const api=axios.create({baseURL:`${process.env.REACT_APP_BACKEND_URL}/api`,withCredentials:true});
export const serviceNames={'recruitment':'Board Recruitment','board-recommitment':'Board Recommitment','strategic-planning':'Strategic Planning','board-fundraising':'Board Fundraising'};
export const problem=e=>typeof e.response?.data?.detail==='string'?e.response.data.detail:'This action could not be completed. Your saved work is retained. Please try again.';
export function Shell({title,children,admin=false,minimal=false}){useEffect(()=>{const robots=document.createElement('meta');robots.name='robots';robots.content='noindex, nofollow';const referrer=document.createElement('meta');referrer.name='referrer';referrer.content='no-referrer';document.head.append(robots,referrer);window.posthog?.stopSessionRecording?.();window.posthog?.set_config?.({autocapture:false,disable_session_recording:true});return()=>{robots.remove();referrer.remove()}},[]);return <div className="nBB-home professional-page guided-service"><header className="nBB-home-nav professional-nav"><SiteBrand/>{!minimal&&<nav><Link to="/">Our Services</Link><Link to="/meet-rooney">Meet Rooney</Link>{admin&&<Link to="/admin">Administration</Link>}</nav>}</header><main className={admin?'guided-admin':'professional-copy consultation-card'}>{title&&<h1>{title}</h1>}{children}</main><footer className="nBB-home-footer"><Link to="/">Nonprofit Board Builder</Link><Link to="/privacy-policy">Privacy</Link></footer></div>}
export function Field({label,value,onChange,large=false,type='text',...props}){return <label className="guided-field">{label}{large?<textarea {...props} aria-label={label} rows={7} value={value??''} onChange={e=>onChange(e.target.value)}/>:<input {...props} aria-label={label} type={type} value={value??''} onChange={e=>onChange(e.target.value)}/>}</label>}
export const Button=({children,secondary=false,...p})=><button type="button" className={secondary?'button button-outline':'button'} {...p}>{children}</button>;
export function EmailComposer({draft,onChange,onSend,busy,onCancel}){return <section className="guided-card" data-testid="service-email-composer"><h2>Review Your Email</h2>{['subject','preview_text','headline','body','cta','support','signature'].map(k=><Field key={k} label={`Email ${k==='body'?'message':k}`} large={k==='body'} value={draft[k]} onChange={v=>onChange({...draft,[k]:v})}/>)}<div className="guided-preview service-email-preview"><h3>{draft.subject}</h3><RichContent text={[draft.headline,draft.body,draft.support].filter(Boolean).join('\n\n')}/><p>{draft.cta}</p><RichContent text={draft.signature||''}/>{draft.recipient&&<p>Recipient: {draft.recipient}</p>}</div><div className="guided-actions"><Button disabled={busy} onClick={onSend}>Approve and Send Email</Button><Button secondary onClick={()=>navigator.clipboard.writeText(draft.body)}>Copy Email</Button><Button secondary onClick={onCancel}>Close</Button></div></section>}
export const latest=m=>m.versions?.find(v=>v.version===m.current_version)||{};
