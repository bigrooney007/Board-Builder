import {Fragment} from 'react';

// Deliberately renders a small, safe Markdown vocabulary rather than administrator HTML.
function inline(text){
 return String(text).split(/(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|\*[^*]+\*)/g).map((part,i)=>{
  const link=part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
  if(link){const href=link[2];return /^(https:\/\/|mailto:|\/(?!\/))/.test(href)?<a key={i} href={href} rel="noreferrer">{link[1]}</a>:<Fragment key={i}>{link[1]}</Fragment>}
  if(part.startsWith('**')&&part.endsWith('**'))return <strong key={i}>{part.slice(2,-2)}</strong>;
  if(part.startsWith('*')&&part.endsWith('*'))return <em key={i}>{part.slice(1,-1)}</em>;
  return <Fragment key={i}>{part}</Fragment>;
 });
}
export default function RichContent({text=''}){
 return <div className="professional-rich">{text.split(/\n\s*\n/).filter(s=>s.trim()).map((block,i)=>{
  const heading=block.match(/^(#{1,3})\s+(.+)$/);
  if(heading)return heading[1].length===3?<h3 key={i}>{inline(heading[2])}</h3>:<h2 key={i}>{inline(heading[2])}</h2>;
  if(block.trim().startsWith('- '))return <ul key={i}>{block.split('\n').map((line,n)=><li key={n}>{inline(line.replace(/^-\s*/,''))}</li>)}</ul>;
  return <p key={i}>{inline(block)}</p>;
 })}</div>;
}
