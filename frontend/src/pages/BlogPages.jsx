import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import { FunnelLayout } from "@/funnels/FunnelLayout";
import { useBlogMeta } from "@/seo";
import { blogPagesText } from "../content/siteContent";

const ORIGIN = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
const API = `${ORIGIN}/api`;
const imageSrc = (post) => post.image_path ? ORIGIN + post.image_path : post.image_url;
const formatDate = (iso) => iso ? new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "";

const PostCard = ({ post }) => (
  <article className="blog-card" data-testid={`blog-card-${post.slug}`}>
    {post.image_url && <Link to={`/blog/${post.slug}`} tabIndex={-1} aria-hidden="true"><img className="blog-cover" src={imageSrc(post)} alt="" loading="lazy" width="1200" height="630"/></Link>}
    <span className="blog-category-tag">{post.category}</span>
    <h2><Link to={`/blog/${post.slug}`}>{post.title}</Link></h2>
    <p className="blog-date">{formatDate(post.published_at)}</p>
    <p className="blog-excerpt">{post.excerpt}</p>
    <Link className="blog-read-link" to={`/blog/${post.slug}`} data-testid={`read-article-${post.slug}`}>Read Article <ArrowRight size={14} /></Link>
  </article>
);

export const BlogPage = () => {
  useBlogMeta();
  const [posts, setPosts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback((category) => {
    setLoading(true); setError("");
    axios.get(`${API}/blog/posts`, { params: category ? { category } : {} }).then((response) => {
      setPosts(response.data.posts);
      setCategories(response.data.categories);
    }).catch(() => setError("The articles could not load. Please refresh to try again.")).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(filter); }, [filter, load]);
  return (
    <FunnelLayout>
      <main className="member-page blog-page" data-testid="blog-page">
        <header className="member-page-heading">
          <p className="eyebrow">Insights</p>
          <h1 data-testid="blog-heading">{blogPagesText.nonprofitBoardBuilderInsights}</h1>
          <p>{blogPagesText.practicalStrategiesToHelpYou}</p>
        </header>
        <div className="blog-filters" data-testid="blog-filters">
          <button className={filter === "" ? "active" : ""} onClick={() => setFilter("")} data-testid="blog-filter-all">All</button>
          {categories.map((category) => (
            <button className={filter === category.key ? "active" : ""} onClick={() => setFilter(category.key)} key={category.key} data-testid={`blog-filter-${category.key}`}>{category.name}</button>
          ))}
        </div>
        {loading && <p>Loading articles...</p>}
        {error && <p role="alert">{error}</p>}
        {!loading && !error && posts.length === 0 && <p className="workspace-note" data-testid="blog-empty">{blogPagesText.articlesAreComingSoon}</p>}
        <div className="blog-grid">{posts.map((post) => <PostCard post={post} key={post.slug} />)}</div>
      </main>
    </FunnelLayout>
  );
};

export const BlogPostPage = () => {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(200);
  useBlogMeta(post, status);
  useEffect(() => {
    let active = true;
    setPost(null); setError(""); setStatus(200);
    axios.get(`${API}/blog/posts/${encodeURIComponent(slug)}`).then((response) => { if (active) setPost(response.data); }).catch((err) => {
      if (active) { setStatus(err.response?.status === 404 ? 404 : 503); setError(err.response?.status === 404 ? "This article could not be found." : "This article could not load. Please try again shortly."); }
    });
    return () => { active = false; };
  }, [slug]);
  const renderBody = (body) => (body || "").split(/\n{2,}|\n(?=## )/).map((block, index) => {
    const trimmed = block.trim();
    if (!trimmed) return null;
    if (trimmed.startsWith("## ")) return <h2 key={index}>{trimmed.replace(/^##\s*/, "")}</h2>;
    return <p key={index}>{trimmed}</p>;
  });
  return (
    <FunnelLayout>
      <main className="member-page blog-article-page" data-testid="blog-article-page">
        {error && <div className="member-card"><h2>{error}</h2><Link className="button" to="/blog">{blogPagesText.backToAllArticles}</Link></div>}
        {!post && !error && <p>Loading article...</p>}
        {post && (
          <>
            {post.image_url && <img className="blog-cover blog-article-cover" src={imageSrc(post)} alt={post.image_alt} width="1200" height="630" fetchPriority="high"/>}
            <header className="member-page-heading">
              <span className="blog-category-tag">{post.category}</span>
              <h1 data-testid="article-title">{post.title}</h1>
              <p className="blog-date" data-testid="article-date">{formatDate(post.published_at)}</p>
              <p className="blog-byline">By Rooney Akpesiri</p>
            </header>
            <article className="blog-article-body" data-testid="article-body">{renderBody(post.body)}</article>
            <section className="blog-cta" data-testid="article-cta">
              <h2>{post.cta_label}</h2>
              <a className="button" href={post.cta_url} data-testid="article-cta-button">{post.cta_button} <ArrowRight size={16} /></a>
            </section>
            <p><Link to="/blog" className="blog-read-link">Read All Articles</Link></p>
          </>
        )}
      </main>
    </FunnelLayout>
  );
};

export const BlogSlider = () => {
  const [posts, setPosts] = useState([]);
  const [active, setActive] = useState(0);
  const touchStart = useRef(null);
  useEffect(() => { axios.get(`${API}/blog/posts`, { params: { limit: 6 } }).then((response) => setPosts(response.data.posts.slice(0, 6))).catch(() => {}); }, []);
  if (!posts.length) return null;
  const go = (next) => setActive(((next % posts.length) + posts.length) % posts.length);
  return (
    <section className="section blog-slider-section" data-testid="homepage-blog-slider">
      <div className="section-heading"><div><p className="eyebrow">Insights</p><h2 data-testid="blog-slider-heading">{blogPagesText.latestFromNonprofitBoardBuilder}</h2></div></div>
      <div className="blog-slider" onTouchStart={(event) => { touchStart.current = event.touches[0].clientX; }}
        onTouchEnd={(event) => { if (touchStart.current === null) return; const delta = event.changedTouches[0].clientX - touchStart.current; if (Math.abs(delta) > 45) go(active + (delta < 0 ? 1 : -1)); touchStart.current = null; }}>
        <div className="blog-slider-track" style={{ transform: `translateX(-${active * 100}%)` }}>
          {posts.map((post) => (
            <div className="blog-slide" key={post.slug}><PostCard post={post} /></div>
          ))}
        </div>
      </div>
      <div className="testimonial-controls">
        <button onClick={() => go(active - 1)} aria-label="Previous article" data-testid="blog-slider-previous"><ChevronLeft /></button>
        <span>{active + 1} / {posts.length}</span>
        <button onClick={() => go(active + 1)} aria-label="Next article" data-testid="blog-slider-next"><ChevronRight /></button>
      </div>
      <a className="button blog-all-button" href="/blog" data-testid="read-all-articles-button">Read All Articles <ArrowRight size={16} /></a>
    </section>
  );
};
