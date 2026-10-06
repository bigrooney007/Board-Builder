# Blog generator in the original admin

Open `/admin?tab=blog`, or choose **Blog Post Generator** in `/admin`.

| Day | Topic | Call to action |
| --- | --- | --- |
| Monday | Board Recruitment | `/recruit` |
| Tuesday | Board Fundraising | `/board-fundraising-game` |
| Wednesday | Strategic Planning | `/strategic-planning` |
| Thursday | Board Recommitment | `/board-recommitment` |
| Friday | Joining Nonprofit Boards | `/join-a-board` |

Choose an article angle and its planned date, then **Generate Blog Post + Graphic**.
Each angle has a specific pain point, limiting belief and desired outcome. The fifth
topic speaks to prospective board members and invites them to the Board Applicant
Network. The four service topics speak to nonprofit leaders.

The draft retains its writing brief. Preview the article and cover, edit their wording,
and use **Publish Article**. Every published article has its own image, description,
shareable URL and correct service button. Published URLs stay stable after edits.
The date organizes the editorial calendar; Publish Article makes it public immediately.

The original posts remain in the same `blog_posts` collection. Older articles keep their
content and URLs. Their recruitment, fundraising and recommitment buttons resolve to
the current landing routes. Articles without a cover receive a cover using their own title.

## Editing the two fundraising guides

In the Admin Dashboard's **Blog** tab, **Edit Your Fundraising Guides** contains the
two public three-step articles. **Edit Guide** opens the title, headings, introduction,
three sections, closing invitation, button wording and sidebar text. Paragraphs are
separated by blank lines. The preview shows changes before saving.
**Save and Publish Guide** saves to the existing `marketing_settings` collection and
updates the public page immediately. No frontend rebuild or GitHub sync is needed for
subsequent wording edits. Page slugs and the `/board-fundraising/start` destination stay fixed.

Both React and the frontend HTML server load the saved guide text. Search descriptions,
Open Graph metadata and featured blog cards also use it. Complete original copy remains
available if the content API is temporarily unreachable. The guide cover artwork remains
the original PNG; its accessible description is editable. `backend/fundraising_guides.json`
is the original fallback copy exported from `frontend/src/content/fundraisingArticles.js`.

## LinkedIn company page RSS

The public feed is **https://nonprofitboardbuilder.com/api/blog/feed.xml**. Copy it from
the Admin Blog tab and paste it into the existing RSS field on the LinkedIn company page.
LinkedIn manages its pickup and posting behavior. No LinkedIn credential is stored by this app.

The feed contains the latest 50 published articles, including the two fundraising guides.
Drafts and failed or archived articles stay private. Publishing an article adds it to the
feed on the next request. Each item supplies its title, description, full escaped article,
canonical link, category, original publication date and public cover image. Its GUID is the
permanent article URL, so editing text preserves that identity and publication date.
ETags allow conditional requests, and a cache lasts at most 60 seconds. Blog HTML advertises
the RSS source through an alternate link.

## Automatic weekday drafts

The admin's **Automatic weekday drafts** panel controls whether the backend prepares
the day's article at the saved time and timezone. It only runs Monday through Friday.
All automatic posts wait for review. The existing environment switch is honored until
an admin saves these settings. A topic and date can have only one post, including across
multiple workers; repeated Generate clicks open that post instead of paying for another.

Generation runs in a background task, with a four-minute limit and at most one corrective
model attempt. A failed or interrupted draft can be regenerated in the admin after five
minutes. This uses the existing Anthropic/Emergent AI configuration. Share text is generated
only when its own button is clicked. No article is emailed to subscribers by this feature.

## Graphics and previews

Each draft includes a short headline and supporting line specific to its argument.
The local Pillow renderer turns them into a 1200x630 PNG in the current brand palette.
The same graphic appears above the article and in Open Graph and Twitter metadata.
The bundled font and license make rendering reproducible without an image service.
The public image endpoint serves only published articles. Draft images require admin
authentication. Editing graphic wording changes the image URL's version automatically.

Initial HTML includes article metadata, BlogPosting structured data and the full readable
article, for all visitors and crawlers. `/api/blog/sitemap.xml` updates from published
posts, and robots.txt advertises it. A new article needs no frontend rebuild.

## Deploy into the existing Emergent project

Sync the approved GitHub revision, preserving the production database, environment
and domain. No database migration or new service account is required.

Run the normal backend compilation and frontend build. The current `yarn start`
configuration already installs the dynamic blog HTML handler. It uses
`BLOG_API_ORIGIN`, then `REACT_APP_BACKEND_URL`, then `http://127.0.0.1:8001`
to read public content. Set BLOG_API_ORIGIN only if the server needs a different
internal backend origin. This is a server-only URL and must not include `/api`.

If the host serves the compiled build instead of using `yarn start`, run `yarn serve`
after building. Keep the existing reverse-proxy routing for `/api` to FastAPI and
forward frontend requests to this server. A static-only SPA fallback cannot supply
fresh metadata for posts published after a build. The production frontend server
supports dynamic blog HTML and the seven existing prerendered landing routes.

After deployment and publishing a draft:

```sh
cd frontend
node scripts/verify-blog-seo.cjs https://nonprofitboardbuilder.com
node scripts/verify-landing-seo.cjs https://nonprofitboardbuilder.com
```

The blog checker reads HTTP responses without executing client JavaScript and checks
one published article in each available category. It checks image dimensions and
the category's call to action. Sharing services may need to refresh an older cached
preview after a published article is edited.

Offline checks: `backend/tests/test_blog_workstation.py`,
`frontend/src/admin/BlogAdminSection.test.jsx`, `frontend/src/admin/FundraisingGuideAdmin.test.jsx`,
`frontend/src/pages/FundraisingArticlePage.test.jsx` and `frontend/src/seo/BlogMetadata.test.jsx`.
Tests mock the model and delivery boundaries and do not alter live content.
