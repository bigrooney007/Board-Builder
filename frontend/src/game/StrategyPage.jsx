import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { MODE_LABELS, getStrategySections, versionLabel, StrategyDocument, sectionToText } from "./strategyRender";

export default function StrategyPage() {
  const { strategyId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const reviewMode = searchParams.get("review") === "1";
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [strategy, setStrategy] = useState(null);
  const [versions, setVersions] = useState([]);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [sectionIndex, setSectionIndex] = useState(0);
  const [draft, setDraft] = useState("");
  const [saveState, setSaveState] = useState("");
  const [reviewDone, setReviewDone] = useState(false);
  const [startingReview, setStartingReview] = useState(false);

  useEffect(() => { document.title = "Fundraising Strategy | Board Fundraising Game"; }, []);

  const load = useCallback(async () => {
    try { setStrategy((await memberApi.get(`/game/strategy/view/${strategyId}`)).data.strategy); }
    catch { setError("This strategy could not be loaded."); }
    try { setVersions((await memberApi.get("/game/strategies")).data.strategies || []); }
    catch { /* the version selector simply stays hidden */ }
  }, [strategyId]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    load();
  }, [loading, member, navigate, load]);

  useEffect(() => {
    if (!strategy) return;
    const section = getStrategySections(strategy)[sectionIndex];
    if (!section) return;
    const edits = strategy.section_edits || {};
    setDraft(edits[section.key] !== undefined && edits[section.key] !== ""
      ? edits[section.key]
      : sectionToText(section, (strategy.data || {})[section.key]));
    setSaveState("");
  }, [strategy, sectionIndex]);

  if (loading || (!strategy && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const sections = strategy ? getStrategySections(strategy) : [];

  const download = async () => {
    setDownloading(true);
    try {
      const response = await memberApi.get(`/game/strategy/view/${strategyId}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `fundraising-strategy-v${strategy.version}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch { /* keep the page usable */ }
    setDownloading(false);
  };

  const copyLink = async () => {
    const link = `${window.location.origin}/strategy/${strategy.share_token}`;
    try { await navigator.clipboard.writeText(link); } catch { window.prompt("Copy this strategy link:", link); }
    setCopied(true); setTimeout(() => setCopied(false), 2500);
  };

  const startBoardReview = async () => {
    setStartingReview(true);
    try {
      await memberApi.post("/game/meeting-review/start", { strategy_id: strategy.strategy_id });
      navigate("/game/meeting-review");
    } catch { setStartingReview(false); }
  };

  const saveSection = async () => {
    setSaveState("saving");
    try {
      await memberApi.put(`/game/strategy/view/${strategyId}/section`, {
        section_key: sections[sectionIndex].key, text: draft });
      setStrategy((current) => ({ ...current, section_edits: { ...(current.section_edits || {}), [sections[sectionIndex].key]: draft } }));
      setSaveState("saved");
    } catch { setSaveState("error"); }
  };

  const finishReview = async () => {
    try { await memberApi.post(`/game/strategy/view/${strategyId}/finish-review`); } catch { /* non-blocking */ }
    setReviewDone(true);
    window.scrollTo({ top: 0 });
  };

  return (
    <BfgShell nav={<Link className="bfg-btn bfg-btn-ghost bfg-btn-sm" to="/game/dashboard" data-testid="bfg-strategy-back-dashboard">Back to Dashboard</Link>}>
      <main className="bfg-dash" data-testid="bfg-strategy-page" style={{ maxWidth: 900 }}>
        {error && <div className="bfg-panel"><p className="bfg-error">{error}</p></div>}
        {strategy && !reviewMode && (
          <>
            <div className="bfg-panel" style={{ padding: "14px 18px", marginBottom: 16 }} data-testid="bfg-strategy-toolbar">
              <div className="bfg-panel-head" style={{ alignItems: "center" }}>
                <label className="bfg-field" style={{ margin: 0, maxWidth: 420 }}>
                  <span>Version</span>
                  <select value={strategyId}
                    onChange={(event) => navigate(`/game/strategy/view/${event.target.value}`)}
                    data-testid="bfg-strategy-version-select">
                    {(versions.length ? versions : [strategy]).map((row) => (
                      <option key={row.strategy_id} value={row.strategy_id}>
                        {versionLabel(row)} — {row.generated_at ? new Date(row.generated_at).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" }) : ""}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="bfg-bm-actions" style={{ marginTop: 0 }}>
                  <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={download} disabled={downloading} data-testid="bfg-download-strategy-btn">
                    {downloading ? "Preparing PDF…" : "Download Strategy"}
                  </button>
                  <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={copyLink} data-testid="bfg-copy-strategy-link-btn">
                    {copied ? "Link Copied" : "Copy Strategy Link"}
                  </button>
                </div>
              </div>
            </div>
            {strategy.mode === "board_prioritized" && strategy.status !== "adopted" && (
              <section className="bfg-panel" data-testid="bfg-review-with-board-panel">
                <h2>Review With Your Board</h2>
                <p className="bfg-panel-sub" style={{ marginTop: 6 }}>
                  Review your Board-Prioritized Fundraising Strategy together during Game Night, capture the decisions your board makes and turn those decisions into your Final Fundraising Strategy.
                </p>
                <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 14 }} disabled={startingReview}
                  onClick={startBoardReview} data-testid="bfg-start-board-review-btn">
                  {startingReview ? "Opening…" : "Start Board Strategy Review"}
                </button>
              </section>
            )}
            <StrategyDocument strategy={strategy} />
          </>
        )}
        {strategy && reviewMode && reviewDone && (
          <div className="bfg-panel" style={{ textAlign: "center" }} data-testid="bfg-review-complete">
            <h2>Board Strategy Review Complete</h2>
            <p className="bfg-panel-sub" style={{ marginTop: 12 }}>
              Your Board-Prioritized Fundraising Strategy has been reviewed. The final adoption process will be completed in the next stage of Game Night.
            </p>
            <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }}
              onClick={() => { setReviewDone(false); setSearchParams({}); }} data-testid="bfg-return-to-strategy-btn">
              Return To Strategy
            </button>
          </div>
        )}
        {strategy && reviewMode && !reviewDone && (
          <div className="bfg-panel" data-testid="bfg-strategy-review">
            <p className="bfg-eyebrow">Reviewing Section {sectionIndex + 1} of {sections.length}</p>
            <h2>{sections[sectionIndex].title}</h2>
            <p className="bfg-note" style={{ marginTop: 8 }}>{MODE_LABELS[strategy.mode]} — edits save without another AI call.</p>
            <label className="bfg-field">
              <span>Strategy text for this section</span>
              <textarea rows={14} value={draft} onChange={(event) => { setDraft(event.target.value); setSaveState(""); }}
                data-testid="bfg-review-section-text" />
            </label>
            {saveState === "saved" && <p className="bfg-success" data-testid="bfg-review-saved">Changes Saved</p>}
            {saveState === "error" && <p className="bfg-error">We could not save your changes. Please try again.</p>}
            <div className="bfg-form-actions">
              <button className="bfg-btn bfg-btn-ghost" disabled={sectionIndex === 0}
                onClick={() => setSectionIndex(sectionIndex - 1)} data-testid="bfg-review-prev-btn">Previous Section</button>
              <button className="bfg-btn bfg-btn-ghost" disabled={saveState === "saving"} onClick={saveSection} data-testid="bfg-review-save-btn">
                {saveState === "saving" ? "Saving…" : "Save Changes"}
              </button>
              {sectionIndex < sections.length - 1 ? (
                <button className="bfg-btn bfg-btn-primary" onClick={() => setSectionIndex(sectionIndex + 1)} data-testid="bfg-review-next-btn">Next Section</button>
              ) : (
                <button className="bfg-btn bfg-btn-primary" onClick={finishReview} data-testid="bfg-finish-review-btn">Finish Review</button>
              )}
            </div>
          </div>
        )}
      </main>
    </BfgShell>
  );
}
