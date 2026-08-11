import React, { useState } from "react";
import { Copy, Download, Pencil, Printer, RefreshCw, Sparkles } from "lucide-react";
import { memberApi } from "../api";

export const printText = (title, text) => {
  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(`<html><head><title>${title}</title></head><body><pre style="font-family:Georgia,serif;white-space:pre-wrap;max-width:760px;margin:40px auto;line-height:1.6;">${text.replace(/</g, "&lt;")}</pre></body></html>`);
  win.document.close();
  win.print();
};

export const currentVersion = (material) => material?.versions?.find((v) => v.version === material.current_version);

export const MaterialCard = ({ type, title, buttonLabel, description, applicationId = "", material, refresh, instructions = "", children, testId, shareable = false, beforeGenerate }) => {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [shareMessage, setShareMessage] = useState("");
  const version = currentVersion(material);

  const copyShareLink = async () => {
    try {
      const response = await memberApi.post(`/workspace/materials/${material.material_id}/share`);
      const url = `${window.location.origin}/shared/${response.data.share_token}`;
      await navigator.clipboard?.writeText(url);
      setShareMessage("Share link copied. Anyone with this unlisted link can view the current version.");
    } catch { setShareMessage("Could not create the share link."); }
  };

  const generate = async (isRegenerate) => {
    if (isRegenerate && !window.confirm("This will create another version of this material. Continue?")) return;
    setBusy(true); setError("");
    try {
      if (beforeGenerate) {
        const proceed = await beforeGenerate();
        if (proceed === false) { setBusy(false); return; }
      }
      await memberApi.post("/workspace/generate", { type, application_id: applicationId, instructions });
      await refresh();
    } catch (err) { setError(err.response?.data?.detail || err.message || "Generation failed. Your information is preserved — you can try again."); }
    setBusy(false);
  };

  const saveEdit = async () => {
    setBusy(true); setError("");
    try {
      await memberApi.put(`/workspace/materials/${material.material_id}`, { display_text: draft });
      setEditing(false);
      await refresh();
    } catch (err) { setError(err.response?.data?.detail || "We could not save your changes."); }
    setBusy(false);
  };

  const setCurrent = async (versionNumber) => {
    await memberApi.post(`/workspace/materials/${material.material_id}/current`, { version: Number(versionNumber) });
    await refresh();
  };

  return (
    <section className="material-card" data-testid={testId || `material-${type}`}>
      <div className="material-card-head">
        <h3>{title}</h3>
        {material && (
          <label className="version-select">Version
            <select value={material.current_version} onChange={(event) => setCurrent(event.target.value)} data-testid={`material-${type}-version-select`}>
              {material.versions.map((v) => <option key={v.version} value={v.version}>Version {v.version}{v.version === material.current_version ? " (Current)" : ""}{v.source === "edited" ? " — edited" : ""}</option>)}
            </select>
          </label>
        )}
      </div>
      {description && <p className="material-description">{description}</p>}
      {children}
      {!material && (
        <button className="button" disabled={busy} onClick={() => generate(false)} data-testid={`generate-${type}`}>
          <Sparkles size={16} /> {busy ? "Generating…" : buttonLabel}
        </button>
      )}
      {material && version && !editing && (
        <>
          <pre className="material-display" data-testid={`material-${type}-display`}>{version.display_text}</pre>
          <div className="material-actions">
            <button className="button button-back" onClick={() => { setDraft(version.display_text); setEditing(true); }} data-testid={`edit-${type}`}><Pencil size={14} /> Edit</button>
            <button className="button button-back" disabled={busy} onClick={() => generate(true)} data-testid={`regenerate-${type}`}><RefreshCw size={14} /> {busy ? "Generating…" : "Regenerate"}</button>
            <button className="button button-back" onClick={() => navigator.clipboard?.writeText(version.display_text)} data-testid={`copy-${type}`}><Copy size={14} /> Copy</button>
            <button className="button button-back" onClick={() => printText(title, version.display_text)} data-testid={`print-${type}`}><Printer size={14} /> Print</button>
            <button className="button button-back" onClick={() => printText(title, version.display_text)} data-testid={`download-${type}`}><Download size={14} /> Download PDF</button>
            {shareable && <button className="button button-back" onClick={copyShareLink} data-testid={`share-${type}`}><Copy size={14} /> Copy Share Link</button>}
          </div>
          {shareMessage && <p className="member-success">{shareMessage}</p>}
          <p className="material-meta">Created {new Date(version.created_at).toLocaleString()} · Status: {material.status}</p>
        </>
      )}
      {editing && (
        <div className="material-edit">
          <textarea rows="16" value={draft} onChange={(event) => setDraft(event.target.value)} data-testid={`edit-${type}-textarea`} />
          <div className="material-actions">
            <button className="button" disabled={busy} onClick={saveEdit} data-testid={`save-${type}`}>Save Changes</button>
            <button className="button button-back" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      )}
      {error && (
        <div className="submit-error material-error" data-testid={`error-${type}`}>
          {error} <button className="link-button" disabled={busy} onClick={() => generate(false)}>Try Again</button>
        </div>
      )}
    </section>
  );
};
