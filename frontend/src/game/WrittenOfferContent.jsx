import { Fragment } from "react";

const inline = value => value.split(/(\*\*[^*]+\*\*)/g).map((part,i)=>part.startsWith("**")?<strong key={i}>{part.slice(2,-2)}</strong>:<Fragment key={i}>{part}</Fragment>);
export default function WrittenOfferContent({text}) {
  return (text||"").split(/\n\s*\n/).filter(Boolean).map((block,i)=>{
    const heading=block.match(/^(#{1,3})\s+([\s\S]*)$/);
    if(heading)return heading[1].length===3?<h3 key={i} style={{marginTop:32}}>{inline(heading[2])}</h3>:<h2 key={i} style={{marginTop:40}}>{inline(heading[2])}</h2>;
    if(block.trim().startsWith('- '))return <ul key={i} style={{paddingLeft:24,textAlign:"left"}}>{block.split('\n').filter(Boolean).map((line,n)=><li key={n} style={{marginBottom:12,textAlign:"left"}}>{inline(line.replace(/^-\s*/,''))}</li>)}</ul>;
    return <p key={i} style={{textAlign:"left",whiteSpace:"pre-line",marginBottom:20}}>{inline(block)}</p>;
  });
}
