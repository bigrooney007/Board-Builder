import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import V2Shell from "./V2Shell";
import { v2Api, errorMessage } from "./api";
import { ActionNotice, AudienceDetails, CopyButton, DocumentPreview, DownloadLink, useV2Load } from "./ResourcePages";
import "./actions.css";

const AUDIENCE_FIELDS = [["funder", "Specific funding audience"], ["why", "Why they may fund your mission"], ["where", "Where to find them"], ["attract", "How to attract their interest and establish credibility"], ["relationship", "How to build relationships and raise money"], ["ask", "What to ask them to support"], ["amount", "How much to ask and why"]];
const emptyAudience = (category) => Object.fromEntries([["category", category], ...AUDIENCE_FIELDS.map(([key]) => [key, ""])]);
const categoryOf = (section) => section.key || section.category || section.title;
const sourceOf = (idea) => idea.source_id || idea.audience_id || idea.submission_id;
const ideaContent = (idea) => idea.content ?? idea.text ?? idea.answer ?? "";
const titleOf = (idea) => idea.title || ideaContent(idea)?.funder || "Participant proposal";

function DecisionEditor({ draft, setDraft, busy, onSave, onCancel, fundraising }) {
  return <form className="v2-card v2-decision-editor" onSubmit={(event) => { event.preventDefault(); onSave(); }} data-testid="v2-decision-editor">
    <h2>{draft.decision_id ? "Edit the group's decision" : "Prepare an agreed idea"}</h2>
    <p>Keep meaningful differences when combining suggestions. Saving this idea as adopted records your group's explicit decision.</p>
    <label className="v2-field">Decision title<input required value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
    {fundraising ? AUDIENCE_FIELDS.map(([key, label]) => <label className="v2-field" key={key}>{label}<textarea rows={key === "funder" ? 2 : 3} value={draft.content[key] || ""} onChange={(event) => setDraft({ ...draft, content: { ...draft.content, [key]: event.target.value } })} /></label>) : <label className="v2-field">Agreed content<textarea required rows={9} value={draft.content} onChange={(event) => setDraft({ ...draft, content: event.target.value })} /></label>}
    <div className="v2-actions"><button className="v2-btn" disabled={busy}>Save as an adopted decision</button><button type="button" className="v2-btn v2-btn-secondary" disabled={busy} onClick={onCancel}>Cancel</button></div>
  </form>;
}

function GroupContent({ data, readOnly, onDecision, draft, setDraft, selected, setSelected, busy }) {
  const fundraising = data?.journey?.product === "board-fundraising-game";
  const decisions = data.decisions || [];
  const start = (section, ideas) => {
    const category = categoryOf(section);
    const sourceIds = ideas.map(sourceOf).filter(Boolean);
    let content;
    if (fundraising) {
      content = emptyAudience(category);
      for (const [key] of AUDIENCE_FIELDS) {
        content[key] = ideas.map((idea) => `${ideas.length > 1 ? `${idea.name || "Participant"}: ` : ""}${ideaContent(idea)?.[key] || ""}`).filter((text) => text.trim()).join("\n\n");
      }
    } else { content = ideas.map((idea) => `${ideas.length > 1 ? `${idea.name || "Participant"}:\n` : ""}${String(ideaContent(idea))}`).join("\n\n"); }
    setDraft({ category, title: ideas.length === 1 ? titleOf(ideas[0]) : `Combined ${section.title || category} proposal`, content, source_ids: sourceIds, status: "adopted" });
  };
  const sections = data.sections || [];
  return <>
    {sections.map((section) => {
      const category = categoryOf(section);
      const originalIdeas = section.ideas || section.responses || [];
      const overlaps = section.overlap_groups || [];
      const orderedSources = [];
      for (const idea of originalIdeas) {
        const source = sourceOf(idea);
        const group = overlaps.find((overlap) => overlap.source_ids.includes(source));
        for (const sourceId of group?.source_ids || [source]) if (!orderedSources.includes(sourceId)) orderedSources.push(sourceId);
      }
      const ideas = orderedSources.map((source) => originalIdeas.find((idea) => sourceOf(idea) === source)).filter(Boolean);
      const chosen = ideas.filter((idea) => selected.includes(sourceOf(idea)));
      const funderNames = fundraising ? ideas.map((idea) => String(ideaContent(idea)?.funder || "").trim().toLowerCase()) : [];
      return <section className="v2-card" key={category} data-testid={`v2-group-${category}`}>
        <h2>{section.title || category}</h2>
        {!readOnly && section.allow_keep_current_mission && <button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => onDecision({ category, title: "Mission", content: "__keep_current__", source_ids: [], status: "adopted" })}>Confirm that we are retaining our existing mission</button>}
        {!ideas.length && <p>No participant suggestions were supplied for this topic. You can add an idea if your group agrees on one during the meeting.</p>}
        {overlaps.length > 0 && <div className="v2-notice"><h3>Compare overlapping audiences</h3>{overlaps.map((overlap) => <div key={overlap.title}><p><strong>{overlap.title}</strong> was suggested by {overlap.source_ids.map((id) => ideas.find((idea) => sourceOf(idea) === id)?.name || "a participant").join(", ")}. Each person's approach remains available below.</p>{!readOnly && <button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => setSelected([...new Set([...selected, ...overlap.source_ids])])}>Select these suggestions to compare or combine</button>}</div>)}</div>}
        {ideas.map((idea, index) => {
          const sourceId = sourceOf(idea);
          const content = ideaContent(idea);
          const related = decisions.filter((decision) => (decision.source_ids || []).includes(sourceId));
          const alreadyAdopted = related.some((decision) => decision.status === "adopted");
          const overlap = fundraising && (overlaps.some((entry) => entry.source_ids.includes(sourceId)) || (funderNames[index] && funderNames.filter((name) => name === funderNames[index]).length > 1));
          const IdeaContainer = fundraising ? "details" : "article";
          return <IdeaContainer className="v2-idea" key={sourceId || index}>
            {fundraising && <summary><strong>{titleOf(idea)}</strong><span className="v2-source-label"> · {idea.name || "Participant"}{alreadyAdopted ? " · Adopted" : ""}</span></summary>}
            <div className="v2-idea-heading"><h3>{titleOf(idea)}</h3>{!readOnly && <label className="v2-check"><input type="checkbox" checked={selected.includes(sourceId)} onChange={(event) => setSelected(event.target.checked ? [...selected, sourceId] : selected.filter((id) => id !== sourceId))} />Compare or combine</label>}</div>
            <p className="v2-source-label">Proposed by {idea.name || "a participant"}. This is their submitted contribution.</p>
            {idea.question && <p><strong>{idea.question}</strong></p>}
            {overlap && <p className="v2-notice">Another participant proposed this audience. Compare the approaches below before choosing or combining them.</p>}
            {fundraising && typeof content === "object" ? <AudienceDetails audience={content} /> : <div className="v2-document-text">{String(content)}</div>}
            {related.map((decision) => <p key={decision.decision_id} className="v2-decision-status">Group decision: {decision.status} as "{decision.title}".</p>)}
            {!readOnly && <><div className="v2-actions"><button data-testid={`v2-adopt-${sourceId}`} className="v2-btn" disabled={busy || alreadyAdopted} onClick={() => onDecision({ category, title: titleOf(idea), content: fundraising ? content : String(content), source_ids: [sourceId], status: "adopted" })}>{alreadyAdopted ? "Already adopted" : "Adopt this idea"}</button><button className="v2-btn v2-btn-secondary" disabled={busy || alreadyAdopted} onClick={() => start(section, [idea])}>Edit before adopting</button><button className="v2-btn v2-btn-secondary" disabled={busy || alreadyAdopted} onClick={() => onDecision({ category, title: titleOf(idea), content: fundraising ? content : String(content), source_ids: [sourceId], status: "rejected" })}>Reject this idea</button></div>{alreadyAdopted && <p>Edit or remove this adopted idea in the group's decisions below.</p>}</>}
          </IdeaContainer>;
        })}
        {!readOnly && <div className="v2-actions"><button className="v2-btn v2-btn-secondary" disabled={busy || chosen.length < 2} onClick={() => start(section, chosen)}>Combine selected suggestions</button><button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => setDraft({ category, title: "", content: fundraising ? emptyAudience(category) : "", source_ids: [], status: "adopted" })}>Add an idea agreed during discussion</button></div>}
      </section>;
    })}
    {draft && !readOnly && <DecisionEditor draft={draft} setDraft={setDraft} busy={busy} fundraising={fundraising} onCancel={() => setDraft(null)} onSave={() => onDecision(draft)} />}
    <section className="v2-card"><h2>Decisions your group has adopted</h2><p>Only these adopted decisions will be included in the final document. Participant suggestions remain preserved separately.</p>
      {decisions.filter((decision) => decision.status === "adopted").map((decision) => <article className="v2-idea" key={decision.decision_id}><h3>{decision.title}</h3>{fundraising ? <AudienceDetails audience={decision.content} /> : <div className="v2-document-text">{String(decision.content || "")}</div>}{!readOnly && <div className="v2-actions"><button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => setDraft({ ...decision, content: fundraising ? { ...decision.content } : decision.content })}>Edit agreed content</button><button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => onDecision({ ...decision, status: "rejected" })}>Remove from adopted decisions</button></div>}</article>)}
      {!decisions.some((decision) => decision.status === "adopted") && <p>No ideas have been adopted yet.</p>}
    </section>
  </>;
}

function Participation({ data, readOnly, busy, onSave, onWithdraw }) {
  const [form, setForm] = useState({ participant_id: "", responsibility: "", audience_ids: [], consent_confirmed: false });
  const participants = data.participants || [];
  const adopted = (data.decisions || []).filter((decision) => decision.status === "adopted");
  useEffect(() => {
    if (!readOnly && data.journey?.journey_id?.startsWith("admin-test-") && !form.participant_id && !(data.commitments || []).length) {
      const sample = participants.find((participant) => participant.submitted && participant.participation);
      if (sample) setForm({ participant_id: sample.participant_id, responsibility: sample.participation, audience_ids: [], consent_confirmed: false });
    }
  }, [data, form.participant_id, participants, readOnly]);
  return <section className="v2-card" data-testid="v2-participation"><h2>Agree on personal participation</h2><p>Discuss the contribution each person is willing to make. Record a responsibility only after they have agreed to it.</p>
    {participants.map((participant) => <article className="v2-idea" key={participant.participant_id}><h3>{participant.name}</h3><div className="v2-document-text">{participant.participation || "No participation statement supplied."}</div></article>)}
    {(data.commitments || []).map((commitment) => <article className="v2-idea" key={commitment.commitment_id}><h3>{commitment.name}</h3><p>{commitment.responsibility}</p><p>Confirmed by the participant during the discussion.</p>{commitment.audience_ids?.length > 0 && <small>Related audiences: {commitment.audience_ids.map((id) => adopted.find((d) => d.decision_id === id)?.title || "An audience that needs review").join(", ")}</small>}{!readOnly && <div className="v2-actions"><button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => setForm({ ...commitment, consent_confirmed: false })}>Edit confirmed commitment</button><button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => { if (window.confirm("Withdraw this participation commitment from the final strategy?")) onWithdraw(commitment); }}>Withdraw commitment</button></div>}</article>)}
    {!readOnly && <form onSubmit={async (event) => { event.preventDefault(); if (await onSave(form)) setForm({ participant_id: "", responsibility: "", audience_ids: [], consent_confirmed: false }); }}>
      <label className="v2-field">Participant<select required value={form.participant_id} onChange={(event) => setForm({ ...form, participant_id: event.target.value, consent_confirmed: false })}><option value="">Choose a participant</option>{participants.map((participant) => <option key={participant.participant_id} value={participant.participant_id}>{participant.name}</option>)}</select></label>
      <label className="v2-field">Responsibility they have agreed to<textarea required rows={3} value={form.responsibility} onChange={(event) => setForm({ ...form, responsibility: event.target.value })} /></label>
      <fieldset className="v2-choices"><legend>Related approved audiences or activities</legend>{adopted.map((decision) => <label className="v2-check" key={decision.decision_id}><input type="checkbox" checked={form.audience_ids.includes(decision.decision_id)} onChange={(event) => setForm({ ...form, audience_ids: event.target.checked ? [...form.audience_ids, decision.decision_id] : form.audience_ids.filter((id) => id !== decision.decision_id) })} />{decision.title}</label>)}</fieldset>
      <label className="v2-check"><input required type="checkbox" checked={form.consent_confirmed} onChange={(event) => setForm({ ...form, consent_confirmed: event.target.checked })} />This participant has explicitly agreed to the responsibility recorded above.</label><button className="v2-btn" disabled={busy || !form.consent_confirmed}>Save confirmed participation</button>
    </form>}
  </section>;
}

function MeetingSettings({ journeyId, initial, onError, onMessage }) {
  const [meeting, setMeeting] = useState({ date: "", time: "", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/London", ...initial });
  const [busy, setBusy] = useState(false);
  const [link, setLink] = useState("");
  const save = async (event) => {
    event.preventDefault(); setBusy(true);
    try { await v2Api.put(`/journeys/${journeyId}/meeting`, meeting); onMessage("Your meeting details have been saved. The group session remains accessible before the meeting."); }
    catch (problem) { onError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  const share = async () => {
    setBusy(true);
    try { const response = await v2Api.post(`/journeys/${journeyId}/group/share`); setLink(response.data.group_link); }
    catch (problem) { onError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  return <details className="v2-card" open={!initial?.date}><summary>Meeting date, time and participant access</summary><p>The date helps you prepare and receive reminders. It does not restrict access to this session. The participant meeting link shows the discussion without giving facilitator approval controls.</p><form onSubmit={save}><div className="v2-grid"><label className="v2-field">Meeting date<input type="date" value={meeting.date} onChange={(event) => setMeeting({ ...meeting, date: event.target.value })} /></label><label className="v2-field">Meeting time<input type="time" value={meeting.time} onChange={(event) => setMeeting({ ...meeting, time: event.target.value })} /></label><label className="v2-field">Time zone<input value={meeting.timezone} onChange={(event) => setMeeting({ ...meeting, timezone: event.target.value })} /></label></div><div className="v2-actions"><button className="v2-btn v2-btn-secondary" disabled={busy}>Save meeting details</button><button type="button" className="v2-btn v2-btn-secondary" disabled={busy} onClick={share}>Create secure participant meeting link</button></div></form>{link && <div className="v2-link-box"><label>Participant meeting link<input readOnly value={link} /></label><CopyButton text={link}>Copy meeting link</CopyButton></div>}</details>;
}

function FinalPreview({ journeyId, data, onError, onMessage, refresh }) {
  const [resource, setResource] = useState(null);
  const [text, setText] = useState("");
  const [editing, setEditing] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const fundraising = data.journey.product === "board-fundraising-game";
  useEffect(() => { if (resource && resource.decision_version !== data.decision_version) { setResource(null); setConfirmed(false); } }, [data.decision_version, resource]);
  useEffect(() => {
    if (!data.final_resource_id) return undefined;
    let active = true;
    v2Api.get(`/journeys/${journeyId}/resources/${data.final_resource_id}`).then(({ data: saved }) => { if (active) { setResource(saved); setText(saved.text); } }).catch((problem) => { if (active) onError(errorMessage(problem)); });
    return () => { active = false; };
  }, [data.final_resource_id, journeyId, onError]);
  const preview = async () => {
    setBusy(true); onError("");
    try { const response = await v2Api.post(`/journeys/${journeyId}/final-preview`); const next = response.data.resource || response.data; setResource(next); setText(next.text || ""); setConfirmed(false); setEditing(false); }
    catch (problem) { onError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  const save = async () => {
    setBusy(true);
    try { const response = await v2Api.put(`/journeys/${journeyId}/resources/${resource.resource_id}`, { text, expected_revision: resource.revision }); const next = response.data.resource || response.data; setResource(next); setText(next.text); setEditing(false); setConfirmed(false); }
    catch (problem) { onError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  const approve = async () => {
    setBusy(true); onError("");
    try { const response = await v2Api.post(`/journeys/${journeyId}/resources/${resource.resource_id}/approve`, { expected_revision: resource.revision }); const next = response.data.resource || response.data; if (next.resource_id) setResource(next); if (next.delivery_error || next.email?.status === "queue_failed") onError("Your approved final document is saved, but its email could not be queued. Retry approved email delivery below."); else onMessage(`Your approved ${fundraising ? "fundraising strategy" : "strategic plan"} has been saved and queued for email delivery. You can download it below or share the email with your board.`); await refresh(); }
    catch (problem) { onError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  return <section className="v2-card" data-testid="v2-final-preview"><h2>{fundraising ? "Review and approve your fundraising strategy" : "Review and approve your strategic plan"}</h2><p>The document includes adopted decisions{fundraising ? " and confirmed participation commitments" : ""}. Complete the discussion, review it together and approve the final version.</p>{!data.final_resource_id && <button className="v2-btn" disabled={busy || !(data.decisions || []).some((decision) => decision.status === "adopted")} onClick={preview}>{busy ? "Preparing..." : fundraising ? "Complete discussion and review the strategy" : "Complete discussion and review the plan"}</button>}
    {resource && <>
      {editing ? <label className="v2-field">Edit the final preview<textarea className="v2-editor" rows={22} value={text} onChange={(event) => setText(event.target.value)} /></label> : <DocumentPreview resource={resource} branding={data.journey.branding} />}
      <div className="v2-actions">{resource.status !== "approved" && (editing ? <><button className="v2-btn" disabled={busy || text === resource.text} onClick={save}>Save corrections for review</button><button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => { setText(resource.text); setEditing(false); }}>Cancel editing</button></> : <button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => { setEditing(true); setConfirmed(false); }}>Make corrections</button>)}<CopyButton text={text}>Copy final document</CopyButton></div>
      {resource.status !== "approved" && <><label className="v2-check"><input data-testid="v2-final-confirm" type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />I confirm that this final document reflects the decisions and commitments our group actually approved.</label><button data-testid="v2-final-approve" className="v2-btn" disabled={busy || editing || !confirmed} onClick={approve}>Approve, save and email the final {fundraising ? "strategy" : "plan"}</button></>}
      {resource.status === "approved" && <p className="v2-notice">This exact final version has been approved and saved.</p>}
      {resource.delivery_error && <button className="v2-btn" disabled={busy} onClick={approve}>Retry approved email delivery</button>}
      <div className="v2-actions">{["pdf", "docx"].map((format) => <DownloadLink key={format} path={`/journeys/${journeyId}/resources/${resource.resource_id}/download?format=${format}`}>Download {format.toUpperCase()}</DownloadLink>)}<CopyButton text={`Our board has approved the ${fundraising ? "fundraising strategy" : "strategic plan"}. Please review the attached document so we can begin the work we agreed to carry out.`}>Copy an email to share with participants</CopyButton></div>
    </>}
  </section>;
}

export function GroupPage() {
  const { journeyId } = useParams();
  const { data, error, setError, loading, refresh } = useV2Load(`/journeys/${journeyId}/group`);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState(null);
  const [selected, setSelected] = useState([]);
  const saveDecision = async (decision) => {
    setBusy(true); setError(""); setMessage("");
    try { await v2Api.post(`/journeys/${journeyId}/decisions`, decision); setDraft(null); setSelected([]); await refresh(); setMessage(decision.status === "adopted" ? "The group's adopted decision has been saved." : "This idea is excluded from the final document."); }
    catch (problem) { setError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  const saveCommitment = async (commitment) => {
    setBusy(true); setError("");
    try { await v2Api.post(`/journeys/${journeyId}/commitments`, commitment); await refresh(); setMessage("The participant's confirmed commitment has been saved."); return true; }
    catch (problem) { setError(errorMessage(problem)); return false; }
    finally { setBusy(false); }
  };
  const withdrawCommitment = async (commitment) => {
    setBusy(true); setError("");
    try { await v2Api.delete(`/journeys/${journeyId}/commitments/${commitment.commitment_id}`); await refresh(); setMessage("This commitment has been withdrawn and will not appear in the final strategy."); }
    catch (problem) { setError(errorMessage(problem)); }
    finally { setBusy(false); }
  };
  const fundraising = data?.journey?.product === "board-fundraising-game";
  const existingMission = data?.journey?.existing_mission || data?.journey?.answers?.mission || data?.journey?.answers?.mission_statement;
  return <V2Shell><div className="v2-action-page v2-group-page" data-testid="v2-group"><Link className="v2-back-link" to={`/v2/resources/${journeyId}`}>Your resources</Link><header><h1>{fundraising ? "Your Group Fundraising Game" : "Your Group Strategic Planning Session"}</h1><p>Review the contributions before your meeting or discuss them together now. You control the decisions. Ideas enter the final document only when you explicitly adopt them.</p></header><ActionNotice error={error} message={message} />
    {loading && <p role="status">Loading your group's contributions...</p>}
    {data && <>
      {!data.read_only && <MeetingSettings journeyId={journeyId} initial={data.journey.meeting} onError={setError} onMessage={setMessage} />}
      <div className="v2-actions"><button className="v2-btn v2-btn-secondary" onClick={refresh}>Refresh submitted ideas</button><Link className="v2-btn v2-btn-secondary" to={`/v2/resources/${journeyId}`}>Open your facilitation guide and resources</Link></div>
      {!data.read_only && !fundraising && existingMission && <section className="v2-card"><h2>Your existing mission</h2><p>{existingMission}</p><button className="v2-btn v2-btn-secondary" disabled={busy} onClick={() => saveDecision({ category: "mission", title: "Mission", content: existingMission, source_ids: [], status: "adopted" })}>Confirm that we are retaining this mission</button></section>}
      <GroupContent data={data} readOnly={data.read_only} onDecision={saveDecision} draft={draft} setDraft={setDraft} selected={selected} setSelected={setSelected} busy={busy} />
      {fundraising && <Participation data={data} readOnly={data.read_only} busy={busy} onSave={saveCommitment} onWithdraw={withdrawCommitment} />}
      <FinalPreview journeyId={journeyId} data={data} onError={setError} onMessage={setMessage} refresh={refresh} />
    </>}
  </div></V2Shell>;
}

export function SharedMeetingPage() {
  const { token } = useParams();
  const { data, error, loading, refresh } = useV2Load(`/meeting/${token}`);
  return <V2Shell><div className="v2-action-page v2-group-page" data-testid="v2-shared-meeting"><header><h1>Your board's group discussion</h1><p>Review the submitted ideas and decisions here. Your meeting facilitator controls adoption and final approval.</p></header><ActionNotice error={error} />{loading && <p role="status">Loading your group's session...</p>}{data && <><button className="v2-btn v2-btn-secondary" onClick={refresh}>Refresh discussion</button><GroupContent data={data} readOnly selected={[]} />{data.journey?.product === "board-fundraising-game" && <Participation data={data} readOnly />}</>}</div></V2Shell>;
}
