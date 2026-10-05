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
