import {act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import ServiceAdminPage,{QuestionEditor} from './ServiceAdminPage';
import {api} from './shared';
jest.mock('@/pages/AdminPage',()=>({Login:()=> <p>Administrator login</p>}));
jest.mock('@/admin/HomepageTextSection',()=>({HomepageTextSection:()=>null}));
jest.mock('./RecruitmentWorkspace',()=>()=>null);
jest.mock('./RecommitmentWorkspace',()=>()=>null);
jest.mock('./PlanningWorkspace',()=>()=>null);
let node,root;
const rows=[{id:'mission',key:'mission',prompt:'What is your mission?',help:'Share your own words.',required:true,archived:false,type:'textarea',options:[]}];
beforeEach(()=>{globalThis.IS_REACT_ACT_ENVIRONMENT=true;node=document.createElement('div');document.body.append(node);root=createRoot(node);global.crypto={randomUUID:()=> '00000000-0000-4000-8000-000000000001'}});
afterEach(async()=>{await act(async()=>root.unmount());node.remove();jest.restoreAllMocks()});
test('question wording has an unambiguous accessible name and stable response identifiers',async()=>{
 const change=jest.fn();await act(async()=>root.render(<QuestionEditor rows={[...rows,{...rows[0],id:'needs',key:'needs'}]} onChange={change}/>));
 const field=node.querySelector('textarea[aria-label="Question 1 wording"]');expect(field.value).toBe('What is your mission?');
 expect(node.querySelector('textarea[aria-label="Question 1 subtitle"]').value).toBe('Share your own words.');
 const checkbox=[...node.querySelectorAll('label')].find(x=>x.textContent.includes('Archive this question')).querySelector('input');await act(async()=>checkbox.click());expect(change.mock.calls[0][0][0]).toMatchObject({id:'mission',key:'mission',archived:true});
});
test('the actual service admin opens the configured question editor after authentication',async()=>{
 jest.spyOn(api,'get').mockImplementation(path=>Promise.resolve({data:path==='/auth/me'?{user_id:'sample-admin'}:path.endsWith('/settings')?{config:{question_groups:{entry:rows}},revision:0,active:true,price:49700}: {customers:[],total:0}}));
 await act(async()=>root.render(<MemoryRouter initialEntries={['/admin/services/recruitment']}><Routes><Route path="/admin/services/:service" element={<ServiceAdminPage/>}/></Routes></MemoryRouter>));
 const button=[...node.querySelectorAll('button')].find(x=>x.textContent==='Entry Questions');expect(button).toBeTruthy();await act(async()=>button.click());
 expect(node.querySelector('textarea[aria-label="Question 1 wording"]').value).toBe('What is your mission?');
});

test('reducing the question count archives later questions and retains their stable identifiers',async()=>{
 const change=jest.fn(),questions=[...rows,{...rows[0],id:'needs',key:'needs'},{...rows[0],id:'count',key:'count'}];
 await act(async()=>root.render(<QuestionEditor rows={questions} onChange={change}/>));
 const input=node.querySelector('input[aria-label="Number of questions to show"]');
 await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'1');input.dispatchEvent(new Event('input',{bubbles:true}))});
 await act(async()=>[...node.querySelectorAll('button')].find(button=>button.textContent==='Apply Question Count').click());
 expect(change.mock.calls[0][0].map(q=>[q.id,q.archived])).toEqual([['mission',false],['needs',true],['count',true]]);
});


test('a customer-specific administrator link opens the correct saved service record',async()=>{
 jest.spyOn(api,'get').mockImplementation(path=>Promise.resolve({data:path==='/auth/me'?{user_id:'sample-admin'}:path.endsWith('/settings')?{config:{question_groups:{entry:rows}},revision:0,active:true,price:49700}:path.endsWith('/customers/requested')?{customer:{customer_id:'requested',organization:'Requested Organization',name:'Sample Leader',email:'leader@example.org',first_email_sent_at:'2026-10-23T12:00:00Z',first_email_delivery_status:'captured',payment_status:'unpaid',question_snapshot:[],answers:{}},deliveries:[],continuation_url:'/saved-next-step',resources_url:'/saved-resources'}:{customers:[],total:0}}));
 await act(async()=>root.render(<MemoryRouter initialEntries={['/admin/services/recruitment?customer=requested']}><Routes><Route path="/admin/services/:service" element={<ServiceAdminPage/>}/></Routes></MemoryRouter>));
 expect(api.get).toHaveBeenCalledWith('/admin/services/recruitment/customers/requested');expect(node.querySelector('[data-testid="guided-customer-workspace"]').textContent).toContain('Requested Organization');expect(node.querySelector('[data-testid="guided-customer-workspace"]').textContent).toContain('Captured sample');
});
