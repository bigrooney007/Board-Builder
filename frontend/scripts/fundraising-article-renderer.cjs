const { renderBlogHtml } = require("../src/seo/blogMetadata");
const { articlePost } = require("../src/content/fundraisingArticles");
const { renderArticleMarkup } = require("../src/content/fundraisingArticleMarkup");

module.exports = function renderFundraisingArticle(template, article) {
  // Reuse the blog's escaped metadata, then replace its basic fallback with the
  // same editorial markup used by React. Both versions load the same stylesheet.
  const html = renderBlogHtml(template, articlePost(article));
  return html.replace(/<div id="root"><main id="blog-page-summary"[\s\S]*?<\/main><\/div>/i, () => `<div id="root">${renderArticleMarkup(article)}</div>`)
    .replace(/<\/head>/i, '<link rel="stylesheet" href="/styles/fundraising-articles.css" />\n</head>');
};
