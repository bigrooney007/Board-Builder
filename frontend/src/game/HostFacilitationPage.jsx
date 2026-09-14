import { useEffect, useState } from "react";
import { memberApi } from "@/member/api";
import { HostContextHeader, HostDocShell, Paragraphs, copyText, useHostTools } from "./hostToolsShared";

const blockLines = (block) => {
  if (block.kind === "group_link") return [];
  const lines = [];
  if (block.label) lines.push(block.label.toUpperCase());
  if (block.items) lines.push(...block.items.map((item, index) => block.kind === "numbered" ? `${index + 1}. ${item}` : `- ${item}`));
  else if (block.text) lines.push(block.text);
  lines.push("");
  return lines;
};

const Block = ({ block, groupLink, onCopyLink, linkCopied }) => {
  if (block.kind === "group_link") {
    if (!groupLink) return null;
    return (
      <button className="bfg-pf-btn ghost bfg-no-print" style={{ marginTop: 12 }} onClick={onCopyLink} data-testid="bfg-fg-copy-group-link-btn">
        {linkCopied ? "Link Copied" : "Copy Group Game Link"}
      </button>
    );
  }
  if (block.kind === "button_label") return <span className="bfg-ht-chip">{block.text}</span>;
  if (block.kind === "list" || block.kind === "numbered") {
    const List = block.kind === "numbered" ? "ol" : "ul";
    return (
      <div className="bfg-ht-block">
        {block.label && <p className="bfg-ht-label">{block.label}</p>}
        <List className="bfg-ht-list">{block.items.map((item, index) => <li key={index}>{item}</li>)}</List>
      </div>
    );
  }
  if (block.kind === "script") {
    return (
      <div className="bfg-ht-script">
        {block.label && <p className="bfg-ht-label">{block.label}</p>}
        <Paragraphs text={block.text} />
      </div>
    );
  }
  if (block.kind === "note") {
    return (
      <div className="bfg-ht-note">
        <p className="bfg-ht-label">{block.label || "Note"}</p>
        <Paragraphs text={block.text} />
      </div>
    );
  }
  return (
    <div className="bfg-ht-block">
      {block.label && <p className="bfg-ht-label">{block.label}</p>}
      <Paragraphs text={block.text} />
    </div>
  );
};

export default function HostFacilitationPage() {
  const data = useHostTools();
  const [openKeys, setOpenKeys] = useState({});
  const [groupToken, setGroupToken] = useState("");
  const [linkCopied, setLinkCopied] = useState(false);
  const [copied, setCopied] = useState("");

  useEffect(() => { document.title = "Facilitation Guide | Board Fundraising Game"; }, []);
  useEffect(() => {
    memberApi.get("/game/group/overview").then((response) => setGroupToken(response.data.session?.token || "")).catch(() => {});
  }, []);

  if (!data) return <div className="bfg" style={{ minHeight: "100vh" }} />;
  const guide = data.content.facilitation;
  const context = data.context;
  const groupLink = groupToken ? `${window.location.origin}/group-game/${groupToken}` : "";

  const toggle = (key) => setOpenKeys((current) => ({ ...current, [key]: !current[key] }));

  const copyGroupLink = async () => {
    await copyText(groupLink);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2500);
  };

  const sectionText = (section) => [section.heading.toUpperCase(), "", ...section.blocks.flatMap(blockLines)].join("\n");

  const fullText = [
    guide.page_title,
    `Organisation: ${context.organisation_name}`,
    `Fundraising Goal: ${context.goal_display}`,
    ...(context.night_display ? [`Game Night: ${context.night_display}`] : []),
    `Board Members Invited: ${context.invited_count}`,
    `Individual Games Completed: ${context.completed_count}`,
    "",
    ...guide.sections.map(sectionText),
  ].join("\n");

  const copyAll = async () => {
    await copyText(fullText);
    setCopied("all");
    setTimeout(() => setCopied(""), 2500);
  };

  const copySection = async (section) => {
    await copyText(sectionText(section));
    setCopied(section.key);
    setTimeout(() => setCopied(""), 2500);
  };

  return (
    <HostDocShell testId="bfg-facilitation-page" actions={
      <>
        <button className="bfg-pf-btn ghost" onClick={copyAll} data-testid="bfg-fg-copy-btn">{copied === "all" ? "Guide Copied" : "Copy Full Guide"}</button>
        <button className="bfg-pf-btn" onClick={() => window.print()} data-testid="bfg-fg-print-btn">Print / Save As PDF</button>
      </>
    }>
      <HostContextHeader title={guide.page_title} rows={[
        ["Organisation", context.organisation_name],
        ["Fundraising Goal", context.goal_display],
        ["Game Night", context.night_display],
        ["Board Members Invited", String(context.invited_count)],
        ["Individual Games Completed", String(context.completed_count)],
      ]} />

      {guide.sections.map((section) => (
        <section className={`bfg-ht-section ${openKeys[section.key] ? "bfg-ht-open" : ""}`} key={section.key} data-testid={`bfg-fg-section-${section.key}`}>
          <button className="bfg-ht-toggle" onClick={() => toggle(section.key)} data-testid={`bfg-fg-toggle-${section.key}`}>
            <span>{section.heading}</span>
            <span className="bfg-no-print">{openKeys[section.key] ? "−" : "+"}</span>
          </button>
          <div className="bfg-ht-body">
            {section.blocks.map((block, index) => (
              <Block key={index} block={block} groupLink={groupLink} onCopyLink={copyGroupLink} linkCopied={linkCopied} />
            ))}
            <div className="bfg-no-print" style={{ marginTop: 14 }}>
              <button className="bfg-pf-btn ghost" onClick={() => copySection(section)} data-testid={`bfg-fg-copy-section-${section.key}`}>
                {copied === section.key ? "Section Copied" : "Copy Section"}
              </button>
            </div>
          </div>
        </section>
      ))}
    </HostDocShell>
  );
}
