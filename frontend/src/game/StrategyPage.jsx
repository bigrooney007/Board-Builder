import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { memberApi } from "@/member/api";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { BfgShell } from "./gameShared";
import { MODE_LABELS, STRATEGY_SECTIONS, StrategyDocument, sectionToText } from "./strategyRender";

export default function StrategyPage() {
  const { strategyId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const reviewMode = searchParams.get("review") === "1";
  const navigate = useNavigate();
  const { member, loading } = useMemberAuth();
  const [strategy, setStrategy] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [sectionIndex, setSectionIndex] = useState(0);
  const [draft, setDraft] = useState("");
  const [saveState, setSaveState] = useState("");
  const [reviewDone, setReviewDone] = useState(false);

  useEffect(() => { document.title = "Fundraising Strategy | Board Fundraising Game"; }, []);

  const load = useCallback(async () => {
    try { setStrategy((await memberApi.get(`/game/strategy/view/${strategyId}`)).data.strategy); }
    catch { setError("This strategy could not be loaded."); }
  }, [strategyId]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/game/signup?mode=login", { replace: true }); return; }
    load();
  }, [loading, member, navigate, load]);

  useEffect(() => {
    if (!strategy) return;
    const section = STRATEGY_SECTIONS[sectionIndex];
    const edits = strategy.section_edits || {};
    setDraft(edits[section.key] !== undefined && edits[section.key] !== ""
      ? edits[section.key]
      : sectionToText(section, (strategy.data || {})[section.key]));
    setSaveState("");
  }, [strategy, sectionIndex]);

  if (loading || (!strategy && !error)) return <div className="bfg" style={{ minHeight: "100vh" }} />;

  const copyLink = async () => {
    const link = `${window.location.origin}/strategy/${strategy.share_token}`;
    try { await navigator.clipboard.writeText(link); } catch { window.prompt("Copy this strategy link:", link); }
    setCopied(true); setTimeout(() => setCopied(false), 2500);
  };

  const saveSection = async () => {
    setSaveState("saving");
    try {
      await memberApi.put(`/game/strategy/view/${strategyId}/section`, {
        section_key: STRATEGY_SECTIONS[sectionIndex].key, text: draft });
      setStrategy((current) => ({ ...current, section_edits: { ...(current.section_edits || {}), [STRATEGY_SECTIONS[sectionIndex].key]: draft } }));
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
            <div className="bfg-bm-actions" style={{ marginBottom: 16 }}>
              <button className="bfg-btn bfg-btn-ghost bfg-btn-sm" onClick={copyLink} data-testid="bfg-copy-strategy-link-btn">
                {copied ? "Link Copied" : "Copy Strategy Link"}
              </button>
              {strategy.mode === "board_prioritized" && (
                <button className="bfg-btn bfg-btn-primary bfg-btn-sm" onClick={() => setSearchParams({ review: "1" })} data-testid="bfg-review-strategy-btn">
                  Review Strategy
                </button>
              )}
            </div>
            <StrategyDocument strategy={strategy} />
          </>
        )}
        {strategy && reviewMode && reviewDone && (
          <div className="bfg-panel" style={{ textAlign: "center" }} data-testid="bfg-review-complete">
            <h2>Board Strategy Review Complete</h2>
            <p className="bfg-panel-sub" style={{ marginTop: 12 }}>
              Your Board-Prioritised Fundraising Strategy has been reviewed. The final adoption process will be completed in the next stage of Game Night.
            </p>
            <button className="bfg-btn bfg-btn-primary" style={{ marginTop: 18 }}
              onClick={() => { setReviewDone(false); setSearchParams({}); }} data-testid="bfg-return-to-strategy-btn">
              Return To Strategy
            </button>
          </div>
        )}
        {strategy && reviewMode && !reviewDone && (
          <div className="bfg-panel" data-testid="bfg-strategy-review">
            <p className="bfg-eyebrow">Reviewing Section {sectionIndex + 1} of {STRATEGY_SECTIONS.length}</p>
            <h2>{STRATEGY_SECTIONS[sectionIndex].title}</h2>
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
              {sectionIndex < STRATEGY_SECTIONS.length - 1 ? (
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
