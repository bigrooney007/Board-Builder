import {useEffect, useState} from 'react';
import axios from 'axios';
import defaults from '@/content/professionalEntry.json';

export {defaults};
export const professionalApi = axios.create({baseURL:`${process.env.REACT_APP_BACKEND_URL}/api`,withCredentials:true});
export function useProfessionalContent(section){
  const [saved,setSaved]=useState({});
  useEffect(()=>{let alive=true;professionalApi.get('/professional/content').then(r=>{if(alive)setSaved(r.data.content[section]||{})}).catch(()=>{});return()=>{alive=false}},[section]);
  return {...defaults[section],...saved};
}

export const logoUrl='https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png';
