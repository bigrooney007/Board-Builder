import {useEffect} from 'react';
import {useNavigate} from 'react-router-dom';
export default function ServiceContactDialog(){return null;}
export function useServiceContact(service,initiallyOpen=false){
 const navigate=useNavigate();
 useEffect(()=>{if(initiallyOpen)navigate('/services/'+service+'/quote',{replace:true});},[initiallyOpen,navigate,service]);
 return {openContact:()=>navigate('/services/'+service+'/quote'),contactDialog:null};
}
