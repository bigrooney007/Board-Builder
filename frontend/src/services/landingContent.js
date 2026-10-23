export function serviceLandingCopy(service,landing={}){
 const {headline,description,cta,...sections}=landing;
 return {...sections,...(headline!==undefined?{headline}:{}),...(description!==undefined?{[service==='recruitment'?'subheadline':'sub']:description}:{}),...(cta!==undefined?{primaryCta:cta}:{})};
}

export const quoteCta = value => !value || /(?:start|get started).*(?:free)|play.*fundraising game/i.test(value) ? 'GET A FREE QUOTE' : value;
