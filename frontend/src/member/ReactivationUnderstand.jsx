import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Brain, Download, Eye, FileText, X } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { ResponseView } from "./ReactivationStep2";
import { reactivationContent, reactivationUnderstandText } from "../content/appContent";

const C = reactivationContent.step3;
const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 60, display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: "40px 16px" };
const Modal = ({ children, onClose, testId }) => (
  <div style={overlayStyle} data-testid={testId}>
    <div style={{ background: "#fff", maxWidth: 860, width: "100%", padding: 28, borderRadius: 8, position: "relative" }}>
      <button type="button" onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer" }} data-testid={`${testId}-close`}><X size={20} /></button>
      {children}
    </div>
  </div>
);

const MemberUnderstanding = ({ row, reload }) => {
  const id = row.member_record_id;
  const [busy, setBusy] = useState(false);
  const [material, setMaterial] = useState(null);
  const [viewing, setViewing] = useState(false);
  const [response, setResponse] = useState(null);
  const [script, setScript] = useState(null);
  const [scriptViewing, setScriptViewing] = useState(false);
  const analysisStatus = material?.status || row.analysis?.status;

  const poll = useCallback(async (materialId) => {
    setBusy(true);
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 4000));
      try {
        const res = await memberApi.get(`/reactivation/materials/${materialId}`);
        if (res.data.status !== "Generating") {
          if (res.data.status !== "Failed") setMaterial(res.data);
          break;
        }
      } catch { break; }
    }
    setBusy(false);
    reload();
  }, [reload]);

  useEffect(() => {
    if (row.analysis?.status === "Generating" && !busy) poll(row.analysis.material_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [row.analysis?.status]);

  const generate = async () => {
    setBusy(true);
    try {
      const res = await memberApi.post(`/reactivation/board-members/${id}/analysis`);
      await poll(res.data.material_id);
    } catch (err) {
      window.alert(err.response?.data?.detail || "That did not work. Please try again.");
      setBusy(false);
    }
  };

  const openView = async () => {
    const m = material?.display_text ? material : (await memberApi.get(`/reactivation/materials/${material?.material_id || row.analysis.material_id}`)).data;
    setMaterial(m);
    setViewing(true);
  };

  const pollScript = async (materialId) => {
    setBusy(true);
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 4000));
      const res = await memberApi.get(`/reactivation/materials/${materialId}`);
      if (res.data.status !== "Generating") { if (res.data.status !== "Failed") setScript(res.data); break; }
    }
    setBusy(false); reload();
  };
  const generateScript = async () => {
    setBusy(true);
    try { const res = await memberApi.post(`/reactivation/board-members/${id}/conversation-script`); await pollScript(res.data.material_id); }
    catch (err) { window.alert(err.response?.data?.detail || "The call script could not be generated."); setBusy(false); }
  };
  const openScript = async () => {
    const materialId = script?.material_id || row.script?.material_id;
    const result = script?.display_text ? script : (await memberApi.get(`/reactivation/materials/${materialId}`)).data;
    setScript(result); setScriptViewing(true);
  };
  const downloadScript = async () => {
    const materialId = script?.material_id || row.script?.material_id;
    const res = await memberApi.get(`/reactivation/materials/${materialId}/pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data); const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `Call-Script-${row.name.replace(/[^a-zA-Z0-9]+/g, "-")}.pdf`; anchor.click(); URL.revokeObjectURL(url);
  };

  if (row.status !== "COMPLETED") {
    return (
      <article className="member-card" data-testid={`understand-waiting-${id}`}>
        <h3 style={{ margin: 0 }}>{row.name}</h3>
        <p style={{ margin: "4px 0 8px" }}>{row.role || "Board Member"}</p>
        <p className="eyebrow">{C.waitingBadge}</p>
      </article>
    );
  }

  const ready = (row.analysis || material) && !["Generating", "Failed"].includes(analysisStatus) && !busy;
  return (
    <article className="member-card" data-testid={`understand-member-${id}`}>
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div>
          <h3 style={{ margin: 0 }}>{row.name}</h3>
          <p style={{ margin: "4px 0 0" }}>
            {row.role || "Board Member"}
            {row.professional_role && <> · {row.professional_role}{row.employer ? `, ${row.employer}` : ""}</>}
          </p>
        </div>
        <span className="eyebrow" style={{ alignSelf: "flex-start", padding: "4px 10px", border: "1px solid #000", borderRadius: 999 }} data-testid={`understand-status-${id}`}>
          {ready ? "UNDERSTOOD" : "RESPONSE RECEIVED"}
        </span>
      </div>
      <div style={{ borderLeft: "4px solid #000", padding: "10px 14px", margin: "14px 0", background: "#fafafa" }}>
        <p className="eyebrow" style={{ margin: 0 }}>Recommitment Response</p>
        <p style={{ margin: "4px 0 0", fontWeight: 700 }} data-testid={`understand-recommitment-${id}`}>{row.recommitment}</p>
      </div>
      {row.expertise?.length > 0 && <p style={{ margin: "6px 0 0" }}><strong>Expertise:</strong> {row.expertise.slice(0, 6).join(", ")}</p>}
      {row.contribution_interests?.length > 0 && <p style={{ margin: "6px 0 0" }}><strong>{reactivationUnderstandText.wantsToContributeIn}</strong> {row.contribution_interests.slice(0, 4).join(", ")}</p>}
      {row.monthly_availability && <p style={{ margin: "6px 0 0" }}><strong>Availability:</strong> {row.monthly_availability}</p>}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
        <button type="button" className="button" onClick={generate} disabled={busy} data-testid={`understand-generate-${id}`}>
          <Brain size={15} /> {busy ? C.analyzingLabel : (row.analysis || material) ? "REANALYZE RESPONSE" : "ANALYZE RESPONSE"}
        </button>
        {ready && <button type="button" className="button button-outline" onClick={openView} data-testid={`understand-view-${id}`}><Eye size={15} /> {C.viewUnderstandingButton}</button>}
        <button type="button" className="button button-outline" onClick={async () => setResponse((await memberApi.get(`/reactivation/board-members/${id}/response`)).data)} data-testid={`understand-view-response-${id}`}>{C.viewResponseButton}</button>
        {ready && <button type="button" className="button" onClick={generateScript} disabled={busy} data-testid={`understand-generate-script-${id}`}><FileText size={15}/> {row.script||script?"REGENERATE CALL SCRIPT":"GENERATE INDIVIDUAL CALL SCRIPT"}</button>}
        {(row.script||script)&&!busy&&<><button type="button" className="button button-outline" onClick={openScript} data-testid={`understand-view-script-${id}`}>VIEW CALL SCRIPT</button><button type="button" className="button button-outline" onClick={downloadScript} data-testid={`understand-download-script-${id}`}><Download size={15}/> DOWNLOAD</button></>}
      </div>
      {analysisStatus === "Failed" && !busy && <p style={{ marginTop: 8 }} data-testid={`understand-failed-${id}`}>{C.failedLabel}</p>}
      {viewing && material && (
        <Modal onClose={() => setViewing(false)} testId={`understand-modal-${id}`}>
          <h2>Understanding {row.name}'s Response</h2>
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 18, borderRadius: 6, maxHeight: 520, overflowY: "auto" }} data-testid={`understand-text-${id}`}>{material.display_text}</div>
          <Link className="button" style={{ marginTop: 14 }} to="/app/reactivation/self-guided/module/4" data-testid={`understand-go-conversation-${id}`}>PREPARE THE CONVERSATION</Link>
        </Modal>
      )}
      {response && (
        <Modal onClose={() => setResponse(null)} testId={`understand-response-modal-${id}`}>
          <h2>{row.name} — Recommitment Response</h2>
          <ResponseView data={response} testPrefix="understand" />
        </Modal>
      )}
      {scriptViewing && script && <Modal onClose={() => setScriptViewing(false)} testId={`understand-script-modal-${id}`}><h2>{row.name}'s Individual Call Script</h2><div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 18, borderRadius: 6, maxHeight: 520, overflowY: "auto" }}>{script.display_text}</div></Modal>}
    </article>
  );
};

export default function ReactivationUnderstand() {
  const { member } = useMemberAuth();
  const isBuf = Boolean(member?.entitlements?.includes("board_fix_system"));
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    memberApi.get("/reactivation/understand").then((res) => setData(res.data)).catch(() => setError("We could not load this step."));
  }, []);
  useEffect(load, [load]);

  if (error) return <p className="submit-error">{error}</p>;
  if (!data) return <p className="sh-loading">Loading your Board…</p>;
  const responded = data.members.filter((m) => m.status === "COMPLETED");
  const waiting = data.members.filter((m) => m.status !== "COMPLETED");

  return (
    <div data-testid="reactivation-understand">
      <section className="member-card" data-testid="understand-intro">
        <h2>{C.heading}</h2>
        {C.intro.map((p) => <p key={p}>{p}</p>)}
        <p className="eyebrow" data-testid="understand-progress">{C.progress(data.progress)}</p>
      </section>
      {responded.length === 0 && (
        <section className="member-card" data-testid="understand-empty">
          {isBuf ? (
            <p><strong>No Board Member responses have been received yet.</strong></p>
          ) : (
            <>
              <p>{C.emptyState}</p>
              <Link className="button button-outline" to="/app/reactivation/self-guided/module/2">{reactivationUnderstandText.goToStep2}</Link>
            </>
          )}
        </section>
      )}
      {responded.map((row) => <MemberUnderstanding key={row.member_record_id} row={row} reload={load} />)}
      {waiting.map((row) => <MemberUnderstanding key={row.member_record_id} row={row} reload={load} />)}
    </div>
  );
}
