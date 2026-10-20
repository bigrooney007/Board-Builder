import {useEffect, useState} from 'react';
import axios from 'axios';
import defaults from '@/content/professionalEntry.json';
import {publicContent} from '@/content/publicPresentation';

export {defaults};
export const professionalApi = axios.create({baseURL:`${process.env.REACT_APP_BACKEND_URL}/api`,withCredentials:true});
export function useProfessionalContent(section){
  const [saved,setSaved]=useState({});
  useEffect(()=>{let alive=true;professionalApi.get('/professional/content').then(r=>{if(alive)setSaved(r.data.content[section]||{})}).catch(()=>{});return()=>{alive=false}},[section]);
  return publicContent({...defaults[section],...saved});
}

import {SITE_LOGO_URL as logoUrl} from "@/content/branding";

export {logoUrl};
