import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { HostContextHeader, HostDocShell, Paragraphs, copyText, useHostTools } from "./hostToolsShared";

export default function HostCallScriptPage() {
  const [params] = useSearchParams();
  const memberId = params.get("member") || "";
  const data = useHostTools(memberId);
  const [name, setName] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => { document.title = "Invitation Call Script | Board Fundraising Game"; }, []);

  if (!data) return <div className="bfg" style={{ minHeight: "100vh" }} />;
  const script = data.content.call_script;
  const context = data.context;
  const displayName = (name ?? context.member_first_name) || "[Board Member Name]";
  const fill = (text) => String(text || "").split("[Board Member First Name]").join(displayName);

  const fullText = [
    script.page_title,
    `Organization: ${context.organization_name}`,
    `Fundraising Goal: ${context.goal_display}`,
    ...(context.night_display ? [`Game Night: ${context.night_display}`] : []),
    "",
    ...script.sections.flatMap((section) => [section.heading.toUpperCase(), "", fill(section.body), ""]),
  ].join("\n");

  const copyFull = async () => {
    await copyText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <HostDocShell testId="bfg-call-script-page" actions={
      <>
        <button className="bfg-pf-btn ghost" onClick={copyFull} data-testid="bfg-cs-copy-btn">{copied ? "Script Copied" : "Copy Full Script"}</button>
        <button className="bfg-pf-btn" onClick={() => window.print()} data-testid="bfg-cs-print-btn">Print / Save As PDF</button>
      </>
    }>
      <HostContextHeader title={script.page_title} rows={[
        ["Organization", context.organization_name],
        ["Fundraising Goal", context.goal_display],
        ["Game Night", context.night_display],
      ]} />

      <p className="bfg-pf-summary bfg-ht-intro" data-testid="bfg-cs-intro">{script.intro}</p>

      <label className="bfg-ht-name bfg-no-print" data-testid="bfg-cs-name-field">
        <span>Board member first name</span>
        <input
          value={name ?? context.member_first_name}
          placeholder="[Board Member Name]"
          onChange={(event) => setName(event.target.value)}
          data-testid="bfg-cs-name-input"
        />
      </label>

      {script.sections.map((section) => (
        <section className="bfg-ht-doc-section" key={section.key} data-testid={`bfg-cs-section-${section.key}`}>
          <h2>{section.heading}</h2>
          <Paragraphs text={fill(section.body)} />
        </section>
      ))}
    </HostDocShell>
  );
}
