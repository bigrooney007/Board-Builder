import { useEffect } from "react";
import { useBlogMeta } from "@/seo";
import { articlePost } from "@/content/fundraisingArticles";
import { renderArticleMarkup } from "@/content/fundraisingArticleMarkup";

// Static, escaped copy is shared with the server renderer so the complete guide
// is available immediately, including when JavaScript or the blog API is unavailable.
export default function FundraisingArticlePage({ article }) {
  useBlogMeta(articlePostCache(article));
  useEffect(() => { window.scrollTo({ top: 0 }); }, [article.slug]);
  return <>
    <link rel="stylesheet" href="/styles/fundraising-articles.css" precedence="article" />
    <div dangerouslySetInnerHTML={{ __html: renderArticleMarkup(article) }} />
  </>;
}

const postCache = new WeakMap();
function articlePostCache(article) {
  if (!postCache.has(article)) postCache.set(article, articlePost(article));
  return postCache.get(article);
}
