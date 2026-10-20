import {act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import GuidedServicePage from './GuidedServicePage';
import DashboardHandover from './DashboardHandover';
import {api} from './shared';
jest.mock('@/game/SpeakButton',()=>()=>null);
jest.mock('./ServiceResources',()=>()=>null);
jest.mock('./FundraisingResources',()=>()=>null);
let node,root;
beforeEach(()=>{global.IS_REACT_ACT_ENVIRONMENT=true;node=document.createElement('div');document.body.append(node);root=createRoot(node)});
afterEach(async()=>{await act(async()=>root.unmount());node.remove();jest.restoreAllMocks()});
for(const [service,amount] of [['board-fundraising',149700],['strategic-planning',199700]])test(service+' presents independent server-provided options and editable copy',async()=>{
 jest.spyOn(api,'get').mockResolvedValue({data:{organization:'Our Nonprofit',question_snapshot:[],answers:{},payment_status:'unpaid',packages:{'self-facilitated':{amount:49700},'rooney-facilitated':{amount}},copy:{offer_heading:'Our Edited Service Heading',offer_intro:'My own explanation.',self_heading:'Prepare Me to Run It',self_description:'My edited guidance description.',professional_heading:'Work With Rooney',professional_description:'My edited professional description.',self_cta:'PAY $497 AND PREPARE MY PROCESS',professional_cta:'PAY $'+(amount/100).toLocaleString('en-US')+' AND HAVE ROONEY FACILITATE'}}});
 await act(async()=>root.render(<MemoryRouter initialEntries={['/services/'+service+'/offer/private-link']}><Routes><Route path="/services/:service/:stage/:token" element={<GuidedServicePage/>}/></Routes></MemoryRouter>));
 expect(node.querySelector('h1').textContent).toBe('Our Edited Service Heading');expect(node.textContent).toContain('My own explanation.');expect(node.textContent).toContain('$497');expect(node.textContent).toContain('$'+(amount/100).toLocaleString('en-US'));
 expect(node.querySelectorAll('.service-offer-options section')).toHaveLength(2);expect(node.textContent).not.toMatch(/password|log in|get access/i);
});
test('professional facilitation has no dashboard handover button',async()=>{
 await act(async()=>root.render(<DashboardHandover service="strategic-planning" record={{customer_id:'c',purchased_package:'rooney-facilitated',operator_status:'rooney_facilitating'}} run={fn=>fn()}/>));
 expect(node.textContent).toContain('ROONEY FACILITATING');expect(node.textContent).not.toContain('HAND OVER DASHBOARD TO ORGANIZATION');
});
test('self-facilitation handover requires explicit preparation confirmation',async()=>{
 await act(async()=>root.render(<DashboardHandover service="board-fundraising" record={{customer_id:'c',purchased_package:'self-facilitated',operator_status:'rooney_preparing'}} run={fn=>fn()}/>));
 const button=[...node.querySelectorAll('button')].find(b=>b.textContent==='HAND OVER DASHBOARD TO ORGANIZATION');expect(button.disabled).toBe(true);
 await act(async()=>node.querySelector('input[type="checkbox"]').click());expect(button.disabled).toBe(false);
});
