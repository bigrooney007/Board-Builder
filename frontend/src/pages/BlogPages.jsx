import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import { FunnelLayout } from "@/funnels/FunnelLayout";
import { PAGE_META, usePageMeta } from "@/seo";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const formatDate = (iso) => iso ? new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "";

const PostCard = ({ post }) => (
  <article className="blog-card" data-testid={`blog-card-${post.slug}`}>
    <span className="blog-category-tag">{post.category}</span>
    <h2><Link to={`/blog/${post.slug}`}>{post.title}</Link></h2>
    <p className="blog-date">{formatDate(post.published_at)}</p>
    <p className="blog-excerpt">{post.excerpt}</p>
    <Link className="blog-read-link" to={`/blog/${post.slug}`} data-testid={`read-article-${post.slug}`}>Read Article <ArrowRight size={14} /></Link>
  </article>
);

export const BlogPage = () => {
  usePageMeta(...PAGE_META.blog);
  const [posts, setPosts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filter, setFilter] = useState("");
  const load = useCallback((category) => {
    axios.get(`${API}/blog/posts`, { params: category ? { category } : {} }).then((response) => {
      setPosts(response.data.posts);
      setCategories(response.data.categories);
    }).catch(() => {});
  }, []);
  useEffect(() => { load(filter); }, [filter, load]);
  return (
    <FunnelLayout>
      <main className="member-page blog-page" data-testid="blog-page">
        <header className="member-page-heading">
          <p className="eyebrow">Insights</p>
          <h1 data-testid="blog-heading">Nonprofit Board Builder Insights</h1>
          <p>Practical strategies to help you reactivate your present board, recruit the board members you are missing and activate your board to start raising money.</p>
        </header>
        <div className="blog-filters" data-testid="blog-filters">
          <button className={filter === "" ? "active" : ""} onClick={() => setFilter("")} data-testid="blog-filter-all">All</button>
          {categories.map((category) => (
            <button className={filter === category.key ? "active" : ""} onClick={() => setFilter(category.key)} key={category.key} data-testid={`blog-filter-${category.key}`}>{category.name}</button>
          ))}
        </div>
        {posts.length === 0 && <p className="workspace-note" data-testid="blog-empty">Articles are coming soon.</p>}
        <div className="blog-grid">{posts.map((post) => <PostCard post={post} key={post.slug} />)}</div>
      </main>
    </FunnelLayout>
  );
};

export const BlogPostPage = () => {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    axios.get(`${API}/blog/posts/${slug}`).then((response) => setPost(response.data)).catch(() => setError("This article could not be found."));
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
        {error && <div className="member-card"><h2>{error}</h2><Link className="button" to="/blog">Back to All Articles</Link></div>}
        {post && (
          <>
            <header className="member-page-heading">
              <span className="blog-category-tag">{post.category}</span>
              <h1 data-testid="article-title">{post.title}</h1>
              <p className="blog-date" data-testid="article-date">{formatDate(post.published_at)}</p>
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
      <div className="section-heading"><div><p className="eyebrow">Insights</p><h2 data-testid="blog-slider-heading">Latest From Nonprofit Board Builder</h2></div></div>
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
