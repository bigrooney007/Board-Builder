/* eslint-env node */
const { articles, START_PATH, CTA, articlePath, articleWordCount } = require("./fundraisingArticles");
const escapeHtml = (text) => String(text || "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
const arrow = '<span aria-hidden="true">&#8594;</span>';
const startLink = (label, className) => `<a class="${className}" data-article-start="true" href="${START_PATH}">${escapeHtml(label)} ${arrow}</a>`;

function renderArticleMarkup(article) {
  const related = articles.find(item => item.slug !== article.slug);
  const relatedTitle = article.relatedGuide?.slug === related.slug ? article.relatedGuide.title : related.title;
  const paragraphs = text => `<p>${escapeHtml(text)}</p>`;
  const stages = article.visualItems.map((label, index) => `<li><span class="fa-visual-number" aria-hidden="true">0${index + 1}</span><span>${escapeHtml(label)}</span></li>`).join("");
  const steps = article.steps.map((step, index) => `<section class="fa-step" id="step-${step.id}" aria-labelledby="heading-${step.id}">
    <div class="fa-step-number" aria-hidden="true">0${index + 1}</div>
    <div class="fa-step-copy"><p class="fa-kicker">${escapeHtml(step.label)}</p><h2 id="heading-${step.id}">${escapeHtml(step.title)}</h2>
    ${step.paragraphs.map(paragraphs).join("")}
    ${step.questions?.length ? `<ol class="fa-questions" aria-label="The five fundraising questions">${step.questions.map(question => `<li>${escapeHtml(question)}</li>`).join("")}</ol>` : ""}
    ${step.afterQuestions ? paragraphs(step.afterQuestions) : ""}</div></section>`).join("");

  return `<div class="fundraising-article" data-testid="fundraising-guide" data-article-slug="${escapeHtml(article.slug)}">
    <a class="fa-skip" href="#article-copy">Skip to article</a>
    <header class="fa-masthead"><a class="fa-brand" href="/" aria-label="Nonprofit Board Builder home"><span class="fa-brand-mark" aria-hidden="true"><i></i><i></i></span><span>Nonprofit<br>Board Builder</span></a><nav aria-label="Article navigation"><a class="fa-all-articles" href="/blog">All articles</a>${startLink("Start my five questions", "fa-nav-start")}</nav></header>
    <main>
      <section class="fa-hero" aria-labelledby="article-title">
        <div class="fa-hero-copy"><p class="fa-kicker">${escapeHtml(article.topic)} <span aria-hidden="true">/</span> Three steps</p>
          <h1 id="article-title">${escapeHtml(article.headline)} <span>${escapeHtml(article.headlineAccent)}</span></h1>
          <p class="fa-deck">${escapeHtml(article.excerpt)}</p>
          <div class="fa-byline"><span class="fa-author-initials" aria-hidden="true">RA</span><div><p>Rooney Akpesiri</p><span>Nonprofit strategist <span aria-hidden="true">·</span> ${Math.ceil(articleWordCount(article) / 200)} min read</span></div></div>
          <a class="fa-read-link" href="#article-copy">Read the guide <span aria-hidden="true">&#8595;</span></a>
        </div>
        <aside class="fa-visual" aria-label="What this approach helps you do"><div class="fa-visual-top"><span class="fa-visual-dot" aria-hidden="true"></span> ${escapeHtml(article.visualEyebrow || "Your next board meeting")}</div><h2>${escapeHtml(article.visualTitle)}</h2><ol>${stages}</ol><div class="fa-visual-bottom"><span aria-hidden="true">&#10003;</span> ${escapeHtml(article.visualFootnote || "A strategy your board can act on")}</div></aside>
      </section>
      <div class="fa-reading-layout" id="article-copy">
        <aside class="fa-contents" aria-label="In this article"><p class="fa-kicker">In this guide</p><ol>${article.steps.map((step, index) => `<li><a href="#step-${step.id}"><span aria-hidden="true">0${index + 1}</span>${escapeHtml(step.navLabel || step.label)}</a></li>`).join("")}</ol><p class="fa-open-note">Free to read.<br> No email required.</p></aside>
        <article class="fa-body" aria-label="${escapeHtml(article.title)}"><div class="fa-intro">${article.intro.map(paragraphs).join("")}</div><div class="fa-takeaway"><p>${escapeHtml(article.takeaway)}</p></div>${steps}</article>
      </div>
      <section class="fa-start-panel" aria-labelledby="fa-start-heading"><div><p class="fa-kicker">Your first step</p><h2 id="fa-start-heading">${escapeHtml(article.closingTitle)}</h2><p>${escapeHtml(article.closing)}</p></div><div class="fa-start-action">${startLink(article.ctaButton || CTA, "fa-start-button")}<p class="fa-offer-note">${escapeHtml(article.offerNote)}</p></div></section>
      <aside class="fa-related" aria-label="Related guide"><p class="fa-kicker">Another way to begin</p><a href="${articlePath(related)}"><span>${escapeHtml(relatedTitle)}</span>${arrow}</a></aside>
    </main>
    <footer class="fa-footer"><p>&copy; ${new Date().getFullYear()} Nonprofit Board Builders, LLC.</p><nav aria-label="Legal links"><a href="/privacy-policy">Privacy policy</a><a href="/terms">Terms</a></nav></footer>
  </div>`;
}

module.exports = { renderArticleMarkup };
