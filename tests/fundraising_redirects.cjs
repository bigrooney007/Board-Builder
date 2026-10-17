const assert = require('node:assert/strict');
const redirect = require('../frontend/scripts/fundraising-redirects.cjs');
for (const [url,code,target] of [
 ['/recruit',301,'/how-the-fundraising-game-works'],
 ['/strategic-planning/video',301,'/how-the-fundraising-game-works'],
 ['/board-fundraising-game',301,'/'],
 ['/board-recommitment/video?session_id=cs_old',302,'/purchase/success?session_id=cs_old'],
]) {
 let observed;const res={writeHead:(status,headers)=>observed={status,headers},end:()=>{}};
 assert(redirect({method:'GET',url},res));assert.equal(observed.status,code);assert.equal(observed.headers.Location,target);
}
for (const url of ['/strategic-planning/dashboard','/strategic-planning/intake','/play/private-token','/group-game/private-token','/api/stripe/webhook','/app/board-recruitment']) {
 assert.equal(redirect({method:'GET',url},{}),false,url);
}
assert.equal(redirect({method:'POST',url:'/recruit'},{}),false);
console.log('PASS retired sales redirects, historical payment return and private customer routes');
