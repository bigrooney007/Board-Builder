const { renderBlogHtml } = require("../src/seo/blogMetadata");
const { articles, articleForPath, articlePost, mergeGuide } = require("../src/content/fundraisingArticles");
const renderFundraisingArticle = require("./fundraising-article-renderer.cjs");

// Fetches only public, published content from the configured application backend.
// Used by both Emergent's existing start command and the production HTML server.
module.exports = function blogSeoHandler(readTemplate, options = {}) {
  const origin = (options.origin || process.env.BLOG_API_ORIGIN || process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8001").replace(/\/$/, "");
  const fetchApi = options.fetch || global.fetch;
  return async (req, res, next) => {
    if (!["GET", "HEAD"].includes(req.method)) return next();
    const pathname = new URL(req.url, "http://localhost").pathname.replace(/\/+$/, "");
    if (pathname !== "/blog" && !/^\/blog\/[^/]+$/.test(pathname)) return next();
    const article = articleForPath(pathname);
    if (article) {
      let guide = article;
      try {
        const response = await fetchApi(`${origin}/api/blog/guides/${article.slug}`, { signal: AbortSignal.timeout(7000), headers: { Accept: "application/json" }, redirect: "error" });
        if (response.ok) guide = mergeGuide(article, await response.json());
      } catch { /* Keep the complete guide available if its content API is temporarily offline. */ }
      try {
        const template = await readTemplate();
        res.statusCode = 200;
        res.setHeader("Content-Type", "text/html; charset=utf-8");
        res.setHeader("Cache-Control", "no-cache");
        return res.end(req.method === "HEAD" ? undefined : renderFundraisingArticle(template, guide));
      } catch (error) { return next(error); }
    }
    const slug = pathname === "/blog" ? "" : pathname.slice(6);
    let status = 200, post = null, posts = [];
    try {
      const response = await fetchApi(`${origin}/api/blog/posts${slug ? "/" + encodeURIComponent(decodeURIComponent(slug)) : "?limit=100"}`, { signal: AbortSignal.timeout(7000), headers: { Accept: "application/json" }, redirect: "error" });
      if (response.status === 404) status = 404;
      else if (!response.ok) status = 503;
      else {
        const data = await response.json();
        if (slug && data.slug && data.title && data.body && data.image_url) post = data;
        else if (!slug && Array.isArray(data.posts)) {
          let guides = articles;
          try {
            const guideResponse = await fetchApi(`${origin}/api/blog/guides`, { signal: AbortSignal.timeout(7000), headers: { Accept: "application/json" }, redirect: "error" });
            const guideData = guideResponse.ok ? await guideResponse.json() : null;
            if (Array.isArray(guideData?.guides)) guides = articles.map(article => mergeGuide(article, guideData.guides.find(guide => guide.slug === article.slug)));
          } catch { /* Use the complete default cards when the guide API is unavailable. */ }
          posts = [...guides.map(articlePost), ...data.posts.filter(post => !articles.some(article => article.slug === post.slug))];
        }
        else status = 503;
      }
    } catch { status = 503; }
    try {
      const template = await readTemplate();
      res.statusCode = status;
      res.setHeader("Content-Type", "text/html; charset=utf-8");
      res.setHeader("Cache-Control", "no-cache");
      if (status !== 200) res.setHeader("X-Robots-Tag", "noindex");
      if (status === 503) res.setHeader("Retry-After", "60");
      res.end(req.method === "HEAD" ? undefined : renderBlogHtml(template, post, posts, status));
    } catch (error) { next(error); }
  };
};
