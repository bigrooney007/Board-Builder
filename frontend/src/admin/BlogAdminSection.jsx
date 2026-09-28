import React, { useCallback, useEffect, useState } from "react";

const API_ORIGIN = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
const imageSrc = (post) => post.image_path ? API_ORIGIN + post.image_path : post.image_url;
const emptyEdit = (post) => Object.fromEntries(["title", "excerpt", "body", "graphic_headline", "graphic_subtitle"].map((key) => [key, post[key] || ""]));
const errorText = (error) => typeof error.response?.data?.detail === "string" ? error.response.data.detail : "This action could not finish. Please try again.";

export function BlogBody({ body }) {
  return (body || "").split(/\n{2,}|\n(?=## )/).map((block, index) => {
    const text = block.trim();
    return !text ? null : text.startsWith("## ") ? <h2 key={index}>{text.replace(/^##\s*/, "")}</h2> : <p key={index}>{text}</p>;
  });
}

function Brief({ brief }) {
  if (!brief) return null;
  return <dl className="blog-brief">
    <div><dt>What they are running from</dt><dd>{brief.pain_point}</dd></div>
    <div><dt>The belief keeping them there</dt><dd>{brief.limiting_belief}</dd></div>
    <div><dt>What they are running to</dt><dd>{brief.desired_outcome}</dd></div>
  </dl>;
}

export default function BlogAdminSection({ client }) {
  const [schedule, setSchedule] = useState([]);
  const [settings, setSettings] = useState(null);
  const [category, setCategory] = useState("recruitment");
  const [topicId, setTopicId] = useState("");
  const [date, setDate] = useState("");
  const [posts, setPosts] = useState([]);
  const [hasMore, setHasMore] = useState(false);
  const [post, setPost] = useState(null);
  const [edit, setEdit] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const selectedCategory = schedule.find((item) => item.category_key === category);
  const angle = selectedCategory?.topics.find((item) => item.topic_id === topicId);
  const dirty = !!edit && JSON.stringify(edit) !== JSON.stringify(emptyEdit(post));
  const loadPosts = useCallback(async (skip = 0) => {
    const response = await client.get("/admin/blog/posts", { params: { skip } });
    setPosts((previous) => skip ? [...previous, ...response.data.posts] : response.data.posts);
    setHasMore(response.data.has_more);
  }, [client]);
  const loadSchedule = useCallback(async () => {
    const response = await client.get("/admin/blog/topics");
    setSchedule(response.data.schedule); setSettings(response.data.settings);
  }, [client]);
  useEffect(() => {
    Promise.all([loadPosts(), loadSchedule()]).catch((err) => setError(errorText(err)));
  }, [loadPosts, loadSchedule]);
  useEffect(() => {
    if (selectedCategory) { setTopicId(selectedCategory.next_topic_id); setDate(selectedCategory.scheduled_date); }
  }, [selectedCategory]);
  const replacePost = useCallback((next) => {
    setPost(next);
    setPosts((previous) => previous.some((item) => item.blog_post_id === next.blog_post_id)
      ? previous.map((item) => item.blog_post_id === next.blog_post_id ? next : item) : [next, ...previous]);
  }, []);
  useEffect(() => {
    if (post?.publication_status !== "Generating") return undefined;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const response = await client.get(`/admin/blog/posts/${post.blog_post_id}`);
        if (!cancelled) replacePost(response.data.post);
      } catch (err) { if (!cancelled) setError(errorText(err)); }
    }, 4000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [client, post?.blog_post_id, post?.publication_status, replacePost]);
  const run = async (operation) => {
    setBusy(true); setError(""); setMessage("");
    try { await operation(); } catch (err) { setError(errorText(err)); }
    finally { setBusy(false); }
  };
  const generate = () => run(async () => {
    const response = await client.post("/blog/generate", { category, topic_id: topicId, scheduled_date: date });
    setEdit(null); replacePost(response.data.post);
    setMessage(response.data.reused ? "Opened the existing article for this topic and date." : "Your draft is generating. You can return here in a few minutes.");
    await loadSchedule();
  });
  const action = (name) => run(async () => {
    const response = await client.post(`/admin/blog/posts/${post.blog_post_id}/${name}`);
    setEdit(null); replacePost(response.data.post);
    setMessage(name === "approve" ? "Published. The article link includes its cover image and description." : name === "regenerate" ? "A new version of this draft is generating." : "Article updated.");
  });
  const save = (event) => { event.preventDefault(); run(async () => {
    const response = await client.patch(`/admin/blog/posts/${post.blog_post_id}`, edit);
    replacePost(response.data.post); setEdit(null); setMessage("Saved. Your cover graphic and share description are updated.");
  }); };
  const selectPost = (item) => { setPost(item); setEdit(null); setError(""); setMessage(""); };

  return <section className="blog-workstation" data-testid="admin-blog-section">
    <div className="blog-workstation-heading"><div><h2>Blog Post Generator</h2><p>Choose the reader's problem. Generate an article with its cover graphic, review it, and publish.</p></div><a className="button button-back button-small" href="/blog" target="_blank" rel="noreferrer">Open Blog</a></div>
    {error && <p className="submit-error" role="alert">{error}</p>}
    {message && <p className="admin-message" role="status">{message}</p>}
    {!schedule.length && !error && <p>Loading your blog topics...</p>}
    <div className="blog-weekdays" aria-label="Weekly blog topics">
      {schedule.map((item) => <button key={item.category_key} className={category === item.category_key ? "active" : ""} aria-pressed={category === item.category_key} onClick={() => setCategory(item.category_key)}>
        <span>{item.publish_day}</span><strong>{item.category}</strong><small>{item.cta_url}</small>
      </button>)}
    </div>
    {selectedCategory && <div className="blog-generator-panel">
      <p><strong>Reader:</strong> {selectedCategory.audience}</p>
      <label>Article angle<select value={topicId} onChange={(event) => setTopicId(event.target.value)}>{selectedCategory.topics.map((item) => <option key={item.topic_id} value={item.topic_id}>{item.topic_title}</option>)}</select></label>
      <Brief brief={angle}/>
      <div className="blog-generator-actions"><label>Planned post date<input type="date" value={date} required onChange={(event) => setDate(event.target.value)}/></label>
        <button className="button" disabled={busy || !date || !topicId || dirty} onClick={generate}>Generate Blog Post + Graphic</button>
      </div><p className="workspace-note">One article per topic and date. Reopening it uses your saved draft.</p>
    </div>}
    {settings && <details className="blog-schedule-settings"><summary>Automatic weekday drafts</summary>
      <p>Prepare the day's topic automatically, Monday through Friday. Drafts wait here for you to review and publish.</p>
      <label className="blog-setting-check"><input type="checkbox" checked={settings.enabled} onChange={(event) => setSettings({ ...settings, enabled: event.target.checked })}/> Generate weekday drafts automatically</label>
      <div className="blog-generator-actions"><label>Generation time<input type="time" value={settings.time} onChange={(event) => setSettings({ ...settings, time: event.target.value })}/></label>
        <label>Timezone<input value={settings.timezone} placeholder="Europe/London" onChange={(event) => setSettings({ ...settings, timezone: event.target.value })}/></label>
        <button className="button button-small" disabled={busy} onClick={() => run(async () => { const response = await client.put("/admin/blog/settings", settings); setSettings(response.data.settings); setMessage("Weekday draft settings saved."); })}>Save Schedule</button>
      </div>
    </details>}
    <div className="blog-workstation-columns">
      <aside className="blog-post-list"><div className="blog-workstation-heading"><h3>Your Articles</h3><button className="button button-back button-small" disabled={busy} onClick={() => run(() => loadPosts())}>Refresh</button></div>
        {!posts.length && <p>Your generated drafts will appear here.</p>}
        {posts.map((item) => <button key={item.blog_post_id} disabled={dirty} className={post?.blog_post_id === item.blog_post_id ? "active" : ""} onClick={() => selectPost(item)}>
          <small>{item.category} · {item.scheduled_date}</small><strong>{item.title || item.topic_title || "Generating article"}</strong><span>{item.publication_status === "Rejected" ? "Archived" : item.publication_status}</span>
        </button>)}
        {hasMore && <button className="button button-back button-small" disabled={busy} onClick={() => run(() => loadPosts(posts.length))}>Load Older Articles</button>}
      </aside>
      <div className="blog-review" aria-live="polite">
        {!post && <p>Select an article to preview, edit or publish.</p>}
        {post && <>
          <p className="eyebrow">{post.publication_status === "Rejected" ? "Archived" : post.publication_status}</p>
          {post.publication_status === "Generating" && <p>{post.generation_interrupted ? "The previous generation did not finish. Use Regenerate Draft to try again." : "Your article and graphic are being prepared. You can leave this page and return in a few minutes."}</p>}
          {post.error && <p className="submit-error">{post.error}</p>}
          {post.content_brief && <details><summary>Article direction</summary><Brief brief={post.content_brief}/></details>}
          {post.title && <>
            <img className="blog-cover" src={imageSrc(post)} alt={post.image_alt} width="1200" height="630"/>
            <h2>{post.title}</h2><p className="blog-preview-excerpt">{post.excerpt}</p>
            <div className="blog-article-body"><BlogBody body={post.body}/></div>
            <div className="blog-preview-cta"><h3>{post.cta_label}</h3><a href={post.cta_url} target="_blank" rel="noreferrer">{post.cta_button}</a></div>
          </>}
          {edit && <form className="blog-edit-form" onSubmit={save}>
            <h3>Edit Article and Graphic</h3>
            <label>Title<input required maxLength={200} value={edit.title} onChange={(event) => setEdit({ ...edit, title: event.target.value })}/></label>
            <label>Search and share description<textarea required minLength={10} maxLength={200} rows={3} value={edit.excerpt} onChange={(event) => setEdit({ ...edit, excerpt: event.target.value })}/></label>
            <label>Article<textarea required minLength={50} rows={16} value={edit.body} onChange={(event) => setEdit({ ...edit, body: event.target.value })}/></label>
            <label>Graphic headline<input maxLength={85} value={edit.graphic_headline} onChange={(event) => setEdit({ ...edit, graphic_headline: event.target.value })}/></label>
            <label>Graphic supporting line<input maxLength={110} value={edit.graphic_subtitle} onChange={(event) => setEdit({ ...edit, graphic_subtitle: event.target.value })}/></label>
            <div className="material-actions"><button className="button" disabled={busy} type="submit">Save Article and Graphic</button><button className="button button-back" type="button" onClick={() => setEdit(null)}>Cancel Edits</button></div>
          </form>}
          <div className="material-actions blog-review-actions">
            {post.title && post.publication_status !== "Generating" && !edit && <button className="button button-back button-small" disabled={busy} onClick={() => setEdit(emptyEdit(post))}>Edit Article and Graphic</button>}
            {post.publication_status === "Pending Review" && <button className="button button-small" disabled={busy || !!edit} onClick={() => action("approve")}>Publish Article</button>}
            {post.can_regenerate && <button className="button button-back button-small" disabled={busy || !!edit} onClick={() => action("regenerate")}>Regenerate Draft</button>}
            {!["Published", "Generating", "Rejected"].includes(post.publication_status) && <button className="button button-back button-small" disabled={busy || !!edit} onClick={() => action("reject")}>Archive Draft</button>}
            {post.publication_status === "Published" && <><a className="button button-small" href={`/blog/${post.slug}`} target="_blank" rel="noreferrer">Open Published Article</a><button className="button button-back button-small" disabled={busy || !!edit} onClick={() => action("linkedin-snippet")}>{post.linkedin_snippet ? "View Share Text" : "Generate Share Text"}</button></>}
          </div>
          {post.publication_status === "Published" && <label className="blog-share-link">Share this article<input readOnly value={`https://nonprofitboardbuilder.com/blog/${post.slug}`} onFocus={(event) => event.target.select()}/></label>}
          {post.linkedin_snippet && <textarea aria-label="Article share text" className="blog-share-text" readOnly value={post.linkedin_snippet} rows={7} onFocus={(event) => event.target.select()}/>}
        </>}
      </div>
    </div>
  </section>;
}
