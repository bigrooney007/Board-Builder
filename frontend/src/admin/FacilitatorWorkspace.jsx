import { useEffect,useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMemberAuth } from '@/member/MemberAuthContext';
import FundraisingWorkspace from '@/game/FundraisingWorkspace';
import GroupGamePage from '@/game/GroupGamePage';

export default function FacilitatorWorkspace({group=false}){
 const {userId}=useParams();const {refresh}=useMemberAuth();const [ready,setReady]=useState(false),[error,setError]=useState('');
 useEffect(()=>{let live=true;setReady(false);sessionStorage.removeItem('adminPreview');sessionStorage.removeItem('operateAsUserId');sessionStorage.setItem('fundraisingCustomer',userId);refresh().then(member=>{if(!live)return;if(member?.fundraising_facilitator)setReady(true);else setError('Sign in to administration to open this customer workspace.')});return()=>{live=false;sessionStorage.removeItem('fundraisingCustomer')}},[userId,refresh]);
 if(!ready)return <main className="fundraising-admin"><p>{error||'Opening customer workspace…'}</p>{error&&<a href="/admin">Administrator Sign In</a>}</main>;
 return group?<GroupGamePage/>:<FundraisingWorkspace/>;
}
