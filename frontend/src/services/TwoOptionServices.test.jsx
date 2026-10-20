import {act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import GuidedServicePage from './GuidedServicePage';
import DashboardHandover from './DashboardHandover';
import ServiceOperatorPage from './ServiceOperatorPage';
jest.mock('./PlanningWorkspace',()=>()=> <p>Prepared planning workspace</p>);
jest.mock('@/member/MemberAuthContext',()=>({useMemberAuth:()=>({refresh:jest.fn()})}));
import {api} from './shared';
jest.mock('@/game/SpeakButton',()=>()=>null);
jest.mock('./ServiceResources',()=>()=>null);
jest.mock('./FundraisingResources',()=>()=>null);
let node,root;
beforeEach(()=>{global.IS_REACT_ACT_ENVIRONMENT=true;node=document.createElement('div');document.body.append(node);root=createRoot(node)});
afterEach(async()=>{await act(async()=>root.unmount());node.remove();jest.restoreAllMocks()});
for(const service of ['recruitment','board-recommitment','board-fundraising','strategic-planning'])test(service+' presents one editable activation offer with no displayed amount',async()=>{
 jest.spyOn(api,'get').mockResolvedValue({data:{organization:'Our Nonprofit',question_snapshot:[],answers:{},submitted_at:'saved',payment_status:'unpaid',packages:{},copy:{offer_heading:'Our Edited Service Heading',offer_intro:'My own explanation.',activation_heading:'Begin With My Activation Call',activation_description:'My edited platform and dashboard description.',activation_cta:'BEGIN MY ACTIVATION'}}});
 await act(async()=>root.render(<MemoryRouter initialEntries={['/services/'+service+'/offer/private-link']}><Routes><Route path="/services/:service/:stage/:token" element={<GuidedServicePage/>}/></Routes></MemoryRouter>));
 expect(node.querySelector('h1').textContent).toBe('Our Edited Service Heading');expect(node.textContent).toContain('My own explanation.');expect(node.textContent).toContain('My edited platform and dashboard description.');
 expect([...node.querySelectorAll('button')].filter(b=>b.textContent==='BEGIN MY ACTIVATION')).toHaveLength(1);expect(node.textContent).not.toMatch(/\$\s*\d|password|log in|get access|done with you/i);
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

test('accepting a planning handover waits for the dashboard record before rendering it',async()=>{
 jest.spyOn(api,'get').mockImplementation(path=>Promise.resolve({data:path.includes('/handover/')?{organization:'Our Prepared Nonprofit',copy:{handover_heading:'Ready',handover_description:'Continue your existing project.',handover_cta:'OPEN MY DASHBOARD'}}:{customer:{customer_id:'prepared',organization:'Our Prepared Nonprofit'},copy:{dashboard_heading:'Our Planning Dashboard'}}}));
 jest.spyOn(api,'post').mockResolvedValue({data:{url:'/services/strategic-planning/dashboard/prepared'}});
 await act(async()=>root.render(<MemoryRouter initialEntries={['/services/strategic-planning/handover/invitation']}><Routes><Route path="/services/:service/handover/:token" element={<ServiceOperatorPage handover/>}/><Route path="/services/:service/dashboard/:ident" element={<ServiceOperatorPage/>}/></Routes></MemoryRouter>));
 await act(async()=>[...node.querySelectorAll('button')].find(b=>b.textContent==='OPEN MY DASHBOARD').click());
 expect(node.textContent).toContain('Prepared planning workspace');expect(node.textContent).toContain('Our Prepared Nonprofit');expect(node.textContent).toContain('YOUR ORGANIZATION IS IN CONTROL');
});
