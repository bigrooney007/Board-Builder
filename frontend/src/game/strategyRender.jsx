import "./game.css";

export const STRATEGY_SECTIONS = [
  { key: "executive_summary", title: "Executive Summary" },
  { key: "fundraising_goal", title: "Our Fundraising Goal" },
  { key: "fundraising_audiences", title: "Who We Will Raise Money From", priorityLabel: "Priority Fundraising Audiences", additionalLabel: "Additional Board Ideas" },
  { key: "where_to_find", title: "Where We Will Find Them", priorityLabel: "Priority Places And Channels", additionalLabel: "Additional Places And Channels To Consider" },
  { key: "attraction", title: "How We Will Attract Their Attention", priorityLabel: "Priority Attraction Activities", additionalLabel: "Additional Ideas To Consider" },
  { key: "fundraising_process", title: "Our Fundraising Process", stages: [["know", "KNOW"], ["like", "LIKE"], ["trust", "TRUST"], ["ask", "ASK"], ["follow_up", "FOLLOW UP"], ["steward", "STEWARD"]] },
  { key: "technology", title: "Technology We Need To Execute", priorityLabel: "Priority Technology", additionalLabel: "Additional Technology To Consider" },
  { key: "fundraising_team", title: "The Fundraising Team We Need", priorityLabel: "Priority Team Roles", additionalLabel: "Additional Roles To Consider" },
  { key: "materials", title: "Fundraising Materials We Need", priorityLabel: "Priority Materials", additionalLabel: "Additional Materials To Consider" },
  { key: "execution_timeline", title: "Execution Timeline", stages: [["set_up", "SET UP"], ["launch", "LAUNCH"], ["execute", "EXECUTE"], ["review_and_improve", "REVIEW AND IMPROVE"]] },
  { key: "additional_board_ideas", title: "Additional Ideas From Your Board" },
  { key: "next_step", title: "Next Step" },
];

export const V2_STRATEGY_SECTIONS = [
  { key: "executive_summary", title: "Executive Summary" },
  { key: "fundraising_goal", title: "Fundraising Goal" },
  { key: "fundraising_audiences", title: "Ideal Funding Audiences", v2: "audiences" },
  { key: "where_to_find", title: "Where To Find Potential Funders", priorityLabel: "Priority Places And Channels", additionalLabel: "Additional Places And Channels To Consider" },
  { key: "attraction", title: "Attraction Strategy", priorityLabel: "Priority Attraction Activities", additionalLabel: "Additional Ideas To Consider" },
  { key: "fundraising_process", title: "Fundraising Process", v2: "process" },
  { key: "board_fundraising_process", title: "Board Fundraising Process", stages: [["know", "KNOW"], ["like", "LIKE"], ["trust", "TRUST"], ["ask", "ASK"], ["follow_up", "FOLLOW UP"], ["steward", "STEWARD"]] },
  { key: "team_roles", title: "Team, Roles & Responsibilities", v2: "team" },
  { key: "execution_resources", title: "Technology, Materials, Resources & Content", v2: "resources" },
  { key: "execution_budget", title: "Lean Execution Budget", v2: "budget" },
  { key: "execution_timeline", title: "Execution Timeline", stages: [["phase_1_build_the_system", "PHASE 1: BUILD THE SYSTEM"], ["phase_2_build_know_like_trust", "PHASE 2: BUILD KNOW, LIKE AND TRUST"], ["phase_3_ask_campaign", "PHASE 3: ASK CAMPAIGN"], ["follow_up_and_steward", "FOLLOW UP AND STEWARD"], ["business_timeline", "BUSINESS TIMELINE"], ["grantor_timeline", "GRANTOR TIMELINE"]] },
  { key: "board_priorities", title: "Board Priorities", v2: "grouped" },
  { key: "additional_board_ideas", title: "Additional Board Ideas", v2: "grouped" },
  { key: "next_step", title: "Next Step" },
];

export const getStrategySections = (strategy) =>
  (strategy?.schema_version || 1) >= 2 ? V2_STRATEGY_SECTIONS : STRATEGY_SECTIONS;

export const MODE_LABELS = { working: "Working Strategy", board_prioritized: "Board-Prioritized Draft", final: "Final Board Fundraising Strategy" };

export const STATUS_LABELS = { final_draft: "Final Draft", adopted: "Adopted" };

export const versionLabel = (row) => {
  if (row.mode === "working") return row.version > 1 ? "Updated Working Strategy" : "Working Strategy";
  if (row.mode === "final") return row.version > 1 ? "Updated Final Strategy" : "Final Board Fundraising Strategy";
  return MODE_LABELS[row.mode] || row.mode;
};

const IDEA_AREA_LABELS = {
  fundraising_audiences: "Potential Fundraising Audiences", where_to_find: "Places To Find Funders",
  attraction: "Attraction Ideas", fundraising_process: "Fundraising Process Ideas", technology: "Technology Ideas",
  fundraising_team: "Team Ideas", materials: "Materials Ideas", execution_timeline: "Timeline Ideas",
};

const AUDIENCE_LABELS = [["individuals", "Individuals"], ["businesses", "Businesses"], ["grantors", "Grantors"]];
const PROCESS_STAGES = [["know", "KNOW"], ["like", "LIKE"], ["trust", "TRUST"], ["ask", "ASK"], ["follow_up", "FOLLOW UP"], ["steward", "STEWARD"]];
const RESOURCE_LABELS = [["people", "People"], ["technology", "Technology"], ["materials", "Materials"], ["resources", "Resources"], ["content", "Content"]];

const EMPTY_MESSAGE = "Your board has not provided enough information for this section yet. Review this area together before adopting the final strategy.";

const itemText = (item) => typeof item === "string" ? item : [item?.title, item?.explanation, item?.focus].filter(Boolean).join(" — ");

const SourceTag = ({ item, mode }) => {
  const source = typeof item === "object" ? item?.source : (String(item).startsWith("Recommended Action") ? "recommendation" : "");
  if (source === "recommendation") return <span className="bfg-doc-tag rec">Recommended Action</span>;
  if (mode === "board_prioritized" && source === "board_priority") return <span className="bfg-doc-tag">Board Priority</span>;
  return null;
};

const PriorityList = ({ items, mode }) => (
  <div className="bfg-doc-cards">
    {(items || []).map((item, index) => (
      <div className="bfg-doc-card" key={index}>
        <div className="bfg-doc-card-head">
          <strong>{typeof item === "string" ? item : item?.title}</strong>
          <SourceTag item={item} mode={mode} />
        </div>
        {typeof item === "object" && item?.explanation && <p>{item.explanation}</p>}
        {typeof item === "object" && item?.focus && <p className="bfg-doc-focus">{item.focus}</p>}
      </div>
    ))}
  </div>
);

const Bullets = ({ items }) => (
  <ul className="bfg-doc-list">
    {(items || []).map((item, index) => <li key={index}>{itemText(item)}</li>)}
  </ul>
);

const hasStageContent = (process) => PROCESS_STAGES.some(([stage]) => ((process || {})[stage] || []).length);

const isEmptySection = (section, data) => {
  if (!data) return true;
  if (section.key === "executive_summary" || section.key === "next_step") return !String(data).trim();
  if (section.v2 === "audiences") return AUDIENCE_LABELS.every(([field]) => !(data[field] || []).length);
  if (section.v2 === "process") return AUDIENCE_LABELS.every(([field]) => !hasStageContent(data[field]));
  if (section.v2 === "team") return !(Array.isArray(data) && data.length);
  if (section.v2 === "resources") return RESOURCE_LABELS.every(([field]) => !(data[field] || []).length);
  if (section.v2 === "budget") return !(data.required_now || []).length && !(data.later_or_optional || []).length && !(data.cost_reduction_options || []).length && !String(data.budget_summary || "").trim();
  if (section.v2 === "grouped") return !(Array.isArray(data) && data.some((group) => (group.items || []).length));
  if (section.stages) return section.stages.every(([stageKey]) => !(data[stageKey] || []).length);
  if (section.priorityLabel) return !(data.priorities || []).length && !(data.additional_ideas || []).length;
  if (section.key === "fundraising_goal") return !data.summary && !data.amount;
  if (section.key === "additional_board_ideas") return !Object.values(data || {}).some((list) => (list || []).length);
  return false;
};

const Stages = ({ stages, data }) => (
  <div>
    {stages.map(([stageKey, label]) => (
      (data[stageKey] || []).length > 0 && (
        <div key={stageKey} className="bfg-doc-stage">
          <h4>{label}</h4>
          <Bullets items={data[stageKey]} />
        </div>
      )
    ))}
  </div>
);

export const SectionBody = ({ section, data, mode }) => {
  if (isEmptySection(section, data)) return <p className="bfg-doc-empty">{EMPTY_MESSAGE}</p>;
  if (section.key === "executive_summary" || section.key === "next_step") return <p className="bfg-doc-text">{data}</p>;
  if (section.key === "fundraising_goal") {
    return (
      <div>
        <div className="bfg-doc-goalbox">
          {data.amount && <p><strong>Goal:</strong> {data.amount}{data.currency && !String(data.amount).includes(data.currency) ? ` ${data.currency}` : ""}</p>}
          {data.deadline && <p><strong>Deadline:</strong> {data.deadline}</p>}
          {data.purpose && <p><strong>Purpose:</strong> {data.purpose}</p>}
        </div>
        {data.summary && <p className="bfg-doc-text">{data.summary}</p>}
      </div>
    );
  }
  if (section.v2 === "audiences") {
    return (
      <div>
        {AUDIENCE_LABELS.map(([field, label]) => (
          (data[field] || []).length > 0 && (
            <div key={field} className="bfg-doc-stage">
              <h4>{label.toUpperCase()}</h4>
              <PriorityList items={data[field]} mode={mode} />
            </div>
          )
        ))}
      </div>
    );
  }
  if (section.v2 === "process") {
    return (
      <div>
        {AUDIENCE_LABELS.map(([field, label]) => {
          const process = data[field] || {};
          if (!hasStageContent(process) && !process.how_this_process_works) return null;
          return (
            <div key={field} className="bfg-doc-stage">
              <h4>{label.toUpperCase()} FUNDRAISING PROCESS</h4>
              {process.how_this_process_works && (
                <div style={{ marginBottom: 10 }}>
                  <h4 className="bfg-doc-sublabel">HOW THIS PROCESS WORKS</h4>
                  <p className="bfg-doc-text">{process.how_this_process_works}</p>
                </div>
              )}
              <Stages stages={PROCESS_STAGES} data={process} />
            </div>
          );
        })}
      </div>
    );
  }
  if (section.v2 === "team") {
    return (
      <div className="bfg-doc-cards">
        {data.map((row, index) => (
          <div className="bfg-doc-card" key={index}>
            <div className="bfg-doc-card-head"><strong>{row.role}</strong></div>
            <p>Assigned: {String(row.assigned || "").trim() || "ROLE / CAPACITY NEEDED"}</p>
            {row.responsibility && <p className="bfg-doc-focus">{row.responsibility}</p>}
          </div>
        ))}
      </div>
    );
  }
  if (section.v2 === "resources") {
    return (
      <div>
        {RESOURCE_LABELS.map(([field, label]) => (
          (data[field] || []).length > 0 && (
            <div key={field} className="bfg-doc-stage">
              <h4>{label.toUpperCase()}</h4>
              <Bullets items={data[field]} />
            </div>
          )
        ))}
      </div>
    );
  }
  if (section.v2 === "budget") {
    return (
      <div>
        {(data.required_now || []).length > 0 && <div className="bfg-doc-stage"><h4>REQUIRED NOW</h4><div className="bfg-doc-cards">{data.required_now.map((item, index) => <div className="bfg-doc-card" key={index}><div className="bfg-doc-card-head"><strong>{item.item}</strong></div>{item.why_needed && <p><strong>Why needed:</strong> {item.why_needed}</p>}{item.lowest_cost_approach && <p className="bfg-doc-focus"><strong>Lean approach:</strong> {item.lowest_cost_approach}</p>}{item.cost && <p><strong>Cost:</strong> {item.cost}</p>}</div>)}</div></div>}
        {(data.later_or_optional || []).length > 0 && <div className="bfg-doc-stage"><h4>LATER / OPTIONAL</h4><div className="bfg-doc-cards">{data.later_or_optional.map((item, index) => <div className="bfg-doc-card" key={index}><div className="bfg-doc-card-head"><strong>{item.item}</strong></div>{item.why_later && <p><strong>Why later:</strong> {item.why_later}</p>}{item.lowest_cost_approach && <p className="bfg-doc-focus"><strong>Lean approach:</strong> {item.lowest_cost_approach}</p>}{item.cost && <p><strong>Cost:</strong> {item.cost}</p>}</div>)}</div></div>}
        {(data.cost_reduction_options || []).length > 0 && <div className="bfg-doc-stage"><h4>WAYS TO REDUCE THE COST</h4><Bullets items={data.cost_reduction_options} /></div>}
        {data.budget_summary && <p className="bfg-doc-text">{data.budget_summary}</p>}
      </div>
    );
  }
  if (section.v2 === "grouped") {
    return (
      <div>
        {data.map((group, index) => (
          (group.items || []).length > 0 && (
            <div key={index} className="bfg-doc-stage">
              <h4>{group.area}</h4>
              <Bullets items={group.items} />
            </div>
          )
        ))}
      </div>
    );
  }
  if (section.stages) {
    const required = section.key === "board_fundraising_process" || section.key === "execution_timeline"
      ? section.stages.filter(([stageKey]) => (data[stageKey] || []).length)
      : section.stages;
    return (
      <div>
        {required.map(([stageKey, label]) => (
          <div key={stageKey} className="bfg-doc-stage">
            <h4>{label}</h4>
            {(data[stageKey] || []).length ? <Bullets items={data[stageKey]} /> : <p className="bfg-doc-empty">{EMPTY_MESSAGE}</p>}
          </div>
        ))}
      </div>
    );
  }
  if (section.key === "additional_board_ideas") {
    return (
      <div>
        <p className="bfg-doc-text">These ideas were contributed by your board but were not selected as current priorities. They remain available if your organization decides to expand or adjust the strategy.</p>
        {Object.entries(IDEA_AREA_LABELS).map(([areaKey, label]) => (
          (data[areaKey] || []).length > 0 && (
            <div key={areaKey} className="bfg-doc-stage">
              <h4>{label}</h4>
              <Bullets items={data[areaKey]} />
            </div>
          )
        ))}
      </div>
    );
  }
  return (
    <div>
      {(data.priorities || []).length > 0 && (
        <>
          <h4 className="bfg-doc-sublabel">{section.priorityLabel}</h4>
          <PriorityList items={data.priorities} mode={mode} />
        </>
      )}
      {(data.additional_ideas || []).length > 0 && (
        <>
          <h4 className="bfg-doc-sublabel">{section.additionalLabel}</h4>
          <Bullets items={data.additional_ideas} />
        </>
      )}
    </div>
  );
};

export const sectionToText = (section, data) => {
  if (!data) return "";
  if (section.key === "executive_summary" || section.key === "next_step") return String(data || "");
  if (section.key === "fundraising_goal") {
    return [data.amount && `Goal: ${data.amount}`, data.deadline && `Deadline: ${data.deadline}`,
            data.purpose && `Purpose: ${data.purpose}`, data.summary].filter(Boolean).join("\n\n");
  }
  if (section.v2 === "audiences") {
    return AUDIENCE_LABELS.map(([field, label]) =>
      (data[field] || []).length ? `${label.toUpperCase()}\n${data[field].map((item) => `- ${itemText(item)}`).join("\n")}` : "").filter(Boolean).join("\n\n");
  }
  if (section.v2 === "process") {
    return AUDIENCE_LABELS.map(([field, label]) => {
      const process = data[field] || {};
      if (!hasStageContent(process)) return "";
      const stages = PROCESS_STAGES.map(([stage, stageLabel]) =>
        (process[stage] || []).length ? `${stageLabel}\n${process[stage].map((item) => `- ${itemText(item)}`).join("\n")}` : "").filter(Boolean).join("\n\n");
      return `${label.toUpperCase()} FUNDRAISING PROCESS\n\n${stages}`;
    }).filter(Boolean).join("\n\n");
  }
  if (section.v2 === "team") {
    return (Array.isArray(data) ? data : []).map((row) =>
      `${row.role}\nAssigned: ${String(row.assigned || "").trim() || "ROLE / CAPACITY NEEDED"}${row.responsibility ? `\n${row.responsibility}` : ""}`).join("\n\n");
  }
  if (section.v2 === "resources") {
    return RESOURCE_LABELS.map(([field, label]) =>
      (data[field] || []).length ? `${label.toUpperCase()}\n${data[field].map((item) => `- ${itemText(item)}`).join("\n")}` : "").filter(Boolean).join("\n\n");
  }
  if (section.v2 === "budget") {
    const parts = [];
    if ((data.required_now || []).length) parts.push("REQUIRED NOW\n" + data.required_now.map((item) => "- " + item.item + (item.why_needed ? " — " + item.why_needed : "") + (item.lowest_cost_approach ? " — Lean approach: " + item.lowest_cost_approach : "") + " — Cost: " + (item.cost || "PRICE TO CONFIRM")).join("\n"));
    if ((data.later_or_optional || []).length) parts.push("LATER / OPTIONAL\n" + data.later_or_optional.map((item) => "- " + item.item + (item.why_later ? " — " + item.why_later : "") + (item.lowest_cost_approach ? " — Lean approach: " + item.lowest_cost_approach : "") + " — Cost: " + (item.cost || "PRICE TO CONFIRM")).join("\n"));
    if ((data.cost_reduction_options || []).length) parts.push("WAYS TO REDUCE THE COST\n" + data.cost_reduction_options.map((item) => "- " + item).join("\n"));
    if (data.budget_summary) parts.push(data.budget_summary);
    return parts.join("\n\n");
  }
  if (section.v2 === "grouped") {
    return (Array.isArray(data) ? data : []).map((group) =>
      (group.items || []).length ? `${group.area}\n${group.items.map((item) => `- ${itemText(item)}`).join("\n")}` : "").filter(Boolean).join("\n\n");
  }
  if (section.stages) {
    return section.stages.map(([stageKey, label]) =>
      (data[stageKey] || []).length ? `${label}\n${(data[stageKey] || []).map((item) => `- ${itemText(item)}`).join("\n")}` : "").filter(Boolean).join("\n\n");
  }
  if (section.key === "additional_board_ideas") {
    return Object.entries(IDEA_AREA_LABELS).map(([areaKey, label]) =>
      (data[areaKey] || []).length ? `${label}\n${data[areaKey].map((item) => `- ${itemText(item)}`).join("\n")}` : "").filter(Boolean).join("\n\n");
  }
  const parts = [];
  if ((data.priorities || []).length) parts.push(`${section.priorityLabel}\n${data.priorities.map((item) => `- ${itemText(item)}`).join("\n")}`);
  if ((data.additional_ideas || []).length) parts.push(`${section.additionalLabel}\n${data.additional_ideas.map((item) => `- ${itemText(item)}`).join("\n")}`);
  return parts.join("\n\n");
};

export const StrategyDocument = ({ strategy }) => {
  const data = strategy.data || {};
  const edits = strategy.section_edits || {};
  const sections = getStrategySections(strategy);
  return (
    <div className="bfg-doc" data-testid="bfg-strategy-document">
      <header className="bfg-doc-header">
        <p className="bfg-doc-org">{strategy.organization_name}</p>
        <h1>{strategy.mode === "final" && strategy.status !== "adopted" ? "Final Fundraising Strategy" : "Fundraising Strategy"}</h1>
        {(strategy.prepared_by || strategy.organization_name) && (
          <p className="bfg-doc-meta" data-testid="bfg-doc-prepared-by">
            Prepared By: <strong>{strategy.prepared_by || (strategy.mode === "final" ? `The Board of ${strategy.organization_name}` : strategy.organization_name)}</strong>
          </p>
        )}
        <p className="bfg-doc-meta">
          {data.fundraising_goal?.amount && <>Fundraising Goal: <strong>{data.fundraising_goal.amount}</strong></>}
          {data.fundraising_goal?.deadline && <> · Deadline: <strong>{data.fundraising_goal.deadline}</strong></>}
        </p>
        <p className="bfg-doc-meta">
          <span className={`bfg-doc-type ${strategy.mode}`}>{versionLabel(strategy)}</span>
          {" "}· Version {strategy.version} · Generated: {strategy.generated_at ? new Date(strategy.generated_at).toLocaleString("en-US", { dateStyle: "long", timeStyle: "short" }) : ""}
          {strategy.adopted_at && <> · Adopted on {new Date(strategy.adopted_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}</>}
        </p>
      </header>
      <nav className="bfg-doc-toc" data-testid="bfg-strategy-toc">
        <h3>Strategy Sections</h3>
        <ol>
          {sections.map((section) => (
            <li key={section.key}><a href={`#strategy-${section.key}`}>{section.title}</a></li>
          ))}
        </ol>
      </nav>
      {sections.map((section, index) => (
        <section key={section.key} id={`strategy-${section.key}`} className="bfg-doc-section" data-testid={`bfg-strategy-section-${section.key}`}>
          <h2><span>{index + 1}.</span> {section.title}</h2>
          {edits[section.key] ? (
            <p className="bfg-doc-text" style={{ whiteSpace: "pre-line" }}>{edits[section.key]}</p>
          ) : (
            <SectionBody section={section} data={data[section.key]} mode={strategy.mode} />
          )}
        </section>
      ))}
    </div>
  );
};
