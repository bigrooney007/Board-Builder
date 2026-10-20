import {useEffect,useState} from 'react';
import {useSearchParams} from 'react-router-dom';
import {GuidedLandingPage,GuidedStartPage} from '@/funnels/GuidedProductPages';
import GuidedServicePage from './GuidedServicePage';
import RecruitmentHomePage from '@/funnels/RecruitmentHomePage';
import {api} from './shared';
export function ServiceLanding({service,startOpen=false}){const [copy,setCopy]=useState(null);useEffect(()=>{let live=true;api.get('/services/'+service+'/questions').then(r=>{if(live)setCopy(r.data.landing)}).catch(()=>{});return()=>{live=false}},[service]);return <GuidedLandingPage product={service} landingOverride={copy} startOpen={startOpen}/>}
export function ServiceStart({service}){
 const [query]=useSearchParams();
 if(query.get('lead'))return <GuidedServicePage fixedService={service}/>;
 if(query.get('token')&&service!=='recruitment')return <GuidedStartPage product={service}/>;
 return service==='recruitment'?<RecruitmentHomePage startOpen/>:<ServiceLanding service={service} startOpen/>;
}
