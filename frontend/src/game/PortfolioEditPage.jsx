import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

const STATUS_LABELS = {
  draft: "Draft", ready_to_send: "Ready To Send", sent: "Sent",
  change_requested: "Change Requested", approved: "Approved", materials_ready: "Execution Materials Ready",
};

export default function PortfolioEditPage() {
  const { portfolioId } = useParams();
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [detail, setDetail] = useState(null);
  const [systemRoles, setSystemRoles] = useState([]);
  const [activities, setActivities] = useState([]);
  const [additional, setAdditional] = useState([]);
  const [orgNote, setOrgNote] = useState("");
  const [addRoleKey, setAddRoleKey] = useState("");
  const [addActivityKey, setAddActivityKey] = useState("");
  const [customLabel, setCustomLabel] = useState("");
  const [conflict, setConflict] = useState(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => { document.title = "Review Portfolio | Board Fundraising Game"; }, []);

  const load = useCallback(async () => {
    try {
      const data = (await memberApi.get(`/game/portfolios/${portfolioId}`)).data;
      setDetail(data);
      setSystemRoles(data.portfolio.system_roles || []);
      setActivities(data.portfolio.direct_activities || []);
      setAdditional(data.portfolio.additional_commitments || []);
      setOrgNote(data.portfolio.org_note || "");
    } catch { navigate("/game/portfolios", { replace: true }); }
  }, [portfolioId, navigate]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    load();
  }, [loading, member, navigate, load]);

  if (loading || !detail) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const portfolio = detail.portfolio;
  const locked = portfolio.status === "approved" || portfolio.status === "materials_ready";
  const catalog = detail.catalog;

  const save = async (thenStatus = "") => {
    setBusy(true); setNotice("");
    try {
      await memberApi.put(`/game/portfolios/${portfolioId}`, {
        system_roles: systemRoles, direct_activities: activities,
        additional_commitments: additional, org_note: orgNote,
      });
      if (thenStatus) await memberApi.post(`/game/portfolios/${portfolioId}/status`, { status: thenStatus });
      setNotice(thenStatus === "ready_to_send" ? "Portfolio marked Ready To Send." : "Draft saved.");
      await load();
    } catch { setNotice("We could not save the portfolio. Please try again."); }
    setBusy(false);
  };

  const send = async () => {
    setBusy(true); setNotice("");
    try {
      await memberApi.post(`/game/portfolios/${portfolioId}/send`, { origin_url: window.location.origin });
      setNotice("Portfolio sent.");
      await load();
    } catch { setNotice("The email could not be sent. Please try again."); }
    setBusy(false);
  };

  const copyLink = async () => {
    const link = `${window.location.origin}/board-portfolio/${portfolio.token}`;
    try { await navigator.clipboard.writeText(link); } catch { window.prompt("Copy this portfolio link:", link); }
    setCopied(true); setTimeout(() => setCopied(false), 2500);
  };

  const updateRole = (itemId, field, value) => {
    setSystemRoles((current) => current.map((role) => role.item_id === itemId ? { ...role, [field]: value } : role));
  };
  const updateActivity = (itemId, field, value) => {
    setActivities((current) => current.map((act) => act.item_id === itemId ? { ...act, [field]: value } : act));
  };

  const addRole = () => {
    if (!addRoleKey) return;
    const isCustom = addRoleKey === "custom";
    if (isCustom && !customLabel.trim()) return;
    const label = isCustom ? customLabel.trim() : (catalog.system_roles.find((r) => r.role_key === addRoleKey)?.label || "");
    setSystemRoles((current) => [...current, {
      item_id: `new-${Date.now()}`, role_key: addRoleKey, label, source: "organisation_added",
      involvement: "", member_note: "", commitment: "", deadline: "", requires_confirmation: false, active: true,
    }]);
    setAddRoleKey(""); setCustomLabel("");
  };

  const addActivity = (confirmed = false) => {
    const key = confirmed ? conflict.key : addActivityKey;
    if (!key) return;
    const isCustom = key === "custom";
    if (isCustom && !customLabel.trim() && !confirmed) return;
    const label = confirmed ? conflict.label
      : isCustom ? customLabel.trim() : (catalog.direct_activities.find((a) => a.activity_key === key)?.label || "");
    if (!confirmed && (portfolio.do_not_want || []).includes(label)) {
      setConflict({ key, label });
      return;
    }
    setActivities((current) => [...current, {
      item_id: `new-${Date.now()}`, activity_key: key, label, source: "organisation_added",
      member_note: "", commitment: "", deadline: "",
      audiences: detail.strategy_audiences || [],
      requires_confirmation: confirmed, active: true,
    }]);
    setConflict(null); setAddActivityKey(""); setCustomLabel("");
  };

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/portfolios" data-testid="bfg-pe-back">Back to Portfolios</Link>}>
      <main className="bfg-dash" data-testid="bfg-portfolio-edit-page" style={{ maxWidth: 960 }}>
        <div className="bfg-panel">
          <p className="bfg-eyebrow">Board Fundraising Portfolio</p>
          <h1>{portfolio.member_name}</h1>
          <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
            Organisation: {detail.organization_name} · Fundraising Goal: {detail.goal_display}
            {detail.goal_deadline && <> · Goal Deadline: {detail.goal_deadline}</>}
            {" "}· Status: <strong data-testid="bfg-pe-status">{STATUS_LABELS[portfolio.status]}</strong>
          </p>
          <div className="bfg-bm-actions">
            <a className="bfg-btn bfg-btn-ghost bfg-btn-sm" href={`/strategy/${detail.strategy_share_token}`} target="_blank" rel="noreferrer"
              data-testid="bfg-pe-view-strategy">View Adopted Fundraising Strategy</a>
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={copyLink} data-testid="bfg-pe-copy-link">
              {copied ? "Link Copied" : "Copy Portfolio Link"}
            </button>
          </div>
          {portfolio.status === "change_requested" && portfolio.change_request && (
            <p className="bfg-error" data-testid="bfg-pe-change-request">
              Change Requested By {portfolio.member_name.split(" ")[0]}: {portfolio.change_request}
            </p>
          )}
        </div>

        <div className="bfg-panel" data-testid="bfg-pe-system-section">
          <h2>Your Role In Building Our Fundraising System</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 6 }}>
            These are the areas where {portfolio.member_name.split(" ")[0]} will help strengthen the people, processes, technology and resources required to execute the fundraising strategy.
          </p>
          {systemRoles.filter((role) => role.active !== false).length === 0 && activities.filter((a) => a.active !== false).length === 0 && (
            <p className="bfg-note" style={{ marginTop: 10, fontWeight: 700 }}>Participation Role Not Defined Yet</p>
          )}
          {systemRoles.map((role) => role.active !== false && (
            <div className="bfg-mr-decision" key={role.item_id} data-testid={`bfg-pe-role-${role.item_id}`}>
              <div className="bfg-panel-head">
                <strong style={{ color: "#111827" }}>{role.label}</strong>
                {!locked && (
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => updateRole(role.item_id, "active", false)}
                    data-testid={`bfg-pe-remove-role-${role.item_id}`}>Remove</button>
                )}
              </div>
              <div className="bfg-pe-fields">
                <label>Involvement
                  <select value={role.involvement || ""} disabled={locked}
                    onChange={(event) => updateRole(role.item_id, "involvement", event.target.value)}>
                    <option value="">Not set</option>
                    {catalog.involvement_options.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label>Deadline
                  <input value={role.deadline || ""} disabled={locked} placeholder="Optional"
                    onChange={(event) => updateRole(role.item_id, "deadline", event.target.value)} />
                </label>
              </div>
              {role.member_note && <p className="bfg-note" style={{ marginTop: 8 }}>How they said they would help: {role.member_note}</p>}
              <label className="bfg-pe-wide">Game Night Commitment
                <input value={role.commitment || ""} disabled={locked} placeholder="Optional"
                  onChange={(event) => updateRole(role.item_id, "commitment", event.target.value)} />
              </label>
            </div>
          ))}
          {!locked && (
            <div className="bfg-pe-add">
              <select value={addRoleKey} onChange={(event) => setAddRoleKey(event.target.value)} data-testid="bfg-pe-add-role-select">
                <option value="">Add system-building responsibility…</option>
                {catalog.system_roles.map((role) => <option key={role.role_key} value={role.role_key}>{role.label}</option>)}
                <option value="custom">Custom responsibility…</option>
              </select>
              {addRoleKey === "custom" && (
                <input value={customLabel} placeholder="Custom responsibility" onChange={(event) => setCustomLabel(event.target.value)} />
              )}
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={addRole} data-testid="bfg-pe-add-role-btn">Add</button>
            </div>
          )}
        </div>

        <div className="bfg-panel" data-testid="bfg-pe-direct-section">
          <h2>How You Will Help Us Raise Money</h2>
          <p className="bfg-panel-sub" style={{ marginTop: 6 }}>
            These are the fundraising activities {portfolio.member_name.split(" ")[0]} agreed to support based on their interests, relationships and strengths.
          </p>
          {activities.map((act) => act.active !== false && (
            <div className="bfg-mr-decision" key={act.item_id} data-testid={`bfg-pe-activity-${act.item_id}`}>
              <div className="bfg-panel-head">
                <div>
                  <strong style={{ color: "#111827" }}>{act.label}</strong>
                  {act.requires_confirmation && <span className="bfg-pe-badge">Requires Board Member Confirmation</span>}
                </div>
                {!locked && (
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => updateActivity(act.item_id, "active", false)}
                    data-testid={`bfg-pe-remove-activity-${act.item_id}`}>Remove</button>
                )}
              </div>
              {act.member_note && <p className="bfg-note" style={{ marginTop: 8 }}>How they said they would help: {act.member_note}</p>}
              {(act.audiences || []).length > 0 && (
                <p className="bfg-note" style={{ marginTop: 6 }}>Priority audiences this may support: {act.audiences.join(", ")}</p>
              )}
              <div className="bfg-pe-fields">
                <label>Deadline
                  <input value={act.deadline || ""} disabled={locked} placeholder="Optional"
                    onChange={(event) => updateActivity(act.item_id, "deadline", event.target.value)} />
                </label>
              </div>
              <label className="bfg-pe-wide">Game Night Commitment
                <input value={act.commitment || ""} disabled={locked} placeholder="Optional"
                  onChange={(event) => updateActivity(act.item_id, "commitment", event.target.value)} />
              </label>
            </div>
          ))}
          {!locked && (
            <div className="bfg-pe-add">
              <select value={addActivityKey} onChange={(event) => setAddActivityKey(event.target.value)} data-testid="bfg-pe-add-activity-select">
                <option value="">Add direct fundraising activity…</option>
                {catalog.direct_activities.map((act) => <option key={act.activity_key} value={act.activity_key}>{act.label}</option>)}
                <option value="custom">Custom activity…</option>
              </select>
              {addActivityKey === "custom" && (
                <input value={customLabel} placeholder="Custom activity" onChange={(event) => setCustomLabel(event.target.value)} />
              )}
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={() => addActivity(false)} data-testid="bfg-pe-add-activity-btn">Add</button>
            </div>
          )}
          {(portfolio.do_not_want || []).length > 0 && (
            <p className="bfg-note" style={{ marginTop: 12 }}>
              Prefers not to do: {portfolio.do_not_want.join(", ")}
            </p>
          )}
        </div>

        <div className="bfg-panel" data-testid="bfg-pe-additional-section">
          <h2>Additional Game Night Commitments</h2>
          {additional.length === 0 && <p className="bfg-note" style={{ marginTop: 8 }}>No additional commitments.</p>}
          {additional.map((item, index) => (
            <div className="bfg-pe-add" key={index}>
              <input value={item.text} disabled={locked} style={{ flex: 1 }}
                onChange={(event) => setAdditional((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, text: event.target.value } : row))} />
              {!locked && (
                <button className="bfg-btn bfg-btn-ghost bfg-btn-sm"
                  onClick={() => setAdditional((current) => current.filter((_, rowIndex) => rowIndex !== index))}>Remove</button>
              )}
            </div>
          ))}
          {!locked && (
            <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" style={{ marginTop: 10 }}
              onClick={() => setAdditional((current) => [...current, { text: "", deadline: "" }])} data-testid="bfg-pe-add-commitment-btn">
              Add Commitment
            </button>
          )}
          <label className="bfg-field">
            <span>Organisation note (shown to the board member)</span>
            <textarea rows={3} value={orgNote} disabled={locked} onChange={(event) => setOrgNote(event.target.value)} data-testid="bfg-pe-org-note" />
          </label>
        </div>

        <div className="bfg-panel">
          {notice && <p className="bfg-note" style={{ marginBottom: 10 }} data-testid="bfg-pe-notice">{notice}</p>}
          <div className="bfg-bm-actions">
            {!locked && (
              <>
                <button className="bfg-btn bfg-btn-ghost" disabled={busy} onClick={() => save()} data-testid="bfg-pe-save-draft-btn">Save Draft</button>
                {portfolio.status === "draft" && (
                  <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={() => save("ready_to_send")} data-testid="bfg-pe-mark-ready-btn">
                    Mark Ready To Send
                  </button>
                )}
                {portfolio.status === "ready_to_send" && (
                  <button className="bfg-btn bfg-btn-primary" disabled={busy} onClick={send} data-testid="bfg-pe-send-btn">Send Portfolio</button>
                )}
                {portfolio.status === "change_requested" && (
                  <button className="bfg-btn bfg-btn-primary" disabled={busy}
                    onClick={async () => { await save(); await send(); }} data-testid="bfg-pe-send-updated-btn">
                    Send Updated Portfolio
                  </button>
                )}
                {portfolio.status === "sent" && (
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={busy} onClick={send} data-testid="bfg-pe-resend-btn">Resend Portfolio Link</button>
                )}
              </>
            )}
            {locked && (
              <>
                <p className="bfg-success" style={{ fontWeight: 700 }}>
                  Portfolio approved{portfolio.approved_at ? ` on ${new Date(portfolio.approved_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}` : ""} — it can no longer be edited directly.
                </p>
                <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={busy} onClick={send} data-testid="bfg-pe-resend-approved-btn">Resend Portfolio Link</button>
                {detail.toolkit_status === "ready" ? (
                  <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => navigate(`/game/portfolios/${portfolioId}/toolkit`)}
                    data-testid="bfg-pe-view-toolkit-btn">View Execution Materials</button>
                ) : (
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      try { await memberApi.post(`/game/portfolios/${portfolioId}/generate-updated-toolkit`, { origin_url: window.location.origin }); setNotice("Execution material generation started."); }
                      catch { setNotice("We could not start the generation. Please try again."); }
                      setBusy(false);
                    }} data-testid="bfg-pe-generate-toolkit-btn">
                    Generate Updated Execution Materials
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {conflict && (
          <div className="bfg-modal-overlay" data-testid="bfg-pe-conflict-modal">
            <div className="bfg-modal">
              <h2>Participation Preference</h2>
              <p className="bfg-panel-sub" style={{ marginTop: 10 }}>
                {portfolio.member_name.split(" ")[0]} previously indicated that they would prefer not to perform this fundraising activity.
              </p>
              <p style={{ marginTop: 10 }}>Their preference: <strong>{conflict.label}</strong></p>
              <div className="bfg-form-actions">
                <button className="bfg-btn bfg-btn-ghost" onClick={() => setConflict(null)} data-testid="bfg-pe-conflict-cancel">Cancel</button>
                <button className="bfg-btn bfg-btn-primary" onClick={() => addActivity(true)} data-testid="bfg-pe-conflict-add">Add For Their Review</button>
              </div>
            </div>
          </div>
        )}
      </main>
    </BfgShell>
  );
}
