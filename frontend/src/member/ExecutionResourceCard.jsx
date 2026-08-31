import { useState } from "react";
import { Download, X } from "lucide-react";
import { memberApi } from "./api";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const dialogStyle = { background: "#fff", maxWidth: 780, width: "100%", padding: "28px", borderRadius: 8, position: "relative" };

export const ExecutionResourceCard = ({ title, description, resource, basePath, testPrefix, generateLabel, load, disabled = false, disabledNote = "", children }) => {
  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState("");
  const status = resource?.status || "NONE";
  const text = resource?.display_text || "";

  const generate = async () => {
    if (text && !window.confirm(`This will replace the current ${title} with a newly generated version. Continue?`)) return;
    try { await memberApi.post(`${basePath}/generate`); load(); } catch (err) {
      window.alert(err.response?.data?.detail || "Generation could not start.");
    }
  };
  const saveEdit = async () => {
    try { await memberApi.put(basePath, { text: editText }); setShowEdit(false); load(); } catch { /* keep open */ }
  };
  const approve = async () => {
    try { await memberApi.post(`${basePath}/approve`); load(); } catch (err) {
      window.alert(err.response?.data?.detail || "Could not approve this resource.");
    }
  };

  return (
    <section className="member-card" data-testid={`${testPrefix}-card`}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <h2 style={{ margin: 0 }}>{title}</h2>
        <span className="eyebrow" style={{ padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid={`${testPrefix}-status`}>{status === "NONE" ? "NOT GENERATED" : status.toUpperCase()}</span>
      </div>
      <p style={{ marginTop: 10 }}>{description}</p>
      {status === "Failed" && <p className="submit-error" data-testid={`${testPrefix}-error`}>Generation failed. Please try again.</p>}
      {status === "Generating" ? (
        <p data-testid={`${testPrefix}-generating`}>Generating your {title}…</p>
      ) : (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
            <button type="button" className="button" onClick={generate} disabled={disabled} data-testid={`${testPrefix}-generate-button`}>{text ? "REGENERATE" : generateLabel}</button>
            {text && (
              <>
                <button type="button" className="button button-outline" onClick={() => { setEditText(text); setShowEdit(true); }} data-testid={`${testPrefix}-edit-button`}>EDIT</button>
                {status !== "Approved" && <button type="button" className="button" onClick={approve} data-testid={`${testPrefix}-approve-button`}>APPROVE</button>}
                <a className="button button-outline" href={`${API}${basePath}/pdf`} target="_blank" rel="noreferrer" data-testid={`${testPrefix}-pdf-button`}><Download size={15} /> DOWNLOAD PDF</a>
              </>
            )}
          </div>
          {disabled && disabledNote && <p style={{ marginTop: 10 }} data-testid={`${testPrefix}-disabled-note`}>{disabledNote}</p>}
        </>
      )}
      {children}
      {text && status !== "Generating" && (
        <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 18, marginTop: 14, maxHeight: 420, overflowY: "auto" }} data-testid={`${testPrefix}-text`}>{text}</div>
      )}
      {showEdit && (
        <div style={overlayStyle} data-testid={`${testPrefix}-edit-modal`}>
          <div style={dialogStyle}>
            <button type="button" onClick={() => setShowEdit(false)} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testPrefix}-edit-modal-close`}><X size={20} /></button>
            <h2>Edit {title}</h2>
            <textarea rows={22} style={{ width: "100%" }} value={editText} onChange={(e) => setEditText(e.target.value)} data-testid={`${testPrefix}-edit-text`} />
            <button type="button" className="button" onClick={saveEdit} data-testid={`${testPrefix}-save-button`}>SAVE</button>
          </div>
        </div>
      )}
    </section>
  );
};
