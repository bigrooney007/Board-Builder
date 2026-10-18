import React from 'react';
import {createRoot} from 'react-dom/client';
import {act} from 'react';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import axios from 'axios';
import {PurchaseSuccessPage} from './PurchaseSuccessPage';
import {useMemberAuth} from './MemberAuthContext';

jest.mock('axios',()=>({get:jest.fn()}));
jest.mock('./MemberAuthContext',()=>({useMemberAuth:jest.fn()}));
jest.mock('./api',()=>({memberApi:{post:jest.fn()}}));
jest.mock('./MemberShell',()=>({MemberShell:({children})=><div>{children}</div>}));

let node,root;
beforeEach(()=>{globalThis.IS_REACT_ACT_ENVIRONMENT=true;node=document.createElement('div');document.body.appendChild(node);root=createRoot(node);axios.get.mockResolvedValue({data:{payment_status:'paid'}});localStorage.setItem('fundraisingLeadDetails',JSON.stringify({name:'Sample Leader',email:'leader@example.org'}));});
afterEach(async()=>{await act(async()=>root.unmount());node.remove();localStorage.clear();jest.clearAllMocks();});

test.each(['1497','997','497'])('verified $%s registration opens the purchased Fundraising Game setup',async tier=>{
 const register=jest.fn().mockResolvedValue({claimed:'board_fundraising_game',claimed_source:'board_fundraising_game_'+tier});
 useMemberAuth.mockReturnValue({member:null,loading:false,register,login:jest.fn(),refresh:jest.fn()});
 await act(async()=>root.render(<MemoryRouter initialEntries={['/purchase/success?session_id=paid-fixture']}><Routes><Route path="/purchase/success" element={<PurchaseSuccessPage/>}/><Route path="/game/setup" element={<h1>Purchased Game Setup</h1>}/></Routes></MemoryRouter>));
 expect(node.querySelector('[data-testid="purchase-paid"]')).not.toBeNull();
 await act(async()=>{for(const id of ['register-password','register-confirm-password']){const input=node.querySelector(`[data-testid="${id}"]`);Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'TemporaryFixturePassword123!');input.dispatchEvent(new Event('input',{bubbles:true}));}});
 await act(async()=>node.querySelector('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));
 expect(register).toHaveBeenCalledWith(expect.objectContaining({session_id:'paid-fixture',email:'leader@example.org',password:'TemporaryFixturePassword123!'}));
 expect(node.textContent).toContain('Purchased Game Setup');
});
