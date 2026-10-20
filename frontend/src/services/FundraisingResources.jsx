import {useEffect,useState} from 'react';
import {api,Shell,problem} from './shared';
import {AudienceDetails} from '@/game/AudienceGroupReview';
export default function FundraisingResources({token}){
 const [data,setData]=useState(null),[error,setError]=useState('');
 useEffect(()=>{api.get(`/services/board-fundraising/customer/${token}/fundraising`).then(r=>setData(r.data)).catch(e=>setError(problem(e)))},[token]);
 return <Shell title="Your Board Fundraising Resources">{error&&<p role="alert">{error}</p>}{data&&<><section className="guided-card"><h2>Submitted Fundraising Ideas</h2>{data.responses.map((r,i)=><details key={i}><summary>{r.name}</summary>{Object.entries(r.audiences).flatMap(([category,rows])=>rows.map(a=><AudienceDetails key={a.id} proposal={{category,contributor:r.name,strategy:a}}/>))}<p>{r.involvement}</p></details>)}{!data.responses.length&&<p>Your board members' ideas will appear here as they respond.</p>}</section>{data.strategy_url&&<section className="guided-card"><h2>Your Approved Fundraising Strategy</h2><a className="button" href={data.strategy_url}>View Approved Strategy</a><a className="button button-outline" href={data.strategy_pdf}>Download Strategy PDF</a></section>}{data.portfolios.map(p=><p key={p.token}><a className="button button-outline" href={'/board-portfolio/'+p.token+'/document.pdf'}>Download {p.member_name}'s Approved Portfolio</a></p>)}</>}</Shell>;
}
