// Public promotional copy is price-free. Stored administrator wording is retained;
// Stripe and private organizational documents keep their actual financial data.
export function publicText(value){
 if(typeof value!=='string'||/^(https?:\/\/|data:)/.test(value))return value;
 return value.replace(/(?:US\s*)?\$\s*\d[\d,]*(?:\.\d{1,2})?/g,'')
  .replace(/\s*[·—–|:]\s*$/g,'').replace(/\b(?:for|at|costs?|priced at)\s*(?=[.!?]|$)/gi,'')
  .replace(/ {2,}/g,' ').trim();
}
export function publicContent(value){
 if(typeof value==='string')return publicText(value);
 if(Array.isArray(value))return value.map(publicContent);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,publicContent(item)]));
 return value;
}
