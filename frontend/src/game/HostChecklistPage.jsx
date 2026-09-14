import { useEffect, useState } from "react";
import { memberApi } from "@/member/api";
import { HostContextHeader, HostDocShell, useHostTools } from "./hostToolsShared";

export default function HostChecklistPage() {
  const data = useHostTools();
  const [state, setState] = useState(null);

  useEffect(() => { document.title = "Game Night Checklist | Board Fundraising Game"; }, []);
  useEffect(() => {
    memberApi.get("/game/host-tools/checklist").then((response) => setState(response.data)).catch(() => {});
  }, []);

  if (!data || !state) return <div className="bfg" style={{ minHeight: "100vh" }} />;
  const checklist = data.content.checklist;
  const context = data.context;

  const toggle = (itemKey, checked) => {
    setState((current) => ({ ...current, checked: { ...current.checked, [itemKey]: checked } }));
    memberApi.put("/game/host-tools/checklist", { item_key: itemKey, checked }).catch(() => {});
  };

  return (
    <HostDocShell testId="bfg-checklist-page" actions={
      <button className="bfg-pf-btn" onClick={() => window.print()} data-testid="bfg-cl-print-btn">Print / Save As PDF</button>
    }>
      <HostContextHeader title={checklist.page_title} rows={[
        ["Organisation", context.organisation_name],
        ["Fundraising Goal", context.goal_display],
        ["Game Night", context.night_display],
      ]} />

      <p className="bfg-pf-summary bfg-ht-intro" data-testid="bfg-cl-intro">{checklist.intro}</p>
      {!state.has_night && (
        <p className="bfg-pf-note" data-testid="bfg-cl-no-night-note">
          Set up your Game Night on the dashboard to save this checklist for a specific meeting. A fresh checklist is created for each new Game Night.
        </p>
      )}

      {checklist.groups.map((group) => (
        <section className="bfg-ht-doc-section" key={group.key} data-testid={`bfg-cl-group-${group.key}`}>
          <h2>{group.heading}</h2>
          <div style={{ marginTop: 8 }}>
            {group.items.map((item, index) => {
              const itemKey = `${group.key}:${index}`;
              const done = !!state.checked[itemKey];
              return (
                <label className={`bfg-ht-check ${done ? "done" : ""}`} key={itemKey} data-testid={`bfg-cl-item-${group.key}-${index}`}>
                  <input type="checkbox" checked={done} onChange={(event) => toggle(itemKey, event.target.checked)} />
                  <span>{item}</span>
                </label>
              );
            })}
          </div>
        </section>
      ))}
    </HostDocShell>
  );
}
