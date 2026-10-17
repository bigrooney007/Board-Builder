import { useEffect, useState } from "react";
import axios from "axios";
import { useBlogMeta } from "@/seo";
import { articlePost, mergeGuide } from "@/content/fundraisingArticles";
import { renderArticleMarkup } from "@/content/fundraisingArticleMarkup";

const API = `${(process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "")}/api`;
const initialGuide = article => {
  try {
    return mergeGuide(article, JSON.parse(document.getElementById("fundraising-guide-data")?.textContent || "null"));
  } catch { return article; }
};

// Server HTML carries the latest saved copy. Fallback copy also keeps the guide readable offline.
export default function FundraisingArticlePage({ article }) {
  const [guide, setGuide] = useState(() => initialGuide(article));
  useBlogMeta(articlePostCache(guide));
  useEffect(() => { window.scrollTo({ top: 0 }); }, [article.slug]);
  useEffect(() => {
    let active = true;
    axios.get(`${API}/blog/guides/${article.slug}`).then(response => {
      if (active) setGuide(current => mergeGuide(current, response.data));
    }).catch(() => {});
    return () => { active = false; };
  }, [article]);
  return <>
    <link rel="stylesheet" href="/styles/fundraising-articles.css" precedence="article" />
    <div dangerouslySetInnerHTML={{ __html: renderArticleMarkup(guide) }} />
  </>;
}

const postCache = new WeakMap();
function articlePostCache(article) {
  if (!postCache.has(article)) postCache.set(article, articlePost(article));
  return postCache.get(article);
}
