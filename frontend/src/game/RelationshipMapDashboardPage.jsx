import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";

const willingText = (entry) => [
  entry.willing_intro && "Make An Introduction",
  entry.willing_participate && "Participate In The Ask",
  entry.willing_ask && "Make The Ask Myself",
  entry.willing_org_ask && "Organization Asks After My Introduction",
].filter(Boolean).join(" · ") || "—";

export default function RelationshipMapDashboardPage() {
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [entries, setEntries] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { document.title = "Relationship Mapping | Board Fundraising Game"; }, []);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    memberApi.get("/game/relationships").then((r) => setEntries(r.data.entries || [])).catch(() => setEntries([]));
  }, [loading, member, navigate]);

  const addMine = async () => {
    setBusy(true);
    try {
      const token = (await memberApi.post("/game/self-play")).data.token;
      navigate(`/relationship-mapping/${token}`);
    } catch { setBusy(false); }
  };

  if (loading || entries === null) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-rm-back-dashboard">Back to Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-relationships-dashboard" style={{ maxWidth: 1040 }}>
        <div className="bfg-panel">
          <div className="bfg-panel-head">
            <div>
              <h1>Relationship Mapping</h1>
              <p className="bfg-panel-sub" style={{ marginTop: 8 }}>
                Every relationship added by you and your board members — the people, businesses and grantors who match your ideal funder profiles.
              </p>
            </div>
            <button className="bfg-btn bfg-btn-primary bfg-btn-sm" style={{ marginTop: 0 }} disabled={busy}
              onClick={addMine} data-testid="bfg-rm-add-my-relationships-btn">
              {busy ? "Opening…" : "Add My Relationships"}
            </button>
          </div>
        </div>

        {entries.length === 0 ? (
          <div className="bfg-panel" data-testid="bfg-rm-empty">
            <p className="bfg-note">No relationships have been added yet. Board members can complete their Relationship Mapping Form from their final strategy link.</p>
          </div>
        ) : (
          entries.map((entry) => (
            <div className="bfg-panel" key={entry.relationship_id} data-testid={`bfg-rm-row-${entry.relationship_id}`}>
              <div className="bfg-panel-head">
                <div>
                  <h2 style={{ fontSize: 18 }}>{entry.name}{entry.organization ? ` — ${entry.organization}` : ""}</h2>
                  <p className="bfg-panel-sub" style={{ marginTop: 4 }}>
                    <strong>{entry.funder_type}</strong> · Added by {entry.member_name || "Board Member"}
                  </p>
                </div>
              </div>
              <div className="bfg-night-summary" style={{ marginTop: 10 }}>
                {(entry.email || entry.phone || entry.other_contact) && (
                  <div className="bfg-summary-row"><span>Contact</span>
                    <strong>{[entry.email, entry.phone, entry.other_contact].filter(Boolean).join(" · ")}</strong></div>
                )}
                {entry.how_know && <div className="bfg-summary-row"><span>How They Know Them</span><strong>{entry.how_know}</strong></div>}
                {entry.why_match && <div className="bfg-summary-row"><span>Why They Match</span><strong>{entry.why_match}</strong></div>}
                <div className="bfg-summary-row"><span>Willing To</span><strong>{willingText(entry)}</strong></div>
              </div>
            </div>
          ))
        )}
      </main>
    </BfgShell>
  );
}
