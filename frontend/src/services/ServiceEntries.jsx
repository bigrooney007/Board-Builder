import {useEffect,useState} from 'react';
import {useSearchParams} from 'react-router-dom';
import {GuidedLandingPage,GuidedStartPage} from '@/funnels/GuidedProductPages';
import GuidedServicePage from './GuidedServicePage';
import {api} from './shared';
export function ServiceLanding({service}){const [copy,setCopy]=useState(null);useEffect(()=>{let live=true;api.get('/services/'+service+'/questions').then(r=>{if(live)setCopy(r.data.landing)}).catch(()=>{});return()=>{live=false}},[service]);return <GuidedLandingPage product={service} landingOverride={copy}/>}
export function ServiceStart({service}){const [q]=useSearchParams();return q.get('token')?<GuidedStartPage product={service}/>:<GuidedServicePage fixedService={service}/>}
