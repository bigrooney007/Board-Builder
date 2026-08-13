import React, { useState } from "react";
import { CheckCircle2, Copy, Download, Pencil, Printer, RefreshCw, Send, Sparkles } from "lucide-react";
import { memberApi } from "../api";

export const printText = (title, text) => {
  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(`<html><head><title>${title}</title></head><body><pre style="font-family:Georgia,serif;white-space:pre-wrap;max-width:760px;margin:40px auto;line-height:1.6;">${text.replace(/</g, "&lt;")}</pre></body></html>`);
  win.document.close();
  win.print();
};

export const printBranded = (title, text, branding = {}) => {
  const win = window.open("", "_blank");
  if (!win) return;
  const primary = branding.primary_color || "#1d3a2f";
  const secondary = branding.secondary_color || "#f4f1ea";
  const logo = branding.logo_data ? `<img src="${branding.logo_data}" alt="" style="max-height:70px;max-width:220px;object-fit:contain;" />` : "";
  win.document.write(`<html><head><title>${title}</title><style>
    body{font-family:Georgia,'Times New Roman',serif;color:#1b1b1b;margin:0;}
    .doc{max-width:780px;margin:0 auto;padding:48px 56px;}
    .head{display:flex;align-items:center;justify-content:space-between;border-bottom:4px solid ${primary};padding-bottom:18px;margin-bottom:30px;}
    .head h1{font-size:24px;color:${primary};margin:0;}
    .band{background:${secondary};padding:10px 16px;font-size:12px;letter-spacing:1px;text-transform:uppercase;color:${primary};margin-bottom:26px;}
    pre{white-space:pre-wrap;font-family:inherit;line-height:1.7;font-size:14.5px;}
    @media print { .doc{padding:24px 8px;} }
  </style></head><body><div class="doc">
    <div class="head"><h1>${title.replace(/</g, "&lt;")}</h1>${logo}</div>
    <div class="band">${(branding.organization_name || "").replace(/</g, "&lt;")}</div>
    <pre>${text.replace(/</g, "&lt;")}</pre>
  </div></body></html>`);
  win.document.close();
  win.print();
};

export const downloadMaterialPdf = async (material) => {
  try {
    const response = await memberApi.get(`/workspace/material-pdf/${material.material_id}`, { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url; link.download = `${material.title || "Document"}.pdf`; link.click();
    URL.revokeObjectURL(url);
  } catch { window.alert("The PDF could not be downloaded."); }
};

export const currentVersion = (material) => material?.versions?.find((v) => v.version === material.current_version);

export const SendMaterialButton = ({ type, applicationId, label = "Send", sentAt = "", onSent, recipientEmail = "" }) => {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const send = async () => {
    const target = recipientEmail ? ` to ${recipientEmail}` : "";
    if (!window.confirm(`This will email the current saved version directly to the applicant${target}${sentAt ? " AGAIN (it was already sent)" : ""}. Send now?`)) return;
    setBusy(true); setMessage("");
    try {
      const response = await memberApi.post("/workspace/send-material", { type, application_id: applicationId, resend: Boolean(sentAt) });
      setMessage(`Sent to ${response.data.to}.`);
      if (onSent) onSent();
    } catch (err) {
      const detail = err.response?.data?.detail || "The email could not be sent.";
      if (detail.includes("email address")) {
        const entered = window.prompt("We do not have an email address for this applicant. Enter it once and it is saved to their record:");
        if (entered && entered.trim()) {
          try {
            await memberApi.patch(`/workspace/applications/${applicationId}`, { candidate_email: entered.trim() });
            const retry = await memberApi.post("/workspace/send-material", { type, application_id: applicationId, resend: Boolean(sentAt) });
            setMessage(`Sent to ${retry.data.to}.`);
            if (onSent) onSent();
            setBusy(false);
            return;
          } catch (err2) { setMessage(err2.response?.data?.detail || "The email could not be sent."); setBusy(false); return; }
        }
      }
      setMessage(detail);
    }
    setBusy(false);
  };
  return (
    <>
      {sentAt && <span className="blog-status-badge published" data-testid={`sent-${type}`}>Sent {new Date(sentAt).toLocaleString()}</span>}
      <button className="button button-back" disabled={busy} onClick={send} data-testid={`send-${type}`}><Send size={14} /> {busy ? "Sending…" : label}</button>
      {message && <p className="member-success" data-testid={`send-${type}-message`}>{message}</p>}
    </>
  );
};

export const MaterialCard = ({ type, title, buttonLabel, description, applicationId = "", material, refresh, instructions = "", children, testId, shareable = false, beforeGenerate, approvable = false, hideDisplay = false, summary = null, extraActions = null }) => {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [shareMessage, setShareMessage] = useState("");
  const version = currentVersion(material);
  const approved = material?.status === "Approved";

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

  const approve = async () => {
    setBusy(true);
    try { await memberApi.post(`/workspace/materials/${material.material_id}/approve`); await refresh(); }
    catch (err) { setError(err.response?.data?.detail || "Could not approve."); }
    setBusy(false);
  };

  const setCurrent = async (versionNumber) => {
    await memberApi.post(`/workspace/materials/${material.material_id}/current`, { version: Number(versionNumber) });
    await refresh();
  };

  return (
    <section className="material-card" data-testid={testId || `material-${type}`}>
      <div className="material-card-head">
        <h3>{title}{approvable && <span className={`blog-status-badge ${approved ? "published" : "pending"}`} style={{ marginLeft: 10 }} data-testid={`status-${type}`}>{material ? (approved ? "Approved" : "Generated") : "Not Generated"}</span>}</h3>
        {material && !hideDisplay && (
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
          {hideDisplay ? summary : <pre className="material-display" data-testid={`material-${type}-display`}>{version.display_text}</pre>}
          <div className="material-actions">
            {!hideDisplay && <button className="button button-back" onClick={() => { setDraft(version.display_text); setEditing(true); }} data-testid={`edit-${type}`}><Pencil size={14} /> Edit</button>}
            <button className="button button-back" disabled={busy} onClick={() => generate(true)} data-testid={`regenerate-${type}`}><RefreshCw size={14} /> {busy ? "Generating…" : "Regenerate"}</button>
            {!hideDisplay && <button className="button button-back" onClick={() => navigator.clipboard?.writeText(version.display_text)} data-testid={`copy-${type}`}><Copy size={14} /> Copy</button>}
            {!hideDisplay && <button className="button button-back" onClick={() => downloadMaterialPdf(material)} data-testid={`download-${type}`}><Download size={14} /> Download PDF</button>}
            {shareable && <button className="button button-back" onClick={copyShareLink} data-testid={`share-${type}`}><Copy size={14} /> Copy Share Link</button>}
            {approvable && !approved && <button className="button" disabled={busy} onClick={approve} data-testid={`approve-${type}`}><CheckCircle2 size={15} /> Approve</button>}
            {extraActions}
          </div>
          {approvable && !approved && <p className="workspace-note">Read it, edit anything you want changed, then approve it before use. Editing an approved resource returns it to Draft for re-approval.</p>}
          {shareMessage && <p className="member-success">{shareMessage}</p>}
          <p className="material-meta">Created {new Date(version.created_at).toLocaleString()} · Status: {approvable ? (approved ? "Approved" : "Draft") : material.status}</p>
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
