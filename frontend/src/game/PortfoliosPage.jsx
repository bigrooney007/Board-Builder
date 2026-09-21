import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

const STATUS_LABELS = {
  draft: "Draft", ready_to_send: "Ready To Send", sent: "Sent",
  change_requested: "Change Requested", approved: "Approved", materials_ready: "Execution Materials Ready",
};
const STATUS_COLORS = {
  draft: "#6B7280", ready_to_send: "#818cf8", sent: "#facc15",
  change_requested: "#fb923c", approved: "#059669", materials_ready: "#059669",
};

export default function PortfoliosPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => { document.title = "Board Fundraising Portfolios | Board Fundraising Game"; }, []);

  const load = useCallback(async () => {
    try { setData((await memberApi.get("/game/portfolios")).data); }
    catch (err) {
      if (err.response?.status === 409) setError("Adopt a fundraising strategy before creating Board Fundraising Portfolios.");
      else setError("We could not load your board portfolios.");
    }
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    load();
  }, [loading, member, navigate, load]);

  if (loading || (!data && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const prepare = async () => {
    setBusy(true);
    try { await memberApi.post("/game/portfolios/prepare"); await load(); }
    catch { setNotice("We could not prepare the portfolios. Please try again."); }
    setBusy(false);
  };

  const sendAll = async () => {
    setBusy(true); setNotice("");
    try {
      const result = (await memberApi.post("/game/portfolios/send-all", { origin_url: window.location.origin })).data;
      setNotice(`${result.count} portfolio${result.count === 1 ? "" : "s"} sent.`);
      await load();
    } catch { setNotice("We could not send the portfolios. Please try again."); }
    setBusy(false);
  };

  const readyCount = (data?.portfolios || []).filter((row) => row.status === "ready_to_send").length;

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-pf-back-dashboard">Back to Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-portfolios-page" style={{ maxWidth: 960 }}>
        {error && <div className="bfg-panel"><p className="bfg-error">{error}</p></div>}
        {data && (
          <>
            <div className="bfg-panel">
              <p className="bfg-eyebrow">Board Fundraising Portfolios</p>
              <h1>Board Fundraising Portfolios</h1>
              <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
                {data.goal_display && <>Fundraising Goal: <strong>{data.goal_display}</strong> · </>}
                Strategy: <strong style={{ color: "#059669" }}>Adopted</strong>
              </p>
              {data.executive_assistant_access?.status !== "not_started" && (
                <p className="bfg-note" style={{ marginTop: 8 }}>
                  Executive Assistants: <strong>{data.executive_assistant_access?.status === "renewal_required" ? "Renewal required" : "Included"}</strong>
                  {data.executive_assistant_access?.included_until && <> · Included through {new Date(data.executive_assistant_access.included_until).toLocaleDateString()}</>}
                </p>
              )}
              {data.total === 0 ? (
                <>
                  <p className="bfg-panel-sub" style={{ marginTop: 12 }}>
                    Turn your board's participation choices and Game Night commitments into a clear fundraising role for every board member.
                  </p>
                  <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 16 }} disabled={busy}
                    onClick={prepare} data-testid="bfg-create-portfolios-btn">
                    {busy ? "Preparing…" : "Create Board Fundraising Portfolios"}
                  </button>
                </>
              ) : (
                <>
                  <div className="bfg-mr-counts" data-testid="bfg-pf-readiness">
                    <span><strong>{data.approved_count}</strong> of {data.total} portfolios approved</span>
                    <span><strong>{data.toolkit_ready_count}</strong> of {data.total} execution toolkits ready</span>
                  </div>
                  <div className="bfg-bm-actions" style={{ marginTop: 14 }}>
                    {readyCount > 0 && (
                      <button className="bfg-btn bfg-btn-primary bfg-btn-sm" disabled={busy} onClick={sendAll} data-testid="bfg-send-all-btn">
                        {busy ? "Sending…" : `Send All Ready Portfolios (${readyCount})`}
                      </button>
                    )}
                    <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={busy} onClick={prepare} data-testid="bfg-prepare-missing-btn">
                      Prepare Missing Portfolios
                    </button>
                  </div>
                  {notice && <p className="bfg-note" style={{ marginTop: 10 }} data-testid="bfg-pf-notice">{notice}</p>}
                </>
              )}
            </div>

            {(data.portfolios || []).map((row) => (
              <div className="bfg-panel" key={row.portfolio_id} data-testid={`bfg-pf-row-${row.portfolio_id}`}>
                <div className="bfg-panel-head">
                  <div>
                    <h2>{row.member_name}</h2>
                    <p className="bfg-panel-sub" style={{ marginTop: 4 }}>
                      Portfolio: <strong style={{ color: STATUS_COLORS[row.status] || "#6B7280" }}>{STATUS_LABELS[row.status] || row.status}</strong>
                      {" "}· System-Building Roles: {row.system_count} · Fundraising Activities: {row.direct_count}
                    </p>
                    <p className="bfg-note" style={{ marginTop: 4 }}>
                      Execution Materials: {row.toolkit_status === "ready" ? "Ready" : row.toolkit_status === "generating" ? "Generating…" : row.status === "approved" || row.status === "materials_ready" ? "Not Generated Yet" : "Waiting For Portfolio Approval"}
                    </p>
                    {row.status === "change_requested" && row.change_request && (
                      <p className="bfg-note" style={{ marginTop: 6, color: "#fb923c" }} data-testid={`bfg-pf-change-${row.portfolio_id}`}>
                        Change Requested By {row.member_name.split(" ")[0]}: {row.change_request}
                      </p>
                    )}
                  </div>
                  <div className="bfg-bm-actions" style={{ marginTop: 0 }}>
                    <button className="bfg-btn bfg-btn-primary bfg-btn-sm"
                      onClick={() => navigate(`/game/portfolios/${row.portfolio_id}`)} data-testid={`bfg-review-portfolio-${row.portfolio_id}`}>
                      {row.status === "change_requested" ? "Edit Portfolio" : "Review Portfolio"}
                    </button>
                    {row.toolkit_status === "ready" && (
                      <button className="bfg-btn bfg-btn-ghost bfg-btn-sm"
                        onClick={() => navigate(`/game/portfolios/${row.portfolio_id}/toolkit`)} data-testid={`bfg-view-toolkit-${row.portfolio_id}`}>
                        View Execution Materials
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </main>
    </BfgShell>
  );
}
