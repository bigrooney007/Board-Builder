// Private consultation links must not enter public analytics or session recordings.
const isConsultation = pathname => /^\/(?:consultation|services)(?:\/|$)/.test(pathname);
function renderConsultationHtml(template) {
  const scripts = [...template.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>[\s\S]*?<\/script>/gi)]
    .filter(match => /^\/static\//.test(match[1])).map(match => match[0]).join("\n");
  const head = (template.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)?.[1] || "")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<title\b[^>]*>[\s\S]*?<\/title>/gi, "")
    .replace(/<meta\b[^>]*(?:name|property)=["'](?:robots|referrer|description|og:[^"']+|twitter:[^"']+)["'][^>]*>/gi, "")
    .replace(/<link\b[^>]*rel=["']canonical["'][^>]*>/gi, "");
  return `<!doctype html><html lang="en"><head><meta name="robots" content="noindex, nofollow"><meta name="referrer" content="no-referrer"><title>Professional Consultation | Nonprofit Board Builder</title>${head}${scripts}</head><body><div id="root"></div></body></html>`;
}
const headers = {"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store","Referrer-Policy":"no-referrer","X-Robots-Tag":"noindex, nofollow"};
function handler(readTemplate) {
  return async (req,res,next) => {
    if (!["GET","HEAD"].includes(req.method) || !isConsultation(new URL(req.url,"http://localhost").pathname)) return next();
    try {
      const html=renderConsultationHtml(await readTemplate());
      for (const [key,value] of Object.entries(headers)) res.setHeader(key,value);
      res.end(req.method==="HEAD"?undefined:html);
    } catch (error) { next(error); }
  };
}
module.exports={isConsultation,renderConsultationHtml,handler,headers};
