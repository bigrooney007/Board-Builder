import {act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter,Route,Routes} from 'react-router-dom';
import MainHomePage from '@/pages/MainHomePage';
import MeetRooneyPage from './MeetRooneyPage';
import ConsultationPage from './ConsultationPage';
import RichContent from './RichContent';
import {professionalApi as api} from './content';
import defaults from '@/content/professionalEntry.json';

jest.mock('@/member/MemberAuthContext',()=>({useMemberAuth:()=>({member:null,loading:false,logout:jest.fn()})}));
jest.mock('@/pages/BlogPages',()=>({BlogSlider:()=> <a href="/blog">Existing Blog</a>}));
jest.mock('@/seo',()=>({useLandingPageMeta:jest.fn()}));
jest.mock('./content',()=>({
 defaults:jest.requireActual('@/content/professionalEntry.json'),
 useProfessionalContent:section=>jest.requireActual('@/content/professionalEntry.json')[section],
 professionalApi:{get:jest.fn(),post:jest.fn(),defaults:{baseURL:'http://localhost/api'}}
}));
let node,root;
beforeEach(()=>{globalThis.IS_REACT_ACT_ENVIRONMENT=true;jest.clearAllMocks();node=document.createElement('div');document.body.appendChild(node);root=createRoot(node);global.crypto={randomUUID:()=> '00000000-0000-4000-8000-000000000001'}});
afterEach(async()=>{await act(async()=>root.unmount());node.remove()});
const render=async element=>act(async()=>root.render(element));
const link=label=>[...node.querySelectorAll('a')].find(a=>a.textContent.includes(label));
const button=label=>[...node.querySelectorAll('button')].find(a=>a.textContent.includes(label));

test('directory has the four exact service promises and landing-page destinations',async()=>{
 await render(<MemoryRouter><MainHomePage/></MemoryRouter>);
 for(const [i,path] of ['/recruit','/board-fundraising','/strategic-planning','/board-recommitment'].entries()){
  expect(link(defaults.home.products[i].cta).getAttribute('href')).toBe(path);
  expect(node.textContent).toContain(defaults.home.products[i].title);
  expect(node.textContent).toContain(defaults.home.products[i].text);
 }
 expect(link('MEET ROONEY').getAttribute('href')).toBe('/meet-rooney');
 expect(node.querySelector('[data-testid="home-join-board-network-button"]').getAttribute('href')).toBe('/join-a-board');
 expect(link('Existing Blog').getAttribute('href')).toBe('/blog');
});

test('personal page uses the existing portrait, biography, all testimonials and separate paid/product paths',async()=>{
 await render(<MemoryRouter><MeetRooneyPage/></MemoryRouter>);
 expect(node.querySelector('img[alt="Rooney Akpesiri"]').getAttribute('src')).toBe(defaults.personal.portrait);
 expect(node.textContent).toContain("I've experienced nonprofit work from almost every side.");
 expect(link('BOOK A SESSION WITH ROONEY').getAttribute('href')).toBe('/consultation');
 expect(link('DEVELOP MY FUNDRAISING STRATEGY').getAttribute('href')).toBe('https://autofundraiser.com/');
 expect(link('GET MY BOARD MEMBERS FUNDRAISING').getAttribute('href')).toBe('/board-fundraising');
 expect(node.querySelector('[data-testid="rooney-testimonial-count"]').textContent).toContain('1 / 8');
 expect(node.textContent.toLowerCase()).not.toContain('free consultation');
});

test('supported formatting renders while scripts and unsafe links remain inert',async()=>{
 await render(<RichContent text={'## My Heading\n\n**Strong** and *emphasis* and [safe](https://example.org).\n\n- First\n- Second\n\n<script>alert(1)</script>\n\n[unsafe](javascript:alert)'}/>);
 expect(node.querySelector('h2').textContent).toBe('My Heading');
 expect(node.querySelector('strong').textContent).toBe('Strong');
 expect(node.querySelector('em').textContent).toBe('emphasis');
 expect(link('safe').getAttribute('href')).toBe('https://example.org');
 expect(node.querySelector('a[href^="javascript:"]')).toBeNull();
 expect(node.querySelector('script')).toBeNull();
 expect(node.querySelectorAll('li')).toHaveLength(2);
});

function resume(){return render(<MemoryRouter initialEntries={['/consultation/resume/secure-token']}><Routes><Route path="/consultation/resume/:token" element={<ConsultationPage/>}/></Routes></MemoryRouter>)}
test('unpaid confirmation cannot display a Calendly booking action',async()=>{
 api.post.mockResolvedValue({data:{payment_status:'pending'}});
 await resume();
 expect(node.textContent).toContain(defaults.consultation.unpaidMessage);
 expect(button('CHOOSE MY MEETING TIME')).toBeUndefined();
 expect(api.post).toHaveBeenCalledWith('/consultations/secure-token/confirm',{session_id:''});
 expect(document.head.querySelector('meta[name="referrer"]').content).toBe('no-referrer');
});
test('server-confirmed paid consultation can resume booking without another checkout',async()=>{
 api.post.mockResolvedValue({data:{payment_status:'paid',booking_status:'not_booked'}});
 await resume();
 expect(node.querySelector('h1').textContent).toBe(defaults.consultation.confirmedHeading);
 expect(button('CHOOSE MY MEETING TIME')).toBeDefined();
 expect(button('CONTINUE TO SECURE PAYMENT')).toBeUndefined();
 expect(api.post).toHaveBeenCalledTimes(1);
});
test('confirmation failure shows recovery and retry without falsely confirming payment',async()=>{
 api.post.mockRejectedValue({response:{data:{detail:'Payment confirmation is temporarily unavailable.'}}});
 await resume();
 expect(node.querySelector('[role="alert"]').textContent).toBe('Payment confirmation is temporarily unavailable.');
 expect(button(defaults.consultation.retryCta)).toBeDefined();
 expect(button(defaults.consultation.recoveryLinkLabel)).toBeDefined();
 expect(button('CHOOSE MY MEETING TIME')).toBeUndefined();
});
