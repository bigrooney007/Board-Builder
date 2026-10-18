import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { getStrategySections, StrategyDocument } from "./strategyRender";

global.IS_REACT_ACT_ENVIRONMENT = true;

test("the strategy shows its seven core sections without an unagreed execution plan", () => {
  const sections = getStrategySections({ schema_version: 4, data: {
    execution_agreements: [], technology: ["Old tools"], execution_timeline: { launch: ["Month one"] },
  } });
  expect(sections.map((section) => section.key)).toEqual([
    "executive_summary", "fundraising_audiences", "where_to_find", "attraction", "funding_ask", "fundraising_process", "board_roles",
  ]);
});

test("actual Board execution agreements appear as an optional final section", async () => {
  const strategy = { schema_version: 4, mode: "final", version: 1, data: {
    execution_agreements: ["Alex agreed to prepare the employer introduction email."],
  } };
  expect(getStrategySections(strategy)).toHaveLength(8);
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  try {
    await act(async () => root.render(<StrategyDocument strategy={strategy} />));
    expect(node.textContent).toContain("Execution Agreed By The Board");
    expect(node.textContent).toContain("Alex agreed to prepare the employer introduction email.");
    expect(node.textContent).not.toContain("Month one");
  } finally { await act(async () => root.unmount()); node.remove(); }
});

test("the approved strategy renders structured headings and bullets with an audience page boundary",async()=>{
  const strategy={schema_version:7,mode:"final",status:"adopted",version:1,data:{},document_sections:[{key:"audience_1",title:"1. Teachers in Pittsburgh",eyebrow:"Ideal Funding Audience:",page_break_before:true,text:"old raw text",blocks:[{kind:"bullet_heading",text:"Why They Would Give"},{kind:"body",text:"Teachers benefit from our work."},{kind:"subheading",text:"How We Will Attract Their Interest"},{kind:"bullet",text:"We will offer the guide agreed by our board."}]}],section_edits:{audience_1:"old raw text"}};
  const node=document.createElement("div");document.body.appendChild(node);const root=createRoot(node);
  try{
    await act(async()=>root.render(<StrategyDocument strategy={strategy}/>));
    expect(node.querySelector('[data-audience-page="true"]')).toBeTruthy();
    expect(node.querySelector('#strategy-audience_1 h2').textContent).toBe("1. Teachers in Pittsburgh");
    expect(node.querySelector('#strategy-audience_1 h3').textContent).toBe("Why They Would Give");
    expect(node.querySelector('#strategy-audience_1 h3').className).toBe("written-strategy-bullet-heading");
    expect(node.querySelector('#strategy-audience_1 li').textContent).toContain("offer the guide");
    expect(node.textContent).not.toContain("old raw text");
  }finally{await act(async()=>root.unmount());node.remove()}
});
