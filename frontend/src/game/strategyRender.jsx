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

export const MODE_LABELS = { working: "Working Strategy", board_prioritized: "Board-Prioritised Draft", final: "Final Fundraising Strategy" };

export const STATUS_LABELS = { final_draft: "Final Draft", adopted: "Adopted" };

const IDEA_AREA_LABELS = {
  fundraising_audiences: "Potential Fundraising Audiences", where_to_find: "Places To Find Funders",
  attraction: "Attraction Ideas", fundraising_process: "Fundraising Process Ideas", technology: "Technology Ideas",
  fundraising_team: "Team Ideas", materials: "Materials Ideas", execution_timeline: "Timeline Ideas",
};

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

const isEmptySection = (section, data) => {
  if (!data) return true;
  if (section.key === "executive_summary" || section.key === "next_step") return !String(data).trim();
  if (section.stages) return section.stages.every(([stageKey]) => !(data[stageKey] || []).length);
  if (section.priorityLabel) return !(data.priorities || []).length && !(data.additional_ideas || []).length;
  if (section.key === "fundraising_goal") return !data.summary && !data.amount;
  if (section.key === "additional_board_ideas") return !Object.values(data || {}).some((list) => (list || []).length);
  return false;
};

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
  if (section.stages) {
    return (
      <div>
        {section.stages.map(([stageKey, label]) => (
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
        <p className="bfg-doc-text">These ideas were contributed by your board but were not selected as current priorities. They remain available if your organisation decides to expand or adjust the strategy.</p>
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
  if (section.stages) {
    return section.stages.map(([stageKey, label]) =>
      `${label}\n${(data[stageKey] || []).map((item) => `- ${itemText(item)}`).join("\n")}`).join("\n\n");
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
  return (
    <div className="bfg-doc" data-testid="bfg-strategy-document">
      <header className="bfg-doc-header">
        <p className="bfg-doc-org">{strategy.organization_name}</p>
        <h1>{strategy.mode === "final" && strategy.status !== "adopted" ? "Final Fundraising Strategy" : "Fundraising Strategy"}</h1>
        <p className="bfg-doc-meta">
          {data.fundraising_goal?.amount && <>Fundraising Goal: <strong>{data.fundraising_goal.amount}</strong></>}
          {data.fundraising_goal?.deadline && <> · Deadline: <strong>{data.fundraising_goal.deadline}</strong></>}
        </p>
        <p className="bfg-doc-meta">
          <span className={`bfg-doc-type ${strategy.mode}`}>{STATUS_LABELS[strategy.status] || MODE_LABELS[strategy.mode] || strategy.mode}</span>
          {" "}· Version {strategy.version} · Generated: {strategy.generated_at ? new Date(strategy.generated_at).toLocaleString("en-US", { dateStyle: "long", timeStyle: "short" }) : ""}
          {strategy.adopted_at && <> · Adopted on {new Date(strategy.adopted_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}</>}
        </p>
      </header>
      <nav className="bfg-doc-toc" data-testid="bfg-strategy-toc">
        <h3>Strategy Sections</h3>
        <ol>
          {STRATEGY_SECTIONS.map((section) => (
            <li key={section.key}><a href={`#strategy-${section.key}`}>{section.title}</a></li>
          ))}
        </ol>
      </nav>
      {STRATEGY_SECTIONS.map((section, index) => (
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
