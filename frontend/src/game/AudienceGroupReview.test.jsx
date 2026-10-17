import React, { act, useState } from "react";
import { createRoot } from "react-dom/client";
import { memberApi } from "@/member/api";
import AudienceGroupReview from "./AudienceGroupReview";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("@/member/api", () => ({ memberApi: { post: jest.fn() } }));

const initial = () => ({workflow_version:7,revision:1,phase:"audiences",index:0,
  proposals:[{id:"audience-1",category:"individuals",contributor:"Alex",strategy:{who_why:"Former mentors",where:"Our community",attraction:"Programme results",process:"Build trust",ask:"Mentoring places; $500"}}],
  decisions:{},statements:[],people:[],commitments:[],summary:{audiences:[],commitments:[],revision:"source"}});
const contribution={suggestion_id:"idea-1",proposal_id:"audience-1",kind:"field",field:"where",text:"The alumni association",quote:"We agreed to meet donors at the alumni association.",adoption:"agreed",status:"pending"};

async function fixture() {
  let saved=initial(),renderReview;
  const transcript={suggestions:[contribution],transcript:contribution.quote,source_hash:"source",reviewed_at:""};
  memberApi.post.mockReset();
  memberApi.post.mockImplementation(async(path)=>{
    if(path.endsWith("/extract"))return {data:transcript};
    if(path.endsWith("/confirm")){
      saved={...saved,revision:2,decisions:{"audience-1":{status:"pending",strategy:{...saved.proposals[0].strategy,where:"Our community\nThe alumni association"}}}};
      transcript.suggestions=[{...contribution,status:"included"}];transcript.reviewed_at="now";
    }
    return {data:{saved:true}};
  });
  function Harness(){const [review,setReview]=useState(saved);renderReview=setReview;return <AudienceGroupReview review={review} session={{status:"in_progress"}} reload={async()=>setReview({...saved})}/>}
  const node=document.createElement("div");document.body.appendChild(node);const root=createRoot(node);
  await act(async()=>root.render(<Harness/>));
  return {node,refresh:async()=>act(async()=>renderReview({...saved})),cleanup:async()=>{await act(async()=>root.unmount());node.remove()}};
}
async function click(node,text){const button=[...node.querySelectorAll("button")].find(b=>b.textContent===text);expect(button).toBeTruthy();await act(async()=>button.click())}
async function write(element,value){await act(async()=>{Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value").set.call(element,value);element.dispatchEvent(new Event("input",{bubbles:true}))})}

test("an explicitly accepted transcript contribution stays in the audience approval without losing other edits",async()=>{
  const {node,cleanup}=await fixture();
  try{
    await write(node.querySelector('[aria-label="How to attract their interest"]'),"Our agreed personal stories");
    await click(node,"Review Meeting Contributions");
    expect(node.querySelector('[aria-label="Where to find them"]').value).toBe("Our community");
    await click(node,"Include This Agreed Idea");
    expect(node.querySelector('[aria-label="Where to find them"]').value).toContain("The alumni association");
    expect(node.querySelector('[aria-label="How to attract their interest"]').value).toBe("Our agreed personal stories");
    await click(node,"Approve Audience");
    const saved=memberApi.post.mock.calls.find(([path,body])=>path.endsWith("/action")&&body.action==="decision")[1];
    expect(saved.strategy.where).toContain("The alumni association");
    expect(saved.strategy.attraction).toBe("Our agreed personal stories");
  }finally{await cleanup()}
});

test("ordinary meeting polling preserves the facilitator's unfinished edits",async()=>{
  const {node,refresh,cleanup}=await fixture();
  try{await write(node.querySelector('[aria-label="Where to find them"]'),"A locally edited answer");await refresh();expect(node.querySelector('[aria-label="Where to find them"]').value).toBe("A locally edited answer")}finally{await cleanup()}
});
