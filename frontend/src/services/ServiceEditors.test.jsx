import {act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import ServiceAdminPage,{QuestionEditor} from './ServiceAdminPage';
import ServiceOfferEditor from './ServiceOfferEditor';
import ServiceCustomerPage from './ServiceCustomerPage';
import ServiceQuotePage from './ServiceQuotePage';
import {api} from './shared';
jest.mock('@/pages/AdminPage',()=>({Login:()=> <p>Administrator login</p>}));
jest.mock('@/admin/HomepageTextSection',()=>({HomepageTextSection:()=>null}));
let node,root;
const rows=[{id:'mission',key:'mission',prompt:'What is your mission?',help:'Share your own words.',required:true,archived:false,type:'textarea',options:[]}];
const customer={customer_id:'requested',organization:'Requested Organization',name:'Sample Leader',email:'leader@example.org',first_email_sent_at:'2026-10-23T12:00:00Z',first_email_delivery_status:'sent',payment_status:'paid',question_snapshot:rows,answers:{mission:'Our original mission.'},leader_question_snapshot:rows,leader_answers:{mission:'Our detailed mission.'}};
const config={question_groups:{entry:rows},customer_copy:{quote_heading:'Request Your Quote',quote_subtitle:'Receive your quote in one hour',question_submit:'GET MY FREE QUOTE'}};
function routes(path){return <MemoryRouter initialEntries={[path]}><Routes><Route path="/admin/services/:service" element={<ServiceAdminPage/>}/><Route path="/admin/services/:service/settings/:section" element={<ServiceOfferEditor/>}/><Route path="/admin/services/:service/customers/:ident" element={<ServiceCustomerPage/>}/></Routes></MemoryRouter>}
function mockApi(){jest.spyOn(api,'get').mockImplementation(path=>Promise.resolve({data:path==='/auth/me'?{user_id:'sample-admin'}:path.endsWith('/settings')?{config,revision:0,active:true,price:49700}:path.endsWith('/customers/requested')?{customer,deliveries:[]}: {customers:[customer],total:1000}}));}
beforeEach(()=>{globalThis.IS_REACT_ACT_ENVIRONMENT=true;node=document.createElement('div');document.body.append(node);root=createRoot(node);global.crypto={randomUUID:()=> '00000000-0000-4000-8000-000000000001'}});
afterEach(async()=>{await act(async()=>root.unmount());node.remove();jest.restoreAllMocks()});
test('question wording and subtitles retain stable answer identifiers',async()=>{
 const change=jest.fn();await act(async()=>root.render(<QuestionEditor rows={[...rows,{...rows[0],id:'needs',key:'needs'}]} onChange={change}/>));
 expect(node.querySelector('textarea[aria-label="Question 1 wording"]').value).toBe('What is your mission?');
 expect(node.querySelector('textarea[aria-label="Question 1 subtitle"]').value).toBe('Share your own words.');
 const box=[...node.querySelectorAll('label')].find(x=>x.textContent.includes('Archive this question')).querySelector('input');await act(async()=>box.click());expect(change.mock.calls[0][0][0]).toMatchObject({id:'mission',key:'mission',archived:true});
});
test('editing links open their own route without keeping the customer table underneath',async()=>{
 mockApi();await act(async()=>root.render(routes('/admin/services/recruitment')));
 expect(node.querySelector('[data-testid="service-customer-list"]')).toBeTruthy();
 expect(node.querySelectorAll('[data-testid="service-customer-profile"]')).toHaveLength(0);
 await act(async()=>[...node.querySelectorAll('a')].find(x=>x.textContent==='Edit Quote Form').click());
 expect(node.querySelector('[data-testid="service-offer-editor"]')).toBeTruthy();
 expect(node.querySelector('[data-testid="service-customer-list"]')).toBeNull();
 expect(node.querySelector('textarea[aria-label="Question 1 wording"]').value).toBe('What is your mission?');
});
test('reducing the question count archives later questions without deleting historic identifiers',async()=>{
 const change=jest.fn(),questions=[...rows,{...rows[0],id:'needs',key:'needs'},{...rows[0],id:'count',key:'count'}];
 await act(async()=>root.render(<QuestionEditor rows={questions} onChange={change}/>));
 const input=node.querySelector('input[aria-label="Number of questions to show"]');
 await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'1');input.dispatchEvent(new Event('input',{bubbles:true}))});
 await act(async()=>[...node.querySelectorAll('button')].find(b=>b.textContent==='Apply Question Count').click());
 expect(change.mock.calls[0][0].map(q=>[q.id,q.archived])).toEqual([['mission',false],['needs',true],['count',true]]);
});
test('clicking a customer name opens a separate profile containing the requested three areas',async()=>{
 mockApi();await act(async()=>root.render(routes('/admin/services/recruitment')));
 await act(async()=>[...node.querySelectorAll('a')].find(x=>x.textContent==='Sample Leader').click());
 expect(node.querySelector('[data-testid="service-customer-list"]')).toBeNull();
 expect(node.querySelector('[data-testid="customer-quote-answers"]').textContent).toContain('Our original mission.');
 expect(node.querySelector('[data-testid="customer-post-payment-answers"]').textContent).toContain('Our detailed mission.');
 expect(node.querySelector('[data-testid="customer-dashboard-access"]')).toBeTruthy();
 expect(node.textContent).not.toMatch(/Record Video|Open Service Workspace|AI Board Member Recommendations/);
});
test('the profile provides the actual shareable dashboard URL through the protected endpoint',async()=>{
 mockApi();jest.spyOn(api,'post').mockResolvedValue({data:{url:'https://nonprofitboardbuilder.com/services/recruitment/dashboard/requested#access=private-token'}});
 await act(async()=>root.render(routes('/admin/services/recruitment/customers/requested')));
 await act(async()=>[...node.querySelectorAll('button')].find(b=>b.textContent==='Copy Customer Dashboard Link').click());
 expect(api.post).toHaveBeenCalledWith('/admin/services/recruitment/customers/requested/dashboard-access');
 expect(node.querySelector('a[href*="#access="]').href).toContain('#access=private-token');
});
test('a quote displays contact details and all questions together, then submits one complete request',async()=>{
 sessionStorage.clear();jest.spyOn(api,'get').mockResolvedValue({data:{copy:{...config.customer_copy,quote_name_label:'Your name',quote_email_label:'Email address',quote_organization_label:'Organization name'},questions:rows,version:'published-1'}});
 jest.spyOn(api,'post').mockResolvedValue({data:{url:'/services/recruitment/received/secure-result'}});jest.spyOn(window,'scrollTo').mockImplementation(()=>{});
 await act(async()=>root.render(<MemoryRouter initialEntries={['/services/recruitment/quote']}><Routes><Route path="/services/:service/quote" element={<ServiceQuotePage/>}/><Route path="/services/:service/received/:token" element={<p>Request received</p>}/></Routes></MemoryRouter>));
 expect(node.querySelectorAll('form input, form textarea')).toHaveLength(4);expect(node.querySelector('input[type="password"]')).toBeNull();
 for(const [label,value] of [['Your name','Sample Leader'],['Email address','leader@example.org'],['Organization name','Sample Organization'],['What is your mission?','Help children learn.']]){
  const field=node.querySelector('[aria-label="'+label+'"]');await act(async()=>{Object.getOwnPropertyDescriptor(field.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set.call(field,value);field.dispatchEvent(new Event('input',{bubbles:true}))});
 }
 await act(async()=>node.querySelector('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));
 expect(api.post).toHaveBeenCalledTimes(1);expect(api.post).toHaveBeenCalledWith('/services/recruitment/quote',expect.objectContaining({name:'Sample Leader',email:'leader@example.org',organization:'Sample Organization',answers:{mission:'Help children learn.'},question_version:'published-1'}));expect(node.textContent).toContain('Request received');
});
