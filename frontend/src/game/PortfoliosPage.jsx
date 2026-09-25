import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

const STATUS_LABELS = {
  draft: "Founder Review Required",
  ready_to_send: "Founder Approved",
  sent: "Shared",
  change_requested: "Board Member Requested A Change",
  approved: "Board Member Approved",
  materials_ready: "Execution Ready",
};

const STATUS_COLORS = {
  draft: "#6B7280",
  ready_to_send: "#4f46e5",
  sent: "#4f46e5",
  change_requested: "#c2410c",
  approved: "#059669",
  materials_ready: "#059669",
};

export default function PortfoliosPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => { document.title = "Board Fundraising Delegations | Board Fundraising Game"; }, []);

  const load = useCallback(async () => {
    try {
      setData((await memberApi.get("/game/portfolios")).data);
      setError("");
    } catch (err) {
      if (err.response?.status === 409) setError("The final fundraising strategy must be ready before participant delegations can be prepared.");
      else setError("We could not load the participant delegations.");
    }
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    load();
  }, [loading, member, navigate, load]);

  const prepare = async () => {
    setBusy(true); setNotice("");
    try {
      await memberApi.post("/game/portfolios/prepare");
      await load();
      setNotice("Proposed delegations are ready for founder review.");
    } catch (err) {
      setNotice(err.response?.data?.detail || "We could not prepare the proposed delegations.");
    }
    setBusy(false);
  };

  if (loading || (!data && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard">Back To Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-portfolios-page" style={{ maxWidth: 980 }}>
        {error && <section className="bfg-panel"><p className="bfg-error">{error}</p></section>}
        {data && (
          <>
            <section className="bfg-panel">
              <p className="bfg-eyebrow">FOUNDER DELEGATION REVIEW</p>
              <h1>Review What Each Person Will Be Responsible For</h1>
              <p className="bfg-panel-sub" style={{ marginTop: 10 }}>
                The platform has combined each person's Individual Game, participation choices, Board decisions and meeting commitments. Review the proposed role yourself. Edit anything that does not reflect what was agreed, then approve the delegation.
              </p>
              <div className="bfg-night-summary" style={{ marginTop: 18 }}>
                <div className="bfg-summary-row"><span>Fundraising Goal</span><strong>{data.goal_display || "Not set"}</strong></div>
                {data.goal_deadline && <div className="bfg-summary-row"><span>Funding Deadline</span><strong>{data.goal_deadline}</strong></div>}
                <div className="bfg-summary-row"><span>Founder-Approved Delegations</span><strong>{data.founder_approved_count || 0} of {data.total}</strong></div>
                <div className="bfg-summary-row"><span>Board Member Portfolio Approvals</span><strong>{data.approved_count || 0} of {data.total}</strong></div>
              </div>
              <p className="bfg-note" style={{ marginTop: 14 }}>
                A participant's final strategy email cannot be sent until you approve that person's delegation here.
              </p>
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 12 }} disabled={busy} onClick={prepare}>
                {busy ? "PREPARING…" : data.total ? "REFRESH / PREPARE MISSING DELEGATIONS" : "PREPARE PROPOSED DELEGATIONS"}
              </button>
              {notice && <p className="bfg-note" style={{ marginTop: 10 }}>{notice}</p>}
            </section>

            {(data.portfolios || []).map((row) => {
              const founderApproved = ["ready_to_send", "sent", "approved", "materials_ready"].includes(row.status);
              return (
                <section className="bfg-panel" key={row.portfolio_id} data-testid={`bfg-pf-row-${row.portfolio_id}`}>
                  <div className="bfg-panel-head">
                    <div>
                      <h2>{row.member_name}</h2>
                      <p className="bfg-panel-sub" style={{ marginTop: 4 }}>
                        Delegation: <strong style={{ color: STATUS_COLORS[row.status] || "#6B7280" }}>{STATUS_LABELS[row.status] || row.status}</strong>
                        {" "}· System-Building Roles: {row.system_count} · Direct Fundraising Activities: {row.direct_count}
                      </p>
                      {row.status === "change_requested" && row.change_request && (
                        <p className="bfg-note" style={{ marginTop: 8, color: "#c2410c" }}>
                          Change requested by {row.member_name.split(" ")[0]}: {row.change_request}
                        </p>
                      )}
                    </div>
                    <button
                      className={founderApproved ? "bfg-btn bfg-btn-ghost bfg-btn-sm" : "bfg-btn bfg-btn-primary bfg-btn-sm"}
                      onClick={() => navigate(`/game/portfolios/${row.portfolio_id}`)}
                      data-testid={`bfg-review-portfolio-${row.portfolio_id}`}
                    >
                      {founderApproved ? "REVIEW DELEGATION" : "REVIEW & APPROVE DELEGATION"}
                    </button>
                  </div>
                </section>
              );
            })}
          </>
        )}
      </main>
    </BfgShell>
  );
}
