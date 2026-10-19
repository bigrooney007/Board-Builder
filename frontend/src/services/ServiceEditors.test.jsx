import {act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import ServiceAdminPage,{QuestionEditor} from './ServiceAdminPage';
import {api} from './shared';
jest.mock('@/pages/AdminPage',()=>({Login:()=> <p>Administrator login</p>}));
jest.mock('./RecruitmentWorkspace',()=>()=>null);
jest.mock('./RecommitmentWorkspace',()=>()=>null);
jest.mock('./PlanningWorkspace',()=>()=>null);
let node,root;
const rows=[{id:'mission',key:'mission',prompt:'What is your mission?',help:'Share your own words.',required:true,archived:false,type:'textarea',options:[]}];
beforeEach(()=>{globalThis.IS_REACT_ACT_ENVIRONMENT=true;node=document.createElement('div');document.body.append(node);root=createRoot(node);global.crypto={randomUUID:()=> '00000000-0000-4000-8000-000000000001'}});
afterEach(async()=>{await act(async()=>root.unmount());node.remove();jest.restoreAllMocks()});
test('question wording has an unambiguous accessible name and stable response identifiers',async()=>{
 const change=jest.fn();await act(async()=>root.render(<QuestionEditor rows={rows} onChange={change}/>));
 const field=node.querySelector('textarea[aria-label="Question 1 wording"]');expect(field.value).toBe('What is your mission?');
 const checkbox=[...node.querySelectorAll('label')].find(x=>x.textContent.includes('Archive this question')).querySelector('input');await act(async()=>checkbox.click());expect(change.mock.calls[0][0][0]).toMatchObject({id:'mission',key:'mission',archived:true});
});
test('the actual service admin opens the configured question editor after authentication',async()=>{
 jest.spyOn(api,'get').mockImplementation(path=>Promise.resolve({data:path==='/auth/me'?{user_id:'sample-admin'}:path.endsWith('/settings')?{config:{question_groups:{entry:rows}},revision:0,active:true,price:49700}: {customers:[],total:0}}));
 await act(async()=>root.render(<MemoryRouter initialEntries={['/admin/services/recruitment']}><Routes><Route path="/admin/services/:service" element={<ServiceAdminPage/>}/></Routes></MemoryRouter>));
 const button=[...node.querySelectorAll('button')].find(x=>x.textContent==='Entry Questions');expect(button).toBeTruthy();await act(async()=>button.click());
 expect(node.querySelector('textarea[aria-label="Question 1 wording"]').value).toBe('What is your mission?');
});
