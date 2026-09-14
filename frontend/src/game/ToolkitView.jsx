import { useState } from "react";

export const ToolkitView = ({ toolkit, showPrint = true }) => {
  const [copiedId, setCopiedId] = useState("");
  if (!toolkit) return null;

  const copy = async (id, content) => {
    try { await navigator.clipboard.writeText(content); } catch { window.prompt("Copy this material:", content); }
    setCopiedId(id);
    setTimeout(() => setCopiedId(""), 2000);
  };

  return (
    <div className="bfg-pf-toolkit" data-testid="bfg-toolkit-view">
      {showPrint && (
        <div className="bfg-no-print" style={{ textAlign: "right", marginBottom: 10 }}>
          <button className="bfg-pf-btn ghost" onClick={() => window.print()} data-testid="bfg-toolkit-print-btn">
            Print / Save As PDF
          </button>
        </div>
      )}
      {toolkit.portfolio_summary && <p className="bfg-pf-summary">{toolkit.portfolio_summary}</p>}
      {(toolkit.material_packs || []).map((pack, packIndex) => (
        <section className="bfg-pf-pack" key={packIndex} data-testid={`bfg-toolkit-pack-${packIndex}`}>
          <h2>{pack.role_title || pack.pack_title}</h2>
          {pack.pack_title && pack.role_title && pack.pack_title !== pack.role_title && (
            <p className="bfg-pf-sub">{pack.pack_title}</p>
          )}
          {(pack.materials || []).map((material, materialIndex) => {
            const id = `${packIndex}-${materialIndex}`;
            return (
              <article className="bfg-pf-material" key={materialIndex} data-testid={`bfg-toolkit-material-${id}`}>
                <div className="bfg-pf-material-head">
                  <div>
                    <h3>{material.title}</h3>
                    {material.purpose && <p className="bfg-pf-sub">{material.purpose}</p>}
                  </div>
                  <button className="bfg-pf-btn ghost bfg-no-print" onClick={() => copy(id, material.content || "")}
                    data-testid={`bfg-copy-material-${id}`}>
                    {copiedId === id ? "Copied" : "Copy"}
                  </button>
                </div>
                <div className="bfg-pf-material-content">{material.content}</div>
              </article>
            );
          })}
        </section>
      ))}
    </div>
  );
};
