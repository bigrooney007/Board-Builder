const assert = require('node:assert/strict');
const {JSDOM}=require('../frontend/node_modules/jsdom');
const {renderConsultationHtml,handler}=require('../frontend/scripts/consultation-page.cjs');
const template='<!doctype html><html><head><title>Public</title><meta name="robots" content="index"><script src="https://assets.emergent.sh/scripts/emergent-main.js"></script><script defer src="/static/js/main.js"></script><link href="/static/css/main.css" rel="stylesheet"></head><body><div id="root"><main>Public directory</main></div><script>posthog.init("key")</script></body></html>';
const html=renderConsultationHtml(template),doc=new JSDOM(html).window.document;
assert.equal(doc.querySelector('#root').innerHTML,'');
assert.equal(doc.querySelector('meta[name="robots"]').content,'noindex, nofollow');
assert.equal(doc.querySelector('meta[name="referrer"]').content,'no-referrer');
assert.equal(doc.querySelectorAll('script').length,1);
assert.equal(doc.querySelector('script').src,'/static/js/main.js');
assert.equal(doc.querySelector('link').href,'/static/css/main.css');
assert(!html.includes('posthog')&&!html.includes('emergent-main')&&!html.includes('Public directory'));
(async()=>{
 const serve=handler(async()=>template);let ended=false;const headers={};
 await serve({url:'/consultation/resume/private-token',method:'GET'},{setHeader:(key,value)=>headers[key]=value,end:body=>{ended=true;assert(body.includes('no-referrer'))}},()=>{throw Error('Private route fell through')});
 assert(ended);assert.equal(headers['Cache-Control'],'no-store');assert.equal(headers['X-Robots-Tag'],'noindex, nofollow');
 let passed=false;await serve({url:'/board-fundraising-game',method:'GET'},{},()=>{passed=true});assert(passed);
 console.log('PASS private consultation HTML, no analytics/session recording, no-referrer and no-store; public game unchanged');
})().catch(error=>{console.error(error);process.exitCode=1});
